import subprocess
import unittest
from unittest import mock

from leilao import dialogos


class ComandoTests(unittest.TestCase):
    def test_zenity_arquivo(self):
        comando = dialogos._comando_zenity("Abrir PDF", ("pdf",), False)
        self.assertEqual(comando[0], "zenity")
        self.assertIn("--file-selection", comando)
        self.assertIn("--title=Abrir PDF", comando)
        self.assertIn("--file-filter=PDF | *.pdf", comando)
        self.assertIn("--file-filter=Todos os arquivos | *", comando)
        self.assertNotIn("--directory", comando)

    def test_zenity_pasta(self):
        comando = dialogos._comando_zenity("Escolher pasta", (), True)
        self.assertIn("--directory", comando)
        self.assertNotIn("--file-filter=Todos os arquivos | *", comando)

    def test_kdialog_arquivo(self):
        comando = dialogos._comando_kdialog("Abrir", ("xlsx",), False)
        self.assertEqual(comando[0], "kdialog")
        self.assertIn("--getopenfilename", comando)
        self.assertEqual(comando[-1], "*.xlsx|Arquivos")

    def test_filtro_windows(self):
        filtro = dialogos._filtro_windows(("pdf", "xlsx"))
        self.assertEqual(
            filtro,
            "PDF (*.pdf)|*.pdf|"
            "Planilha do Excel (*.xlsx)|*.xlsx|"
            "Todos os arquivos (*.*)|*.*",
        )

    @mock.patch.object(dialogos, "_powershell", return_value="powershell")
    def test_comando_windows_usa_dialogo_nativo(self, _):
        comando = dialogos._comando_windows("Abrir", ("db",), False)
        self.assertEqual(comando[0], "powershell")
        self.assertIn("-STA", comando)
        self.assertIn("OpenFileDialog", comando[-1])
        self.assertIn("Banco de dados", comando[-1])

    def test_extensoes_normalizadas(self):
        self.assertEqual(
            dialogos._extensoes((".PDF", "xlsx", "")), ("pdf", "xlsx")
        )


class ExecutarTests(unittest.TestCase):
    @mock.patch("leilao.dialogos.subprocess.run")
    def test_cancelado_retorna_vazio(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, "", "")
        self.assertEqual(dialogos._executar(["zenity"]), "")

    @mock.patch("leilao.dialogos.subprocess.run")
    def test_caminho_eh_limpo(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, "  /tmp/arquivo.pdf\n", ""
        )
        self.assertEqual(dialogos._executar(["zenity"]), "/tmp/arquivo.pdf")

    @mock.patch("leilao.dialogos.subprocess.run", side_effect=OSError("falhou"))
    def test_erro_ao_abrir_gera_indisponivel(self, _):
        with self.assertRaises(dialogos.DialogoIndisponivel):
            dialogos._executar(["zenity"])

    @mock.patch("leilao.dialogos.sys.stdin.isatty", return_value=False)
    def test_sem_terminal_nao_esta_disponivel(self, _):
        self.assertFalse(dialogos.disponivel())


if __name__ == "__main__":
    unittest.main()
