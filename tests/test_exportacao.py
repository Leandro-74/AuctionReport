import copy
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from leilao.entrada import DEFAULT_GROUPS, build_results
from leilao.exportacao import exportar
from leilao.models import Asset, Lot, ReportData


def _data():
    data = ReportData(
        grupos=[copy.deepcopy(DEFAULT_GROUPS["Prefeitura"])],
        lotes=[
            Lot(
                numero="01",
                valor=Decimal("100.00"),
                grupo="Prefeitura",
                secao="Bens",
            )
        ],
        bens=[
            Asset(lote="01", codigo="1", descricao="MESA", categoria="Mobiliário"),
            Asset(lote="01", codigo="2", descricao="CADEIRA", categoria="Mobiliário"),
        ],
    )
    build_results(data)
    return data


class ExportacaoTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.destino = Path(self.pasta.name) / "exportacoes"

    def tearDown(self):
        self.pasta.cleanup()

    def test_exporta_xlsx(self):
        resultado = exportar(_data(), self.destino, nome_base="teste")
        self.assertTrue(resultado.exists())
        wb = load_workbook(resultado)
        self.assertIn("Relatório Bens da Prefeitura", wb.sheetnames)
        wb.close()

    def test_nao_exporta_leilao_vazio(self):
        data = ReportData(
            grupos=[copy.deepcopy(DEFAULT_GROUPS["Prefeitura"])],
            lotes=[],
            bens=[],
        )
        build_results(data)
        with self.assertRaises(ValueError) as ctx:
            exportar(data, self.destino, nome_base="vazio")
        self.assertIn("não tem lotes", str(ctx.exception))
        self.assertFalse((self.destino / "vazio.xlsx").exists())

    def test_nome_repetido_recebe_sufixo(self):
        primeiro = exportar(_data(), self.destino, nome_base="teste")
        segundo = exportar(_data(), self.destino, nome_base="teste")
        self.assertEqual(primeiro.name, "teste.xlsx")
        self.assertEqual(segundo.name, "teste_2.xlsx")

    def test_nome_invalido_nao_sai_da_pasta(self):
        resultado = exportar(_data(), self.destino, nome_base="../fora")
        self.assertEqual(resultado.parent, self.destino)
        self.assertEqual(resultado.name, "fora.xlsx")


if __name__ == "__main__":
    unittest.main()
