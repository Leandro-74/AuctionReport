import copy
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from leilao.banco import (
    BANCO_NOME,
    PASTA_DOCUMENTOS,
    PASTA_EXPORTACOES,
    carregar_leilao,
    copiar_documentos,
    criar_banco,
    criar_estrutura,
    criar_leilao,
    migrar_planilha,
    salvar_leilao,
)
from leilao.edicao import (
    adicionar_conta,
    editar_grupo,
    encontrar_conta,
    mover_bens,
    remover_bens,
    remover_conta,
    remover_lote,
)
from leilao.entrada import DEFAULT_GROUPS, write_entrada
from leilao.models import Asset, Conta, Lot, ReportData


def _grupos():
    return [
        copy.deepcopy(DEFAULT_GROUPS["Prefeitura"]),
        copy.deepcopy(DEFAULT_GROUPS["Saúde"]),
    ]


def _lotes():
    return [
        Lot(numero="01", valor=Decimal("100.00"), grupo="Prefeitura", secao="Bens"),
        Lot(numero="02", valor=Decimal("60.00"), grupo="Prefeitura", secao="Bens"),
        Lot(numero="03", valor=Decimal("80.00"), grupo="Saúde", secao="Bens"),
    ]


def _bens():
    return [
        Asset(
            lote="01",
            codigo="1",
            descricao="MESA",
            categoria="Mobiliário",
            origem="Prefeitura",
            valor_contabil=Decimal("10.00"),
        ),
        Asset(
            lote="01",
            codigo="2",
            descricao="CADEIRA",
            categoria="Mobiliário",
            origem="Prefeitura",
            valor_contabil=Decimal("20.00"),
        ),
        Asset(
            lote="02",
            codigo="3",
            descricao="ARMARIO",
            categoria="Mobiliário",
            origem="Prefeitura",
            valor_contabil=Decimal("30.00"),
        ),
        Asset(
            lote="03",
            codigo="1",
            descricao="MACA",
            categoria="Hospitalar",
            origem="Saúde",
            valor_contabil=Decimal("40.00"),
        ),
    ]


class BancoTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.raiz = Path(self.pasta.name) / "2026-1"
        self.db = self.raiz / BANCO_NOME
        criar_estrutura(self.raiz)
        criar_banco(self.db, nome="2026-1")
        self.data = salvar_leilao(
            self.db, ReportData(grupos=_grupos(), lotes=_lotes(), bens=_bens())
        )

    def tearDown(self):
        self.pasta.cleanup()

    def test_estrutura_e_banco(self):
        self.assertTrue(self.db.exists())
        self.assertTrue((self.raiz / PASTA_DOCUMENTOS).is_dir())
        self.assertTrue((self.raiz / PASTA_EXPORTACOES).is_dir())

    def test_roundtrip(self):
        carregado = carregar_leilao(self.db)
        self.assertEqual(len(carregado.grupos), 2)
        self.assertEqual(len(carregado.lotes), 3)
        self.assertEqual(len(carregado.bens), 4)
        self.assertFalse(carregado.erros, [str(e) for e in carregado.erros])
        self.assertTrue(all(bem.id for bem in carregado.bens))
        self.assertTrue(all(lote.id for lote in carregado.lotes))
        self.assertTrue(all(grupo.id for grupo in carregado.grupos))
        self.assertEqual(
            sum(r.lote.valor for r in carregado.resultados), Decimal("240.00")
        )
        self.assertEqual(
            sum(r.soma for r in carregado.resultados), Decimal("240.00")
        )

    def test_atualiza_move_e_renomeia(self):
        carregado = carregar_leilao(self.db)
        mover_bens(carregado, lote_destino="02", codigos="1", lote_origem="01")
        editar_grupo(carregado, "Prefeitura", novo_nome="Município")
        carregado = salvar_leilao(self.db, carregado)

        self.assertIn("Município", [grupo.nome for grupo in carregado.grupos])
        bem = next(bem for bem in carregado.bens if bem.codigo == "1" and bem.origem == "Prefeitura")
        self.assertEqual(bem.lote, "02")
        recarregado = carregar_leilao(self.db)
        self.assertIn("Município", [grupo.nome for grupo in recarregado.grupos])
        self.assertEqual(len(recarregado.resultados), 3)

    def test_contas_compartilhadas_por_lotes(self):
        data = carregar_leilao(self.db)
        adicionar_conta(
            data,
            nome="Conta Compartilhada",
            titulo="CONTAS COMPARTILHADAS",
            descricao="Conta usada por mais de um lote",
            agencia="0000-0 (Banco de Exemplo)",
            conta_corrente="12345-6",
            cnpj="00.000.000/0001-99",
        )
        data = salvar_leilao(self.db, data)
        conta = encontrar_conta(data, "Conta Compartilhada")
        self.assertIsNotNone(conta.id)

        for lote in data.lotes[:2]:
            lote.conta_id = conta.id
        data = salvar_leilao(self.db, data)

        recarregado = carregar_leilao(self.db)
        self.assertEqual(len(recarregado.contas), 1)
        self.assertEqual(recarregado.contas[0].nome, "Conta Compartilhada")
        self.assertEqual(recarregado.contas[0].conta_corrente, "12345-6")
        self.assertEqual(
            {lote.conta_id for lote in recarregado.lotes[:2]},
            {conta.id},
        )

        with self.assertRaises(ValueError):
            remover_conta(recarregado, "Conta Compartilhada")

        for lote in recarregado.lotes:
            lote.conta_id = None
        recarregado = salvar_leilao(self.db, recarregado)
        remover_conta(recarregado, "Conta Compartilhada")
        recarregado = salvar_leilao(self.db, recarregado)
        self.assertEqual(recarregado.contas, [])

    def test_migra_banco_da_versao_1(self):
        import sqlite3

        conn = sqlite3.connect(self.db)
        conn.execute("ALTER TABLE lotes DROP COLUMN conta_id")
        conn.execute("DROP TABLE contas")
        conn.execute("PRAGMA user_version = 1")
        conn.commit()
        conn.close()

        recarregado = carregar_leilao(self.db)
        self.assertEqual(recarregado.contas, [])
        self.assertTrue(all(lote.conta_id is None for lote in recarregado.lotes))
        self.assertFalse(recarregado.erros, [str(e) for e in recarregado.erros])

    def test_remove_bem_e_lote(self):
        carregado = carregar_leilao(self.db)
        remover_bens(carregado, codigos="3")
        remover_lote(carregado, "02")
        carregado = salvar_leilao(self.db, carregado)
        self.assertNotIn("02", [lote.numero for lote in carregado.lotes])
        self.assertNotIn("3", [bem.codigo for bem in carregado.bens])

    def test_codigo_repetido_na_mesma_origem(self):
        data = ReportData(grupos=_grupos(), lotes=_lotes(), bens=_bens())
        data.bens.append(
            Asset(lote="01", codigo="1", descricao="OUTRA MESA", origem="Prefeitura")
        )
        with self.assertRaises(ValueError) as ctx:
            salvar_leilao(self.db, data)
        self.assertIn("código 1", str(ctx.exception))

    def test_codigo_repetido_em_origens_diferentes(self):
        data = carregar_leilao(self.db)
        data.bens.append(
            Asset(lote="03", codigo="1", descricao="OUTRO BEM", origem="Saúde")
        )
        # The code 1 from Saúde already exists in the fixture, so this must fail.
        with self.assertRaises(ValueError):
            salvar_leilao(self.db, data)

        # The same code in two different origins is valid.
        data.bens.pop()
        data.bens.append(
            Asset(lote="01", codigo="99", descricao="BEM PREFEITURA", origem="Prefeitura")
        )
        data.bens.append(
            Asset(lote="03", codigo="99", descricao="BEM SAÚDE", origem="Saúde")
        )
        salvo = salvar_leilao(self.db, data)
        self.assertEqual(len([b for b in salvo.bens if b.codigo == "99"]), 2)

    def test_criar_leilao_remove_banco_temporario(self):
        with tempfile.TemporaryDirectory() as temp:
            pasta = Path(temp) / "novo"
            data = ReportData(grupos=_grupos(), lotes=_lotes(), bens=_bens())
            resultado = criar_leilao(pasta, data)
            self.assertTrue((pasta / BANCO_NOME).exists())
            self.assertFalse((pasta / f"{BANCO_NOME}.tmp").exists())
            self.assertFalse(resultado.erros, [str(e) for e in resultado.erros])

    def test_criar_leilao_nao_deixa_banco_parcial(self):
        with tempfile.TemporaryDirectory() as temp:
            pasta = Path(temp) / "novo"
            data = ReportData(grupos=_grupos(), lotes=_lotes(), bens=_bens())
            data.bens.append(
                Asset(
                    lote="01",
                    codigo="1",
                    descricao="DUPLICADO",
                    origem="Prefeitura",
                )
            )
            with self.assertRaises(ValueError):
                criar_leilao(pasta, data)
            self.assertFalse((pasta / BANCO_NOME).exists())
            self.assertFalse((pasta / f"{BANCO_NOME}.tmp").exists())

    def test_migrar_planilha(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            entrada = temp / "entrada.xlsx"
            pasta = temp / "2025-2"
            write_entrada(entrada, _grupos(), _lotes(), _bens())
            data = migrar_planilha(entrada, pasta)
            self.assertTrue((pasta / BANCO_NOME).exists())
            self.assertEqual(len(data.bens), 4)
            self.assertFalse(data.erros, [str(e) for e in data.erros])

    def test_copiar_documentos(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            pdf = temp / "report.pdf"
            pdf.write_bytes(b"%PDF-1.4 teste")
            registros = copiar_documentos(self.db, [("Prefeitura", pdf)])
            self.assertEqual(len(registros), 1)
            destino = self.raiz / registros[0]["caminho"]
            self.assertTrue(destino.exists())
            self.assertTrue(registros[0]["hash"])
            self.assertEqual(destino.read_bytes(), pdf.read_bytes())

    def test_banco_invalido(self):
        invalido = Path(self.pasta.name) / "invalido.db"
        invalido.write_bytes(b"nao e um banco")
        with self.assertRaises(ValueError):
            carregar_leilao(invalido)


if __name__ == "__main__":
    unittest.main()
