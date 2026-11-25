import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from leilao.entrada import DEFAULT_GROUPS, importar_pdfs, ler_entrada, write_entrada
from leilao.models import Asset, Lot
from leilao.relatorio import gerar_relatorio

RAIZ = Path(__file__).resolve().parents[1]
PREF = RAIZ / "Report_prefeitura.pdf"
SAUDE = RAIZ / "Report_saúde.pdf"
PL = RAIZ / "Projeto de Lei  - Autoriza Alienação de Bens -.pdf"
EXEMPLO = RAIZ / "2025-2 LEILÃO - ITENS PARA BAIXA.xlsx"


@unittest.skipUnless(EXEMPLO.exists(), "planilha de exemplo não encontrada")
class IntegracaoLote14Tests(unittest.TestCase):
    def test_reproduz_o_lote_14(self):
        origem = load_workbook(EXEMPLO, data_only=True)
        ws = origem["Relatório Bens da Educação"]

        bens = []
        for row in ws.iter_rows(min_row=16, max_row=230, max_col=6):
            if row[0].value != "Bens Móveis":
                continue
            bens.append(
                Asset(
                    lote="14",
                    tipo=row[0].value,
                    codigo=str(int(row[1].value)),
                    conta_credito=str(int(row[2].value)),
                    conta_debito=str(int(row[3].value)),
                    descricao=row[4].value,
                    valor_contabil=Decimal(str(row[5].value)),
                    categoria="Mobiliário",
                    row=len(bens) + 2,
                )
            )
        self.assertEqual(len(bens), 211)
        self.assertEqual(sum(b.valor_contabil for b in bens), Decimal("50.00"))

        lote = Lot(
            numero="14",
            valor=Decimal("50.00"),
            grupo="Educação",
            secao="Mobiliário em Geral",
        )
        grupo = DEFAULT_GROUPS["Educação"]

        with tempfile.TemporaryDirectory() as pasta:
            entrada = Path(pasta) / "entrada.xlsx"
            saida = Path(pasta) / "relatorio.xlsx"
            write_entrada(entrada, [grupo], [lote], bens)
            dados = ler_entrada(entrada)
            self.assertFalse(dados.erros, [str(e) for e in dados.erros])
            self.assertEqual(len(dados.resultados), 1)
            gerar_relatorio(dados, saida)

            gerado = load_workbook(saida, data_only=True)
            aba = gerado[grupo.aba]
            valores = []
            for row in aba.iter_rows(min_row=12, max_row=222, min_col=6, max_col=6):
                valores.append(row[0].value)
            self.assertEqual(len(valores), 211)
            self.assertEqual(valores[:210], [0.23] * 210)
            self.assertEqual(valores[-1], 1.70)
            self.assertAlmostEqual(sum(valores), 50.00, places=2)

            self.assertEqual(aba["A10"].value, "Mobiliário em Geral (Lote 14)")
            self.assertEqual(aba["F11"].number_format, '[$R$ -416]#,##0.00')
            self.assertIn("Valor total dos lotes: R$ 50,00", aba["A8"].value)


@unittest.skipUnless(
    PREF.exists() and SAUDE.exists() and PL.exists(),
    "PDFs de exemplo não encontrados",
)
class IntegracaoLeilaoCompletoTests(unittest.TestCase):
    def test_fluxo_completo(self):
        grupos, lotes, bens, issues = importar_pdfs(
            [("Prefeitura", PREF), ("Saúde", SAUDE)], PL
        )
        self.assertEqual(len(bens), 93)  # 91 dos relatórios + 2 criados pelo PL
        self.assertEqual(len(lotes), 10)
        self.assertEqual([l.numero for l in lotes], [f"{i:02d}" for i in range(1, 11)])
        self.assertEqual(len([b for b in bens if not b.lote]), 1)
        self.assertTrue(any("Lote 05" in i.mensagem for i in issues))

        with tempfile.TemporaryDirectory() as pasta:
            entrada = Path(pasta) / "entrada.xlsx"
            saida = Path(pasta) / "relatorio.xlsx"
            write_entrada(entrada, grupos, lotes, bens, issues)
            dados = ler_entrada(entrada)
            self.assertFalse(dados.erros, [str(e) for e in dados.erros])
            self.assertEqual(len(dados.resultados), 10)
            self.assertEqual(
                sum(r.lote.valor for r in dados.resultados), Decimal("420850.00")
            )
            gerar_relatorio(dados, saida, incluir_resumo=False)

            gerado = load_workbook(saida, data_only=True)
            self.assertIn("Relatório Bens da Prefeitura", gerado.sheetnames)
            self.assertIn("Relatório Bens da Saúde", gerado.sheetnames)
            self.assertIn("Relatório Todos os Veículos", gerado.sheetnames)
            self.assertIn("Relatório Veículos", gerado.sheetnames)
            self.assertIn("Relatório Veículos Hospital", gerado.sheetnames)
            self.assertIn("Relatório Mobiliário em Geral", gerado.sheetnames)
            self.assertIn("Relatório Mobiliário em Geral H", gerado.sheetnames)
            self.assertIn("Relatório Itens de Informática", gerado.sheetnames)
            self.assertIn("Conta Município", gerado.sheetnames)
            self.assertIn("Conta Fundo Municipal de Saude", gerado.sheetnames)
            self.assertNotIn("Resumo", gerado.sheetnames)

            # Abas auxiliares com as mesmas colunas e linhas do modelo.
            aux = gerado["Relatório Todos os Veículos"]
            self.assertEqual(aux["A4"].value, "Tipo de bem")
            self.assertEqual(aux["C4"].value, "Conta Crédito")
            self.assertEqual(aux["D4"].value, "Conta Débito")
            self.assertEqual(aux["F4"].value, "Valor")
            self.assertEqual(aux.max_row, 11)  # 7 veículos + cabeçalho na linha 4

            mobiliario = gerado["Relatório Mobiliário em Geral"]
            self.assertEqual(mobiliario.max_row, 17)  # 13 bens + cabeçalho na linha 4
            hospital = gerado["Relatório Mobiliário em Geral H"]
            self.assertEqual(hospital.max_row, 38)  # 34 bens + cabeçalho na linha 4
            informatica = gerado["Relatório Itens de Informática"]
            self.assertEqual(informatica.max_row, 42)  # 38 bens + cabeçalho na linha 4

            conta = gerado["Conta Município"]
            self.assertIn("Valor total dos lotes: R$ 378.750,00", conta["A7"].value)
            conta_saude = gerado["Conta Fundo Municipal de Saude"]
            self.assertIn("Valor total dos lotes: R$ 42.100,00", conta_saude["A7"].value)

            # A aba Resumo é opcional.
            saida_resumo = Path(pasta) / "relatorio_com_resumo.xlsx"
            gerar_relatorio(dados, saida_resumo, incluir_resumo=True)
            com_resumo = load_workbook(saida_resumo, data_only=True)
            self.assertIn("Resumo", com_resumo.sheetnames)
            resumo = com_resumo["Resumo"]
            self.assertEqual(resumo["A8"].value, "TOTAL GERAL")
            self.assertAlmostEqual(resumo["G8"].value, 420850.00, places=2)


if __name__ == "__main__":
    unittest.main()
