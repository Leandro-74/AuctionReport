"""Gera o relatório final em Excel no formato usado pela prefeitura."""

from __future__ import annotations

import re
from collections import OrderedDict
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

from .models import Group, Lot, LotResult, ReportData, norm
from .money import format_brl

CINZA = "FFD9D9D9"
VERDE = "FFE2EFDA"
VERMELHO = "FFFCE4D6"
BORDA_FINA = Side(style="thin", color="000000")
BORDA = Border(left=BORDA_FINA, right=BORDA_FINA, top=BORDA_FINA, bottom=BORDA_FINA)
FONTE_TITULO = Font(name="Calibri", size=13, bold=True)
FONTE_SECAO = Font(name="Calibri", size=13, bold=True)
FONTE_CONTA = Font(name="Arial", size=10)
FONTE_CONTA_NEGRITO = Font(name="Arial", size=10, bold=True)
FONTE_DADOS = Font(name="Calibri", size=11)
FORMATO_MOEDA = '[$R$ -416]#,##0.00'

COLUNAS = ["Tipo de bem", "Código", "Conta Crédito", "Conta Débito", "Descrição", "Valor"]
LARGURAS = [8.43, 10.13, 15.13, 15.13, 47.63, 17.0]


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


def _merge(ws, row: int, text: str, font: Font, fill: str | None = None,
           horizontal: str = "center", height: float | None = None) -> None:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = font
    cell.alignment = Alignment(horizontal=horizontal, vertical="center", wrap_text=True)
    if fill:
        cell.fill = PatternFill("solid", fgColor=fill)
    if height:
        ws.row_dimensions[row].height = height
    for col in range(1, 7):
        if fill:
            ws.cell(row=row, column=col).fill = PatternFill("solid", fgColor=fill)


def _header(ws, row: int) -> None:
    for col, titulo in enumerate(COLUNAS, start=1):
        cell = ws.cell(row=row, column=col, value=titulo)
        cell.font = FONTE_TITULO
        cell.fill = PatternFill("solid", fgColor=CINZA)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDA
        if col == 6:
            cell.number_format = FORMATO_MOEDA
    ws.row_dimensions[row].height = 24


def _data_row(ws, row: int, resultado: LotResult, indice: int) -> None:
    bem = resultado.bens[indice]
    valor = resultado.valores[indice]
    valores = [
        bem.tipo or "Bens Móveis",
        int(bem.codigo) if bem.codigo.isdigit() else bem.codigo,
        int(bem.conta_credito) if bem.conta_credito.isdigit() else bem.conta_credito,
        int(bem.conta_debito) if bem.conta_debito.isdigit() else bem.conta_debito,
        bem.descricao,
        float(valor),
    ]
    for col, value in enumerate(valores, start=1):
        cell = ws.cell(row=row, column=col, value=value)
        cell.font = FONTE_DADOS
        cell.border = BORDA
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        if col == 6:
            cell.number_format = FORMATO_MOEDA
            cell.alignment = Alignment(horizontal="right", vertical="center")


def _setup_page(ws) -> None:
    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_margins.left = 0.39
    ws.page_margins.right = 0.39
    ws.page_margins.top = 0.39
    ws.page_margins.bottom = 0.39
    ws.page_margins.header = 0
    ws.page_margins.footer = 0
    ws.print_options.horizontalCentered = True


