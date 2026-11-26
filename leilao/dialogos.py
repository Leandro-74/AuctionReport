"""Seletores de arquivos e pastas nativos do sistema operacional."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROTULOS = {
    "pdf": "PDF",
    "xlsx": "Planilha do Excel",
    "db": "Banco de dados",
}


class DialogoIndisponivel(RuntimeError):
    """O seletor nativo não está disponível neste ambiente."""


def _extensoes(valores: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(valor.lower().lstrip(".") for valor in valores if valor)


def _ferramenta_linux() -> str | None:
    for nome in ("zenity", "kdialog"):
        if shutil.which(nome):
            return nome
    return None


def _powershell() -> str:
    for nome in ("powershell", "pwsh"):
        caminho = shutil.which(nome)
        if caminho:
            return caminho
    return ""


def disponivel() -> bool:
    """Informa se há um seletor gráfico nativo utilizável."""
    try:
        if not sys.stdin.isatty():
            return False
    except (AttributeError, OSError):
        return False
    if os.name == "nt":
        return bool(_powershell())
    if sys.platform == "darwin":
        return bool(shutil.which("osascript"))
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return False
    return _ferramenta_linux() is not None


def _ps_texto(texto: str) -> str:
    return "'" + texto.replace("'", "''") + "'"


def _apple_texto(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace('"', '\\"')


def _filtro_windows(extensoes: tuple[str, ...]) -> str:
    filtros = []
    for extensao in extensoes:
        rotulo = ROTULOS.get(extensao, extensao.upper())
        filtros.append(f"{rotulo} (*.{extensao})|*.{extensao}")
    filtros.append("Todos os arquivos (*.*)|*.*")
    return "|".join(filtros)


def _comando_windows(
    titulo: str, extensoes: tuple[str, ...], pasta: bool
) -> list[str]:
    cabecalho = """
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
$OutputEncoding = New-Object System.Text.UTF8Encoding
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::EnableVisualStyles()
"""
    if pasta:
        corpo = f"""
$dlg = New-Object System.Windows.Forms.FolderBrowserDialog
$dlg.Description = {_ps_texto(titulo)}
$dlg.ShowNewFolderButton = $true
if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
    [Console]::Out.Write($dlg.SelectedPath)
}}
"""
    else:
        corpo = f"""
$dlg = New-Object System.Windows.Forms.OpenFileDialog
$dlg.Title = {_ps_texto(titulo)}
$dlg.Filter = {_ps_texto(_filtro_windows(extensoes))}
$dlg.CheckFileExists = $true
$dlg.Multiselect = $false
$dlg.RestoreDirectory = $true
if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
    [Console]::Out.Write($dlg.FileName)
}}
"""
    return [
        _powershell(),
        "-NoProfile",
        "-STA",
        "-Command",
        cabecalho + corpo,
    ]


def _comando_zenity(
    titulo: str, extensoes: tuple[str, ...], pasta: bool
) -> list[str]:
    inicial = str(Path.home()) + os.sep
    comando = [
        "zenity",
        "--file-selection",
        f"--title={titulo}",
        f"--filename={inicial}",
    ]
    if pasta:
        comando.append("--directory")
    else:
        for extensao in extensoes:
            rotulo = ROTULOS.get(extensao, extensao.upper())
            comando.append(f"--file-filter={rotulo} | *.{extensao}")
        comando.append("--file-filter=Todos os arquivos | *")
    return comando


def _comando_kdialog(
    titulo: str, extensoes: tuple[str, ...], pasta: bool
) -> list[str]:
    inicial = str(Path.home())
    if pasta:
        return [
            "kdialog",
            "--title",
            titulo,
            "--getexistingdirectory",
            inicial,
        ]
    padroes = " ".join(f"*.{extensao}" for extensao in extensoes) or "*"
    rotulo = "Arquivos" if extensoes else "Todos os arquivos"
    return [
        "kdialog",
        "--title",
        titulo,
        "--getopenfilename",
        inicial,
        f"{padroes}|{rotulo}",
    ]


def _comando_mac(
    titulo: str, extensoes: tuple[str, ...], pasta: bool
) -> list[str]:
    if pasta:
        script = (
            f'POSIX path of (choose folder with prompt '
            f'"{_apple_texto(titulo)}")'
        )
    else:
        script = (
            f'POSIX path of (choose file with prompt '
            f'"{_apple_texto(titulo)}")'
        )
    return ["osascript", "-e", script]


def _comando(
    titulo: str, extensoes: tuple[str, ...], pasta: bool
) -> list[str]:
    extensoes = _extensoes(extensoes)
    if os.name == "nt":
        if not _powershell():
            raise DialogoIndisponivel("PowerShell não encontrado")
        return _comando_windows(titulo, extensoes, pasta)
    if sys.platform == "darwin":
        if not shutil.which("osascript"):
            raise DialogoIndisponivel("osascript não encontrado")
        return _comando_mac(titulo, extensoes, pasta)
    ferramenta = _ferramenta_linux()
    if ferramenta is None:
        raise DialogoIndisponivel("instale zenity ou kdialog")
    if ferramenta == "zenity":
        return _comando_zenity(titulo, extensoes, pasta)
    return _comando_kdialog(titulo, extensoes, pasta)


def _executar(comando: list[str]) -> str:
    opcoes: dict[str, object] = {}
    if os.name == "nt":
        opcoes["creationflags"] = getattr(
            subprocess, "CREATE_NO_WINDOW", 0x08000000
        )
    try:
        processo = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            **opcoes,
        )
    except OSError as exc:
        raise DialogoIndisponivel(str(exc)) from exc
    if processo.returncode != 0:
        return ""
    return processo.stdout.strip()


def selecionar_arquivo(
    titulo: str, extensoes: tuple[str, ...] = ()
) -> str:
    """Abre o seletor nativo e devolve o arquivo escolhido."""
    return _executar(_comando(titulo, extensoes, pasta=False))


def selecionar_pasta(titulo: str) -> str:
    """Abre o seletor nativo e devolve a pasta escolhida."""
    return _executar(_comando(titulo, (), pasta=True))
