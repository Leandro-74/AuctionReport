"""Interface TUI do AuctionReport, com seleção nativa de arquivos."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from . import __version__
from .edicao import (
    EdicaoError,
    adicionar_bem,
    adicionar_grupo,
    adicionar_lote,
    editar_bem,
    editar_grupo,
    editar_lote,
    encontrar_bem,
    encontrar_grupo,
    encontrar_lote,
    filtrar_bens,
    mover_bens,
    remover_bens,
    remover_grupo,
    remover_lote,
    salvar_entrada,
    substituir_descricao,
)
from .entrada import importar_pdfs, ler_entrada, modelo_entrada, write_entrada
from .models import Asset, Issue, ReportData, norm
from .money import format_brl
from .relatorio import gerar_relatorio

console = Console()


# ---------------------------------------------------------------------------
# Estado e utilidades
# ---------------------------------------------------------------------------


@dataclass
class Estado:
    entrada: Path | None = None
    relatorio: Path | None = None
    data: ReportData | None = None

    @property
    def tem_dados(self) -> bool:
        return self.data is not None and self.entrada is not None


def _open_file(path: str | Path) -> None:
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        console.print("[yellow]Não foi possível abrir o arquivo automaticamente.[/]")


def _tk_root():
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    return root


def selecionar_pdf(titulo: str, inicial: Path | None = None) -> str:
    try:
        from tkinter import filedialog

        root = _tk_root()
        caminho = filedialog.askopenfilename(
            title=titulo,
            initialdir=str(inicial.parent if inicial else Path.cwd()),
            filetypes=[("PDF", "*.pdf"), ("Todos os arquivos", "*.*")],
        )
        root.destroy()
        return caminho or ""
    except Exception:
        return Prompt.ask(f"{titulo} (caminho do PDF, Enter para pular)", default="")


def selecionar_xlsx(titulo: str, inicial: Path | None = None) -> str:
    try:
        from tkinter import filedialog

        root = _tk_root()
        caminho = filedialog.askopenfilename(
            title=titulo,
            initialdir=str(inicial.parent if inicial else Path.cwd()),
            filetypes=[("Excel", "*.xlsx"), ("Todos os arquivos", "*.*")],
        )
        root.destroy()
        return caminho or ""
    except Exception:
        return Prompt.ask(f"{titulo} (caminho do .xlsx)", default="")


def salvar_xlsx(titulo: str, nome_padrao: str, inicial: Path | None = None) -> str:
    try:
        from tkinter import filedialog

        root = _tk_root()
        caminho = filedialog.asksaveasfilename(
            title=titulo,
            initialdir=str(inicial.parent if inicial else Path.cwd()),
            initialfile=nome_padrao,
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        root.destroy()
        return caminho or ""
    except Exception:
        return Prompt.ask(
            f"{titulo} (caminho do .xlsx)", default=str(Path.cwd() / nome_padrao)
        )


def _pause() -> None:
    try:
        Prompt.ask("\n[dim]Enter para continuar[/]", default="", show_default=False)
    except EOFError:
        pass


def _confirm(prompt: str, default: bool = False) -> bool:
    sufixo = "S/n" if default else "s/N"
    resposta = Prompt.ask(
        f"{prompt} [{sufixo}]",
        default="s" if default else "n",
        show_default=False,
    ).strip().lower()
    return resposta in ("s", "sim", "y", "yes")


def _banner() -> None:
    texto = Text()
    texto.append("AuctionReport", style="bold cyan")
    texto.append(f"  v{__version__}", style="dim")
    texto.append("  ·  relatórios de bens de leilão", style="dim")
    console.print(Panel.fit(texto, border_style="cyan", padding=(0, 2)))


def _erro(mensagem: str) -> None:
    console.print(Panel(mensagem, title="[bold red]Erro[/]", border_style="red"))


def _sucesso(mensagem: str) -> None:
    console.print(Panel(mensagem, title="[bold green]OK[/]", border_style="green"))


def _avisos(issues: list[Issue], titulo: str = "Avisos") -> None:
    erros = [i for i in issues if i.nivel == "erro"]
    avisos = [i for i in issues if i.nivel == "aviso"]
    if erros:
        linhas = "\n".join(f"• {i}" for i in erros[:15])
        if len(erros) > 15:
            linhas += f"\n… e mais {len(erros) - 15} erro(s)."
        console.print(Panel(linhas, title="[bold red]Erros[/]", border_style="red"))
    if avisos:
        linhas = "\n".join(f"• {i}" for i in avisos[:15])
        if len(avisos) > 15:
            linhas += f"\n… e mais {len(avisos) - 15} aviso(s)."
        console.print(Panel(linhas, title="[bold yellow]Avisos[/]", border_style="yellow"))


def _menu(titulo: str, opcoes: list[tuple[str, str, str]]) -> str:
    tabela = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    tabela.add_column("Opção", style="bold cyan", width=3, justify="right")
    tabela.add_column("Ação", style="bold")
    tabela.add_column("Descrição", style="dim")
    for chave, acao, descricao in opcoes:
        tabela.add_row(chave, acao, descricao)
    console.print(Panel(tabela, title=titulo, border_style="blue"))
    return Prompt.ask("Escolha", default="0").strip()


def _status(estado: Estado) -> None:
    linhas = []
    if estado.entrada:
        linhas.append(f"[bold]Planilha:[/] {estado.entrada}")
    else:
        linhas.append("[dim]Planilha: nenhuma carregada[/]")
    if estado.data:
        bens = len([b for b in estado.data.bens if b.lote])
        linhas.append(
            f"[bold]Conteúdo:[/] {bens} bens em {len(estado.data.resultados)} lote(s), "
            f"{len(estado.data.grupos)} grupo(s)"
        )
    if estado.relatorio:
        linhas.append(f"[bold]Relatório:[/] {estado.relatorio}")
    console.print(Panel("\n".join(linhas), border_style="dim", padding=(0, 1)))


def _carregar(estado: Estado, caminho: str | Path, mostrar: bool = True) -> bool:
    caminho = Path(caminho)
    try:
        data = ler_entrada(caminho)
    except ValueError as exc:
        _erro(str(exc))
        return False
    estado.entrada = caminho
    estado.data = data
    if mostrar:
        console.print(f"[green]Planilha carregada:[/] {caminho}")
        _avisos(data.issues)
    return True


def _salvar(estado: Estado) -> bool:
    if not estado.tem_dados:
        _erro("Nenhuma planilha carregada.")
        return False
    try:
        estado.data = salvar_entrada(estado.entrada, estado.data)
    except PermissionError:
        _erro(
            "Não foi possível salvar porque a planilha está aberta no Excel. "
            "Feche o arquivo e tente novamente."
        )
        return False
    except Exception as exc:
        _erro(f"Não foi possível salvar: {exc}")
        return False
    console.print(f"[green]Alterações salvas em[/] {estado.entrada}")
    return True


def _ensure_data(estado: Estado) -> bool:
    if estado.tem_dados:
        return True
    console.print("[yellow]Nenhuma planilha de entrada carregada.[/]")
    if _confirm("Abrir uma planilha agora?", default=True):
        caminho = selecionar_xlsx("Abrir planilha de entrada", estado.entrada)
        if not caminho:
            return False
        return _carregar(estado, caminho)
    return False


def _tabela_grupos(data: ReportData) -> Table:
    tabela = Table(box=box.SIMPLE_HEAVY, header_style="bold cyan")
    tabela.add_column("Grupo", no_wrap=True)
    tabela.add_column("Aba", overflow="ellipsis", max_width=34)
    tabela.add_column("Lotes", justify="right", no_wrap=True)
    tabela.add_column("Bens", justify="right", no_wrap=True)
    tabela.add_column("Valor total", justify="right", no_wrap=True)
    for grupo in sorted(data.grupos, key=lambda g: (g.ordem, g.nome)):
        resultados = [
            r for r in data.resultados if norm(r.lote.grupo) == norm(grupo.nome)
        ]
        total = sum((r.lote.valor for r in resultados), Decimal("0.00"))
        tabela.add_row(
            grupo.nome,
            grupo.aba,
            str(len(resultados)),
            str(sum(len(r.bens) for r in resultados)),
            format_brl(total),
        )
    return tabela


def _tabela_lotes(data: ReportData) -> Table:
    resultados = {r.lote.numero: r for r in data.resultados}
    tabela = Table(box=box.SIMPLE_HEAVY, header_style="bold cyan")
    tabela.add_column("Lote", no_wrap=True)
    tabela.add_column("Grupo", no_wrap=True)
    tabela.add_column("Seção", overflow="ellipsis", max_width=42)
    tabela.add_column("Bens", justify="right", no_wrap=True)
    tabela.add_column("Valor do lote", justify="right", no_wrap=True)
    tabela.add_column("Soma", justify="right", no_wrap=True)
    tabela.add_column("Status", no_wrap=True)
    for lote in sorted(data.lotes, key=lambda l: l.numero_int):
        resultado = resultados.get(lote.numero)
        if resultado:
            status = "[green]OK[/]" if resultado.fecha else "[red]ERRO[/]"
            tabela.add_row(
                lote.numero,
                lote.grupo,
                lote.secao,
                str(len(resultado.bens)),
                format_brl(lote.valor),
                format_brl(resultado.soma),
                status,
            )
        else:
            tabela.add_row(
                lote.numero,
                lote.grupo,
                lote.secao,
                "0",
                format_brl(lote.valor),
                "-",
                "[red]SEM BENS[/]",
            )
    return tabela


def _tabela_bens(bens: list[Asset], limite: int = 200) -> Table:
    tabela = Table(box=box.SIMPLE_HEAVY, header_style="bold cyan", expand=True)
    tabela.add_column("Lote", width=6)
    tabela.add_column("Código", width=8)
    tabela.add_column("Descrição", overflow="ellipsis", max_width=52)
    tabela.add_column("C. Crédito", width=12)
    tabela.add_column("C. Débito", width=12)
    tabela.add_column("Categoria", width=13)
    tabela.add_column("Origem", width=11)
    tabela.add_column("Valor contábil", justify="right", width=14)
    for bem in bens[:limite]:
        tabela.add_row(
            bem.lote or "-",
            bem.codigo or "-",
            bem.descricao,
            bem.conta_credito or "-",
            bem.conta_debito or "-",
            bem.categoria or "-",
            bem.origem or "-",
            format_brl(bem.valor_contabil) if bem.valor_contabil else "-",
        )
    return tabela


def _totais(data: ReportData) -> tuple[int, Decimal]:
    total = sum((r.lote.valor for r in data.resultados), Decimal("0.00"))
    return sum(len(r.bens) for r in data.resultados), total


# ---------------------------------------------------------------------------
# Dashboard de edição
# ---------------------------------------------------------------------------


def _dashboard(estado: Estado) -> None:
    data = estado.data
    if data is None:
        return
    console.print(f"[bold]Planilha:[/] {estado.entrada}")
    console.print(_tabela_grupos(data))
    console.print(_tabela_lotes(data))
    _avisos(data.issues)


def editar_dashboard(estado: Estado) -> None:
    if not _ensure_data(estado):
        return
    while True:
        console.clear()
        _banner()
        _dashboard(estado)
        console.print(
            "[dim]As edições são salvas na planilha de entrada. "
            "Use 'Gerar relatório' para atualizar o Excel final.[/]"
        )
        opcao = _menu(
            "Editar relatório",
            [
                ("1", "Ver/listar bens", "Filtrar por lote, código, texto ou categoria"),
                ("2", "Mover bens", "Mover bens por código/faixa para outro lote"),
                ("3", "Editar lote", "Valor da venda, grupo, seção"),
                ("4", "Editar bem", "Descrição, contas, código, lote"),
                ("5", "Substituir texto", "Trocar um trecho da descrição em vários bens"),
                ("6", "Adicionar/remover", "Novo lote, novo bem, remover"),
                ("7", "Grupos e contas", "Dados bancários e abas"),
                ("8", "Abrir no Excel", "Visualizar a planilha de entrada"),
                ("9", "Salvar agora", "As edições já são salvas automaticamente"),
                ("0", "Voltar", "Voltar ao menu principal"),
            ],
        )
        try:
            if opcao == "1":
                _ver_bens(estado)
            elif opcao == "2":
                _mover_bens(estado)
            elif opcao == "3":
                _editar_lote(estado)
            elif opcao == "4":
                _editar_bem(estado)
            elif opcao == "5":
                _substituir_texto(estado)
            elif opcao == "6":
                _adicionar_remover(estado)
            elif opcao == "7":
                _grupos(estado)
            elif opcao == "8":
                if estado.entrada:
                    _open_file(estado.entrada)
            elif opcao == "9":
                _salvar(estado)
                _pause()
            elif opcao == "0":
                return
            else:
                _erro("Opção inválida.")
                _pause()
        except EdicaoError as exc:
            _erro(str(exc))
            _pause()
        except Exception as exc:
            _erro(f"Erro inesperado: {exc}")
            _pause()


# ---------------------------------------------------------------------------
# Ações de edição
# ---------------------------------------------------------------------------


def _ver_bens(estado: Estado) -> None:
    data = estado.data
    assert data is not None
    console.print("[dim]Deixe em branco para não filtrar.[/]")
    lote = Prompt.ask("Lote", default="")
    codigos = Prompt.ask("Código ou faixa (ex.: 300-400)", default="")
    texto = Prompt.ask("Texto na descrição", default="")
    categoria = Prompt.ask("Categoria", default="")
    bens = filtrar_bens(
        data, codigos=codigos, texto=texto, lote=lote, categoria=categoria
    )
    if not bens:
        console.print("[yellow]Nenhum bem encontrado.[/]")
    else:
        console.print(_tabela_bens(bens))
        if len(bens) > 200:
            console.print(f"[dim]Mostrando 200 de {len(bens)} bens.[/]")
    _pause()


def _mover_bens(estado: Estado) -> None:
    data = estado.data
    assert data is not None
    console.print(_tabela_lotes(data))
    codigos = Prompt.ask("Código ou faixa a mover (ex.: 300-400, 305, 310)", default="")
    texto = Prompt.ask("Filtrar por texto na descrição (Enter = não)", default="")
    lote_origem = Prompt.ask("Lote de origem (Enter = qualquer)", default="")
    categoria = Prompt.ask("Categoria (Enter = qualquer)", default="")
    if not codigos and not texto and not categoria:
        _erro("Informe pelo menos um filtro para não mover todos os bens.")
        _pause()
        return
    lote_destino = Prompt.ask("Lote de destino", default="")
    if not lote_destino:
        _erro("Informe o lote de destino.")
        _pause()
        return
    encontrar_lote(data, lote_destino)
    matches = filtrar_bens(
        data,
        codigos=codigos,
        texto=texto,
        lote=lote_origem,
        categoria=categoria,
    )
    if not matches:
        console.print("[yellow]Nenhum bem corresponde aos filtros.[/]")
        _pause()
        return
    console.print(f"[bold]{len(matches)} bem(ns)[/] serão movidos para o lote {lote_destino}:")
    console.print(_tabela_bens(matches, limite=60))
    if len(matches) > 60:
        console.print(f"[dim]Mostrando 60 de {len(matches)}.[/]")
    if not _confirm("Confirmar a movimentação?", default=False):
        console.print("[dim]Cancelado.[/]")
        _pause()
        return
    movidos = mover_bens(
        data,
        lote_destino=lote_destino,
        codigos=codigos,
        texto=texto,
        lote_origem=lote_origem,
        categoria=categoria,
    )
    _salvar(estado)
    _sucesso(f"{len(movidos)} bem(ns) movido(s) para o lote {lote_destino}.")
    _pause()


def _editar_lote(estado: Estado) -> None:
    data = estado.data
    assert data is not None
    console.print(_tabela_lotes(data))
    numero = Prompt.ask("Número do lote", default="")
    lote = encontrar_lote(data, numero)
    console.print(
        Panel(
            f"[bold]Lote {lote.numero}[/]\n"
            f"Grupo: {lote.grupo}\nSeção: {lote.secao}\n"
            f"Valor: {format_brl(lote.valor)}\n"
            f"Observação: {lote.observacao or '-'}",
            border_style="blue",
        )
    )
    valor_atual = format_brl(lote.valor, symbol=False)
    novo_valor = Prompt.ask("Novo valor (Enter mantém)", default=valor_atual)
    novo_grupo = Prompt.ask("Grupo (Enter mantém)", default=lote.grupo)
    nova_secao = Prompt.ask("Seção (Enter mantém)", default=lote.secao)
    nova_obs = Prompt.ask("Observação (Enter mantém)", default=lote.observacao)
    editar_lote(
        data,
        lote.numero,
        valor=novo_valor,
        grupo=novo_grupo,
        secao=nova_secao,
        observacao=nova_obs,
    )
    _salvar(estado)
    _sucesso(f"Lote {lote.numero} atualizado.")
    _pause()


def _editar_bem(estado: Estado) -> None:
    data = estado.data
    assert data is not None
    codigo = Prompt.ask("Código do bem", default="")
    try:
        bem = encontrar_bem(data, codigo)
    except EdicaoError as exc:
        _erro(str(exc))
        _pause()
        return
    console.print(
        Panel(
            f"[bold]Bem {bem.codigo}[/]\n"
            f"Lote: {bem.lote or '-'}\nTipo: {bem.tipo}\n"
            f"Categoria: {bem.categoria}\nConta Crédito: {bem.conta_credito or '-'}\n"
            f"Conta Débito: {bem.conta_debito or '-'}\n"
            f"Valor contábil: {format_brl(bem.valor_contabil) if bem.valor_contabil else '-'}\n"
            f"Descrição: {bem.descricao}",
            border_style="blue",
        )
    )
    alteracoes: dict[str, str] = {}
    if _confirm("Alterar a descrição?", default=False):
        alteracoes["descricao"] = Prompt.ask("Nova descrição")
    if _confirm("Alterar o código?", default=False):
        alteracoes["novo_codigo"] = Prompt.ask("Novo código")
    if _confirm("Alterar o lote?", default=False):
        alteracoes["lote"] = Prompt.ask("Novo lote (vazio = sem lote)", default="")
    if _confirm("Alterar o tipo?", default=False):
        alteracoes["tipo"] = Prompt.ask("Novo tipo", default=bem.tipo)
    if _confirm("Alterar a categoria?", default=False):
        alteracoes["categoria"] = Prompt.ask("Nova categoria", default=bem.categoria)
    if _confirm("Alterar a Conta Crédito?", default=False):
        alteracoes["conta_credito"] = Prompt.ask("Nova Conta Crédito", default=bem.conta_credito)
    if _confirm("Alterar a Conta Débito?", default=False):
        alteracoes["conta_debito"] = Prompt.ask("Nova Conta Débito", default=bem.conta_debito)
    if _confirm("Alterar o valor contábil?", default=False):
        alteracoes["valor_contabil"] = Prompt.ask(
            "Novo valor contábil",
            default=format_brl(bem.valor_contabil, symbol=False) if bem.valor_contabil else "",
        )
    if _confirm("Alterar a observação?", default=False):
        alteracoes["observacao"] = Prompt.ask("Nova observação", default=bem.observacao)
    if not alteracoes:
        console.print("[dim]Nada alterado.[/]")
        _pause()
        return
    editar_bem(data, codigo, **alteracoes)
    _salvar(estado)
    _sucesso(f"Bem {bem.codigo} atualizado.")
    _pause()


def _substituir_texto(estado: Estado) -> None:
    data = estado.data
    assert data is not None
    antigo = Prompt.ask("Texto a substituir", default="")
    if not antigo.strip():
        _erro("Informe o texto a substituir.")
        _pause()
        return
    novo = Prompt.ask("Novo texto", default="")
    lote = Prompt.ask("Filtrar por lote (Enter = todos)", default="")
    categoria = Prompt.ask("Filtrar por categoria (Enter = todas)", default="")
    matches = [
        bem
        for bem in filtrar_bens(data, lote=lote, categoria=categoria)
        if antigo.lower() in bem.descricao.lower()
    ]
    if not matches:
        console.print("[yellow]Nenhuma descrição contém esse texto.[/]")
        _pause()
        return
    console.print(f"[bold]{len(matches)} bem(ns)[/] serão alterados:")
    console.print(_tabela_bens(matches, limite=30))
    if not _confirm("Confirmar a substituição?", default=False):
        console.print("[dim]Cancelado.[/]")
        _pause()
        return
    alterados = substituir_descricao(
        data, antigo, novo, lote=lote, categoria=categoria
    )
    _salvar(estado)
    _sucesso(f"{len(alterados)} descrição(ões) alterada(s).")
    _pause()


def _adicionar_remover(estado: Estado) -> None:
    data = estado.data
    assert data is not None
    opcao = _menu(
        "Adicionar/remover",
        [
            ("1", "Adicionar lote", "Novo lote com valor e grupo"),
            ("2", "Adicionar bem", "Novo bem em um lote"),
            ("3", "Remover lote", "Só se não houver bens no lote"),
            ("4", "Remover bens", "Excluir bens por código/faixa/texto"),
            ("0", "Voltar", ""),
        ],
    )
    if opcao == "1":
        numero = Prompt.ask("Número do lote")
        valor = Prompt.ask("Valor da venda", default="0,00")
        console.print(_tabela_grupos(data))
        grupo = Prompt.ask("Grupo", default=data.grupos[0].nome if data.grupos else "Prefeitura")
        secao = Prompt.ask("Seção", default="Bens em Geral")
        obs = Prompt.ask("Observação (Enter = vazio)", default="")
        adicionar_lote(
            data,
            numero=numero,
            valor=valor,
            grupo=grupo,
            secao=secao,
            observacao=obs,
        )
        _salvar(estado)
        _sucesso(f"Lote {numero} criado.")
        _pause()
    elif opcao == "2":
        console.print(_tabela_lotes(data))
        lote = Prompt.ask("Lote do bem")
        codigo = Prompt.ask("Código")
        descricao = Prompt.ask("Descrição")
        tipo = Prompt.ask("Tipo de bem", default="Bens Móveis")
        categoria = Prompt.ask("Categoria", default="Outros")
        credito = Prompt.ask("Conta Crédito (Enter = vazio)", default="")
        debito = Prompt.ask("Conta Débito (Enter = vazio)", default="")
        valor = Prompt.ask("Valor contábil (Enter = vazio)", default="")
        adicionar_bem(
            data,
            lote=lote,
            codigo=codigo,
            descricao=descricao,
            tipo=tipo,
            categoria=categoria,
            conta_credito=credito,
            conta_debito=debito,
            valor_contabil=valor or None,
        )
        _salvar(estado)
        _sucesso(f"Bem {codigo} adicionado.")
        _pause()
    elif opcao == "3":
        console.print(_tabela_lotes(data))
        numero = Prompt.ask("Número do lote a remover")
        remover_lote(data, numero)
        _salvar(estado)
        _sucesso(f"Lote {numero} removido.")
        _pause()
    elif opcao == "4":
        codigos = Prompt.ask("Código ou faixa (ex.: 300-400)", default="")
        texto = Prompt.ask("Texto na descrição (Enter = não)", default="")
        lote = Prompt.ask("Lote (Enter = qualquer)", default="")
        categoria = Prompt.ask("Categoria (Enter = qualquer)", default="")
        if not codigos and not texto and not lote and not categoria:
            _erro("Informe pelo menos um filtro.")
            _pause()
            return
        matches = filtrar_bens(
            data, codigos=codigos, texto=texto, lote=lote, categoria=categoria
        )
        if not matches:
            console.print("[yellow]Nenhum bem encontrado.[/]")
            _pause()
            return
        console.print(_tabela_bens(matches, limite=50))
        if not _confirm(
            f"Excluir {len(matches)} bem(ns) da planilha?", default=False
        ):
            console.print("[dim]Cancelado.[/]")
            _pause()
            return
        removidos = remover_bens(
            data, codigos=codigos, texto=texto, lote=lote, categoria=categoria
        )
        _salvar(estado)
        _sucesso(f"{len(removidos)} bem(ns) removido(s).")
        _pause()


def _grupos(estado: Estado) -> None:
    data = estado.data
    assert data is not None
    console.print(_tabela_grupos(data))
    opcao = _menu(
        "Grupos e contas",
        [
            ("1", "Editar grupo", "Título, conta, agência, CNPJ"),
            ("2", "Adicionar grupo", "Nova aba de secretaria"),
            ("3", "Remover grupo", "Só se não houver lotes"),
            ("0", "Voltar", ""),
        ],
    )
    if opcao == "1":
        nome = Prompt.ask("Nome do grupo", default=data.grupos[0].nome if data.grupos else "")
        grupo = encontrar_grupo(data, nome)
        console.print(
            Panel(
                f"[bold]{grupo.nome}[/]\nAba: {grupo.aba}\nTítulo: {grupo.titulo}\n"
                f"Subtítulo: {grupo.subtitulo}\nConta: {grupo.conta}\n"
                f"Agência: {grupo.agencia}\nConta Corrente: {grupo.conta_corrente}\n"
                f"CNPJ: {grupo.cnpj}",
                border_style="blue",
            )
        )
        novo_nome = Prompt.ask("Nome (Enter mantém)", default=grupo.nome)
        aba = Prompt.ask("Aba (Enter mantém)", default=grupo.aba)
        titulo = Prompt.ask("Título (Enter mantém)", default=grupo.titulo)
        subtitulo = Prompt.ask("Subtítulo (Enter mantém)", default=grupo.subtitulo)
        conta = Prompt.ask("Conta de depósito (Enter mantém)", default=grupo.conta)
        agencia = Prompt.ask("Agência (Enter mantém)", default=grupo.agencia)
        cc = Prompt.ask("Conta Corrente (Enter mantém)", default=grupo.conta_corrente)
        cnpj = Prompt.ask("CNPJ (Enter mantém)", default=grupo.cnpj)
        editar_grupo(
            data,
            grupo.nome,
            novo_nome=novo_nome,
            aba=aba,
            titulo=titulo,
            subtitulo=subtitulo,
            conta=conta,
            agencia=agencia,
            conta_corrente=cc,
            cnpj=cnpj,
        )
        _salvar(estado)
        _sucesso("Grupo atualizado.")
        _pause()
    elif opcao == "2":
        nome = Prompt.ask("Nome do grupo")
        aba = Prompt.ask("Nome da aba", default=f"Relatório Bens da {nome}")
        titulo = Prompt.ask("Título", default="MUNICÍPIO DE EXEMPLO")
        subtitulo = Prompt.ask("Subtítulo", default=nome)
        conta = Prompt.ask("Conta de depósito", default=f"Conta de depósito para lotes da {nome}")
        agencia = Prompt.ask("Agência", default="0000-0 (Banco de Exemplo)")
        cc = Prompt.ask("Conta Corrente", default="")
        cnpj = Prompt.ask("CNPJ", default="")
        adicionar_grupo(
            data,
            nome=nome,
            aba=aba,
            titulo=titulo,
            subtitulo=subtitulo,
            conta=conta,
            agencia=agencia,
            conta_corrente=cc,
            cnpj=cnpj,
        )
        _salvar(estado)
        _sucesso(f"Grupo {nome} criado.")
        _pause()
    elif opcao == "3":
        nome = Prompt.ask("Nome do grupo a remover")
        remover_grupo(data, nome)
        _salvar(estado)
        _sucesso(f"Grupo {nome} removido.")
        _pause()


# ---------------------------------------------------------------------------
# Importação
# ---------------------------------------------------------------------------


def novo_leilao(estado: Estado) -> None:
    console.clear()
    _banner()
    console.print(
        Panel(
            "Selecione os PDFs do sistema. O seletor do Windows será aberto.\n"
            "Cancelar no seletor = pular aquele arquivo.",
            title="Novo leilão",
            border_style="blue",
        )
    )
    relatorios: list[tuple[str, str]] = []
    for label, titulo in (
        ("Prefeitura", "Relatório da Prefeitura"),
        ("Saúde", "Relatório da Saúde"),
        ("Educação", "Relatório da Educação (opcional)"),
    ):
        console.print(f"[bold]{titulo}[/]")
        caminho = selecionar_pdf(titulo, estado.entrada)
        if caminho:
            relatorios.append((label, caminho))
            console.print(f"  [green]✓[/] {caminho}")
        else:
            console.print("  [dim]pulado[/]")
    if not relatorios:
        _erro("Nenhum relatório selecionado.")
        _pause()
        return
    pl = selecionar_pdf("Projeto de Lei", estado.entrada)
    if pl:
        console.print(f"[green]✓[/] Projeto de lei: {pl}")
    else:
        console.print("[yellow]Projeto de lei não selecionado; os lotes terão que ser preenchidos manualmente.[/]")
    saida = salvar_xlsx(
        "Salvar planilha de entrada",
        "leilao_entrada.xlsx",
        estado.entrada,
    )
    if not saida:
        console.print("[dim]Cancelado.[/]")
        _pause()
        return
    with console.status("[cyan]Lendo PDFs e montando a planilha...[/]"):
        try:
            grupos, lotes, bens, issues = importar_pdfs(relatorios, pl or None)
            write_entrada(saida, grupos, lotes, bens, issues)
        except Exception as exc:
            _erro(str(exc))
            _pause()
            return
    estado.entrada = Path(saida)
    estado.data = ler_entrada(estado.entrada)
    _sucesso(
        f"Planilha criada com {len(bens)} bens, {len(lotes)} lotes e {len(grupos)} grupo(s).\n"
        f"{saida}"
    )
    _avisos(issues)
    if _confirm("Abrir a planilha no Excel agora?", default=False):
        _open_file(estado.entrada)
    if _confirm("Ir para a edição agora?", default=True):
        editar_dashboard(estado)
    else:
        _pause()


# ---------------------------------------------------------------------------
# Gerar e conferir
# ---------------------------------------------------------------------------


def _validar_para_gerar(estado: Estado) -> bool:
    if not _ensure_data(estado):
        return False
    assert estado.data is not None
    _dashboard(estado)
    if estado.data.erros:
        console.print(
            Panel(
                "Existem erros que impedem a geração. Corrija-os na edição.",
                border_style="red",
            )
        )
        return False
    return True


def gerar(estado: Estado) -> None:
    console.clear()
    _banner()
    if not _validar_para_gerar(estado):
        _pause()
        return
    assert estado.data is not None
    bens, total = _totais(estado.data)
    console.print(
        Panel(
            f"{bens} bens em {len(estado.data.resultados)} lote(s)\n"
            f"Total: {format_brl(total)}",
            title="Pronto para gerar",
            border_style="green",
        )
    )
    incluir_resumo = _confirm(
        "Incluir a aba extra de conferência (Resumo)?", default=False
    )
    saida = salvar_xlsx(
        "Salvar relatório final",
        "relatorio_leilao.xlsx",
        estado.relatorio or estado.entrada,
    )
    if not saida:
        console.print("[dim]Cancelado.[/]")
        _pause()
        return
    with console.status("[cyan]Gerando o Excel...[/]"):
        try:
            caminho = gerar_relatorio(
                estado.data, saida, incluir_resumo=incluir_resumo
            )
        except Exception as exc:
            _erro(str(exc))
            _pause()
            return
    estado.relatorio = Path(caminho)
    from openpyxl import load_workbook

    try:
        wb_abas = load_workbook(caminho, read_only=True)
        abas = wb_abas.sheetnames
        wb_abas.close()
    except Exception:
        abas = []
    _sucesso(f"Relatório gerado:\n{caminho}")
    if abas:
        console.print(Panel("\n".join(f"• {aba}" for aba in abas), title="Abas criadas", border_style="blue"))
    if _confirm("Abrir o relatório no Excel agora?", default=True):
        _open_file(caminho)
    _pause()


def conferir(estado: Estado) -> None:
    console.clear()
    _banner()
    if not _ensure_data(estado):
        _pause()
        return
    assert estado.data is not None
    _dashboard(estado)
    if estado.data.erros:
        console.print("[red]Existem erros que impedem a geração.[/]")
    else:
        console.print("[green]Tudo certo: todos os lotes fecham exatamente.[/]")
    _pause()


# ---------------------------------------------------------------------------
# Início
# ---------------------------------------------------------------------------


def _carregar_padrao(estado: Estado) -> None:
    padrao = Path.cwd() / "leilao_entrada.xlsx"
    if padrao.exists():
        _carregar(estado, padrao, mostrar=False)


def main_tui() -> int:
    estado = Estado()
    _carregar_padrao(estado)
    while True:
        console.clear()
        _banner()
        _status(estado)
        opcao = _menu(
            "Menu principal",
            [
                ("1", "Novo leilão", "Importar PDFs e criar a planilha de entrada"),
                ("2", "Abrir/editar", "Editar bens, lotes, valores e descrições"),
                ("3", "Gerar relatório", "Gerar o Excel no formato do modelo"),
                ("4", "Conferir", "Validar somas e avisos"),
                ("5", "Grupos e contas", "Editar dados bancários e abas"),
                ("6", "Modelo vazio", "Criar uma planilha de entrada em branco"),
                ("0", "Sair", ""),
            ],
        )
        try:
            if opcao == "1":
                novo_leilao(estado)
            elif opcao == "2":
                caminho = selecionar_xlsx("Abrir planilha de entrada", estado.entrada)
                if caminho:
                    if _carregar(estado, caminho):
                        editar_dashboard(estado)
                    else:
                        _pause()
                else:
                    _pause()
            elif opcao == "3":
                gerar(estado)
            elif opcao == "4":
                conferir(estado)
            elif opcao == "5":
                if _ensure_data(estado):
                    _grupos(estado)
                else:
                    _pause()
            elif opcao == "6":
                saida = salvar_xlsx("Salvar modelo de planilha", "modelo_leilao.xlsx")
                if saida:
                    modelo_entrada(saida)
                    _sucesso(f"Modelo criado:\n{saida}")
                    if _confirm("Abrir o modelo agora?", default=True):
                        _open_file(saida)
                _pause()
            elif opcao == "0":
                console.print("[dim]Até mais.[/]")
                return 0
            else:
                _erro("Opção inválida.")
                _pause()
        except KeyboardInterrupt:
            console.print("\n[dim]Cancelado.[/]")
            _pause()
        except Exception as exc:
            _erro(f"Erro inesperado: {exc}")
            _pause()
