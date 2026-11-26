"""Read and write the local .env configuration."""

from __future__ import annotations

import shutil
from pathlib import Path

from dotenv import dotenv_values, set_key

from .config import BASE_DIR

CAMINHO_ENV = BASE_DIR / ".env"
CAMINHO_EXEMPLO = BASE_DIR / ".env.example"

CAMPOS = (
    ("AUCTIONREPORT_MUNICIPIO", "Nome do município", "MUNICÍPIO DE EXEMPLO"),
    (
        "AUCTIONREPORT_TITULO_SAUDE",
        "Título do fundo de saúde",
        "FUNDO MUNICIPAL DE SAÚDE",
    ),
    (
        "AUCTIONREPORT_SUBTITULO_PREFEITURA",
        "Subtítulo da Prefeitura",
        "Prefeitura Municipal",
    ),
    (
        "AUCTIONREPORT_SUBTITULO_SAUDE",
        "Subtítulo da Saúde",
        "Fundo Municipal de Saúde",
    ),
    (
        "AUCTIONREPORT_AGENCIA",
        "Agência bancária padrão",
        "0000-0 (Banco de Exemplo)",
    ),
    (
        "AUCTIONREPORT_CNPJ_MUNICIPIO",
        "CNPJ do município",
        "00.000.000/0001-00",
    ),
    (
        "AUCTIONREPORT_CNPJ_SAUDE",
        "CNPJ do fundo de saúde",
        "00.000.000/0001-01",
    ),
    (
        "AUCTIONREPORT_CONTA_PREFEITURA",
        "Conta corrente da Prefeitura",
        "00000-0",
    ),
    (
        "AUCTIONREPORT_CONTA_SAUDE",
        "Conta corrente da Saúde",
        "00000-2",
    ),
)


def valores_atuais(caminho: str | Path | None = None) -> dict[str, str]:
    caminho = Path(caminho) if caminho is not None else CAMINHO_ENV
    atuais = dotenv_values(caminho) if caminho.exists() else {}
    return {
        chave: (atuais.get(chave) or padrao)
        for chave, _, padrao in CAMPOS
    }


def salvar(
    valores: dict[str, str], caminho: str | Path | None = None
) -> Path:
    caminho = Path(caminho) if caminho is not None else CAMINHO_ENV
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if not caminho.exists() and CAMINHO_EXEMPLO.exists():
        shutil.copy2(CAMINHO_EXEMPLO, caminho)
    if caminho.exists():
        shutil.copy2(caminho, caminho.with_name(caminho.name + ".bak"))
    for chave, _, padrao in CAMPOS:
        set_key(
            str(caminho),
            chave,
            valores.get(chave, padrao),
            quote_mode="always",
        )
    return caminho
