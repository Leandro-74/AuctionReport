"""Gera o relatório final no formato visual do modelo da prefeitura."""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

from .models import Asset, Group, Lot, LotResult, ReportData, norm
from .money import format_brl

# ---------------------------------------------------------------------------
# Aparência do modelo
# ---------------------------------------------------------------------------

CINZA = "FFD9D9D9"
VERDE = "FFE2EFDA"
VERMELHO = "FFFCE4D6"
BORDA_FINA = Side(style="thin")
BORDA = Border(left=BORDA_FINA, right=BORDA_FINA, top=BORDA_FINA, bottom=BORDA_FINA)
FONTE_TITULO = Font(name="Calibri", size=13, bold=True)
FONTE_SECAO = Font(name="Calibri", size=13, bold=True)
FONTE_CONTA = Font(name="Arial", size=10)
FONTE_CONTA_NEGRITO = Font(name="Arial", size=10, bold=True)
FONTE_DADOS = Font(name="Calibri", size=11)
FORMATO_MOEDA = '[$R$ -416]#,##0.00'

COLUNAS_PRINCIPAIS = [
    "Tipo de bem",
    "Código",
    "Conta Crédito",
    "Conta Débito",
    "Descrição",
    "Valor",
]
LARGURAS_PRINCIPAIS = [8.43, 10.13, 15.13, 15.13, 47.63, 17.0]
LARGURA_G = 7.63

COLUNAS_AUX = ["Tipo de bem", "Código", "Conta Débito", "Descrição", "Valor"]
LARGURAS_AUX = [8.43, 8.43, 18.88, 47.63, 17.0]

LARGURAS_CONTA = [14.38, 14.13, 54.63, 17.5]

TITULO_MUNICIPIO = "MUNICÍPIO DE EXEMPLO"
TITULO_SAUDE = "FUNDO MUNICIPAL DE SAÚDE"
TITULO_CONTA_MUNICIPIO = "MUNICIPIO DE EXEMPLO: CONTAS PARA DEPÓSITO"
TITULO_CONTA_SAUDE = "FUNDO MUNICIPAL DE SAUDE: CONTAS PARA DEPÓSITO"
CNPJ_MUNICIPIO = "00.000.000/0001-00"
CNPJ_SAUDE = "00.000.000/0001-01"

MARGEM = 1 / 2.54  # 1 cm, igual ao modelo


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------


def format_lots(lotes: list[Lot]) -> str:
    """``[4, 12]`` -> ``Lotes 04 e 12``; ``[14]`` -> ``Lote 14``."""
    numeros = [lote.numero for lote in sorted(lotes, key=lambda l: l.numero_int)]
    if not numeros:
        return "Lotes"
    if len(numeros) == 1:
        return f"Lote {numeros[0]}"
    if len(numeros) == 2:
        return f"Lotes {numeros[0]} e {numeros[1]}"
    return f"Lotes {', '.join(numeros[:-1])} e {numeros[-1]}"


def _sheet_name(base: str, usados: set[str]) -> str:
    nome = re.sub(r"[\[\]:*?/\\]", " ", base or "Relatório")
    nome = " ".join(nome.split()).strip()[:31] or "Relatório"
    candidato = nome
    contador = 2
    while candidato.upper() in usados:
        sufixo = f" ({contador})"
        candidato = nome[: 31 - len(sufixo)] + sufixo
        contador += 1
    usados.add(candidato.upper())
    return candidato


def _fill(ws, row: int, end_col: int, cor: str = CINZA) -> None:
    for col in range(1, end_col + 1):
        ws.cell(row=row, column=col).fill = PatternFill("solid", fgColor=cor)


def _merge(
    ws,
    row: int,
    text: str,
    font: Font,
    *,
    fill: str | None = None,
    horizontal: str = "center",
    vertical: str = "center",
    wrap: bool = True,
    height: float | None = None,
    end_col: int = 6,
) -> None:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=end_col)
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = font
    cell.alignment = Alignment(
        horizontal=horizontal, vertical=vertical, wrap_text=wrap
    )
    if fill:
        _fill(ws, row, end_col, fill)
    if height is not None:
        ws.row_dimensions[row].height = height


