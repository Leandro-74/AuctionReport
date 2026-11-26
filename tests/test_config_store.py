import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from leilao.config_store import (
    CAMPOS,
    Configuracao,
    carregar,
    migrar_legado,
    salvar,
)


class ConfigStoreTests(unittest.TestCase):
    def test_salva_e_carrega_json(self):
        with tempfile.TemporaryDirectory() as temp:
            caminho = Path(temp) / "config.json"
            config = Configuracao(
                municipio="MUNICÍPIO TESTE",
                agencia="0000-0",
                cnpj_municipio="00.000.000/0001-00",
                cnpj_saude="00.000.000/0001-01",
                conta_prefeitura="11111-1",
                conta_saude="22222-2",
            )
            salvar(config, caminho)
            lido = carregar(caminho)
            self.assertEqual(lido.municipio, "MUNICÍPIO TESTE")
            self.assertEqual(lido.conta_prefeitura, "11111-1")
            self.assertEqual(lido.conta_saude, "22222-2")
            self.assertFalse((Path(temp) / "config.json.bak").exists())

    @unittest.skipIf(os.name == "nt", "permissões POSIX")
    def test_arquivo_tem_permissao_restrita(self):
        with tempfile.TemporaryDirectory() as temp:
            caminho = Path(temp) / "config.json"
            salvar(Configuracao(), caminho)
            self.assertEqual(caminho.stat().st_mode & 0o777, 0o600)

    def test_campos_cobrem_a_configuracao(self):
        self.assertEqual(
            {campo for campo, _ in CAMPOS},
            set(Configuracao.__dataclass_fields__),
        )

    def test_json_invalido(self):
        with tempfile.TemporaryDirectory() as temp:
            caminho = Path(temp) / "config.json"
            caminho.write_text("{invalido", encoding="utf-8")
            with self.assertRaises(ValueError):
                carregar(caminho)

    def test_migra_env_antigo(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            legado = temp / ".env"
            legado.write_text(
                "AUCTIONREPORT_MUNICIPIO=MUNICÍPIO LEGADO\n"
                "AUCTIONREPORT_CONTA_SAUDE=99999-9\n",
                encoding="utf-8",
            )
            destino = temp / "config.json"
            with mock.patch(
                "leilao.config_store.caminho_legado", return_value=legado
            ):
                migrado = migrar_legado(destino)
            self.assertIsNotNone(migrado)
            self.assertEqual(migrado.municipio, "MUNICÍPIO LEGADO")
            dados = json.loads(destino.read_text(encoding="utf-8"))
            self.assertEqual(dados["municipio"], "MUNICÍPIO LEGADO")
            self.assertEqual(dados["conta_saude"], "99999-9")


if __name__ == "__main__":
    unittest.main()
