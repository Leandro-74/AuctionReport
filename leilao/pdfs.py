"""Leitura dos PDFs do sistema e do projeto de lei."""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from .models import Asset, LawLot, norm
from .money import parse_money

# Palavras-chave para classificar os bens. A ordem importa: veículo primeiro,
# depois saúde, mobiliário, informática e hospitalar.
VEHICLE_HINTS = (
    "RENAVAM",
    "CHASSI",
    "VEICULO",
    "CAMINHAO",
    "CAMINH",
    "AUTOMOVEL",
    "TRATOR",
    "RETRO",
    "ESCAVADEIRA",
    "MOTO",
    "ONIBUS",
    "MINIBUS",
    "PIPA",
    "CACAMBA",
    "ATEGO",
    "ATRON",
    "CARGO",
    "SPIN",
    "VOYAGE",
    "GOL",
    "UNO",
    "HB20",
    "AGILE",
    "DUCATO",
    "CLASSIC",
)

IT_HINTS = (
    "CPU",
    "MONITOR",
    "COMPUTADOR",
    "MICROCOMPUTADOR",
    "NETBOOK",
    "NOTEBOOK",
    "IMPRESSORA",
    "RELOGIO PONTO",
    "TELEVISAO",
    "NOBREAK",
    "ALARME",
    "CAMERA",
    "CENTRAL TELEFONICA",
    "DATA SHOW",
    "PROJETOR",
    "GABINETE",
    "CAIXA DE SOM",
    "RECEPTOR",
    "PARABOLICA",
    "ESTABILIZADOR",
    "SCANNER",
    "MODEM",
    "ROTEADOR",
    "SWITCH",
    "PEN DRIVE",
    "MEMORIA",
    "HD ",
    "ALL IN ONE",
)

HOSPITAL_HINTS = (
    "MACA ",
    "HASTE P/ SORO",
    "HASTE DE SORO",
    "DETECTOR FETAL",
    "NEGATOSCOPIO",
    "BIOMBO",
    "HOSPITALAR",
    "CADEIRA DE RODAS",
    "CAMINHA",
    "BERCO",
    "INCUBADORA",
    "AUTOCLAVE",
    "ESTERILIZADOR",
    "SORO",
    "ODONTOLOGICO",
    "RAIO X",
    "ULTRASSOM",
    "ELETROCARDIOGRAMA",
)

FURNITURE_HINTS = (
    "MESA",
    "CADEIRA",
    "ARMARIO",
    "ESTANTE",
    "SOFA",
    "ARQUIVO",
    "BEBEDOURO",
    "GELADEIRA",
    "FOGAO",
    "FORNO",
    "MICROONDAS",
    "PANIFICADORA",
    "LAVADORA",
    "SECADORA",
    "BANCO",
    "CAMA",
    "COLCHAO",
    "QUADRO",
    "VENTILADOR",
    "AR CONDICIONADO",
    "LIXEIRA",
    "MDP",
    "MDF",
    "SUPORTE",
)


class PdfError(Exception):
    """Erro com contexto para o usuário."""


def _hint_in(texto: str, hint: str) -> bool:
    """Casa a palavra-chave sem confundir, por exemplo, MOTO com REMOTO.

    Para palavras curtas (até 4 letras) exige a palavra inteira; para as
    demais aceita plural/derivados (MONITOR -> MONITORES, RETRO -> RETROESCAVADEIRA).
    """
    hint = hint.strip()
    inicio = r"(?<![A-Z0-9])"
    fim = r"(?![A-Z0-9])" if len(hint) <= 4 else ""
    return re.search(inicio + re.escape(hint) + fim, texto) is not None


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ")
    return " ".join(text.split())


def classify_asset(descricao: str, origem: str = "") -> str:
    """Classifica um bem em Veículos, Informática, Hospitalar, Mobiliário/Outros.

    A ordem evita confusões comuns: "MESA P/ COMPUTADOR" é mobiliário, não
    informática; "GABINETE COM PLACA INTEL" é informática. Bens da Saúde são
    tratados como hospitalares, pois entram no lote de equipamentos hospitalares.
    """
    texto = norm(descricao)
    if any(_hint_in(texto, hint) for hint in VEHICLE_HINTS):
        return "Veículos"
    if norm(origem) == "SAUDE":
        return "Hospitalar"
    if any(_hint_in(texto, hint) for hint in FURNITURE_HINTS):
        return "Mobiliário"
    if any(_hint_in(texto, hint) for hint in IT_HINTS):
        return "Informática"
    if any(_hint_in(texto, hint) for hint in HOSPITAL_HINTS):
        return "Hospitalar"
    return "Outros"


