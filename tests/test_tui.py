import copy
import os
import unittest
from decimal import Decimal
from unittest import mock

from leilao.entrada import DEFAULT_GROUPS, build_results
from leilao.models import Asset, Group, Lot, ReportData
from leilao.tui import _limpar_caminho, _pedir_caminho, _resumo_grupo


def _data_nao_vendida():
    data = ReportData(
        grupos=[
            copy.deepcopy(DEFAULT_GROUPS["Prefeitura"]),
            copy.deepcopy(DEFAULT_GROUPS["Saúde"]),
        ],
        lotes=[
            Lot(
                numero="01",
                valor=Decimal("0.00"),
                valor_avaliado=Decimal("100.00"),
                valor_informado=False,
                grupo="Prefeitura",
                secao="Bens",
            ),
            Lot(
                numero="02",
                valor=Decimal("0.00"),
                valor_avaliado=Decimal("50.00"),
                valor_informado=False,
                grupo="Saúde",
                secao="Bens",
            ),
        ],
        bens=[
            Asset(lote="01", descricao="MESA", origem="Prefeitura"),
            Asset(lote="01", descricao="CADEIRA", origem="Prefeitura"),
            Asset(lote="02", descricao="MACA", origem="Saúde"),
        ],
        venda_realizada=False,
    )
    build_results(data)
    return data


class PedirCaminhoTests(unittest.TestCase):
    def test_enter_abre_o_seletor(self):
        with (
            mock.patch(
                "leilao.tui.dialogos.disponivel", return_value=True
            ),
            mock.patch("leilao.tui.Prompt.ask", return_value=""),
            mock.patch(
                "leilao.tui.dialogos.selecionar_arquivo",
                return_value="/tmp/arquivo.pdf",
            ) as selecionar,
        ):
            caminho = _pedir_caminho(
                "Abrir", "teste", opcional=True, extensoes=("pdf",)
            )
        self.assertEqual(caminho, "/tmp/arquivo.pdf")
        selecionar.assert_called_once_with("Abrir", ("pdf",))

    def test_hifen_pula_sem_abrir_seletor(self):
        with (
            mock.patch(
                "leilao.tui.dialogos.disponivel", return_value=True
            ),
            mock.patch("leilao.tui.Prompt.ask", return_value="-"),
            mock.patch(
                "leilao.tui.dialogos.selecionar_arquivo"
            ) as selecionar,
        ):
            caminho = _pedir_caminho("Abrir", "teste", opcional=True)
        self.assertEqual(caminho, "")
        selecionar.assert_not_called()

    def test_sem_seletor_enter_cancela(self):
        with (
            mock.patch(
                "leilao.tui.dialogos.disponivel", return_value=False
            ),
            mock.patch("leilao.tui.Prompt.ask", return_value=""),
            mock.patch(
                "leilao.tui.dialogos.selecionar_arquivo"
            ) as selecionar,
        ):
            caminho = _pedir_caminho("Abrir", "teste")
        self.assertEqual(caminho, "")
        selecionar.assert_not_called()


class ResumoGrupoTests(unittest.TestCase):
    def test_conta_lotes_e_bens_de_venda_nao_realizada(self):
        data = _data_nao_vendida()
        self.assertEqual(
            _resumo_grupo(data, "Prefeitura"), (1, 2, Decimal("100.00"))
        )
        self.assertEqual(
            _resumo_grupo(data, "Saúde"), (1, 1, Decimal("50.00"))
        )

    def test_nao_avisa_grupo_sem_lotes_quando_venda_nao_realizada(self):
        data = _data_nao_vendida()
        self.assertFalse(
            [i for i in data.issues if "não tem lotes" in i.mensagem],
            [str(i) for i in data.issues],
        )

    def test_avisa_grupo_realmente_sem_lotes(self):
        data = _data_nao_vendida()
        data.grupos.append(Group(nome="Vazio", aba="Relatório Vazio"))
        data.issues = []
        build_results(data)
        avisos = [i for i in data.issues if "não tem lotes" in i.mensagem]
        self.assertEqual(len(avisos), 1, [str(i) for i in data.issues])
        self.assertIn("Vazio", avisos[0].mensagem)


class CaminhoTests(unittest.TestCase):
    def test_vazio(self):
        self.assertEqual(_limpar_caminho(""), "")
        self.assertEqual(_limpar_caminho("   "), "")

    def test_caminho_simples(self):
        self.assertEqual(_limpar_caminho("/tmp/leilao.pdf"), "/tmp/leilao.pdf")

    def test_caminho_com_espacos_sem_escape(self):
        self.assertEqual(
            _limpar_caminho("/tmp/Meu Arquivo.pdf"),
            "/tmp/Meu Arquivo.pdf",
        )

    @unittest.skipIf(os.name == "nt", "escape de shell é usado no Linux")
    def test_caminho_arrastado_com_espacos_escapados(self):
        self.assertEqual(
            _limpar_caminho("/tmp/Meu\\ Arquivo.pdf"),
            "/tmp/Meu Arquivo.pdf",
        )

    @unittest.skipIf(os.name == "nt", "escape de shell é usado no Linux")
    def test_caminho_arrastado_entre_aspas(self):
        self.assertEqual(
            _limpar_caminho("'/tmp/Meu Arquivo.pdf'"),
            "/tmp/Meu Arquivo.pdf",
        )
        self.assertEqual(
            _limpar_caminho('"/tmp/Meu Arquivo.pdf"'),
            "/tmp/Meu Arquivo.pdf",
        )

    def test_arquivo_uri(self):
        self.assertEqual(
            _limpar_caminho("file:///tmp/Meu%20Arquivo.pdf"),
            "/tmp/Meu Arquivo.pdf",
        )

    def test_caminho_do_windows(self):
        self.assertEqual(
            _limpar_caminho(r"C:\Users\Example\leilao.pdf"),
            r"C:\Users\Example\leilao.pdf",
        )


if __name__ == "__main__":
    unittest.main()
