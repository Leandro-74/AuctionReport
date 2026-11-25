import unittest
from decimal import Decimal

from leilao.money import distribute, format_brl, parse_money


class MoneyTests(unittest.TestCase):
    def test_parse_brl(self):
        self.assertEqual(parse_money("R$ 1.234,56"), Decimal("1234.56"))
        self.assertEqual(parse_money("1.234,56"), Decimal("1234.56"))
        self.assertEqual(parse_money("1234.56"), Decimal("1234.56"))
        self.assertEqual(parse_money("1.234"), Decimal("1234.00"))
        self.assertEqual(parse_money(0.23), Decimal("0.23"))

    def test_valor_invalido(self):
        with self.assertRaises(ValueError):
            parse_money("1.234.567")
        with self.assertRaises(ValueError):
            parse_money("abc")
        with self.assertRaises(ValueError):
            parse_money("")

    def test_format_brl(self):
        self.assertEqual(format_brl(Decimal("1234.5")), "R$ 1.234,50")
        self.assertEqual(format_brl(Decimal("0.23")), "R$ 0,23")

    def test_lote_14_real(self):
        valores = distribute(Decimal("50.00"), 211)
        self.assertEqual(len(valores), 211)
        self.assertEqual(valores[:210], [Decimal("0.23")] * 210)
        self.assertEqual(valores[-1], Decimal("1.70"))
        self.assertEqual(sum(valores), Decimal("50.00"))

    def test_divisao_simples(self):
        self.assertEqual(
            distribute(Decimal("100.00"), 3),
            [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")],
        )

    def test_valor_pequeno(self):
        self.assertEqual(
            distribute(Decimal("0.05"), 3),
            [Decimal("0.01"), Decimal("0.01"), Decimal("0.03")],
        )
        self.assertEqual(
            distribute(Decimal("0.01"), 3),
            [Decimal("0.00"), Decimal("0.00"), Decimal("0.01")],
        )

    def test_exato_em_uma_parcela(self):
        self.assertEqual(distribute(Decimal("850.00"), 1), [Decimal("850.00")])
        self.assertEqual(distribute(Decimal("850.00"), 5), [Decimal("170.00")] * 5)

    def test_sempre_fecha_e_duas_casas(self):
        for total in ("0.01", "0.02", "0.07", "1.00", "50.00", "100.00", "427900.00"):
            for count in (1, 2, 3, 4, 5, 7, 13, 34, 38, 211):
                valores = distribute(Decimal(total), count)
                self.assertEqual(sum(valores), Decimal(total))
                for valor in valores:
                    self.assertEqual(valor, valor.quantize(Decimal("0.01")))
                    self.assertGreaterEqual(valor, Decimal("0.00"))


if __name__ == "__main__":
    unittest.main()
