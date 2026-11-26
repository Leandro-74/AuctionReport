import unittest
from pathlib import Path

from leilao.pdfs import classify_asset, parse_asset_report, parse_law

RAIZ = Path(__file__).resolve().parents[1]
MODELO = RAIZ / "novo_modelo"
PREF = MODELO / "Report_prefeitura.pdf"
SAUDE = MODELO / "Report_saude.pdf"
PL = RAIZ / "Projeto de Lei  - Autoriza Alienação de Bens -.pdf"


class ClassificacaoTests(unittest.TestCase):
    def test_mesa_de_computador_e_mobiliario(self):
        self.assertEqual(
            classify_asset("MESA DE MDP P/ COMPUTADOR, MEDIDAS: 75X75X58 CM."),
            "Mobiliário",
        )

    def test_gabinete_com_placa_e_informatica(self):
        self.assertEqual(
            classify_asset(
                "GABINETE COM PLACA INTEL H61M-DS2, MEMORIA 4GB, HD SATA 3 ITB."
            ),
            "Informática",
        )

    def test_remoto_nao_e_moto(self):
        self.assertNotEqual(
            classify_asset(
                "AR CONDICIONADO SPLIT, CONTROLE REMOTO COM DISPLAY DE LCD."
            ),
            "Veículos",
        )

    def test_aluno_nao_e_uno(self):
        self.assertNotEqual(
            classify_asset("CADEIRA PARA ALUNO DA REDE MUNICIPAL."),
            "Veículos",
        )

    def test_saude_e_hospitalar(self):
        self.assertEqual(
            classify_asset("CADEIRA GIRATÓRIA SECRETÁRIA.", "Saúde"),
            "Hospitalar",
        )


@unittest.skipUnless(PREF.exists() and SAUDE.exists(), "PDFs de exemplo não encontrados")
class RelatoriosTests(unittest.TestCase):
    def test_prefeitura(self):
        bens = parse_asset_report(PREF, "Prefeitura")
        self.assertEqual(len(bens), 56)
        self.assertTrue(all(b.conta_debito for b in bens))
        self.assertTrue(all(b.conta_credito for b in bens))
        self.assertTrue(all(b.valor_contabil is None for b in bens))
        self.assertNotIn("Total de Registros", bens[-1].descricao)

    def test_saude(self):
        bens = parse_asset_report(SAUDE, "Saúde")
        self.assertEqual(len(bens), 37)
        self.assertTrue(all(b.conta_debito for b in bens))
        self.assertTrue(all(b.conta_credito for b in bens))
        self.assertTrue(all(b.valor_contabil is None for b in bens))

    def test_nao_ha_codigos_repetidos(self):
        codigos = [b.codigo for b in parse_asset_report(PREF, "Prefeitura")]
        codigos += [b.codigo for b in parse_asset_report(SAUDE, "Saúde")]
        self.assertEqual(len(codigos), len(set(codigos)))


@unittest.skipUnless(PL.exists(), "Projeto de lei de exemplo não encontrado")
class LeisTests(unittest.TestCase):
    def test_dez_lotes(self):
        lotes = parse_law(PL)
        self.assertEqual(len(lotes), 10)
        self.assertEqual([l.numero for l in lotes], [f"{i:02d}" for i in range(1, 11)])

    def test_avaliacoes_e_patrimonios(self):
        por_numero = {l.numero: l for l in parse_law(PL)}
        self.assertEqual(por_numero["01"].codigo_bem, "27")
        self.assertEqual(por_numero["01"].valor_avaliado, 17000)
        self.assertEqual(por_numero["02"].codigo_bem, "28")
        self.assertEqual(por_numero["02"].valor_avaliado, 93500)
        self.assertEqual(por_numero["03"].codigo_bem, "37")
        self.assertEqual(por_numero["03"].valor_avaliado, 125000)
        self.assertEqual(por_numero["04"].codigo_bem, "65")
        self.assertEqual(por_numero["05"].codigo_bem, "77")
        self.assertIsNone(por_numero["06"].codigo_bem)
        self.assertEqual(por_numero["06"].valor_avaliado, 130000)
        self.assertEqual(por_numero["07"].codigo_bem, "62")
        self.assertEqual(por_numero["08"].categoria, "Mobiliário")
        self.assertEqual(por_numero["09"].categoria, "Hospitalar")
        self.assertEqual(por_numero["10"].categoria, "Informática")


if __name__ == "__main__":
    unittest.main()