def _header(ws, row: int, colunas: list[str], money_col: int) -> None:
    """Cabeçalho do modelo: sem alinhamento definido, fonte 13, fundo cinza."""
    for col, titulo in enumerate(colunas, start=1):
        cell = ws.cell(row=row, column=col, value=titulo)
        cell.font = FONTE_TITULO
        cell.fill = PatternFill("solid", fgColor=CINZA)
        cell.border = BORDA
        if col == money_col:
            cell.number_format = FORMATO_MOEDA


def _data(ws, row: int, valores: list[object], money_col: int) -> None:
    """Linha de dados do modelo: fonte 11, borda fina e quebra de texto."""
    for col, value in enumerate(valores, start=1):
        cell = ws.cell(row=row, column=col, value=value)
        cell.font = FONTE_DADOS
        cell.border = BORDA
        cell.alignment = Alignment(wrap_text=True)
        if col == money_col:
            cell.number_format = FORMATO_MOEDA


def _setup_page(ws, *, fit: bool = False) -> None:
    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_margins.left = MARGEM
    ws.page_margins.right = MARGEM
    ws.page_margins.top = MARGEM
    ws.page_margins.bottom = MARGEM
    ws.page_margins.header = 0
    ws.page_margins.footer = 0
    if fit:
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)


def _codigo(valor: str):
    return int(valor) if valor.isdigit() else valor


# ---------------------------------------------------------------------------
# Abas principais (por grupo/secretaria)
# ---------------------------------------------------------------------------


def _write_group_sheet(
    wb, grupo: Group, resultados: list[LotResult], usados: set[str]
) -> None:
    ws = wb.create_sheet(_sheet_name(grupo.aba, usados))
    for col, largura in enumerate(LARGURAS_PRINCIPAIS, start=1):
        ws.column_dimensions[get_column_letter(col)].width = largura
    ws.column_dimensions["G"].width = LARGURA_G

    lotes = [r.lote for r in resultados]
    total = sum((r.lote.valor for r in resultados), Decimal("0.00"))

    _merge(ws, 1, grupo.titulo, FONTE_TITULO, fill=CINZA, wrap=False, height=21.75)
    subtitulo = f"{grupo.subtitulo} ({format_lots(lotes)})"
    _merge(ws, 2, subtitulo, FONTE_TITULO, fill=CINZA, height=None)
    ws.row_dimensions[3].height = 21.75

    _merge(
        ws,
        4,
        grupo.conta,
        FONTE_CONTA_NEGRITO,
        fill=CINZA,
        horizontal=None,
        vertical=None,
        wrap=False,
        height=15,
    )
    _merge(
        ws,
        5,
        f"Agência: {grupo.agencia}",
        FONTE_CONTA,
        horizontal=None,
        vertical=None,
        wrap=False,
        height=15,
    )
    _merge(
        ws,
        6,
        f"Conta Corrente: {grupo.conta_corrente}",
        FONTE_CONTA,
        horizontal=None,
        vertical=None,
        wrap=False,
        height=15,
    )
    _merge(
        ws,
        7,
        f"CNPJ: {grupo.cnpj}",
        FONTE_CONTA,
        horizontal=None,
        vertical=None,
        wrap=False,
        height=15,
    )
    _merge(
        ws,
        8,
        f"Valor total dos lotes: {format_brl(total)}",
        FONTE_CONTA,
        horizontal="right",
        vertical=None,
        wrap=False,
        height=15,
    )
    ws.row_dimensions[9].height = 21.75

    secoes: "OrderedDict[str, list[LotResult]]" = OrderedDict()
    for resultado in sorted(resultados, key=lambda r: r.lote.numero_int):
        secoes.setdefault(resultado.lote.secao, []).append(resultado)

    row = 10
    for secao, resultados_secao in secoes.items():
        lotes_secao = [r.lote for r in resultados_secao]
        _merge(
            ws,
            row,
            f"{secao} ({format_lots(lotes_secao)})",
            FONTE_SECAO,
            fill=CINZA,
        )
        row += 1
        _header(ws, row, COLUNAS_PRINCIPAIS, 6)
        row += 1
        for resultado in resultados_secao:
            for indice, bem in enumerate(resultado.bens):
                _data(
                    ws,
                    row,
                    [
                        bem.tipo or "Bens Móveis",
                        _codigo(bem.codigo),
                        _codigo(bem.conta_credito),
                        _codigo(bem.conta_debito),
                        bem.descricao,
                        float(resultado.valores[indice]),
                    ],
                    6,
                )
                row += 1
        row += 1

    _setup_page(ws)


