"""Monta e lê a planilha de entrada editável (Bens, Lotes e Grupos)."""

from __future__ import annotations

import copy
import re
import shutil
from collections import Counter
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from .config import (
    AGENCIA,
    CNPJ_MUNICIPIO,
    CNPJ_SAUDE,
    CONTA_CORRENTE_PREFEITURA,
    CONTA_CORRENTE_SAUDE,
    MUNICIPIO,
    SUBTITULO_PREFEITURA,
    SUBTITULO_SAUDE,
)
from .models import Asset, Group, Issue, LawLot, Lot, LotResult, ReportData, norm
from .money import format_brl, parse_money, distribute
from .pdfs import PdfError, parse_asset_report, parse_law

CINZA = "FFD9D9D9"
AMARELO = "FFFFF2CC"
VERDE = "FFE2EFDA"
VERMELHO = "FFFCE4D6"
BORDA_FINA = Side(style="thin", color="000000")
BORDA = Border(left=BORDA_FINA, right=BORDA_FINA, top=BORDA_FINA, bottom=BORDA_FINA)
FONTE_TITULO = Font(name="Calibri", size=13, bold=True)
FONTE_CONTA = Font(name="Arial", size=10)
FONTE_CONTA_NEGRITO = Font(name="Arial", size=10, bold=True)
FONTE_DADOS = Font(name="Calibri", size=11)
FORMATO_MOEDA = '[$R$ -416]#,##0.00'

DEFAULT_GROUPS: dict[str, Group] = {
    "Prefeitura": Group(
        nome="Prefeitura",
        aba="Relatório Bens da Prefeitura",
        ordem=1,
        titulo=MUNICIPIO,
        subtitulo=SUBTITULO_PREFEITURA,
        conta="Conta de depósito para lotes da Prefeitura",
        agencia=AGENCIA,
        conta_corrente=CONTA_CORRENTE_PREFEITURA,
        cnpj=CNPJ_MUNICIPIO,
    ),
    "Saúde": Group(
        nome="Saúde",
        aba="Relatório Bens da Saúde",
        ordem=2,
        titulo=MUNICIPIO,
        subtitulo=SUBTITULO_SAUDE,
        conta="Conta de depósito para lotes da Saúde",
        agencia=AGENCIA,
        conta_corrente=CONTA_CORRENTE_SAUDE,
        cnpj=CNPJ_SAUDE,
    ),
}


def normalize_source(label: str) -> str:
    texto = norm(label)
    if "SAUDE" in texto:
        return "Saúde"
    if "PREFEITURA" in texto or "MUNICIPIO" in texto:
        return "Prefeitura"
    return label.strip() or "Prefeitura"


def group_for_source(source: str) -> Group:
    nome = normalize_source(source)
    if nome in DEFAULT_GROUPS:
        return copy.deepcopy(DEFAULT_GROUPS[nome])
    return Group(
        nome=nome,
        aba=f"Relatório Bens da {nome}",
        ordem=99,
        subtitulo=nome,
        conta=f"Conta de depósito para lotes da {nome}",
        agencia=AGENCIA,
    )


