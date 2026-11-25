"""Generate XLSX files from an auction report."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .models import ReportData, norm
from .relatorio import gerar_relatorio


def _nome_seguro(nome: str) -> str:
    texto = norm(nome).lower()
    texto = re.sub(r"[^a-z0-9._-]+", "-", texto)
    return texto.strip("-._")


def _nome_base(pasta: Path, nome: str | None) -> str:
    padrao = f"relatorio_{datetime.now():%Y-%m-%d_%H%M}"
    base = _nome_seguro(nome or padrao) or padrao
    candidato = base
    contador = 2
    while (pasta / f"{candidato}.xlsx").exists():
        candidato = f"{base}_{contador}"
        contador += 1
    return candidato


def exportar(
    data: ReportData,
    pasta: str | Path,
    *,
    nome_base: str | None = None,
    incluir_resumo: bool = False,
) -> Path:
    """Generate the XLSX report inside the export folder."""
    pasta = Path(pasta).expanduser()
    pasta.mkdir(parents=True, exist_ok=True)
    nome = _nome_base(pasta, nome_base)
    xlsx = pasta / f"{nome}.xlsx"
    gerar_relatorio(data, xlsx, incluir_resumo=incluir_resumo)
    return xlsx
