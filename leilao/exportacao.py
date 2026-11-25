"""Generate XLSX and PDF files from an auction report."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .models import ReportData
from .pdf_export import converter_xlsx_para_pdf
from .relatorio import gerar_relatorio

FORMATOS = ("xlsx", "pdf", "ambos")


@dataclass
class ResultadoExportacao:
    xlsx: Path | None = None
    pdf: Path | None = None


def _nome_base(pasta: Path, nome: str | None) -> str:
    base = (nome or f"relatorio_{datetime.now():%Y-%m-%d_%H%M}").strip()
    candidato = base
    contador = 2
    while (pasta / f"{candidato}.xlsx").exists() or (pasta / f"{candidato}.pdf").exists():
        candidato = f"{base}_{contador}"
        contador += 1
    return candidato


def exportar(
    data: ReportData,
    pasta: str | Path,
    formato: str = "xlsx",
    *,
    nome_base: str | None = None,
    incluir_resumo: bool = False,
) -> ResultadoExportacao:
    """Generate the requested files inside the export folder."""
    formato = formato.strip().lower()
    if formato not in FORMATOS:
        raise ValueError(
            f"Formato inválido: {formato!r}. Use xlsx, pdf ou ambos."
        )
    pasta = Path(pasta).expanduser()
    pasta.mkdir(parents=True, exist_ok=True)
    nome = _nome_base(pasta, nome_base)
    resultado = ResultadoExportacao()

    xlsx = pasta / f"{nome}.xlsx"
    gerar_relatorio(data, xlsx, incluir_resumo=incluir_resumo)
    resultado.xlsx = xlsx

    if formato in ("pdf", "ambos"):
        pdf = pasta / f"{nome}.pdf"
        converter_xlsx_para_pdf(resultado.xlsx, pdf)
        resultado.pdf = pdf

    return resultado