def normalize_lot(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if text.isdigit():
        return text.zfill(2)
    return text


def text_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(Decimal(str(value)), "f")
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def number_or_text(value: str):
    text = (value or "").strip()
    if text.isdigit() and len(text) <= 15:
        return int(text)
    return text


def _column_key(name: object) -> str:
    text = norm(text_cell(name)).lower()
    text = text.replace("nº", " ").replace("n°", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    aliases = {
        "n do lote": "lote",
        "numero do lote": "lote",
        "num lote": "lote",
        "valor": "valor da venda",
        "valor do lote": "valor da venda",
        "valor arrematado": "valor da venda",
        "secretaria": "grupo",
        "titulo da secao": "secao",
        "patrimonio": "codigo",
        "conta de deposito": "conta de deposito",
        "valor avaliado": "valor avaliado pl",
        "valor avaliado pl": "valor avaliado pl",
        "descricao do pl": "descricao do pl",
    }
    return aliases.get(text, text)


def _read_sheet(ws) -> tuple[dict[str, int], list[dict[str, object]]]:
    """Lê uma aba com cabeçalho na linha 1 e devolve colunas + linhas."""
    header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())
    columns: dict[str, int] = {}
    for index, value in enumerate(header_row):
        if value is None:
            continue
        key = _column_key(value)
        if key:
            columns[key] = index
    rows: list[dict[str, object]] = []
    for row_number, values in enumerate(
        ws.iter_rows(min_row=2, values_only=True), start=2
    ):
        if values is None:
            continue
        if not any(value is not None and str(value).strip() for value in values):
            continue
        row = {
            key: values[index] if index < len(values) else None
            for key, index in columns.items()
        }
        row["_linha"] = row_number
        rows.append(row)
    return columns, rows


def _required(columns: dict[str, int], required: list[str], sheet: str) -> None:
    faltando = [name for name in required if name not in columns]
    if faltando:
        raise ValueError(
            f"Aba '{sheet}' sem as colunas obrigatórias: {', '.join(faltando)}. "
            "Use o modelo gerado pela ferramenta."
        )


def _default_headers() -> dict[str, list[str]]:
    return {
        "Grupos": [
            "Grupo",
            "Aba",
            "Ordem",
            "Título",
            "Subtítulo",
            "Conta de depósito",
            "Agência",
            "Conta Corrente",
            "CNPJ",
        ],
        "Lotes": [
            "Lote",
            "Valor da venda",
            "Grupo",
            "Seção",
            "Valor avaliado (PL)",
            "Descrição do PL",
            "Observação",
        ],
        "Bens": [
            "Lote",
            "Tipo de bem",
            "Código",
            "Conta Crédito",
            "Conta Débito",
            "Descrição",
            "Valor Contábil",
            "Origem",
            "Categoria",
            "Observação",
        ],
    }


def _write_header(ws, headers: list[str], widths: list[int]) -> None:
    for col, (title, width) in enumerate(zip(headers, widths), start=1):
        cell = ws.cell(row=1, column=col, value=title)
        cell.font = FONTE_TITULO
        cell.fill = PatternFill("solid", fgColor=CINZA)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDA
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.row_dimensions[1].height = 28
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"


def _style_data_rows(ws, first_row: int, last_row: int, money_columns: set[int]) -> None:
    for row in ws.iter_rows(min_row=first_row, max_row=last_row):
        for cell in row:
            cell.font = FONTE_DADOS
            cell.border = BORDA
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            if cell.column in money_columns:
                cell.number_format = FORMATO_MOEDA
                cell.alignment = Alignment(horizontal="right", vertical="center")


def _add_text(ws, row: int, text: str, bold: bool = False, size: int = 11) -> None:
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = Font(name="Calibri", size=size, bold=bold)
    cell.alignment = Alignment(wrap_text=True, vertical="top")


LEIA_ME = [
    ("COMO USAR ESTA PLANILHA", True),
    ("", False),
    (
        "1. Aba BENS: cada linha é um bem. A coluna Lote diz em qual lote ele entra. "
        "Se a coluna Lote ficar vazia, o bem é ignorado. Use a lista suspensa ou digite o número.",
        False,
    ),
    (
        "2. Aba LOTES: cada linha é um lote. Preencha 'Valor da venda' com o valor arrematado. "
        "Enquanto o leilão não acontece, o valor avaliado do projeto de lei é usado como referência.",
        False,
    ),
    (
        "3. A coluna Grupo decide em qual aba do relatório o lote aparece. A coluna Seção vira o "
        "título da seção; lotes com a mesma Seção e o mesmo Grupo ficam juntos, por exemplo "
        "'Veículos (Lotes 01, 03 e 09)'.",
        False,
    ),
    (
        "4. Aba GRUPOS: dados de cada aba (título, conta de depósito, agência, conta corrente, CNPJ). "
        "Para criar uma nova aba, acrescente uma linha aqui e use esse nome na coluna Grupo dos lotes.",
        False,
    ),
    ("", False),
    ("COMO O VALOR É DIVIDIDO", True),
    (
        "O valor do lote é dividido igualmente entre os bens. Todas as parcelas ficam com no máximo "
        "duas casas decimais. O que sobra da divisão vai para o último bem do lote, então a soma "
        "fecha exatamente o valor do lote. Exemplo: R$ 50,00 em 211 bens = 210 x R$ 0,23 e o último "
        "com R$ 1,70.",
        False,
    ),
    ("", False),
    ("COMO GERAR O RELATÓRIO", True),
    (
        "No terminal, dentro desta pasta, execute:  python -m leilao gerar leilao_entrada.xlsx",
        False,
    ),
    (
        "Ou dê dois cliques em iniciar.bat e escolha a opção 2. O relatório final será criado em "
        "relatorio_leilao.xlsx.",
        False,
    ),
    ("", False),
    ("DICAS", True),
    (
        "• As colunas Conta Crédito e Conta Débito podem ficar vazias; preencha se o relatório "
        "precisar delas.",
        False,
    ),
    (
        "• Linhas destacadas em amarelo na aba BENS estão sem lote e não entram no relatório.",
        False,
    ),
    (
        "• A aba AVISOS (quando existir) lista bens sem lote, lotes sem bens e outras "
        "pendências da importação. A distribuição automática dos lotes é uma sugestão: "
        "confira antes de gerar o relatório.",
        False,
    ),
    (
        "• A aba Resumo do relatório final mostra a conferência lote a lote: valor do lote, soma "
        "dos bens e diferença.",
        False,
    ),
]


def _ordem_bem(bem: Asset):
    """Ordena a aba Bens por lote; bens sem lote ficam no fim."""
    lote = normalize_lot(bem.lote)
    if not lote:
        return (2, 0, "", bem.row)
    if lote.isdigit():
        return (0, int(lote), "", bem.row)
    return (1, 0, lote, bem.row)


def write_entrada(
    path: str | Path,
    grupos: list[Group],
    lotes: list[Lot],
    bens: list[Asset],
    avisos: list[Issue] | None = None,
) -> Path:
    """Grava a planilha de entrada editável."""
    path = Path(path)
    if path.exists():
        # Guarda a versão anterior antes de sobrescrever, para não perder
        # lotes/valores que o usuário já tenha preenchido.
        shutil.copy2(path, path.with_name(f"{path.stem}.backup{path.suffix}"))
    wb = Workbook()
    wb.remove(wb.active)

    ws_leia = wb.create_sheet("Leia-me")
    ws_leia.column_dimensions["A"].width = 110
    for row, (text, bold) in enumerate(LEIA_ME, start=1):
        _add_text(ws_leia, row, text, bold=bold, size=12 if bold else 11)
        ws_leia.row_dimensions[row].height = 18 if not text else None
    ws_leia.sheet_view.showGridLines = False

    headers = _default_headers()

    ws_grupos = wb.create_sheet("Grupos")
    _write_header(ws_grupos, headers["Grupos"], [16, 34, 8, 30, 38, 46, 28, 16, 24])
    for row, grupo in enumerate(sorted(grupos, key=lambda g: (g.ordem, g.nome)), start=2):
        values = [
            grupo.nome,
            grupo.aba,
            grupo.ordem,
            grupo.titulo,
            grupo.subtitulo,
            grupo.conta,
            grupo.agencia,
            grupo.conta_corrente,
            grupo.cnpj,
        ]
        for col, value in enumerate(values, start=1):
            ws_grupos.cell(row=row, column=col, value=value)
    _style_data_rows(ws_grupos, 2, max(2, ws_grupos.max_row), set())
    ws_grupos.auto_filter.ref = f"A1:I{max(1, ws_grupos.max_row)}"

    ws_lotes = wb.create_sheet("Lotes")
    _write_header(
        ws_lotes,
        headers["Lotes"],
        [10, 20, 16, 55, 20, 65, 35],
    )
    for row, lote in enumerate(sorted(lotes, key=lambda l: l.numero_int), start=2):
        values = [
            lote.numero,
            float(lote.valor),
            lote.grupo,
            lote.secao,
            float(lote.valor_avaliado) if lote.valor_avaliado is not None else None,
            lote.descricao_pl,
            lote.observacao,
        ]
        for col, value in enumerate(values, start=1):
            ws_lotes.cell(row=row, column=col, value=value)
    _style_data_rows(ws_lotes, 2, max(2, ws_lotes.max_row), {2, 5})
    ws_lotes.auto_filter.ref = f"A1:G{max(1, ws_lotes.max_row)}"

    ws_bens = wb.create_sheet("Bens")
    _write_header(
        ws_bens,
        headers["Bens"],
        [10, 15, 10, 17, 17, 70, 17, 14, 14, 35],
    )
    for row, bem in enumerate(sorted(bens, key=_ordem_bem), start=2):
        values = [
            bem.lote or None,
            bem.tipo,
            number_or_text(bem.codigo),
            number_or_text(bem.conta_credito) if bem.conta_credito else None,
            number_or_text(bem.conta_debito) if bem.conta_debito else None,
            bem.descricao,
            float(bem.valor_contabil) if bem.valor_contabil is not None else None,
            bem.origem,
            bem.categoria,
            bem.observacao,
        ]
        for col, value in enumerate(values, start=1):
            ws_bens.cell(row=row, column=col, value=value)
    _style_data_rows(ws_bens, 2, max(2, ws_bens.max_row), {7})
    ws_bens.auto_filter.ref = f"A1:J{max(1, ws_bens.max_row)}"

    if avisos:
        ws_avisos = wb.create_sheet("Avisos")
        _write_header(ws_avisos, ["Nível", "Aba", "Linha", "Mensagem"], [12, 14, 8, 100])
        for row, issue in enumerate(avisos, start=2):
            values = [
                issue.nivel.capitalize(),
                issue.aba or "",
                issue.linha or "",
                issue.mensagem,
            ]
            for col, value in enumerate(values, start=1):
                ws_avisos.cell(row=row, column=col, value=value)
        _style_data_rows(ws_avisos, 2, max(2, ws_avisos.max_row), set())
        ws_avisos.auto_filter.ref = f"A1:D{max(1, ws_avisos.max_row)}"
        ws_avisos.sheet_view.showGridLines = False

    # Validações e destaque de linhas sem lote.
    last_bens = max(2, ws_bens.max_row)
    last_lotes = max(2, ws_lotes.max_row)
    last_grupos = max(2, ws_grupos.max_row)
    dv_lote = DataValidation(
        type="list",
        formula1=f"='Lotes'!$A$2:$A${last_lotes}",
        allow_blank=True,
        showDropDown=False,
    )
    dv_lote.error = "Escolha um lote cadastrado na aba Lotes."
    dv_lote.errorTitle = "Lote não cadastrado"
    dv_lote.errorStyle = "warning"
    ws_bens.add_data_validation(dv_lote)
    dv_lote.add(f"A2:A{last_bens}")

    dv_grupo = DataValidation(
        type="list",
        formula1=f"='Grupos'!$A$2:$A${last_grupos}",
        allow_blank=True,
        showDropDown=False,
    )
    dv_grupo.error = "Escolha um grupo cadastrado na aba Grupos."
    dv_grupo.errorTitle = "Grupo não cadastrado"
    dv_grupo.errorStyle = "warning"
    ws_lotes.add_data_validation(dv_grupo)
    dv_grupo.add(f"C2:C{last_lotes}")

    dv_tipo = DataValidation(
        type="list", formula1='"Bens Móveis,Bens Imóveis"', allow_blank=True
    )
    dv_tipo.errorStyle = "warning"
    ws_bens.add_data_validation(dv_tipo)
    dv_tipo.add(f"B2:B{last_bens}")

    ws_bens.conditional_formatting.add(
        f"A2:J{last_bens}",
        FormulaRule(
            formula=["LEN($A2)=0"],
            fill=PatternFill("solid", fgColor=AMARELO),
            stopIfTrue=False,
        ),
    )

    wb.save(path)
    return path


def suggest_section(law: LawLot) -> str:
    if law.categoria == "Veículos":
        return "Veículos"
    if law.categoria == "Mobiliário":
        return "Mobiliário em Geral"
    if law.categoria == "Informática":
        return "Equipamentos de Informática"
    if law.categoria == "Hospitalar":
        texto = law.descricao.strip().rstrip(".")
        if "HOSPITALAR" in norm(texto):
            return texto
        return "Equipamentos e mobiliários hospitalares em geral"
    return "Bens em Geral"


def bulk_lots(law_lots: list[LawLot]) -> dict[str, LawLot | None]:
    """Lotes genéricos (sem patrimônio) por categoria."""
    result: dict[str, LawLot | None] = {}
    for category in ("Mobiliário", "Hospitalar", "Informática"):
        candidatos = [
            lot for lot in law_lots if lot.categoria == category and not lot.codigo_bem
        ]
        result[category] = candidatos[0] if len(candidatos) == 1 else None
    return result


def importar_pdfs(
    relatorios: list[tuple[str, str | Path]],
    pl: str | Path | None = None,
) -> tuple[list[Group], list[Lot], list[Asset], list[Issue]]:
    """Lê os PDFs, sugere os lotes e devolve os dados para a planilha de entrada."""
    issues: list[Issue] = []
    bens: list[Asset] = []
    origens: list[str] = []

    for label, pdf_path in relatorios:
        origem = normalize_source(label)
        origens.append(origem)
        try:
            encontrados = parse_asset_report(pdf_path, origem)
        except PdfError as exc:
            raise ValueError(str(exc)) from exc
        bens.extend(encontrados)
        issues.append(
            Issue(
                "aviso",
                f"{origem}: {len(encontrados)} bens lidos de {Path(pdf_path).name}.",
            )
        )

    law_lots: list[LawLot] = []
    if pl:
        try:
            law_lots = parse_law(pl)
        except PdfError as exc:
            raise ValueError(str(exc)) from exc
        issues.append(
            Issue("aviso", f"Projeto de lei: {len(law_lots)} lotes encontrados.")
        )

    # Associação automática.
    code_to_law = {
        lot.codigo_bem: lot for lot in law_lots if lot.codigo_bem is not None
    }
    codigos_bens: dict[str, list[Asset]] = {}
    for bem in bens:
        if bem.codigo:
            codigos_bens.setdefault(bem.codigo, []).append(bem)
    codigos_ambiguos = {
        codigo for codigo, itens in codigos_bens.items() if len(itens) > 1
    }
    bulk = bulk_lots(law_lots)
    for bem in bens:
        if bem.codigo in codigos_ambiguos:
            continue
        law = code_to_law.get(bem.codigo)
        if law is not None:
            bem.lote = law.numero
            continue
        if bem.categoria == "Veículos":
            continue
        if norm(bem.origem) == "SAUDE" and bulk.get("Hospitalar"):
            bem.lote = bulk["Hospitalar"].numero
        elif bem.categoria == "Informática" and bulk.get("Informática"):
            bem.lote = bulk["Informática"].numero
        elif bem.categoria == "Mobiliário" and bulk.get("Mobiliário"):
            bem.lote = bulk["Mobiliário"].numero
        elif bem.categoria == "Hospitalar" and bulk.get("Hospitalar"):
            bem.lote = bulk["Hospitalar"].numero

    for codigo in sorted(codigos_ambiguos & set(code_to_law)):
        law = code_to_law[codigo]
        origens = ", ".join(
            sorted({bem.origem or "sem origem" for bem in codigos_bens[codigo]})
        )
        issues.append(
            Issue(
                "aviso",
                f"O código {codigo} aparece em mais de um bem ({origens}); "
                f"o lote {law.numero} não foi aplicado automaticamente. "
                "Atribua o lote na edição.",
            )
        )

    # Lotes do projeto de lei que não vieram nos relatórios: cria uma linha
    # editável a partir da descrição do PL, para o relatório não ficar incompleto.
    for law in law_lots:
        if any(bem.lote == law.numero for bem in bens):
            continue
        if law.codigo_bem and law.codigo_bem in codigos_ambiguos:
            issues.append(
                Issue(
                    "aviso",
                    f"Lote {law.numero} (patrimônio {law.codigo_bem}) não foi "
                    "associado automaticamente porque o código aparece em mais "
                    "de um bem. Atribua o lote na edição.",
                )
            )
            continue
        grupo_padrao = (
            DEFAULT_GROUPS["Saúde"]
            if law.categoria == "Hospitalar"
            else DEFAULT_GROUPS["Prefeitura"]
        )
        descricao = re.sub(r"^\d+\s+", "", law.descricao).strip()
        bens.append(
            Asset(
                tipo="Bens Móveis",
                codigo=law.codigo_bem or "",
                descricao=descricao,
                origem=grupo_padrao.nome,
                categoria=law.categoria,
                lote=law.numero,
                observacao=(
                    "Criado a partir do projeto de lei; confira a descrição, "
                    "as contas e o valor contábil."
                ),
            )
        )
        issues.append(
            Issue(
                "aviso",
                f"Lote {law.numero} não tinha bens nos relatórios; criei uma linha "
                "a partir do projeto de lei. Confira a descrição e o valor contábil.",
            )
        )

    # Grupos que aparecem nos lotes.
    grupos: dict[str, Group] = {}
    for origem in origens:
        grupo = group_for_source(origem)
        grupos[grupo.nome] = grupo

    # Lotes a partir do projeto de lei.
    lotes: list[Lot] = []
    if law_lots:
        for law in law_lots:
            vinculados = [bem for bem in bens if bem.lote == law.numero]
            origens_lote = [bem.origem for bem in vinculados]
            contagem = Counter(origens_lote)
            if contagem:
                origem_predominante = contagem.most_common(1)[0][0]
                grupo = group_for_source(origem_predominante)
                if len(contagem) > 1:
                    issues.append(
                        Issue(
                            "aviso",
                            f"Lote {law.numero} tem bens de mais de uma origem "
                            f"({', '.join(sorted(contagem))}); confira o grupo.",
                        )
                    )
            else:
                grupo = DEFAULT_GROUPS["Prefeitura"]
                issues.append(
                    Issue(
                        "aviso",
                        f"Lote {law.numero} não tem bens nos relatórios. "
                        "Acrescente o bem na aba Bens ou remova o lote.",
                    )
                )
            grupos[grupo.nome] = grupo
            lotes.append(
                Lot(
                    numero=law.numero,
                    valor=law.valor_avaliado or Decimal("0.00"),
                    grupo=grupo.nome,
                    secao=suggest_section(law),
                    valor_avaliado=law.valor_avaliado,
                    descricao_pl=law.descricao,
                )
            )

    # Avisos de associação.
    sem_lote = [bem for bem in bens if not bem.lote]
    if sem_lote:
        exemplos = ", ".join(
            f"{bem.codigo} ({bem.origem})" for bem in sem_lote[:15]
        )
        restante = "" if len(sem_lote) <= 15 else f" e mais {len(sem_lote) - 15}"
        issues.append(
            Issue(
                "aviso",
                f"{len(sem_lote)} bem(ns) ficaram sem lote: {exemplos}{restante}. "
                "Atribua o lote na aba Bens.",
            )
        )
    for law in law_lots:
        if law.codigo_bem and not any(bem.lote == law.numero for bem in bens):
            issues.append(
                Issue(
                    "aviso",
                    f"Lote {law.numero} (patrimônio {law.codigo_bem}) não encontrou "
                    "o bem correspondente nos relatórios.",
                )
            )

    if not lotes:
        issues.append(
            Issue(
                "aviso",
                "Nenhum lote foi criado. Preencha a aba Lotes manualmente ou importe o projeto de lei.",
            )
        )

    grupos_ordenados = sorted(
        grupos.values(), key=lambda g: (g.ordem, g.nome)
    )
    return grupos_ordenados, lotes, bens, issues


def _read_grupos(ws) -> tuple[list[Group], list[Issue]]:
    columns, rows = _read_sheet(ws)
    _required(columns, ["grupo"], "Grupos")
    grupos: list[Group] = []
    issues: list[Issue] = []
    vistos: set[str] = set()
    for index, row in enumerate(rows, start=1):
        nome = text_cell(row.get("grupo")).strip()
        if not nome:
            continue
        chave = norm(nome)
        if chave in vistos:
            issues.append(
                Issue("erro", f"Grupo duplicado: {nome}.", linha=int(row["_linha"]), aba="Grupos")
            )
            continue
        vistos.add(chave)
        ordem = row.get("ordem")
        try:
            ordem_int = int(float(ordem)) if ordem not in (None, "") else index
        except (TypeError, ValueError):
            ordem_int = index
        grupos.append(
            Group(
                nome=nome,
                aba=text_cell(row.get("aba")).strip() or f"Relatório Bens da {nome}",
                ordem=ordem_int,
                titulo=text_cell(row.get("titulo")).strip() or MUNICIPIO,
                subtitulo=text_cell(row.get("subtitulo")).strip() or nome,
                conta=text_cell(row.get("conta de deposito")).strip()
                or f"Conta de depósito para lotes da {nome}",
                agencia=text_cell(row.get("agencia")).strip() or AGENCIA,
                conta_corrente=text_cell(row.get("conta corrente")).strip(),
                cnpj=text_cell(row.get("cnpj")).strip(),
            )
        )
    if not grupos:
        raise ValueError("A aba Grupos está vazia.")
    return grupos, issues


def _read_lotes(ws) -> tuple[list[Lot], list[Issue]]:
    columns, rows = _read_sheet(ws)
    _required(columns, ["lote", "valor da venda", "grupo"], "Lotes")
    lotes: list[Lot] = []
    issues: list[Issue] = []
    vistos: set[str] = set()
    for row in rows:
        numero = normalize_lot(row.get("lote"))
        if not numero:
            continue
        if numero in vistos:
            issues.append(
                Issue("erro", f"Lote duplicado: {numero}.", linha=int(row["_linha"]), aba="Lotes")
            )
            continue
        vistos.add(numero)
        valor_avaliado = None
        avaliado_bruto = row.get("valor avaliado pl")
        if avaliado_bruto not in (None, ""):
            try:
                valor_avaliado = parse_money(avaliado_bruto)
            except ValueError:
                issues.append(
                    Issue(
                        "aviso",
                        f"Valor avaliado inválido no lote {numero}; ignorado.",
                        linha=int(row["_linha"]),
                        aba="Lotes",
                    )
                )
        valor_bruto = row.get("valor da venda")
        valor = None
        if valor_bruto not in (None, ""):
            try:
                valor = parse_money(valor_bruto)
            except ValueError:
                issues.append(
                    Issue(
                        "erro",
                        f"Valor da venda inválido no lote {numero}: {valor_bruto!r}.",
                        linha=int(row["_linha"]),
                        aba="Lotes",
                    )
                )
                continue
        if valor is None and valor_avaliado is not None:
            valor = valor_avaliado
            issues.append(
                Issue(
                    "aviso",
                    f"Lote {numero} sem valor da venda; usando o valor avaliado "
                    f"{format_brl(valor_avaliado)}.",
                    linha=int(row["_linha"]),
                    aba="Lotes",
                )
            )
        if valor is None:
            issues.append(
                Issue(
                    "erro",
                    f"Lote {numero} sem valor da venda.",
                    linha=int(row["_linha"]),
                    aba="Lotes",
                )
            )
            continue
        grupo = text_cell(row.get("grupo")).strip()
        if not grupo:
            issues.append(
                Issue(
                    "erro",
                    f"Lote {numero} sem grupo.",
                    linha=int(row["_linha"]),
                    aba="Lotes",
                )
            )
            continue
        secao = text_cell(row.get("secao")).strip()
        if not secao:
            secao = "Bens em Geral"
            issues.append(
                Issue(
                    "aviso",
                    f"Lote {numero} sem seção; usando 'Bens em Geral'.",
                    linha=int(row["_linha"]),
                    aba="Lotes",
                )
            )
        lotes.append(
            Lot(
                numero=numero,
                valor=valor,
                grupo=grupo,
                secao=secao,
                valor_avaliado=valor_avaliado,
                descricao_pl=text_cell(row.get("descricao do pl")).strip(),
                observacao=text_cell(row.get("observacao")).strip(),
                row=int(row["_linha"]),
            )
        )
    if not lotes:
        raise ValueError("A aba Lotes está vazia.")
    return lotes, issues


def _read_bens(ws) -> tuple[list[Asset], list[Issue]]:
    columns, rows = _read_sheet(ws)
    _required(columns, ["lote", "descricao"], "Bens")
    bens: list[Asset] = []
    issues: list[Issue] = []
    for row in rows:
        lote = normalize_lot(row.get("lote"))
        descricao = text_cell(row.get("descricao")).strip()
        if not lote and not descricao:
            continue
        if not descricao:
            issues.append(
                Issue(
                    "erro",
                    "Bem sem descrição.",
                    linha=int(row["_linha"]),
                    aba="Bens",
                )
            )
            continue
        valor_contabil = None
        valor_bruto = row.get("valor contabil")
        if valor_bruto not in (None, ""):
            try:
                valor_contabil = parse_money(valor_bruto)
            except ValueError:
                issues.append(
                    Issue(
                        "aviso",
                        f"Valor contábil inválido na linha {row['_linha']}; ignorado.",
                        linha=int(row["_linha"]),
                        aba="Bens",
                    )
                )
        bens.append(
            Asset(
                lote=lote,
                tipo=text_cell(row.get("tipo de bem")).strip() or "Bens Móveis",
                codigo=text_cell(row.get("codigo")).strip(),
                conta_credito=text_cell(row.get("conta credito")).strip(),
                conta_debito=text_cell(row.get("conta debito")).strip(),
                descricao=descricao,
                valor_contabil=valor_contabil,
                origem=text_cell(row.get("origem")).strip(),
                categoria=text_cell(row.get("categoria")).strip() or "Outros",
                observacao=text_cell(row.get("observacao")).strip(),
                row=int(row["_linha"]),
            )
        )
    return bens, issues


def build_results(data: ReportData) -> None:
    grupos = {norm(g.nome): g for g in data.grupos}
    lotes = {lote.numero: lote for lote in data.lotes}
    por_lote: dict[str, list[Asset]] = {lote.numero: [] for lote in data.lotes}

    for bem in data.bens:
        if not bem.incluido:
            continue
        if bem.lote not in lotes:
            data.issues.append(
                Issue(
                    "erro",
                    f"Bem {bem.codigo or '(sem código)'} aponta para o lote "
                    f"{bem.lote}, que não existe na aba Lotes.",
                    linha=bem.row,
                    aba="Bens",
                )
            )
            continue
        por_lote[bem.lote].append(bem)

    sem_lote = [bem for bem in data.bens if not bem.incluido]
    if sem_lote:
        exemplos = ", ".join(
            f"{bem.codigo or bem.descricao[:20]} ({bem.origem or 'sem origem'})"
            for bem in sem_lote[:20]
        )
        restante = "" if len(sem_lote) <= 20 else f" e mais {len(sem_lote) - 20}"
        data.issues.append(
            Issue(
                "aviso",
                f"{len(sem_lote)} bem(ns) sem lote não entram no relatório: "
                f"{exemplos}{restante}.",
            )
        )

    for lote in data.lotes:
        if norm(lote.grupo) not in grupos:
            data.issues.append(
                Issue(
                    "erro",
                    f"Lote {lote.numero} aponta para o grupo '{lote.grupo}', "
                    "que não existe na aba Grupos.",
                    linha=lote.row,
                    aba="Lotes",
                )
            )
        if lote.conta_id is not None and not any(
            conta.id == lote.conta_id for conta in data.contas
        ):
            data.issues.append(
                Issue(
                    "erro",
                    f"Lote {lote.numero} aponta para uma conta de depósito "
                    "que não existe.",
                    linha=lote.row,
                    aba="Lotes",
                )
            )
        bens_lote = sorted(por_lote[lote.numero], key=lambda b: b.row)
        if not bens_lote:
            data.issues.append(
                Issue(
                    "erro",
                    f"Lote {lote.numero} não tem nenhum bem associado.",
                    linha=lote.row,
                    aba="Lotes",
                )
            )
            continue
        if lote.valor == 0:
            data.issues.append(
                Issue(
                    "aviso",
                    f"Lote {lote.numero} está com valor R$ 0,00; confira.",
                    linha=lote.row,
                    aba="Lotes",
                )
            )
        try:
            valores = distribute(lote.valor, len(bens_lote))
        except ValueError as exc:
            data.issues.append(
                Issue(
                    "erro",
                    f"Lote {lote.numero}: {exc}.",
                    linha=lote.row,
                    aba="Lotes",
                )
            )
            continue
        data.resultados.append(LotResult(lote=lote, bens=bens_lote, valores=valores))

    data.resultados.sort(key=lambda r: r.lote.numero_int)

    # Conferências de códigos e contas. O mesmo código pode existir em
    # origens diferentes, então a origem faz parte da chave.
    codigos_lote: dict[tuple[str, str, str], list[Asset]] = {}
    codigos_geral: dict[tuple[str, str], set[str]] = {}
    origens_codigo: dict[tuple[str, str], str] = {}
    for resultado in data.resultados:
        for bem in resultado.bens:
            if not bem.codigo:
                continue
            chave = (norm(bem.origem), bem.codigo)
            codigos_lote.setdefault(
                (resultado.lote.numero, chave[0], chave[1]), []
            ).append(bem)
            codigos_geral.setdefault(chave, set()).add(resultado.lote.numero)
            origens_codigo[chave] = bem.origem
    for (numero, _, codigo), bens_mesmo in codigos_lote.items():
        if len(bens_mesmo) > 1:
            origem = bens_mesmo[0].origem or "sem origem"
            data.issues.append(
                Issue(
                    "aviso",
                    f"O bem {codigo} ({origem}) aparece {len(bens_mesmo)} "
                    f"vezes no lote {numero}.",
                )
            )
    for chave, lotes_codigo in codigos_geral.items():
        if len(lotes_codigo) > 1:
            codigo = chave[1]
            origem = origens_codigo.get(chave) or "sem origem"
            data.issues.append(
                Issue(
                    "aviso",
                    f"O bem {codigo} ({origem}) aparece em mais de um lote: "
                    f"{', '.join(sorted(lotes_codigo))}.",
                )
            )

    incluidos = [bem for resultado in data.resultados for bem in resultado.bens]
    sem_contas = [bem for bem in incluidos if not bem.conta_credito or not bem.conta_debito]
    if sem_contas:
        data.issues.append(
            Issue(
                "aviso",
                f"{len(sem_contas)} bem(ns) sem Conta Crédito e/ou Conta Débito. "
                "As células ficarão vazias no relatório.",
            )
        )

    grupos_com_lotes = {norm(resultado.lote.grupo) for resultado in data.resultados}
    for grupo in data.grupos:
        if norm(grupo.nome) not in grupos_com_lotes:
            data.issues.append(
                Issue(
                    "aviso",
                    f"Grupo '{grupo.nome}' não tem lotes e não gerará aba.",
                    aba="Grupos",
                )
            )


def ler_entrada(path: str | Path) -> ReportData:
    """Lê a planilha de entrada e calcula o rateio de cada lote."""
    path = Path(path)
    if not path.exists():
        raise ValueError(f"arquivo não encontrado: {path}")
    try:
        wb = load_workbook(path, data_only=True)
    except Exception as exc:
        raise ValueError(f"não foi possível abrir {path.name}: {exc}") from exc

    faltando = [name for name in ("Grupos", "Lotes", "Bens") if name not in wb.sheetnames]
    if faltando:
        raise ValueError(
            f"{path.name} não tem as abas: {', '.join(faltando)}. "
            "Use a planilha gerada por 'python -m leilao importar'."
        )

    data = ReportData()
    try:
        grupos, issues_grupos = _read_grupos(wb["Grupos"])
        lotes, issues_lotes = _read_lotes(wb["Lotes"])
        bens, issues_bens = _read_bens(wb["Bens"])
        data.grupos = grupos
        data.lotes = lotes
        data.bens = bens
        data.issues.extend(issues_grupos + issues_lotes + issues_bens)
        build_results(data)
        return data
    finally:
        wb.close()


def modelo_entrada(path: str | Path) -> Path:
    """Cria uma planilha de entrada vazia, com os grupos padrão."""
    grupos = [DEFAULT_GROUPS["Prefeitura"], DEFAULT_GROUPS["Saúde"]]
    return write_entrada(path, grupos, [], [])
