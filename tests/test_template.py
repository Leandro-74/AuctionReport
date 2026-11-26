import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from leilao.entrada import DEFAULT_GROUPS, ler_entrada, write_entrada
from leilao.models import Asset, Lot
from leilao.relatorio import gerar_relatorio

MOEDA = '[$R$ -416]#,##0.00'


def _grupos():
    return [DEFAULT_GROUPS["Prefeitura"], DEFAULT_GROUPS["Saúde"]]


def _lotes():
    return [
        Lot(numero="01", valor=Decimal("100.00"), grupo="Prefeitura", secao="Veículos"),
        Lot(
            numero="02",
            valor=Decimal("50.00"),
            grupo="Prefeitura",
            secao="Mobiliário em Geral",
        ),
        Lot(numero="03", valor=Decimal("80.00"), grupo="Saúde", secao="Veículos"),
        Lot(
            numero="04",
            valor=Decimal("40.00"),
            grupo="Saúde",
            secao="Equipamentos e mobiliários hospitalares em geral",
        ),
        Lot(
            numero="05",
            valor=Decimal("30.00"),
            grupo="Prefeitura",
            secao="Equipamentos de Informática",
        ),
    ]


def _bens():
    return [
        Asset(lote="01", codigo="1", descricao="VEÍCULO A", categoria="Veículos"),
        Asset(lote="02", codigo="2", descricao="MESA A", categoria="Mobiliário"),
        Asset(lote="02", codigo="3", descricao="CADEIRA A", categoria="Mobiliário"),
        Asset(lote="03", codigo="4", descricao="VEÍCULO B", categoria="Veículos"),
        Asset(lote="04", codigo="5", descricao="MACA", categoria="Hospitalar"),
        Asset(lote="05", codigo="6", descricao="CPU", categoria="Informática"),
    ]


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.entrada = Path(self.pasta.name) / "entrada.xlsx"
        self.saida = Path(self.pasta.name) / "relatorio.xlsx"
        write_entrada(self.entrada, _grupos(), _lotes(), _bens())
        self.data = ler_entrada(self.entrada)
        self.assertFalse(self.data.erros, [str(e) for e in self.data.erros])
        gerar_relatorio(self.data, self.saida)
        self.wb = load_workbook(self.saida)

    def tearDown(self):
        self.pasta.cleanup()

    def test_abas_do_modelo(self):
        self.assertEqual(
            self.wb.sheetnames,
            [
                "Relatório Bens da Prefeitura",
                "Relatório Bens da Saúde",
                "Relatório Todos os Veículos",
                "Relatório Veículos",
                "Relatório Veículos Hospital",
                "Relatório Mobiliário em Geral",
                "Relatório Mobiliário em Geral H",
                "Relatório Itens de Informática",
                "Conta Município",
                "Conta Fundo Municipal de Saude",
            ],
        )
        self.assertNotIn("Resumo", self.wb.sheetnames)

    def test_aba_principal(self):
        ws = self.wb["Relatório Bens da Prefeitura"]
        self.assertEqual(ws["A1"].font.name, "Calibri")
        self.assertEqual(ws["A1"].font.sz, 13)
        self.assertTrue(ws["A1"].font.b)
        self.assertEqual(ws["A1"].fill.fgColor.rgb, "FFD9D9D9")
        self.assertEqual(ws["A1"].alignment.horizontal, "center")
        self.assertTrue(ws["A2"].alignment.wrap_text)
        self.assertEqual(ws["A4"].font.name, "Arial")
        self.assertTrue(ws["A4"].font.b)
        self.assertEqual(ws["A4"].fill.fgColor.rgb, "FFD9D9D9")
        self.assertEqual(ws["A5"].font.name, "Arial")
        self.assertFalse(ws["A5"].font.b)
        self.assertEqual(ws["A8"].alignment.horizontal, "right")

        self.assertEqual(ws["A11"].font.sz, 13)
        self.assertTrue(ws["A11"].font.b)
        self.assertEqual(ws["A11"].fill.fgColor.rgb, "FFD9D9D9")
        self.assertEqual(ws["A11"].border.left.style, "thin")
        self.assertIsNone(ws["A11"].alignment.horizontal)
        self.assertEqual(ws["F11"].number_format, MOEDA)

        self.assertEqual(ws["A12"].font.sz, 11)
        self.assertEqual(ws["A12"].border.left.style, "thin")
        self.assertIsNone(ws["A12"].alignment.horizontal)
        self.assertTrue(ws["A12"].alignment.wrap_text)
        self.assertEqual(ws["F12"].number_format, MOEDA)

        self.assertEqual(ws.column_dimensions["A"].width, 14.43)
        self.assertEqual(ws.column_dimensions["B"].width, 11.57)
        self.assertEqual(ws.column_dimensions["C"].width, 17.29)
        self.assertEqual(ws.column_dimensions["D"].width, 17.29)
        self.assertEqual(ws.column_dimensions["E"].width, 54.43)
        self.assertEqual(ws.column_dimensions["F"].width, 19.43)
        self.assertEqual(ws.column_dimensions["G"].width, 7.63)

        self.assertEqual(ws.row_dimensions[1].height, 21.75)
        self.assertEqual(ws.row_dimensions[2].height, 15.75)
        self.assertEqual(ws.row_dimensions[3].height, 21.75)
        self.assertEqual(ws.row_dimensions[4].height, 15)
        self.assertEqual(ws.row_dimensions[9].height, 21.75)

        self.assertIsNone(ws.sheet_view.showGridLines)
        self.assertEqual(ws.page_setup.orientation, "portrait")
        self.assertEqual(int(ws.page_setup.paperSize), 9)
        self.assertIsNone(ws.page_setup.fitToWidth)
        self.assertAlmostEqual(ws.page_margins.left, 0.3937007874015748, places=6)

    def test_aba_auxiliar(self):
        ws = self.wb["Relatório Todos os Veículos"]
        self.assertEqual(ws.max_column, 6)
        self.assertEqual(ws["A1"].fill.fgColor.rgb, "FFD9D9D9")
        self.assertEqual(ws["A2"].fill.fgColor.rgb, "FFD9D9D9")
        self.assertTrue(ws["A2"].alignment.wrap_text)
        self.assertEqual(ws["A4"].value, "Tipo de bem")
        self.assertEqual(ws["B4"].value, "Código")
        self.assertEqual(ws["C4"].value, "Conta Crédito")
        self.assertEqual(ws["D4"].value, "Conta Débito")
        self.assertEqual(ws["E4"].value, "Descrição")
        self.assertEqual(ws["F4"].value, "Valor")
        self.assertEqual(ws["F4"].number_format, MOEDA)
        self.assertEqual(ws["F5"].number_format, MOEDA)
        self.assertEqual(ws["A5"].border.left.style, "thin")
        self.assertEqual(ws.column_dimensions["A"].width, 14.43)
        self.assertEqual(ws.column_dimensions["B"].width, 11.57)
        self.assertEqual(ws.column_dimensions["C"].width, 17.29)
        self.assertEqual(ws.column_dimensions["D"].width, 17.29)
        self.assertEqual(ws.column_dimensions["E"].width, 54.43)
        self.assertEqual(ws.column_dimensions["F"].width, 19.43)
        self.assertEqual(ws.column_dimensions["G"].width, 7.63)
        self.assertEqual(ws.row_dimensions[3].height, 21.75)
        self.assertIsNone(ws.sheet_view.showGridLines)

    def test_aba_auxiliar_sem_conta_credito(self):
        ws = self.wb["Relatório Veículos"]
        self.assertEqual(ws.max_column, 5)
        self.assertEqual(ws["A4"].value, "Tipo de bem")
        self.assertEqual(ws["B4"].value, "Código")
        self.assertEqual(ws["C4"].value, "Conta Débito")
        self.assertEqual(ws["D4"].value, "Descrição")
        self.assertEqual(ws["E4"].value, "Valor")
        self.assertEqual(ws["E4"].number_format, MOEDA)
        self.assertEqual(ws.column_dimensions["A"].width, 14.43)
        self.assertEqual(ws.column_dimensions["B"].width, 11.57)
        self.assertEqual(ws.column_dimensions["C"].width, 17.29)
        self.assertEqual(ws.column_dimensions["D"].width, 54.43)
        self.assertEqual(ws.column_dimensions["E"].width, 19.43)

    def test_aba_de_conta(self):
        ws = self.wb["Conta Município"]
        self.assertEqual(ws.max_column, 4)
        self.assertEqual(ws["A1"].font.name, "Calibri")
        self.assertTrue(ws["A1"].font.b)
        self.assertEqual(ws["A1"].fill.fgColor.rgb, "FFD9D9D9")
        self.assertEqual(ws["A3"].font.name, "Arial")
        self.assertTrue(ws["A3"].font.b)
        self.assertEqual(ws["A3"].fill.fgColor.rgb, "FFD9D9D9")
        self.assertEqual(ws["A7"].alignment.horizontal, "right")
        self.assertEqual(ws.column_dimensions["A"].width, 14.38)
        self.assertEqual(ws.column_dimensions["C"].width, 54.63)
        self.assertIsNone(ws.sheet_view.showGridLines)


if __name__ == "__main__":
    unittest.main()
