import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from openpyxl import Workbook

from leilao.pdf_export import (
    PdfExportError,
    converter_xlsx_para_pdf,
    encontrar_soffice,
    nome_seguro_pdf,
)


class PdfExportTests(unittest.TestCase):
    def test_encontra_pelo_env(self):
        with tempfile.TemporaryDirectory() as temp:
            executavel = Path(temp) / "soffice"
            executavel.write_text("#!/bin/sh\n", encoding="utf-8")
            with mock.patch.dict(
                os.environ, {"SOFFICE_PATH": str(executavel)}, clear=False
            ):
                self.assertEqual(encontrar_soffice(), executavel)

    def test_arquivo_inexistente(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(PdfExportError) as ctx:
                converter_xlsx_para_pdf(
                    Path(temp) / "nao_existe.xlsx",
                    Path(temp) / "saida.pdf",
                )
            self.assertIn("não encontrada", str(ctx.exception))

    def test_sem_libreoffice(self):
        with tempfile.TemporaryDirectory() as temp:
            xlsx = Path(temp) / "relatorio.xlsx"
            wb = Workbook()
            wb.active["A1"] = "teste"
            wb.save(xlsx)
            with mock.patch(
                "leilao.pdf_export.encontrar_soffice", return_value=None
            ):
                with self.assertRaises(PdfExportError) as ctx:
                    converter_xlsx_para_pdf(xlsx, Path(temp) / "saida.pdf")
            self.assertIn("LibreOffice não encontrado", str(ctx.exception))

    def test_nome_seguro(self):
        self.assertEqual(nome_seguro_pdf("Relatório Leilão 2026"), "relatorio-leilao-2026.pdf")
        self.assertEqual(nome_seguro_pdf(""), "relatorio.pdf")

    @unittest.skipIf(os.name == "nt", "teste usa um script shell")
    def test_conversao_com_executavel_falso(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            falso = temp / "soffice"
            falso.write_text(
                "#!/bin/sh\n"
                "outdir=''\n"
                "input=''\n"
                "prev=''\n"
                "for arg in \"$@\"; do\n"
                "  if [ \"$prev\" = '--outdir' ]; then outdir=\"$arg\"; fi\n"
                "  prev=\"$arg\"\n"
                "  input=\"$arg\"\n"
                "done\n"
                "base=$(basename \"$input\" .xlsx)\n"
                "printf '%%PDF-1.4 fake\\n' > \"$outdir/$base.pdf\"\n",
                encoding="utf-8",
            )
            falso.chmod(0o755)
            xlsx = temp / "relatorio.xlsx"
            pdf = temp / "saida.pdf"
            wb = Workbook()
            wb.active["A1"] = "teste"
            wb.save(xlsx)
            with mock.patch.dict(
                os.environ, {"SOFFICE_PATH": str(falso)}, clear=False
            ):
                convertido = converter_xlsx_para_pdf(xlsx, pdf)
            self.assertEqual(convertido, pdf.resolve())
            self.assertTrue(pdf.exists())
            self.assertEqual(pdf.read_bytes()[:4], b"%PDF")

    @unittest.skipUnless(encontrar_soffice(), "LibreOffice não encontrado")
    def test_conversao_real(self):
        with tempfile.TemporaryDirectory() as temp:
            xlsx = Path(temp) / "relatorio.xlsx"
            pdf = Path(temp) / "saida.pdf"
            wb = Workbook()
            wb.active["A1"] = "Relatório de teste"
            wb.save(xlsx)
            converter_xlsx_para_pdf(xlsx, pdf)
            self.assertTrue(pdf.exists())
            self.assertEqual(pdf.read_bytes()[:4], b"%PDF")


if __name__ == "__main__":
    unittest.main()