def _write_group_sheet(wb, grupo: Group, resultados: list[LotResult], usados: set[str]) -> None:
    ws = wb.create_sheet(_sheet_name(grupo.aba, usados))
    for col, largura in enumerate(LARGURAS, start=1):
        ws.column_dimensions[get_column_letter(col)].width = largura

    lotes = [r.lote for r in resultados]
    total = sum((r.lote.valor for r in resultados), Decimal("0.00"))

    _merge(ws, 1, grupo.titulo, FONTE_TITULO, CINZA, height=21.75)
    subtitulo = f"{grupo.subtitulo} ({format_lots(lotes)})"
    _merge(
        ws,
        2,
        subtitulo,
        FONTE_TITULO,
        CINZA,
        height=21.75 if len(subtitulo) <= 80 else None,
    )
    ws.row_dimensions[3].height = 18

    _merge(ws, 4, grupo.conta, FONTE_CONTA_NEGRITO, CINZA, horizontal="left", height=15)
    _merge(ws, 5, f"Agência: {grupo.agencia}", FONTE_CONTA, horizontal="left", height=15)
    _merge(
        ws,
        6,
        f"Conta Corrente: {grupo.conta_corrente}",
        FONTE_CONTA,
        horizontal="left",
        height=15,
    )
    _merge(ws, 7, f"CNPJ: {grupo.cnpj}", FONTE_CONTA, horizontal="left", height=15)
    _merge(
        ws,
        8,
        f"Valor total dos lotes: {format_brl(total)}",
        FONTE_CONTA,
        horizontal="right",
        height=15,
    )
    ws.row_dimensions[9].height = 18

    # Seções na ordem do primeiro lote que usa cada nome.
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
            CINZA,
        )
        row += 1
        _header(ws, row)
        row += 1
        for resultado in resultados_secao:
            for indice in range(len(resultado.bens)):
                _data_row(ws, row, resultado, indice)
                row += 1
        row += 1  # linha em branco entre seções

    _setup_page(ws)
    ws.sheet_view.showGridLines = False


def _write_lot_sheet(
    wb, grupo: Group, resultado: LotResult, usados: set[str]
) -> None:
    """Aba simples de um lote com vários bens (para publicação/conferência)."""
    categoria = resultado.bens[0].categoria if resultado.bens else ""
    sufixo = f" - {categoria}" if categoria and categoria != "Outros" else ""
    base = f"Lote {resultado.lote.numero}{sufixo}"
    ws = wb.create_sheet(_sheet_name(base, usados))
    for col, largura in enumerate(LARGURAS, start=1):
        ws.column_dimensions[get_column_letter(col)].width = largura

    _merge(ws, 1, grupo.titulo, FONTE_TITULO, CINZA, height=21.75)
    titulo = f"LOTE {resultado.lote.numero}: {resultado.lote.secao}"
    _merge(
        ws,
        2,
        titulo,
        FONTE_SECAO,
        CINZA,
        height=21.75 if len(titulo) <= 80 else None,
    )
    ws.row_dimensions[3].height = 18
    _header(ws, 4)
    row = 5
    for indice in range(len(resultado.bens)):
        _data_row(ws, row, resultado, indice)
        row += 1
    _setup_page(ws)
    ws.sheet_view.showGridLines = False


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
        ["Grupo", "Conta de depósito", "Agência", "Conta Corrente", "CNPJ",
         "Qtd. bens", "Valor total"],
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
                cell.alignment = Alignment(horizontal="right", vertical="center")
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
            cell.alignment = Alignment(horizontal="right", vertical="center")
    row += 2

    _summary_title(ws, row, "CONFERÊNCIA POR LOTE")
    row += 1
    _summary_header(
        ws,
        row,
        ["Lote", "Grupo", "Seção", "Qtd. bens", "Valor do lote", "Soma dos bens",
         "Diferença", "Situação"],
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
                cell.alignment = Alignment(horizontal="right", vertical="center")
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
            cell.alignment = Alignment(horizontal="right", vertical="center")

    ws.sheet_view.showGridLines = False
    _setup_page(ws)


def gerar_relatorio(
    data: ReportData,
    path: str | Path,
    incluir_resumo: bool = True,
    por_lote: bool = False,
) -> Path:
    """Grava o relatório final. Levanta ValueError se houver erros de validação."""
    if data.erros:
        linhas = "\n".join(f"- {issue}" for issue in data.erros)
        raise ValueError(f"Corrija os erros antes de gerar o relatório:\n{linhas}")

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

    if por_lote:
        grupos_por_nome = {norm(g.nome): g for g in data.grupos}
        for resultado in sorted(data.resultados, key=lambda r: r.lote.numero_int):
            if len(resultado.bens) <= 1:
                continue
            grupo = grupos_por_nome.get(norm(resultado.lote.grupo))
            if grupo is None:
                continue
            _write_lot_sheet(wb, grupo, resultado, usados)

    if incluir_resumo:
        _write_summary(wb, data, usados)

    wb.properties.title = "Relatório de Bens para Leilão"
    wb.properties.creator = "Leilão Auto"
    wb.save(path)
    return path
