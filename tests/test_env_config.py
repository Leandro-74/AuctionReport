import tempfile
import unittest
from pathlib import Path

from dotenv import dotenv_values

from leilao.env_config import CAMPOS, salvar, valores_atuais


class EnvConfigTests(unittest.TestCase):
    def test_le_e_grava_valores(self):
        with tempfile.TemporaryDirectory() as temp:
            caminho = Path(temp) / ".env"
            caminho.write_text(
                "AUCTIONREPORT_MUNICIPIO=MUNICÍPIO ANTIGO\n", encoding="utf-8"
            )
            valores = valores_atuais(caminho)
            self.assertEqual(valores["AUCTIONREPORT_MUNICIPIO"], "MUNICÍPIO ANTIGO")
            self.assertEqual(
                valores["AUCTIONREPORT_CNPJ_MUNICIPIO"],
                "00.000.000/0001-00",
            )

            valores["AUCTIONREPORT_MUNICIPIO"] = "MUNICÍPIO NOVO"
            valores["AUCTIONREPORT_CONTA_SAUDE"] = "99999-9"
            salvar(valores, caminho)

            lidos = dotenv_values(caminho)
            self.assertEqual(
                lidos["AUCTIONREPORT_MUNICIPIO"], "MUNICÍPIO NOVO"
            )
            self.assertEqual(lidos["AUCTIONREPORT_CONTA_SAUDE"], "99999-9")
            self.assertTrue(
                (Path(temp) / ".env.bak").exists()
            )

    def test_cria_arquivo_a_partir_do_exemplo(self):
        with tempfile.TemporaryDirectory() as temp:
            caminho = Path(temp) / ".env"
            valores = {chave: padrao for chave, _, padrao in CAMPOS}
            salvar(valores, caminho)
            self.assertTrue(caminho.exists())
            lidos = dotenv_values(caminho)
            for chave, _, padrao in CAMPOS:
                self.assertEqual(lidos[chave], padrao)


if __name__ == "__main__":
    unittest.main()
