import copy
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from openpyxl import load_workbook

from leilao.entrada import DEFAULT_GROUPS, build_results
from leilao.exportacao import exportar
from leilao.models import Asset, Lot, ReportData
from leilao.pdf_export import PdfExportError


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
        resultado = exportar(_data(), self.destino, "xlsx", nome_base="teste")
        self.assertTrue(resultado.xlsx.exists())
        self.assertIsNone(resultado.pdf)
        wb = load_workbook(resultado.xlsx)
        self.assertIn("Relatório Bens da Prefeitura", wb.sheetnames)
        wb.close()

    def test_pdf_sem_libreoffice(self):
        with mock.patch(
            "leilao.exportacao.converter_xlsx_para_pdf",
            side_effect=PdfExportError("sem LibreOffice"),
        ):
            with self.assertRaises(PdfExportError) as ctx:
                exportar(_data(), self.destino, "pdf", nome_base="teste")
        self.assertIn("teste.xlsx", str(ctx.exception))
        self.assertTrue((self.destino / "teste.xlsx").exists())
        self.assertFalse((self.destino / "teste.pdf").exists())

    def test_exporta_ambos(self):
        def converte(xlsx, pdf):
            Path(pdf).write_bytes(b"%PDF-1.4 teste")
            return Path(pdf)

        with mock.patch(
            "leilao.exportacao.converter_xlsx_para_pdf", side_effect=converte
        ) as mock_convert:
            resultado = exportar(
                _data(), self.destino, "ambos", nome_base="teste"
            )
        self.assertTrue(resultado.xlsx.exists())
        self.assertTrue(resultado.pdf.exists())
        mock_convert.assert_called_once()
        self.assertEqual(mock_convert.call_args.args[0], resultado.xlsx)

    def test_formato_invalido(self):
        with self.assertRaises(ValueError):
            exportar(_data(), self.destino, "odt")

    def test_nao_exporta_leilao_vazio(self):
        data = ReportData(
            grupos=[copy.deepcopy(DEFAULT_GROUPS["Prefeitura"])],
            lotes=[],
            bens=[],
        )
        build_results(data)
        with self.assertRaises(ValueError) as ctx:
            exportar(data, self.destino, "xlsx", nome_base="vazio")
        self.assertIn("não tem lotes", str(ctx.exception))
        self.assertFalse((self.destino / "vazio.xlsx").exists())

    def test_nome_repetido_recebe_sufixo(self):
        primeiro = exportar(_data(), self.destino, "xlsx", nome_base="teste")
        segundo = exportar(_data(), self.destino, "xlsx", nome_base="teste")
        self.assertEqual(primeiro.xlsx.name, "teste.xlsx")
        self.assertEqual(segundo.xlsx.name, "teste_2.xlsx")

    def test_nome_invalido_nao_sai_da_pasta(self):
        resultado = exportar(_data(), self.destino, "xlsx", nome_base="../fora")
        self.assertEqual(resultado.xlsx.parent, self.destino)
        self.assertEqual(resultado.xlsx.name, "fora.xlsx")


if __name__ == "__main__":
    unittest.main()
