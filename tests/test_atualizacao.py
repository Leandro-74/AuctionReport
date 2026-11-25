import copy
import unittest
from decimal import Decimal
from unittest import mock

from leilao.atualizacao import planejar_atualizacao
from leilao.entrada import DEFAULT_GROUPS, build_results
from leilao.models import Asset, LawLot, Lot, ReportData


def _data(origens=("Prefeitura",)):
    grupos = [copy.deepcopy(DEFAULT_GROUPS[origem]) for origem in origens]
    lotes = [
        Lot(
            numero=f"{indice:02d}",
            valor=Decimal("100.00"),
            grupo=origem,
            secao="Bens",
        )
        for indice, origem in enumerate(origens, start=1)
    ]
    bens = [
        Asset(
            lote=f"{indice:02d}",
            codigo=str(indice),
            descricao=f"BEM {indice}",
            origem=origem,
            categoria="Mobiliário",
            valor_contabil=Decimal("10.00"),
        )
        for indice, origem in enumerate(origens, start=1)
    ]
    data = ReportData(grupos=grupos, lotes=lotes, bens=bens)
    build_results(data)
    return data


def _bem(codigo, descricao, origem="Prefeitura", valor="10.00"):
    return Asset(
        codigo=codigo,
        descricao=descricao,
        origem=origem,
        categoria="Mobiliário",
        valor_contabil=Decimal(valor),
    )


class AtualizacaoTests(unittest.TestCase):
    def test_detecta_novos_alterados_e_ausentes(self):
        data = _data()
        data.bens.append(
            Asset(
                lote="01",
                codigo="2",
                descricao="BEM 2",
                origem="Prefeitura",
                categoria="Mobiliário",
                valor_contabil=Decimal("10.00"),
            )
        )
        data.bens.append(
            Asset(
                lote="01",
                codigo="3",
                descricao="ESTANTE",
                origem="Prefeitura",
                categoria="Mobiliário",
            )
        )
        novos_pdf = [
            _bem("1", "BEM 1 NOVO", valor="20.00"),
            _bem("2", "BEM 2"),
            _bem("4", "BEM 4"),
        ]
        with mock.patch(
            "leilao.atualizacao.parse_asset_report", return_value=novos_pdf
        ):
            plano = planejar_atualizacao(data, [("Prefeitura", "pref.pdf")])

        self.assertEqual([bem.codigo for bem in plano.novos], ["4"])
        self.assertEqual(len(plano.alterados), 1)
        self.assertEqual(plano.alterados[0].bem.codigo, "1")
        self.assertIn("descricao", plano.alterados[0].campos)
        self.assertIn("valor_contabil", plano.alterados[0].campos)
        self.assertEqual([bem.codigo for bem in plano.ausentes], ["3"])
        self.assertTrue(plano.tem_mudancas)

        plano.aplicar(data)
        bem1 = next(bem for bem in data.bens if bem.codigo == "1")
        self.assertEqual(bem1.descricao, "BEM 1 NOVO")
        self.assertEqual(bem1.valor_contabil, Decimal("20.00"))
        self.assertIn("4", [bem.codigo for bem in data.bens])
        self.assertIn("3", [bem.codigo for bem in data.bens])

    def test_cria_lote_do_projeto_de_lei(self):
        data = _data()
        novo = _bem("2", "BEM NOVO")
        law = [
            LawLot(
                numero="02",
                descricao="Mobiliário",
                valor_avaliado=Decimal("50.00"),
                codigo_bem="2",
                categoria="Mobiliário",
            )
        ]
        with mock.patch(
            "leilao.atualizacao.parse_asset_report", return_value=[novo]
        ), mock.patch(
            "leilao.atualizacao.parse_law", return_value=law
        ):
            plano = planejar_atualizacao(
                data, [("Prefeitura", "pref.pdf")], "pl.pdf"
            )

        self.assertEqual(plano.novos[0].lote, "02")
        self.assertEqual(len(plano.novos_lotes), 1)
        self.assertEqual(plano.novos_lotes[0].numero, "02")
        self.assertEqual(plano.novos_lotes[0].grupo, "Prefeitura")
        self.assertEqual(plano.novos_lotes[0].valor, Decimal("50.00"))

        plano.aplicar(data)
        self.assertIn("02", [lote.numero for lote in data.lotes])
        self.assertEqual(
            next(bem for bem in data.bens if bem.codigo == "2").lote, "02"
        )

    def test_codigo_ambiguo_nao_recebe_lote(self):
        data = _data(("Prefeitura", "Saúde"))
        novo = _bem("9", "BEM NOVO")
        novo_saude = _bem("9", "BEM NOVO SAÚDE", origem="Saúde")
        law = [
            LawLot(
                numero="03",
                descricao="Bem 9",
                valor_avaliado=Decimal("50.00"),
                codigo_bem="9",
                categoria="Mobiliário",
            )
        ]
        with mock.patch(
            "leilao.atualizacao.parse_asset_report",
            side_effect=lambda path, origem: (
                [novo] if origem == "Prefeitura" else [novo_saude]
            ),
        ), mock.patch("leilao.atualizacao.parse_law", return_value=law):
            plano = planejar_atualizacao(
                data,
                [("Prefeitura", "pref.pdf"), ("Saúde", "saude.pdf")],
                "pl.pdf",
            )

        self.assertEqual([bem.lote for bem in plano.novos], ["", ""])
        self.assertTrue(
            any("mais de uma origem" in issue.mensagem for issue in plano.avisos)
        )
        self.assertEqual(plano.novos_lotes[0].numero, "03")

    def test_adiciona_grupo_da_nova_origem(self):
        data = _data()
        novo = _bem("5", "MACA", origem="Saúde")
        with mock.patch(
            "leilao.atualizacao.parse_asset_report", return_value=[novo]
        ):
            plano = planejar_atualizacao(
                data, [("Prefeitura", "pref.pdf"), ("Saúde", "saude.pdf")]
            )
        self.assertIn("Saúde", [grupo.nome for grupo in plano.novos_grupos])

    def test_nao_reutiliza_grupo_de_outra_origem_com_mesmo_cnpj(self):
        data = _data(("Educação",))
        novo = _bem("9", "BEM NOVO", origem="Prefeitura")
        with mock.patch(
            "leilao.atualizacao.parse_asset_report", return_value=[novo]
        ):
            plano = planejar_atualizacao(
                data, [("Prefeitura", "pref.pdf")]
            )
        self.assertIn(
            "Prefeitura", [grupo.nome for grupo in plano.novos_grupos]
        )

    def test_grupo_renomeado_recebe_grupo_padrao_se_preciso(self):
        data = _data()
        data.grupos[0].nome = "Município"
        data.lotes[0].grupo = "Município"
        with mock.patch(
            "leilao.atualizacao.parse_asset_report", return_value=[]
        ):
            plano = planejar_atualizacao(data, [("Prefeitura", "pref.pdf")])
        self.assertIn(
            "Prefeitura", [grupo.nome for grupo in plano.novos_grupos]
        )


if __name__ == "__main__":
    unittest.main()
