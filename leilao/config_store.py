"""Local JSON configuration stored in the user profile."""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import dotenv_values


@dataclass
class Configuracao:
    municipio: str = "MUNICÍPIO DE EXEMPLO"
    titulo_saude: str = "FUNDO MUNICIPAL DE SAÚDE"
    subtitulo_prefeitura: str = "Prefeitura Municipal"
    subtitulo_saude: str = "Fundo Municipal de Saúde"
    agencia: str = "0000-0 (Banco de Exemplo)"
    cnpj_municipio: str = "00.000.000/0001-00"
    cnpj_saude: str = "00.000.000/0001-01"
    conta_prefeitura: str = "00000-0"
    conta_saude: str = "00000-2"


CAMPOS = (
    ("municipio", "Nome do município"),
    ("titulo_saude", "Título do fundo de saúde"),
    ("subtitulo_prefeitura", "Subtítulo da Prefeitura"),
    ("subtitulo_saude", "Subtítulo da Saúde"),
    ("agencia", "Agência bancária padrão"),
    ("cnpj_municipio", "CNPJ do município"),
    ("cnpj_saude", "CNPJ do fundo de saúde"),
    ("conta_prefeitura", "Conta corrente da Prefeitura"),
    ("conta_saude", "Conta corrente da Saúde"),
)

_LEGADO = {
    "AUCTIONREPORT_MUNICIPIO": "municipio",
    "AUCTIONREPORT_TITULO_SAUDE": "titulo_saude",
    "AUCTIONREPORT_SUBTITULO_PREFEITURA": "subtitulo_prefeitura",
    "AUCTIONREPORT_SUBTITULO_SAUDE": "subtitulo_saude",
    "AUCTIONREPORT_AGENCIA": "agencia",
    "AUCTIONREPORT_CNPJ_MUNICIPIO": "cnpj_municipio",
    "AUCTIONREPORT_CNPJ_SAUDE": "cnpj_saude",
    "AUCTIONREPORT_CONTA_PREFEITURA": "conta_prefeitura",
    "AUCTIONREPORT_CONTA_SAUDE": "conta_saude",
}


def base_dir() -> Path:
    """Directory used for a legacy .env and for development files."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _config_dir() -> Path:
    if os.name == "nt":
        base = Path(
            os.environ.get("APPDATA")
            or Path.home() / "AppData" / "Roaming"
        )
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "AuctionReport"


def caminho_config() -> Path:
    env = os.environ.get("AUCTIONREPORT_CONFIG", "").strip()
    if env:
        return Path(env).expanduser()
    return _config_dir() / "config.json"


def caminho_legado() -> Path:
    return base_dir() / ".env"


def existe_json() -> bool:
    return caminho_config().exists()


def existe_legado() -> bool:
    return caminho_legado().exists()


def _do_dicionario(dados: dict) -> Configuracao:
    padrao = Configuracao()
    valores = asdict(padrao)
    for campo in valores:
        valor = dados.get(campo)
        if valor is not None:
            valores[campo] = str(valor).strip()
    return Configuracao(**valores)


def _do_env(caminho: Path) -> Configuracao:
    dados = dotenv_values(caminho)
    valores = asdict(Configuracao())
    for chave, campo in _LEGADO.items():
        if dados.get(chave):
            valores[campo] = str(dados[chave]).strip()
    return Configuracao(**valores)


def carregar(caminho: str | Path | None = None) -> Configuracao:
    caminho = Path(caminho) if caminho is not None else caminho_config()
    if caminho.exists():
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(
                f"configuração inválida em {caminho}: {exc}"
            ) from exc
        if not isinstance(dados, dict):
            raise ValueError(f"configuração inválida em {caminho}.")
        return _do_dicionario(dados)
    legado = caminho_legado()
    if legado.exists():
        return _do_env(legado)
    return Configuracao()


def _restringir_permissoes(caminho: Path) -> None:
    if os.name == "nt":
        return
    try:
        caminho.chmod(0o600)
    except OSError:
        pass


def salvar(
    config: Configuracao, caminho: str | Path | None = None
) -> Path:
    caminho = Path(caminho) if caminho is not None else caminho_config()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists():
        backup = caminho.with_name(caminho.name + ".bak")
        shutil.copy2(caminho, backup)
        _restringir_permissoes(backup)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporario.replace(caminho)
    _restringir_permissoes(caminho)
    return caminho


def migrar_legado(
    caminho: str | Path | None = None,
) -> Configuracao | None:
    destino = Path(caminho) if caminho is not None else caminho_config()
    if destino.exists():
        return None
    legado = caminho_legado()
    if not legado.exists():
        return None
    config = _do_env(legado)
    salvar(config, destino)
    return config