# ---------------------------------------------------------------------------
# Abas auxiliares por categoria
# ---------------------------------------------------------------------------


@dataclass
class ItemView:
    bem: Asset
    valor: Decimal
    lote: Lot
    grupo: Group


@dataclass
class ViewSpec:
    aba: str
    titulo: str
    subtitulo: str
    itens: list[ItemView]
    completo: bool = False  # True = 6 colunas (com Conta Crédito), como "Todos os Veículos"


def _is_saude(grupo: Group) -> bool:
    texto = norm(grupo.nome)
    return (
        "SAUDE" in texto
        or "FUNDO" in texto
        or grupo.cnpj.strip() == CNPJ_SAUDE
    )


def _itens(data: ReportData) -> list[ItemView]:
    grupos = {norm(g.nome): g for g in data.grupos}
    itens: list[ItemView] = []
    for resultado in data.resultados:
        grupo = grupos.get(norm(resultado.lote.grupo))
        if grupo is None:
            continue
        for indice, bem in enumerate(resultado.bens):
            itens.append(
                ItemView(bem, resultado.valores[indice], resultado.lote, grupo)
            )
    return itens


def _lotes_de(itens: list[ItemView]) -> list[Lot]:
    vistos: dict[str, Lot] = {}
    for item in itens:
        vistos[item.lote.numero] = item.lote
    return sorted(vistos.values(), key=lambda lote: lote.numero_int)


def _grupos_de(itens: list[ItemView]) -> list[str]:
    nomes: list[str] = []
    vistos: set[str] = set()
    for item in itens:
        chave = norm(item.grupo.nome)
        if chave not in vistos:
            vistos.add(chave)
            nomes.append(item.grupo.nome)
    return nomes


def _nome_grupos(itens: list[ItemView]) -> str:
    nomes = _grupos_de(itens)
    if set(nomes) == {"Prefeitura", "Educação"}:
        return "Prefeitura e Sec. da Educação"
    if len(nomes) == 1:
        return nomes[0]
    if len(nomes) == 2:
        return f"{nomes[0]} e {nomes[1]}"
    return ", ".join(nomes[:-1]) + f" e {nomes[-1]}"


def _subtitulo_lote_ou_categoria(itens: list[ItemView], fallback: str) -> str:
    lotes = _lotes_de(itens)
    if len(lotes) == 1:
        lote = lotes[0]
        texto = (lote.descricao_pl or lote.secao).strip().rstrip(".")
        return f"LOTE {lote.numero}: {texto}."
    return f"{fallback} ({format_lots(lotes)})"


