"""Load local configuration from environment variables."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


BASE_DIR = _base_dir()
load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


MUNICIPIO = _env("AUCTIONREPORT_MUNICIPIO", "MUNICÍPIO DE EXEMPLO")
TITULO_SAUDE = _env(
    "AUCTIONREPORT_TITULO_SAUDE", "FUNDO MUNICIPAL DE SAÚDE"
)
SUBTITULO_PREFEITURA = _env(
    "AUCTIONREPORT_SUBTITULO_PREFEITURA", "Prefeitura Municipal"
)
SUBTITULO_SAUDE = _env(
    "AUCTIONREPORT_SUBTITULO_SAUDE", "Fundo Municipal de Saúde"
)
AGENCIA = _env("AUCTIONREPORT_AGENCIA", "0000-0 (Banco de Exemplo)")
CNPJ_MUNICIPIO = _env(
    "AUCTIONREPORT_CNPJ_MUNICIPIO", "00.000.000/0001-00"
)
CNPJ_SAUDE = _env("AUCTIONREPORT_CNPJ_SAUDE", "00.000.000/0001-01")
CONTA_CORRENTE_PREFEITURA = _env(
    "AUCTIONREPORT_CONTA_PREFEITURA", "00000-0"
)
CONTA_CORRENTE_SAUDE = _env("AUCTIONREPORT_CONTA_SAUDE", "00000-2")
TITULO_CONTA_MUNICIPIO = f"{MUNICIPIO}: CONTAS PARA DEPÓSITO"
TITULO_CONTA_SAUDE = f"{TITULO_SAUDE}: CONTAS PARA DEPÓSITO"
