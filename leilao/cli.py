"""Linha de comando do AuctionReport. Sem argumentos, abre a TUI."""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

from .banco import (
    BANCO_NOME,
    caminho_banco,
    carregar_leilao,
    copiar_documentos,
    criar_leilao,
    migrar_planilha,
)
from .entrada import importar_pdfs, ler_entrada, modelo_entrada, write_entrada
from .exportacao import FORMATOS, exportar
from .models import Issue, ReportData, norm
from .money import format_brl
from .relatorio import gerar_relatorio


def _utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _print_issues(issues: list[Issue]) -> None:
    erros = [i for i in issues if i.nivel == "erro"]
    avisos = [i for i in issues if i.nivel == "aviso"]
    if erros:
        print("\nERROS:")
        for issue in erros:
            print(f"  - {issue}")
    if avisos:
        print("\nAVISOS:")
        for issue in avisos:
            print(f"  - {issue}")


def _print_resumo(data: ReportData) -> None:
    print(
        f"\n{'Lote':<6} {'Grupo':<14} {'Bens':>5}  {'Valor do lote':>16}  "
        f"{'Soma dos bens':>16}  Situação"
    )
    print("-" * 80)
    total = Decimal("0.00")
    for resultado in sorted(data.resultados, key=lambda r: r.lote.numero_int):
        total += resultado.lote.valor
        situacao = "OK" if resultado.fecha else "ERRO"
        print(
            f"{resultado.lote.numero:<6} {resultado.lote.grupo:<14} "
            f"{len(resultado.bens):>5}  {format_brl(resultado.lote.valor):>16}  "
            f"{format_brl(resultado.soma):>16}  {situacao}"
        )
    print("-" * 80)
    print(
        f"{'TOTAL':<6} {'':<14} {sum(len(r.bens) for r in data.resultados):>5}  "
        f"{format_brl(total):>16}  {format_brl(total):>16}"
    )
    print("\nTotais por grupo:")
    for grupo in sorted(data.grupos, key=lambda g: (g.ordem, g.nome)):
        resultados = [
            r for r in data.resultados if norm(r.lote.grupo) == norm(grupo.nome)
        ]
        if not resultados:
            continue
        subtotal = sum((r.lote.valor for r in resultados), Decimal("0.00"))
        print(
            f"  {grupo.nome:<14} {len(resultados):>3} lote(s)  {format_brl(subtotal):>16}"
        )


def _cmd_importar(args: argparse.Namespace) -> int:
    relatorios: list[tuple[str, str]] = []
    for label, caminho in (
        ("Prefeitura", args.prefeitura),
        ("Saúde", args.saude),
        ("Educação", args.educacao),
    ):
        if caminho:
            if not Path(caminho).exists():
                print(f"ERRO: arquivo não encontrado: {caminho}")
                return 1
            relatorios.append((label, caminho))
    if not relatorios:
        print("ERRO: informe pelo menos --prefeitura ou --saude.")
        return 1
    if args.pl and not Path(args.pl).exists():
        print(f"ERRO: arquivo não encontrado: {args.pl}")
        return 1

    try:
        grupos, lotes, bens, issues = importar_pdfs(relatorios, args.pl)
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return 1

    saida = Path(args.saida)
    write_entrada(saida, grupos, lotes, bens, issues)
    _print_issues(issues)
    print(f"\nPlanilha de entrada criada: {saida.resolve()}")
    print(
        f"{len(bens)} bens, {len(lotes)} lotes e {len(grupos)} grupo(s).\n"
        "Abra a planilha, confira os lotes e preencha o valor da venda.\n"
        "Depois gere o relatório com: python -m leilao gerar"
    )
    return 0