def _view_specs(itens: list[ItemView]) -> list[ViewSpec]:
    specs: list[ViewSpec] = []

    veiculos = [i for i in itens if i.bem.categoria == "Veículos"]
    if veiculos:
        specs.append(
            ViewSpec(
                "Relatório Todos os Veículos",
                TITULO_MUNICIPIO,
                f"Veículos Leiloados ({format_lots(_lotes_de(veiculos))})",
                veiculos,
                completo=True,
            )
        )
        municipais = [i for i in veiculos if not _is_saude(i.grupo)]
        saude = [i for i in veiculos if _is_saude(i.grupo)]
        # Só cria as visões separadas quando há os dois lados; caso contrário
        # "Todos os Veículos" já cobre a lista.
        if municipais and saude:
            specs.append(
                ViewSpec(
                    "Relatório Veículos",
                    TITULO_MUNICIPIO,
                    f"Veículos referentes aos Lotes da {_nome_grupos(municipais)} "
                    f"({format_lots(_lotes_de(municipais))})",
                    municipais,
                )
            )
            specs.append(
                ViewSpec(
                    "Relatório Veículos Hospital",
                    TITULO_SAUDE,
                    "Veículos referentes aos Lotes do Fundo Municipal de Saúde "
                    f"({format_lots(_lotes_de(saude))})",
                    saude,
                )
            )

    municipais_moveis = [
        i
        for i in itens
        if i.bem.categoria == "Mobiliário" and not _is_saude(i.grupo)
    ]
    if municipais_moveis:
        specs.append(
            ViewSpec(
                "Relatório Mobiliário em Geral",
                TITULO_MUNICIPIO,
                _subtitulo_lote_ou_categoria(
                    municipais_moveis, "Mobiliário em Geral"
                ),
                municipais_moveis,
            )
        )

    saude_moveis = [
        i
        for i in itens
        if _is_saude(i.grupo) and i.bem.categoria != "Veículos"
    ]
    if saude_moveis:
        specs.append(
            ViewSpec(
                "Relatório Mobiliário em Geral H",
                TITULO_SAUDE,
                _subtitulo_lote_ou_categoria(
                    saude_moveis, "Equipamentos e mobiliários hospitalares em geral"
                ),
                saude_moveis,
            )
        )

    municipais_info = [
        i
        for i in itens
        if i.bem.categoria == "Informática" and not _is_saude(i.grupo)
    ]
    if municipais_info:
        specs.append(
            ViewSpec(
                "Relatório Itens de Informática",
                TITULO_MUNICIPIO,
                _subtitulo_lote_ou_categoria(
                    municipais_info, "Equipamentos de Informática"
                ),
                municipais_info,
            )
        )

    categorias_cobertas = {"Veículos", "Mobiliário", "Informática"}
    outros = [
        i
        for i in itens
        if not _is_saude(i.grupo)
        and i.bem.categoria not in categorias_cobertas
    ]
    if outros:
        specs.append(
            ViewSpec(
                "Relatório Outros Bens",
                TITULO_MUNICIPIO,
                f"Outros bens ({format_lots(_lotes_de(outros))})",
                outros,
            )
        )

    return specs


def _write_view_sheet(wb, spec: ViewSpec, usados: set[str]) -> None:
    ws = wb.create_sheet(_sheet_name(spec.aba, usados))
    colunas = COLUNAS_PRINCIPAIS if spec.completo else COLUNAS_AUX
    larguras = LARGURAS_PRINCIPAIS if spec.completo else LARGURAS_AUX
    money_col = 6 if spec.completo else 5
    end_col = 6 if spec.completo else 5

    for col, largura in enumerate(larguras, start=1):
        ws.column_dimensions[get_column_letter(col)].width = largura
    ws.column_dimensions["G"].width = LARGURA_G

    _merge(
        ws,
        1,
        spec.titulo,
        FONTE_TITULO,
        fill=CINZA,
        wrap=False,
        height=21.75,
        end_col=end_col,
    )
    _merge(
        ws,
        2,
        spec.subtitulo,
        FONTE_TITULO,
        fill=CINZA,
        wrap=True,
        end_col=end_col,
    )
    ws.row_dimensions[3].height = 21.75

    _header(ws, 4, colunas, money_col)
    row = 5
    for item in spec.itens:
        if spec.completo:
            valores = [
                item.bem.tipo or "Bens Móveis",
                _codigo(item.bem.codigo),
                _codigo(item.bem.conta_credito),
                _codigo(item.bem.conta_debito),
                item.bem.descricao,
                float(item.valor),
            ]
        else:
            valores = [
                item.bem.tipo or "Bens Móveis",
                _codigo(item.bem.codigo),
                _codigo(item.bem.conta_debito),
                item.bem.descricao,
                float(item.valor),
            ]
        _data(ws, row, valores, money_col)
        row += 1

    _setup_page(ws)


# ---------------------------------------------------------------------------
# Abas de contas para depósito
# ---------------------------------------------------------------------------


