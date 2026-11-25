"""Convert an XLSX report to PDF using LibreOffice."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import norm


class PdfExportError(ValueError):
    """Error while converting the report to PDF."""


def encontrar_soffice() -> Path | None:
    """Return the LibreOffice executable, if available."""
    env = os.environ.get("SOFFICE_PATH", "").strip()
    if env:
        caminho = Path(env).expanduser()
        if caminho.exists():
            return caminho

    for nome in ("soffice", "libreoffice"):
        encontrado = shutil.which(nome)
        if encontrado:
            return Path(encontrado)

    candidatos: list[Path] = []
    if os.name == "nt":
        for base in (
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("LOCALAPPDATA"),
        ):
            if base:
                candidatos.append(
                    Path(base) / "LibreOffice" / "program" / "soffice.exe"
                )
    else:
        candidatos.append(
            Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
        )
    for candidato in candidatos:
        if candidato.exists():
            return candidato
    return None


def _instrucoes_instalacao() -> str:
    if os.name == "nt":
        return (
            "Instale o LibreOffice (https://www.libreoffice.org/) e tente "
            "novamente, ou defina a variável SOFFICE_PATH."
        )
    return (
        "No Arch Linux, instale com: sudo pacman -S libreoffice-fresh. "
        "Em outras distribuições, instale o pacote do LibreOffice."
    )


def converter_xlsx_para_pdf(xlsx_path: str | Path, pdf_path: str | Path) -> Path:
    """Convert an XLSX file to PDF and return the PDF path."""
    xlsx_path = Path(xlsx_path).expanduser().resolve()
    pdf_path = Path(pdf_path).expanduser().resolve()
    if not xlsx_path.exists():
        raise PdfExportError(f"Planilha não encontrada: {xlsx_path}")

    soffice = encontrar_soffice()
    if soffice is None:
        raise PdfExportError(
            "LibreOffice não encontrado. Ele é necessário para gerar o PDF. "
            + _instrucoes_instalacao()
        )

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="auctionreport-") as perfil:
        comando = [
            str(soffice),
            "--headless",
            "--norestore",
            f"-env:UserInstallation={Path(perfil).as_uri()}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(pdf_path.parent),
            str(xlsx_path),
        ]
        try:
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except OSError as exc:
            raise PdfExportError(
                f"Não foi possível executar o LibreOffice: {exc}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise PdfExportError(
                "O LibreOffice demorou demais para gerar o PDF."
            ) from exc

    if resultado.returncode != 0:
        detalhe = (resultado.stderr or resultado.stdout or "").strip()
        raise PdfExportError(
            "O LibreOffice não conseguiu gerar o PDF."
            + (f"\n{detalhe}" if detalhe else "")
        )

    gerado = pdf_path.parent / f"{xlsx_path.stem}.pdf"
    if not gerado.exists():
        raise PdfExportError(
            "O LibreOffice terminou sem criar o PDF esperado."
        )
    if gerado != pdf_path:
        if pdf_path.exists():
            pdf_path.unlink()
        gerado.replace(pdf_path)
    return pdf_path


def nome_seguro_pdf(nome: str) -> str:
    """Return a filesystem-safe PDF file name."""
    limpo = norm(nome).lower()
    limpo = "".join(
        caractere if caractere.isalnum() or caractere in "-_" else "-"
        for caractere in limpo
    )
    limpo = "-".join(parte for parte in limpo.split("-") if parte)
    return f"{limpo or 'relatorio'}.pdf"
