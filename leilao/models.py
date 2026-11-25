"""Modelos simples usados pelo importador e pelo gerador."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal


def norm(text: str) -> str:
    """Maiúsculas sem acentos, para comparações por palavra-chave."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in decomposed if not unicodedata.combining(c)).upper()


@dataclass
class Asset:
    """Um bem que pode entrar em um lote."""

    tipo: str = "Bens Móveis"
    codigo: str = ""
    conta_credito: str = ""
    conta_debito: str = ""
    descricao: str = ""
    valor_contabil: Decimal | None = None
    origem: str = ""
    categoria: str = "Outros"
    lote: str = ""
    observacao: str = ""
    row: int = 0  # ordem original no arquivo de entrada

    @property
    def incluido(self) -> bool:
        return bool(self.lote.strip())


@dataclass
class Lot:
    """Um lote e o valor pelo qual foi (ou será) vendido."""

    numero: str
    valor: Decimal
    grupo: str
    secao: str
    valor_avaliado: Decimal | None = None
    descricao_pl: str = ""
    observacao: str = ""
    row: int = 0

    @property
    def numero_int(self) -> int:
        try:
            return int(self.numero)
        except ValueError:
            return 10**9


@dataclass
class Group:
    """Uma aba do relatório (Prefeitura, Educação, Saúde...)."""

    nome: str
    aba: str
    ordem: int = 0
    titulo: str = "MUNICÍPIO DE EXEMPLO"
    subtitulo: str = ""
    conta: str = ""
    agencia: str = "0000-0 (Banco de Exemplo)"
    conta_corrente: str = ""
    cnpj: str = ""


@dataclass
class LawLot:
    """Lote descrito no projeto de lei."""

    numero: str
    descricao: str
    valor_avaliado: Decimal | None
    codigo_bem: str | None
    categoria: str


@dataclass
class Issue:
    """Erro ou aviso de validação."""

    nivel: str  # "erro" ou "aviso"
    mensagem: str
    linha: int | None = None
    aba: str | None = None

    def __str__(self) -> str:
        onde = []
        if self.aba:
            onde.append(self.aba)
        if self.linha:
            onde.append(f"linha {self.linha}")
        prefixo = f"[{', '.join(onde)}] " if onde else ""
        return f"{self.nivel.upper()}: {prefixo}{self.mensagem}"


@dataclass
class LotResult:
    """Resultado do rateio de um lote."""

    lote: Lot
    bens: list[Asset]
    valores: list[Decimal]

    @property
    def soma(self) -> Decimal:
        return sum(self.valores, Decimal("0.00"))

    @property
    def fecha(self) -> bool:
        return self.soma == self.lote.valor


@dataclass
class ReportData:
    grupos: list[Group] = field(default_factory=list)
    lotes: list[Lot] = field(default_factory=list)
    bens: list[Asset] = field(default_factory=list)
    resultados: list[LotResult] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def erros(self) -> list[Issue]:
        return [i for i in self.issues if i.nivel == "erro"]

    @property
    def avisos(self) -> list[Issue]:
        return [i for i in self.issues if i.nivel == "aviso"]