def _write_account_sheet(wb, chave: str, grupos: list[tuple[Group, Decimal]], usados: set[str]) -> None:
    cnpj = grupos[0][0].cnpj.strip() if grupos else ""
    if cnpj == CNPJ_MUNICIPIO:
        aba = "Conta Município"
        titulo = TITULO_CONTA_MUNICIPIO
    elif cnpj == CNPJ_SAUDE:
        aba = "Conta Fundo Municipal de Saude"
        titulo = TITULO_CONTA_SAUDE
    elif len(grupos) == 1:
        aba = f"Conta {grupos[0][0].nome}"
        titulo = f"{grupos[0][0].nome.upper()}: CONTAS PARA DEPÓSITO"
    else:
        aba = f"Conta {cnpj}" if cnpj else f"Conta {chave}"
        titulo = f"CONTAS PARA DEPÓSITO - {cnpj or chave}"

    ws = wb.create_sheet(_sheet_name(aba, usados))
    for col, largura in enumerate(LARGURAS_CONTA, start=1):
        ws.column_dimensions[get_column_letter(col)].width = largura
    ws.column_dimensions["E"].width = LARGURA_G

    _merge(
        ws,
        1,
        titulo,
        FONTE_TITULO,
        fill=CINZA,
        wrap=False,
        height=21.75,
        end_col=4,
    )

    row = 3
    for grupo, total in grupos:
        _merge(
            ws,
            row,
            grupo.conta,
            FONTE_CONTA_NEGRITO,
            fill=CINZA,
            horizontal=None,
            vertical=None,
            wrap=False,
            height=15,
            end_col=4,
        )
        row += 1
        for texto in (
            f"Agência: {grupo.agencia}",
            f"Conta Corrente: {grupo.conta_corrente}",
            f"CNPJ: {grupo.cnpj}",
        ):
            _merge(
                ws,
                row,
                texto,
                FONTE_CONTA,
                horizontal=None,
                vertical=None,
                wrap=False,
                height=15,
                end_col=4,
            )
            row += 1
        _merge(
            ws,
            row,
            f"Valor total dos lotes: {format_brl(total)}",
            FONTE_CONTA,
            horizontal="right",
            vertical=None,
            wrap=False,
            height=15,
            end_col=4,
        )
        row += 2

    _setup_page(ws)


def _write_account_sheets(wb, data: ReportData, usados: set[str]) -> None:
    entidades: "OrderedDict[str, list[tuple[Group, Decimal]]]" = OrderedDict()
    for grupo in sorted(data.grupos, key=lambda g: (g.ordem, g.nome)):
        resultados = [
            r for r in data.resultados if norm(r.lote.grupo) == norm(grupo.nome)
        ]
        if not resultados:
            continue
        total = sum((r.lote.valor for r in resultados), Decimal("0.00"))
        chave = grupo.cnpj.strip() or f"grupo:{grupo.nome}"
        entidades.setdefault(chave, []).append((grupo, total))

    for chave, grupos in entidades.items():
        _write_account_sheet(wb, chave, grupos, usados)


# ---------------------------------------------------------------------------
# Resumo opcional
# ---------------------------------------------------------------------------


def _summary_title(ws, row: int, text: str) -> None:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = FONTE_SECAO
    cell.fill = PatternFill("solid", fgColor=CINZA)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[row].height = 22


def _summary_header(ws, row: int, headers: list[str]) -> None:
    for col, titulo in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col, value=titulo)
        cell.font = FONTE_TITULO
        cell.fill = PatternFill("solid", fgColor=CINZA)
        cell.border = BORDA
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 24


