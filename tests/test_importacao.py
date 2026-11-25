import unittest
from decimal import Decimal
from unittest import mock

from leilao.entrada import importar_pdfs
from leilao.models import Asset, LawLot


def _law():
    return [
        LawLot(
            numero="01",
            descricao="Bem 3500",
            valor_avaliado=Decimal("100.00"),
            codigo_bem="3500",
            categoria="Mobiliário",
        )
    ]


class ImportacaoTests(unittest.TestCase):
    def test_codigo_ambiguo_nao_e_associado(self):
        prefeitura = Asset(
            codigo="3500",
            descricao="MESA",
            origem="Prefeitura",
            categoria="Mobiliário",
        )
        saude = Asset(
            codigo="3500",
            descricao="MACA",
            origem="Saúde",
            categoria="Hospitalar",
        )

        def fake_parse(path, origem):
            return [prefeitura] if origem == "Prefeitura" else [saude]

        with mock.patch(
            "leilao.entrada.parse_asset_report", side_effect=fake_parse
        ), mock.patch("leilao.entrada.parse_law", return_value=_law()):
            grupos, lotes, bens, issues = importar_pdfs(
                [("Prefeitura", "pref.pdf"), ("Saúde", "saude.pdf")],
                "pl.pdf",
            )

        self.assertEqual(len(bens), 2)
        self.assertEqual([bem.lote for bem in bens], ["", ""])
        self.assertEqual(len(lotes), 1)
        self.assertTrue(
            any("aparece em mais de um bem" in issue.mensagem for issue in issues)
        )

    def test_codigo_unico_e_associado(self):
        prefeitura = Asset(
            codigo="3500",
            descricao="MESA",
            origem="Prefeitura",
            categoria="Mobiliário",
        )

        with mock.patch(
            "leilao.entrada.parse_asset_report", return_value=[prefeitura]
        ), mock.patch("leilao.entrada.parse_law", return_value=_law()):
            grupos, lotes, bens, issues = importar_pdfs(
                [("Prefeitura", "pref.pdf")], "pl.pdf"
            )

        self.assertEqual(len(bens), 1)
        self.assertEqual(bens[0].lote, "01")
        self.assertEqual(len(lotes), 1)
        self.assertFalse(
            any("mais de um bem" in issue.mensagem for issue in issues)
        )


if __name__ == "__main__":
    unittest.main()