def _cmd_novo(args: argparse.Namespace) -> int:
    relatorios: list[tuple[str, str]] = []
    for label, caminho in (
        ("Prefeitura", args.prefeitura),
        ("Saúde", args.saude),
        ("Educação", args.educacao),
    ):
        if caminho:
            if not Path(caminho).exists():
                print(f"ERRO: arquivo não encontrado: {caminho}")
                return 1
            relatorios.append((label, caminho))
    if not relatorios:
        print("ERRO: informe pelo menos --prefeitura ou --saude.")
        return 1
    if args.pl and not Path(args.pl).exists():
        print(f"ERRO: arquivo não encontrado: {args.pl}")
        return 1

    pasta = Path(args.pasta).expanduser()
    db_path = caminho_banco(pasta)
    if db_path.exists():
        print(f"ERRO: já existe um leilão em {pasta}.")
        return 1

    try:
        grupos, lotes, bens, issues = importar_pdfs(relatorios, args.pl)
        data = criar_leilao(
            pasta, ReportData(grupos=grupos, lotes=lotes, bens=bens)
        )
        documentos = list(relatorios)
        if args.pl:
            documentos.append(("Projeto de Lei", args.pl))
        copiar_documentos(db_path, documentos)
    except (ValueError, OSError) as exc:
        print(f"ERRO: {exc}")
        return 1

    _print_issues(issues)
    _print_issues(data.issues)
    _print_resumo(data)
    print(f"\nLeilão criado em: {pasta.resolve()}")
    print(f"Banco: {db_path.resolve()}")
    return 0


def _cmd_migrar(args: argparse.Namespace) -> int:
    pasta = Path(args.pasta).expanduser()
    try:
        data = migrar_planilha(args.entrada, pasta)
    except (ValueError, OSError) as exc:
        print(f"ERRO: {exc}")
        return 1
    _print_issues(data.issues)
    _print_resumo(data)
    print(f"\nLeilão migrado para: {pasta.resolve()}")
    print(f"Banco: {caminho_banco(pasta).resolve()}")
    return 0


def _cmd_exportar(args: argparse.Namespace) -> int:
    db_path = Path(args.banco).expanduser()
    try:
        data = carregar_leilao(db_path)
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return 1

    _print_issues(data.issues)
    if data.erros:
        print("\nCorrija os erros antes de exportar.")
        return 1

    pasta = (
        Path(args.saida).expanduser()
        if args.saida
        else db_path.parent / "exportacoes"
    )
    try:
        resultado = exportar(
            data,
            pasta,
            args.formato,
            nome_base=args.nome,
            incluir_resumo=args.com_resumo,
        )
    except (ValueError, OSError) as exc:
        print(f"ERRO: {exc}")
        return 1

    if resultado.xlsx:
        print(f"\nXLSX gerado: {resultado.xlsx.resolve()}")
    if resultado.pdf:
        print(f"PDF gerado: {resultado.pdf.resolve()}")
    return 0


def _cmd_gerar(args: argparse.Namespace) -> int:
    try:
        data = ler_entrada(args.entrada)
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return 1

    _print_issues(data.issues)
    _print_resumo(data)
    if data.erros:
        print("\nO relatório não foi gerado. Corrija os erros acima.")
        return 1

    try:
        saida = gerar_relatorio(data, args.saida, incluir_resumo=args.com_resumo)
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return 1
    print(f"\nRelatório gerado: {saida.resolve()}")
    return 0


def _ler_leilao(caminho: str | Path) -> ReportData:
    caminho = Path(caminho)
    if caminho.suffix.lower() == ".db":
        return carregar_leilao(caminho)
    return ler_entrada(caminho)


def _cmd_conferir(args: argparse.Namespace) -> int:
    try:
        data = _ler_leilao(args.entrada)
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return 1
    _print_issues(data.issues)
    _print_resumo(data)
    if data.erros:
        print("\nExistem erros que impedem a geração do relatório.")
        return 1
    print("\nTudo certo: todos os lotes fecham exatamente.")
    return 0


