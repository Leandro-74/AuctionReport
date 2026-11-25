import os
import unittest

from leilao.tui import _limpar_caminho


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
