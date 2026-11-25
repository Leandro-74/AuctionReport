import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from leilao.edicao import (
    EdicaoError,
    adicionar_bem,
    adicionar_lote,
    codigo_selecionado,
    editar_bem,
    editar_lote,
    encontrar_bem,
    filtrar_bens,
    mover_bens,
    remover_bens,
    remover_lote,
    salvar_entrada,
    substituir_descricao,
)
from leilao.entrada import DEFAULT_GROUPS, ler_entrada, write_entrada
from leilao.models import Asset, Lot


class SelecaoTests(unittest.TestCase):
    def test_faixa(self):
        self.assertTrue(codigo_selecionado("300", "300-400"))
        self.assertTrue(codigo_selecionado("400", "300-400"))
        self.assertFalse(codigo_selecionado("299", "300-400"))
        self.assertFalse(codigo_selecionado("401", "300-400"))

    def test_lista(self):
        self.assertTrue(codigo_selecionado("305", "300,305,310"))
        self.assertFalse(codigo_selecionado("306", "300,305,310"))

    def test_dois_pontos(self):
        self.assertTrue(codigo_selecionado("350", "300..400"))


class EdicaoTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.entrada = Path(self.pasta.name) / "entrada.xlsx"
        self.grupo = DEFAULT_GROUPS["Prefeitura"]
        self.lotes = [
            Lot(numero="01", valor=Decimal("100.00"), grupo="Prefeitura", secao="Bens"),
            Lot(numero="02", valor=Decimal("60.00"), grupo="Prefeitura", secao="Bens"),
        ]
        self.bens = [
            Asset(lote="01", codigo="1", descricao="MESA GRANDE", categoria="Mobiliário"),
            Asset(lote="01", codigo="2", descricao="MESA PEQUENA", categoria="Mobiliário"),
            Asset(lote="01", codigo="3", descricao="CADEIRA", categoria="Mobiliário"),
            Asset(lote="02", codigo="4", descricao="ARMARIO", categoria="Mobiliário"),
            Asset(lote="02", codigo="5", descricao="ESTANTE", categoria="Mobiliário"),
        ]
        for bem in self.bens:
            bem.origem = "Prefeitura"
        write_entrada(self.entrada, [self.grupo], self.lotes, self.bens)
        self.data = ler_entrada(self.entrada)
        self.assertFalse(self.data.erros, [str(e) for e in self.data.erros])

    def tearDown(self):
        self.pasta.cleanup()

    def test_mover_por_faixa(self):
        movidos = mover_bens(self.data, lote_destino="02", codigos="2-3")
        self.assertEqual(len(movidos), 2)
        self.assertEqual({b.lote for b in self.data.bens if b.codigo in ("2", "3")}, {"02"})
        self.data = salvar_entrada(self.entrada, self.data)
        self.assertFalse(self.data.erros, [str(e) for e in self.data.erros])
        lote2 = [r for r in self.data.resultados if r.lote.numero == "02"][0]
        self.assertEqual(len(lote2.bens), 4)
        self.assertEqual(lote2.soma, Decimal("60.00"))

    def test_editar_lote_e_bem(self):
        editar_lote(self.data, "01", valor="120,00", secao="Veículos")
        editar_bem(self.data, "1", descricao="MESA NOVA", conta_credito="123", conta_debito="456")
        self.data = salvar_entrada(self.entrada, self.data)
        lote1 = [r for r in self.data.resultados if r.lote.numero == "01"][0]
        self.assertEqual(lote1.lote.valor, Decimal("120.00"))
        self.assertEqual(lote1.lote.secao, "Veículos")
        bem = [b for b in self.data.bens if b.codigo == "1"][0]
        self.assertEqual(bem.descricao, "MESA NOVA")
        self.assertEqual(bem.conta_credito, "123")
        self.assertEqual(bem.conta_debito, "456")

    def test_substituir_descricao(self):
        alterados = substituir_descricao(self.data, "MESA", "CADEIRA")
        self.assertEqual(len(alterados), 2)
        self.assertTrue(all("MESA" not in b.descricao for b in self.data.bens))

    def test_adicionar_e_remover(self):
        adicionar_lote(
            self.data,
            numero="03",
            valor="30,00",
            grupo="Prefeitura",
            secao="Bens",
        )
        adicionar_bem(
            self.data,
            lote="03",
            codigo="6",
            descricao="BEM NOVO",
            categoria="Mobiliário",
        )
        self.data = salvar_entrada(self.entrada, self.data)
        self.assertIn("03", [l.numero for l in self.data.lotes])
        self.assertIn("6", [b.codigo for b in self.data.bens])
        remover_bens(self.data, codigos="6")
        self.data = salvar_entrada(self.entrada, self.data)
        remover_lote(self.data, "03")
        self.data = salvar_entrada(self.entrada, self.data)
        self.assertNotIn("03", [l.numero for l in self.data.lotes])

    def test_filtro_por_texto_e_lote(self):
        self.assertEqual(len(filtrar_bens(self.data, texto="mesa", lote="01")), 2)
        self.assertEqual(len(filtrar_bens(self.data, categoria="Mobiliário")), 5)

    def test_mesmo_codigo_em_origens_diferentes(self):
        saude = Asset(
            lote="02",
            codigo="1",
            descricao="MACA",
            categoria="Hospitalar",
            origem="Saúde",
        )
        self.data.bens.append(saude)

        with self.assertRaises(EdicaoError):
            encontrar_bem(self.data, "1")
        self.assertEqual(encontrar_bem(self.data, "1", origem="Saúde"), saude)
        self.assertEqual(len(filtrar_bens(self.data, origem="Saúde")), 1)

        movidos = mover_bens(
            self.data, lote_destino="02", codigos="1", origem="Prefeitura"
        )
        self.assertEqual(len(movidos), 1)
        self.assertEqual(movidos[0].origem, "Prefeitura")
        self.assertEqual(saude.lote, "02")

        editar_bem(self.data, "1", origem="Saúde", descricao="MACA NOVA")
        self.assertEqual(saude.descricao, "MACA NOVA")


if __name__ == "__main__":
    unittest.main()
