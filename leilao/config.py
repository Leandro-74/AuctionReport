"""Load local configuration from the user profile."""

from __future__ import annotations

from .config_store import Configuracao, base_dir, carregar

BASE_DIR = base_dir()

ERRO_CONFIG = ""
try:
    CONFIG = carregar()
except ValueError as exc:
    CONFIG = Configuracao()
    ERRO_CONFIG = str(exc)

MUNICIPIO = CONFIG.municipio
TITULO_SAUDE = CONFIG.titulo_saude
SUBTITULO_PREFEITURA = CONFIG.subtitulo_prefeitura
SUBTITULO_SAUDE = CONFIG.subtitulo_saude
AGENCIA = CONFIG.agencia
CNPJ_MUNICIPIO = CONFIG.cnpj_municipio
CNPJ_SAUDE = CONFIG.cnpj_saude
CONTA_CORRENTE_PREFEITURA = CONFIG.conta_prefeitura
CONTA_CORRENTE_SAUDE = CONFIG.conta_saude
TITULO_CONTA_MUNICIPIO = f"{MUNICIPIO}: CONTAS PARA DEPÓSITO"
TITULO_CONTA_SAUDE = f"{TITULO_SAUDE}: CONTAS PARA DEPÓSITO"
