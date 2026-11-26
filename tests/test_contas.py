import copy
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from leilao.entrada import DEFAULT_GROUPS, build_results
from leilao.models import Asset, Conta, Lot, ReportData
from leilao.relatorio import gerar_relatorio


def _data():
    conta = Conta(
        id=1,
        nome="Conta Compartilhada",
        titulo="CONTAS COMPARTILHADAS",
        descricao="Conta usada pelos dois lotes",
        agencia="0000-0 (Banco de Exemplo)",
        conta_corrente="12345-6",
        cnpj="00.000.000/0001-99",
    )
    data = ReportData(
        grupos=[
            copy.deepcopy(DEFAULT_GROUPS["Prefeitura"]),
            copy.deepcopy(DEFAULT_GROUPS["Saúde"]),
        ],
        contas=[conta],
        lotes=[
            Lot(
                numero="01",
                valor=Decimal("100.00"),
                grupo="Prefeitura",
                secao="Bens",
                conta_id=1,
            ),
            Lot(
                numero="02",
                valor=Decimal("60.00"),
                grupo="Saúde",
                secao="Bens",
                conta_id=1,
            ),
        ],
        bens=[
            Asset(lote="01", codigo="1", descricao="MESA", categoria="Mobiliário"),
            Asset(lote="02", codigo="2", descricao="MACA", categoria="Hospitalar", origem="Saúde"),
        ],
    )
    build_results(data)
    return data


class ContaReportTests(unittest.TestCase):
    def test_conta_compartilhada_gera_uma_aba_com_a_soma(self):
        data = _data()
        self.assertFalse(data.erros, [str(e) for e in data.erros])
        with tempfile.TemporaryDirectory() as temp:
            saida = Path(temp) / "relatorio.xlsx"
            gerar_relatorio(data, saida)
            wb = load_workbook(saida)
            self.assertIn("Conta Compartilhada", wb.sheetnames)
            self.assertNotIn("Conta Município", wb.sheetnames)
            self.assertNotIn("Conta Fundo Municipal de Saude", wb.sheetnames)
            ws = wb["Conta Compartilhada"]
            self.assertEqual(ws["A1"].value, "CONTAS COMPARTILHADAS")
            self.assertEqual(ws["A3"].value, "Conta usada pelos dois lotes")
            self.assertIn("Valor total dos lotes: R$ 160,00", ws["A7"].value)
            wb.close()

    def test_lote_sem_conta_usa_a_conta_do_grupo(self):
        data = _data()
        data.lotes[0].conta_id = None
        data.lotes[1].conta_id = None
        data.resultados = []
        data.issues = []
        build_results(data)
        with tempfile.TemporaryDirectory() as temp:
            saida = Path(temp) / "relatorio.xlsx"
            gerar_relatorio(data, saida)
            wb = load_workbook(saida)
            self.assertIn("Conta Município", wb.sheetnames)
            self.assertIn("Conta Fundo Municipal de Saude", wb.sheetnames)
            self.assertNotIn("Conta Compartilhada", wb.sheetnames)
            wb.close()


if __name__ == "__main__":
    unittest.main()