def _write_summary(wb, data: ReportData, usados: set[str]) -> None:
    ws = wb.create_sheet(_sheet_name("Resumo", usados))
    larguras = [10, 16, 42, 10, 18, 18, 16, 14]
    for col, largura in enumerate(larguras, start=1):
        ws.column_dimensions[get_column_letter(col)].width = largura

    _summary_title(ws, 1, "RESUMO DO LEILÃO")
    ws.merge_cells("A2:H2")
    nota = ws.cell(
        row=2,
        column=1,
        value="Valores rateados em duas casas decimais; a diferença vai para o último bem de cada lote.",
    )
    nota.font = Font(name="Calibri", size=10, italic=True)
    nota.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 10

    _summary_title(ws, 4, "CONTAS E TOTAIS POR GRUPO")
    _summary_header(
        ws,
        5,
        [
            "Grupo",
            "Conta de depósito",
            "Agência",
            "Conta Corrente",
            "CNPJ",
            "Qtd. bens",
            "Valor total",
        ],
    )

    row = 6
    total_geral = Decimal("0.00")
    total_bens = 0
    for grupo in sorted(data.grupos, key=lambda g: (g.ordem, g.nome)):
        resultados = [
            r for r in data.resultados if norm(r.lote.grupo) == norm(grupo.nome)
        ]
        if not resultados:
            continue
        quantidade = sum(len(r.bens) for r in resultados)
        total = sum((r.lote.valor for r in resultados), Decimal("0.00"))
        total_geral += total
        total_bens += quantidade
        valores = [
            grupo.nome,
            grupo.conta,
            grupo.agencia,
            grupo.conta_corrente,
            grupo.cnpj,
            quantidade,
            float(total),
        ]
        for col, value in enumerate(valores, start=1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.font = FONTE_DADOS
            cell.border = BORDA
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            if col == 7:
                cell.number_format = FORMATO_MOEDA
        row += 1

    for col, value in enumerate(
        ["TOTAL GERAL", "", "", "", "", total_bens, float(total_geral)], start=1
    ):
        cell = ws.cell(row=row, column=col, value=value)
        cell.font = Font(name="Calibri", size=11, bold=True)
        cell.border = BORDA
        cell.fill = PatternFill("solid", fgColor=CINZA)
        if col == 7:
            cell.number_format = FORMATO_MOEDA
    row += 2

    _summary_title(ws, row, "CONFERÊNCIA POR LOTE")
    row += 1
    _summary_header(
        ws,
        row,
        [
            "Lote",
            "Grupo",
            "Seção",
            "Qtd. bens",
            "Valor do lote",
            "Soma dos bens",
            "Diferença",
            "Situação",
        ],
    )
    row += 1
    for resultado in sorted(data.resultados, key=lambda r: r.lote.numero_int):
        diferenca = resultado.lote.valor - resultado.soma
        situacao = "OK" if resultado.fecha else "ERRO"
        valores = [
            resultado.lote.numero,
            resultado.lote.grupo,
            resultado.lote.secao,
            len(resultado.bens),
            float(resultado.lote.valor),
            float(resultado.soma),
            float(diferenca),
            situacao,
        ]
        for col, value in enumerate(valores, start=1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.font = FONTE_DADOS
            cell.border = BORDA
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            if col in (5, 6, 7):
                cell.number_format = FORMATO_MOEDA
            if col == 8:
                cell.fill = PatternFill(
                    "solid", fgColor=VERDE if situacao == "OK" else VERMELHO
                )
                cell.alignment = Alignment(horizontal="center", vertical="center")
        row += 1

    for col, value in enumerate(
        ["TOTAL", "", "", total_bens, float(total_geral), float(total_geral), 0.0, ""],
        start=1,
    ):
        cell = ws.cell(row=row, column=col, value=value)
        cell.font = Font(name="Calibri", size=11, bold=True)
        cell.border = BORDA
        cell.fill = PatternFill("solid", fgColor=CINZA)
        if col in (5, 6, 7):
            cell.number_format = FORMATO_MOEDA

    _setup_page(ws, fit=True)


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------


def gerar_relatorio(
    data: ReportData,
    path: str | Path,
    incluir_resumo: bool = False,
) -> Path:
    """Grava o relatório final no formato do modelo.

    A aba Resumo é opcional; por padrão o arquivo contém apenas as abas do
    modelo (principais, auxiliares e contas).
    """
    if data.erros:
        linhas = "\n".join(f"- {issue}" for issue in data.erros)
        raise ValueError(f"Corrija os erros antes de gerar o relatório:\n{linhas}")
    if not data.resultados:
        raise ValueError("O leilão não tem lotes com bens para exportar.")

    path = Path(path)
    wb = Workbook()
    wb.remove(wb.active)
    usados: set[str] = set()

    for grupo in sorted(data.grupos, key=lambda g: (g.ordem, g.nome)):
        resultados = [
            r for r in data.resultados if norm(r.lote.grupo) == norm(grupo.nome)
        ]
        if not resultados:
            continue
        _write_group_sheet(wb, grupo, resultados, usados)

    itens = _itens(data)
    for spec in _view_specs(itens):
        _write_view_sheet(wb, spec, usados)

    _write_account_sheets(wb, data, usados)

    if incluir_resumo:
        _write_summary(wb, data, usados)

    wb.properties.title = "Relatório de Bens para Leilão"
    wb.properties.creator = "AuctionReport"
    wb.save(path)
    return path
