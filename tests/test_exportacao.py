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
            Asset(
                lote="01",
                codigo="1",
                descricao="MESA",
                categoria="Mobiliário",
                conta_credito="1231102010000000000",
                conta_debito="1231104050000000000",
            ),
            Asset(
                lote="01",
                codigo="2",
                descricao="CADEIRA",
                categoria="Mobiliário",
                conta_credito="1231102010000000000",
                conta_debito="1231104050000000000",
            ),
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

    def test_estilo_do_modelo(self):
        resultado = exportar(_data(), self.destino, nome_base="estilo")
        wb = load_workbook(resultado)

        grupo = wb["Relatório Bens da Prefeitura"]
        self.assertEqual(grupo.column_dimensions["A"].width, 14.43)
        self.assertEqual(grupo.column_dimensions["B"].width, 11.57)
        self.assertEqual(grupo.column_dimensions["C"].width, 17.29)
        self.assertEqual(grupo.column_dimensions["D"].width, 17.29)
        self.assertEqual(grupo.column_dimensions["E"].width, 54.43)
        self.assertEqual(grupo.column_dimensions["F"].width, 19.43)
        self.assertEqual(grupo["A11"].fill.fgColor.rgb, "FFD9D9D9")
        self.assertEqual(grupo["A11"].border.left.color.rgb, "FF999999")
        self.assertEqual(grupo["A13"].border.bottom.color.rgb, "FF999999")
        self.assertEqual(grupo["A13"].fill.fgColor.rgb, "FFF2F2F2")
        self.assertNotEqual(
            grupo["A12"].fill.fgColor.rgb, "FFF2F2F2"
        )

        auxiliar = wb["Relatório Mobiliário em Geral"]
        self.assertEqual(auxiliar.column_dimensions["A"].width, 14.43)
        self.assertEqual(auxiliar.column_dimensions["B"].width, 11.57)
        self.assertEqual(auxiliar.column_dimensions["C"].width, 17.29)
        self.assertEqual(auxiliar.column_dimensions["D"].width, 54.43)
        self.assertEqual(auxiliar.column_dimensions["E"].width, 19.43)
        self.assertNotEqual(
            auxiliar["A5"].fill.fgColor.rgb, "FFF2F2F2"
        )
        self.assertEqual(auxiliar["A6"].fill.fgColor.rgb, "FFF2F2F2")
        wb.close()

    def test_codigos_como_texto(self):
        resultado = exportar(_data(), self.destino, nome_base="codigos")
        wb = load_workbook(resultado)
        grupo = wb["Relatório Bens da Prefeitura"]
        self.assertEqual(grupo["B12"].value, "1")
        self.assertEqual(grupo["B12"].data_type, "s")
        self.assertEqual(grupo["B12"].number_format, "@")
        self.assertEqual(grupo["C12"].value, "1231102010")
        self.assertEqual(grupo["C12"].data_type, "s")
        self.assertEqual(grupo["C12"].number_format, "@")
        self.assertEqual(grupo["D12"].value, "1231104050")
        self.assertEqual(grupo["D12"].data_type, "s")
        self.assertEqual(grupo["D12"].number_format, "@")
        wb.close()

    def test_altura_da_linha_acompanha_a_descricao(self):
        data = _data()
        data.bens[0].descricao = "PALAVRA " * 40
        data.resultados = []
        data.issues = []
        build_results(data)
        resultado = exportar(data, self.destino, nome_base="altura")
        wb = load_workbook(resultado)
        grupo = wb["Relatório Bens da Prefeitura"]
        self.assertGreater(grupo.row_dimensions[12].height, 15.75 * 2)
        wb.close()

    def test_nao_exporta_venda_nao_realizada(self):
        data = _data()
        data.venda_realizada = False
        with self.assertRaises(ValueError) as ctx:
            exportar(data, self.destino, nome_base="sem-venda")
        self.assertIn("ainda não foi realizada", str(ctx.exception))
        self.assertFalse((self.destino / "sem-venda.xlsx").exists())

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
