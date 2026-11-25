import contextlib
import copy
import io
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from leilao.banco import BANCO_NOME, caminho_banco, criar_estrutura
from leilao.cli import main
from leilao.entrada import DEFAULT_GROUPS, write_entrada
from leilao.models import Asset, Issue, Lot, ReportData


def _grupos():
    return [copy.deepcopy(DEFAULT_GROUPS["Prefeitura"])]


def _lotes():
    return [
        Lot(numero="01", valor=Decimal("100.00"), grupo="Prefeitura", secao="Bens")
    ]


def _bens():
    return [
        Asset(lote="01", codigo="1", descricao="MESA", categoria="Mobiliário"),
        Asset(lote="01", codigo="2", descricao="CADEIRA", categoria="Mobiliário"),
    ]


class CliTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.raiz = Path(self.pasta.name)

    def tearDown(self):
        self.pasta.cleanup()

    def _rodar(self, *args):
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(saida):
            codigo = main(list(args))
        return codigo, saida.getvalue()

    def test_migrar_conferir_e_exportar(self):
        entrada = self.raiz / "entrada.xlsx"
        leilao = self.raiz / "2025-2"
        write_entrada(entrada, _grupos(), _lotes(), _bens())

        codigo, saida = self._rodar(
            "migrar", str(entrada), "--pasta", str(leilao)
        )
        self.assertEqual(codigo, 0, saida)
        self.assertTrue(caminho_banco(leilao).exists())

        codigo, saida = self._rodar("conferir", str(caminho_banco(leilao)))
        self.assertEqual(codigo, 0, saida)
        self.assertIn("Tudo certo", saida)

        codigo, saida = self._rodar(
            "exportar",
            str(caminho_banco(leilao)),
            "--formato",
            "xlsx",
            "--saida",
            str(leilao / "exportacoes"),
            "--nome",
            "relatorio",
        )
        self.assertEqual(codigo, 0, saida)
        self.assertTrue((leilao / "exportacoes" / "relatorio.xlsx").exists())

    def test_novo_cria_pasta_e_copia_documentos(self):
        prefeitura = self.raiz / "prefeitura.pdf"
        pl = self.raiz / "pl.pdf"
        prefeitura.write_bytes(b"%PDF prefeitura")
        pl.write_bytes(b"%PDF pl")
        leilao = self.raiz / "2026-1"
        data = ReportData(grupos=_grupos(), lotes=_lotes(), bens=_bens())

        with mock.patch(
            "leilao.cli.importar_pdfs",
            return_value=(
                data.grupos,
                data.lotes,
                data.bens,
                [Issue("aviso", "importação de teste")],
            ),
        ):
            codigo, saida = self._rodar(
                "novo",
                "--prefeitura",
                str(prefeitura),
                "--pl",
                str(pl),
                "--pasta",
                str(leilao),
            )

        self.assertEqual(codigo, 0, saida)
        self.assertTrue(caminho_banco(leilao).exists())
        self.assertTrue((leilao / "documentos" / "prefeitura.pdf").exists())
        self.assertTrue((leilao / "documentos" / "pl.pdf").exists())

    def test_novo_continua_quando_documentos_falham(self):
        prefeitura = self.raiz / "prefeitura.pdf"
        prefeitura.write_bytes(b"%PDF")
        leilao = self.raiz / "2026-1"
        data = ReportData(grupos=_grupos(), lotes=_lotes(), bens=_bens())

        with mock.patch(
            "leilao.cli.importar_pdfs",
            return_value=(data.grupos, data.lotes, data.bens, []),
        ), mock.patch(
            "leilao.cli.copiar_documentos", side_effect=OSError("sem permissão")
        ):
            codigo, saida = self._rodar(
                "novo", "--prefeitura", str(prefeitura), "--pasta", str(leilao)
            )

        self.assertEqual(codigo, 0, saida)
        self.assertIn("AVISO", saida)
        self.assertTrue(caminho_banco(leilao).exists())

    def test_novo_recusa_pasta_com_leilao(self):
        leilao = self.raiz / "2026-1"
        criar_estrutura(leilao)
        (leilao / BANCO_NOME).write_bytes(b"x")
        prefeitura = self.raiz / "prefeitura.pdf"
        prefeitura.write_bytes(b"%PDF")
        codigo, saida = self._rodar(
            "novo", "--prefeitura", str(prefeitura), "--pasta", str(leilao)
        )
        self.assertEqual(codigo, 1)
        self.assertIn("já existe", saida)


if __name__ == "__main__":
    unittest.main()