def parse_asset_report(path: str | Path, origem: str) -> list[Asset]:
    """Lê um relatório do sistema (BIRT) e devolve os bens encontrados."""
    path = Path(path)
    if not path.exists():
        raise PdfError(f"arquivo não encontrado: {path}")

    bens: list[Asset] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables() or []
                for table in tables:
                    for row in table:
                        if not row or len(row) < 4:
                            continue
                        cells = [clean_text(cell) for cell in row]
                        codigo = cells[1]
                        if not codigo.isdigit():
                            continue
                        descricao = cells[2]
                        if not descricao:
                            raise PdfError(
                                f"{path.name}, página {page_number}: bem {codigo} sem descrição"
                            )
                        valor = None
                        if cells[3]:
                            try:
                                valor = parse_money(cells[3])
                            except ValueError as exc:
                                raise PdfError(
                                    f"{path.name}, página {page_number}, bem {codigo}: "
                                    f"valor contábil inválido ({cells[3]!r})"
                                ) from exc
                        bens.append(
                            Asset(
                                tipo=cells[0] or "Bens Móveis",
                                codigo=codigo,
                                descricao=descricao,
                                valor_contabil=valor,
                                origem=origem,
                                categoria=classify_asset(descricao, origem),
                            )
                        )
    except PdfError:
        raise
    except Exception as exc:  # pdfplumber levanta vários tipos de erro
        raise PdfError(f"não foi possível ler {path.name}: {exc}") from exc

    if not bens:
        raise PdfError(
            f"{path.name}: nenhum bem encontrado. O PDF está no formato do relatório do sistema?"
        )
    return bens


def law_lot_category(descricao: str) -> str:
    texto = norm(descricao)
    if "INFORMATICA" in texto or "ELETRONIC" in texto:
        return "Informática"
    if "HOSPITALAR" in texto:
        return "Hospitalar"
    if "MOBILIARIO" in texto:
        return "Mobiliário"
    if any(_hint_in(texto, hint) for hint in VEHICLE_HINTS):
        return "Veículos"
    return "Outros"


def parse_law(path: str | Path) -> list[LawLot]:
    """Extrai os lotes do projeto de lei (número, descrição, avaliação e patrimônio)."""
    path = Path(path)
    if not path.exists():
        raise PdfError(f"arquivo não encontrado: {path}")

    try:
        with pdfplumber.open(path) as pdf:
            texto = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as exc:
        raise PdfError(f"não foi possível ler {path.name}: {exc}") from exc

    if not texto.strip():
        raise PdfError(f"{path.name}: PDF sem texto (talvez seja digitalizado?)")

    texto = re.sub(r"\s+", " ", texto)
    padrao = re.compile(
        r"LOTE\s+(\d{1,3})\s*:\s*(.*?)"
        r"(?=\s*(?:[IVXLCDM]+\s*[–-]\s*)?LOTE\s+\d{1,3}\s*:|\s*Art\.\s*2º|$)",
        re.IGNORECASE,
    )
    achados = list(padrao.finditer(texto))
    if not achados:
        raise PdfError(
            f"{path.name}: não encontrei os lotes. O texto deve conter 'LOTE 01: ...'."
        )

    lotes: list[LawLot] = []
    for match in achados:
        numero = f"{int(match.group(1)):02d}"
        trecho = match.group(2).strip()

        avaliado = None
        valor_match = re.search(
            r"Avaliado\s+em\s+R\$\s*([\d.]+,\d{2})", trecho, re.IGNORECASE
        )
        if valor_match:
            avaliado = parse_money(valor_match.group(1))

        descricao = re.split(
            r"\s*Avaliado\s+em\s+R\$", trecho, maxsplit=1, flags=re.IGNORECASE
        )[0]
        descricao = descricao.strip(" .;,-–")

        codigo = None
        codigo_match = re.search(
            r"Patrim[oô]nio\s+n[ºo°]?\s*(\d+)", descricao, re.IGNORECASE
        )
        if codigo_match:
            codigo = codigo_match.group(1)

        lotes.append(
            LawLot(
                numero=numero,
                descricao=descricao,
                valor_avaliado=avaliado,
                codigo_bem=codigo,
                categoria=law_lot_category(descricao),
            )
        )

    return lotes
