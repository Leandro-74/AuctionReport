"""Dinheiro com duas casas decimais e rateio que fecha exatamente."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP

CENT = Decimal("0.01")


def parse_money(value: object) -> Decimal:
    """Converte número ou texto (inclusive ``R$ 1.234,56``) em Decimal de 2 casas.

    Aceita também ``1234.56``. Em textos com apenas um ponto e três dígitos
    depois dele (ex.: ``1.234``), o ponto é tratado como separador de milhar.
    """
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, bool):
        raise ValueError("valor booleano não é dinheiro")
    elif isinstance(value, (int, float)):
        result = Decimal(str(value))
    elif isinstance(value, str):
        text = value.strip().replace("\xa0", " ").replace("R$", "").strip()
        if not text:
            raise ValueError("valor vazio")
        text = text.replace(" ", "")
        if "," in text:
            # Formato brasileiro: 1.234,56
            text = text.replace(".", "").replace(",", ".")
        elif text.count(".") == 1:
            inteiro, decimal = text.split(".")
            # "1.234" costuma ser mil duzentos e trinta e quatro; "0.234" é decimal.
            if len(decimal) == 3 and inteiro not in ("", "0"):
                text = inteiro + decimal
        try:
            result = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"valor inválido: {value!r}") from exc
    else:
        raise ValueError(f"valor não numérico: {value!r}")

    try:
        return result.quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError(f"valor inválido: {value!r}") from exc


def format_brl(value: Decimal, symbol: bool = True) -> str:
    """Formata ``1234.5`` como ``R$ 1.234,50``."""
    value = value.quantize(CENT, rounding=ROUND_HALF_UP)
    negative = value < 0
    text = f"{abs(value):,.2f}"
    text = text.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'-' if negative else ''}{'R$ ' if symbol else ''}{text}"


def distribute(total: Decimal, count: int) -> list[Decimal]:
    """Divide ``total`` em ``count`` parcelas de no máximo 2 casas.

    As primeiras ``count - 1`` parcelas recebem o quociente truncado em duas
    casas; a última recebe o que sobrar. Assim a soma é sempre exatamente
    ``total`` e nenhuma parcela tem mais de duas casas decimais.

    Exemplo: 50,00 em 211 parcelas -> 210 x 0,23 e a última 1,70.
    """
    if count <= 0:
        raise ValueError("a quantidade de bens deve ser maior que zero")

    total = total.quantize(CENT, rounding=ROUND_HALF_UP)
    if total < 0:
        raise ValueError("o valor do lote não pode ser negativo")
    if count == 1:
        return [total]

    parcela = (total / count).quantize(CENT, rounding=ROUND_DOWN)
    valores = [parcela] * (count - 1)
    ultima = (total - parcela * (count - 1)).quantize(CENT)
    if ultima < 0:
        raise ValueError("rateio gerou parcela negativa")
    valores.append(ultima)

    if sum(valores) != total:
        raise AssertionError("rateio não fechou o valor do lote")
    return valores