def _cmd_modelo(args: argparse.Namespace) -> int:
    saida = modelo_entrada(args.saida)
    print(f"Modelo criado: {saida.resolve()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    _utf8()
    parser = argparse.ArgumentParser(
        prog="python -m leilao",
        description="AuctionReport: relatórios de bens de leilão em Excel.",
    )
    sub = parser.add_subparsers(dest="comando")

    p_novo = sub.add_parser(
        "novo", help="lê os PDFs e cria a pasta e o banco do leilão"
    )
    p_novo.add_argument("--prefeitura", help="PDF do relatório da Prefeitura")
    p_novo.add_argument("--saude", help="PDF do relatório da Saúde")
    p_novo.add_argument("--educacao", help="PDF do relatório da Educação")
    p_novo.add_argument("--pl", help="PDF do projeto de lei com os lotes")
    p_novo.add_argument(
        "--pasta", required=True, help="pasta do leilão a criar"
    )
    p_novo.set_defaults(func=_cmd_novo)

    p_mig = sub.add_parser(
        "migrar", help="converte uma planilha de entrada antiga em banco"
    )
    p_mig.add_argument("entrada", help="planilha .xlsx de entrada")
    p_mig.add_argument(
        "--pasta", required=True, help="pasta do leilão a criar"
    )
    p_mig.set_defaults(func=_cmd_migrar)

    p_exp = sub.add_parser(
        "exportar", help="gera o XLSX e/ou o PDF a partir do banco"
    )
    p_exp.add_argument("banco", nargs="?", default=BANCO_NOME)
    p_exp.add_argument(
        "--formato",
        choices=FORMATOS,
        default="xlsx",
        help="formato de saída (padrão: xlsx)",
    )
    p_exp.add_argument("--saida", help="pasta de exportação")
    p_exp.add_argument("--nome", help="nome base dos arquivos")
    p_exp.add_argument(
        "--com-resumo",
        action="store_true",
        help="incluir a aba extra de conferência (Resumo)",
    )
    p_exp.set_defaults(func=_cmd_exportar)

    p_imp = sub.add_parser(
        "importar", help="(legado) lê os PDFs e cria a planilha de entrada"
    )
    p_imp.add_argument("--prefeitura", help="PDF do relatório da Prefeitura")
    p_imp.add_argument("--saude", help="PDF do relatório da Saúde")
    p_imp.add_argument("--educacao", help="PDF do relatório da Educação")
    p_imp.add_argument("--pl", help="PDF do projeto de lei com os lotes")
    p_imp.add_argument(
        "-o", "--saida", default="leilao_entrada.xlsx", help="planilha de entrada a criar"
    )
    p_imp.set_defaults(func=_cmd_importar)

    p_ger = sub.add_parser("gerar", help="gera o relatório final")
    p_ger.add_argument("entrada", nargs="?", default="leilao_entrada.xlsx")
    p_ger.add_argument("-o", "--saida", default="relatorio_leilao.xlsx")
    p_ger.add_argument(
        "--com-resumo",
        action="store_true",
        help="incluir a aba extra de conferência (Resumo)",
    )
    p_ger.set_defaults(func=_cmd_gerar)

    p_con = sub.add_parser(
        "conferir", help="confere um banco (.db) ou uma planilha (.xlsx)"
    )
    p_con.add_argument("entrada", nargs="?", default=BANCO_NOME)
    p_con.set_defaults(func=_cmd_conferir)

    p_mod = sub.add_parser("modelo", help="cria uma planilha de entrada vazia")
    p_mod.add_argument("-o", "--saida", default="modelo_leilao.xlsx")
    p_mod.set_defaults(func=_cmd_modelo)

    args = parser.parse_args(argv)
    if not args.comando:
        from .tui import main_tui

        try:
            return main_tui()
        except KeyboardInterrupt:
            print("\nAté mais.")
            return 0
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nCancelado.")
        return 130
    except Exception as exc:
        print(f"ERRO inesperado: {exc}")
        return 1
