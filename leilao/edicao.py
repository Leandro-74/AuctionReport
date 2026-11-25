"""Operações de edição dos bens e lotes da planilha de entrada."""

from __future__ import annotations

import re
from pathlib import Path

from .entrada import ler_entrada, normalize_lot, write_entrada
from .models import Asset, Group, Lot, ReportData, norm
from .money import parse_money


class EdicaoError(ValueError):
    """Erro de edição com mensagem amigável."""


# ---------------------------------------------------------------------------
# Seleção de bens por código/faixa/texto
# ---------------------------------------------------------------------------


def codigo_selecionado(codigo: str, expressao: str) -> bool:
    """Testa um código contra ``300-400``, ``300,305``, ``300..400`` etc."""
    if not expressao.strip():
        return True
    codigo = (codigo or "").strip()
    for parte in re.split(r"[,;]", expressao):
        parte = parte.strip()
        if not parte:
            continue
        if ".." in parte:
            esquerda, direita = parte.split("..", 1)
        elif "-" in parte:
            esquerda, direita = parte.split("-", 1)
        else:
            if codigo == parte or (codigo.isdigit() and parte.isdigit() and int(codigo) == int(parte)):
                return True
            continue
        esquerda, direita = esquerda.strip(), direita.strip()
        if codigo.isdigit() and esquerda.isdigit() and direita.isdigit():
            if int(esquerda) <= int(codigo) <= int(direita):
                return True
        elif codigo in (esquerda, direita):
            return True
    return False


def filtrar_bens(
    data: ReportData,
    *,
    codigos: str = "",
    texto: str = "",
    lote: str = "",
    categoria: str = "",
) -> list[Asset]:
    """Filtra bens por código/faixa, texto da descrição, lote e categoria."""
    lote = normalize_lot(lote)
    texto_norm = norm(texto).strip()
    categoria_norm = norm(categoria).strip()
    resultado: list[Asset] = []
    for bem in data.bens:
        if codigos and not codigo_selecionado(bem.codigo, codigos):
            continue
        if lote and normalize_lot(bem.lote) != lote:
            continue
        if texto_norm and texto_norm not in norm(bem.descricao):
            continue
        if categoria_norm and categoria_norm not in norm(bem.categoria):
            continue
        resultado.append(bem)
    return resultado


# ---------------------------------------------------------------------------
# Edição de lotes
# ---------------------------------------------------------------------------


def encontrar_lote(data: ReportData, numero: str) -> Lot:
    alvo = normalize_lot(numero)
    for lote in data.lotes:
        if normalize_lot(lote.numero) == alvo:
            return lote
    raise EdicaoError(f"Lote {numero} não encontrado.")


def encontrar_bem(data: ReportData, codigo: str) -> Asset:
    alvo = (codigo or "").strip()
    encontrados = [bem for bem in data.bens if (bem.codigo or "").strip() == alvo]
    if not encontrados:
        raise EdicaoError(f"Bem com código {codigo} não encontrado.")
    if len(encontrados) > 1:
        lotes = ", ".join(sorted({bem.lote or "(sem lote)" for bem in encontrados}))
        raise EdicaoError(
            f"O código {codigo} aparece {len(encontrados)} vezes (lotes: {lotes}). "
            "Use a edição por linha ou mova os bens por faixa."
        )
    return encontrados[0]


def editar_lote(
    data: ReportData,
    numero: str,
    *,
    valor: object | None = None,
    grupo: str | None = None,
    secao: str | None = None,
    observacao: str | None = None,
) -> Lot:
    lote = encontrar_lote(data, numero)
    if valor is not None:
        try:
            lote.valor = parse_money(valor)
        except ValueError as exc:
            raise EdicaoError(f"Valor inválido: {valor!r}.") from exc
    if grupo is not None and grupo.strip():
        nomes = {norm(g.nome) for g in data.grupos}
        if norm(grupo) not in nomes:
            raise EdicaoError(f"Grupo '{grupo}' não cadastrado.")
        lote.grupo = grupo.strip()
    if secao is not None and secao.strip():
        lote.secao = secao.strip()
    if observacao is not None:
        lote.observacao = observacao.strip()
    return lote


def mover_bens(
    data: ReportData,
    *,
    lote_destino: str,
    codigos: str = "",
    texto: str = "",
    lote_origem: str = "",
    categoria: str = "",
) -> list[Asset]:
    destino = normalize_lot(lote_destino)
    if not destino:
        raise EdicaoError("Informe o lote de destino.")
    encontrar_lote(data, destino)
    bens = filtrar_bens(
        data, codigos=codigos, texto=texto, lote=lote_origem, categoria=categoria
    )
    if not bens:
        return []
    for bem in bens:
        bem.lote = destino
    return bens


# ---------------------------------------------------------------------------
# Edição de bens
# ---------------------------------------------------------------------------


def editar_bem(
    data: ReportData,
    codigo: str,
    *,
    descricao: str | None = None,
    novo_codigo: str | None = None,
    lote: str | None = None,
    tipo: str | None = None,
    categoria: str | None = None,
    conta_credito: str | None = None,
    conta_debito: str | None = None,
    valor_contabil: object | None = None,
    observacao: str | None = None,
) -> Asset:
    bem = encontrar_bem(data, codigo)
    if descricao is not None and descricao.strip():
        bem.descricao = descricao.strip()
    if novo_codigo is not None and novo_codigo.strip():
        bem.codigo = novo_codigo.strip()
    if lote is not None:
        lote_norm = normalize_lot(lote)
        if lote_norm:
            encontrar_lote(data, lote_norm)
        bem.lote = lote_norm
    if tipo is not None and tipo.strip():
        bem.tipo = tipo.strip()
    if categoria is not None and categoria.strip():
        bem.categoria = categoria.strip()
    if conta_credito is not None:
        bem.conta_credito = conta_credito.strip()
    if conta_debito is not None:
        bem.conta_debito = conta_debito.strip()
    if valor_contabil is not None:
        if str(valor_contabil).strip() == "":
            bem.valor_contabil = None
        else:
            try:
                bem.valor_contabil = parse_money(valor_contabil)
            except ValueError as exc:
                raise EdicaoError(f"Valor contábil inválido: {valor_contabil!r}.") from exc
    if observacao is not None:
        bem.observacao = observacao.strip()
    return bem


def substituir_descricao(
    data: ReportData,
    antigo: str,
    novo: str,
    *,
    lote: str = "",
    categoria: str = "",
) -> list[Asset]:
    if not antigo.strip():
        raise EdicaoError("Informe o texto a substituir.")
    padrao = re.compile(re.escape(antigo.strip()), re.IGNORECASE)
    alterados: list[Asset] = []
    for bem in filtrar_bens(data, lote=lote, categoria=categoria):
        if padrao.search(bem.descricao):
            bem.descricao = padrao.sub(novo.strip(), bem.descricao)
            alterados.append(bem)
    return alterados


# ---------------------------------------------------------------------------
# Adicionar / remover
# ---------------------------------------------------------------------------


def adicionar_lote(
    data: ReportData,
    *,
    numero: str,
    valor: object,
    grupo: str,
    secao: str,
    observacao: str = "",
) -> Lot:
    numero = normalize_lot(numero)
    if not numero:
        raise EdicaoError("Informe o número do lote.")
    if any(normalize_lot(lote.numero) == numero for lote in data.lotes):
        raise EdicaoError(f"Já existe um lote {numero}.")
    if not any(norm(g.nome) == norm(grupo) for g in data.grupos):
        raise EdicaoError(f"Grupo '{grupo}' não cadastrado.")
    try:
        valor_dec = parse_money(valor)
    except ValueError as exc:
        raise EdicaoError(f"Valor inválido: {valor!r}.") from exc
    lote = Lot(
        numero=numero,
        valor=valor_dec,
        grupo=grupo.strip(),
        secao=secao.strip() or "Bens em Geral",
        observacao=observacao.strip(),
        row=max((l.row for l in data.lotes), default=0) + 1,
    )
    data.lotes.append(lote)
    return lote


def adicionar_bem(
    data: ReportData,
    *,
    lote: str,
    codigo: str,
    descricao: str,
    tipo: str = "Bens Móveis",
    categoria: str = "Outros",
    conta_credito: str = "",
    conta_debito: str = "",
    valor_contabil: object | None = None,
    observacao: str = "",
) -> Asset:
    lote = normalize_lot(lote)
    if lote:
        encontrar_lote(data, lote)
    if not descricao.strip():
        raise EdicaoError("Informe a descrição do bem.")
    valor = None
    if valor_contabil not in (None, ""):
        try:
            valor = parse_money(valor_contabil)
        except ValueError as exc:
            raise EdicaoError(f"Valor contábil inválido: {valor_contabil!r}.") from exc
    bem = Asset(
        lote=lote,
        tipo=tipo.strip() or "Bens Móveis",
        codigo=codigo.strip(),
        descricao=descricao.strip(),
        categoria=categoria.strip() or "Outros",
        conta_credito=conta_credito.strip(),
        conta_debito=conta_debito.strip(),
        valor_contabil=valor,
        observacao=observacao.strip(),
        row=max((b.row for b in data.bens), default=0) + 1,
    )
    data.bens.append(bem)
    return bem


def remover_bens(
    data: ReportData,
    *,
    codigos: str = "",
    texto: str = "",
    lote: str = "",
    categoria: str = "",
) -> list[Asset]:
    bens = filtrar_bens(
        data, codigos=codigos, texto=texto, lote=lote, categoria=categoria
    )
    if not bens:
        return []
    ids = {id(bem) for bem in bens}
    data.bens = [bem for bem in data.bens if id(bem) not in ids]
    return bens


def remover_lote(data: ReportData, numero: str) -> Lot:
    lote = encontrar_lote(data, numero)
    associados = [bem for bem in data.bens if normalize_lot(bem.lote) == normalize_lot(lote.numero)]
    if associados:
        raise EdicaoError(
            f"O lote {lote.numero} ainda tem {len(associados)} bem(ns) associado(s). "
            "Mova os bens para outro lote antes de removê-lo."
        )
    data.lotes.remove(lote)
    return lote


# ---------------------------------------------------------------------------
# Grupos
# ---------------------------------------------------------------------------


def encontrar_grupo(data: ReportData, nome: str) -> Group:
    for grupo in data.grupos:
        if norm(grupo.nome) == norm(nome):
            return grupo
    raise EdicaoError(f"Grupo '{nome}' não encontrado.")


def editar_grupo(
    data: ReportData,
    nome: str,
    *,
    novo_nome: str | None = None,
    aba: str | None = None,
    titulo: str | None = None,
    subtitulo: str | None = None,
    conta: str | None = None,
    agencia: str | None = None,
    conta_corrente: str | None = None,
    cnpj: str | None = None,
) -> Group:
    grupo = encontrar_grupo(data, nome)
    if novo_nome is not None and novo_nome.strip() and norm(novo_nome) != norm(grupo.nome):
        if any(norm(g.nome) == norm(novo_nome) for g in data.grupos):
            raise EdicaoError(f"Já existe o grupo '{novo_nome}'.")
        antigo = grupo.nome
        grupo.nome = novo_nome.strip()
        for lote in data.lotes:
            if norm(lote.grupo) == norm(antigo):
                lote.grupo = grupo.nome
    for atributo, valor in (
        ("aba", aba),
        ("titulo", titulo),
        ("subtitulo", subtitulo),
        ("conta", conta),
        ("agencia", agencia),
        ("conta_corrente", conta_corrente),
        ("cnpj", cnpj),
    ):
        if valor is not None:
            setattr(grupo, atributo, valor.strip())
    return grupo


def adicionar_grupo(
    data: ReportData,
    *,
    nome: str,
    aba: str = "",
    titulo: str = "MUNICÍPIO DE EXEMPLO",
    subtitulo: str = "",
    conta: str = "",
    agencia: str = "0000-0 (Banco de Exemplo)",
    conta_corrente: str = "",
    cnpj: str = "",
) -> Group:
    nome = nome.strip()
    if not nome:
        raise EdicaoError("Informe o nome do grupo.")
    if any(norm(g.nome) == norm(nome) for g in data.grupos):
        raise EdicaoError(f"Já existe o grupo '{nome}'.")
    grupo = Group(
        nome=nome,
        aba=aba.strip() or f"Relatório Bens da {nome}",
        ordem=max((g.ordem for g in data.grupos), default=0) + 1,
        titulo=titulo.strip() or "MUNICÍPIO DE EXEMPLO",
        subtitulo=subtitulo.strip() or nome,
        conta=conta.strip() or f"Conta de depósito para lotes da {nome}",
        agencia=agencia.strip() or "0000-0 (Banco de Exemplo)",
        conta_corrente=conta_corrente.strip(),
        cnpj=cnpj.strip(),
    )
    data.grupos.append(grupo)
    return grupo


def remover_grupo(data: ReportData, nome: str) -> Group:
    grupo = encontrar_grupo(data, nome)
    associados = [lote for lote in data.lotes if norm(lote.grupo) == norm(grupo.nome)]
    if associados:
        raise EdicaoError(
            f"O grupo '{grupo.nome}' ainda tem {len(associados)} lote(s). "
            "Mude o grupo dos lotes antes de removê-lo."
        )
    data.grupos.remove(grupo)
    return grupo


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


def salvar_entrada(path: str | Path, data: ReportData) -> ReportData:
    """Salva as alterações na planilha de entrada e recarrega os dados."""
    write_entrada(path, data.grupos, data.lotes, data.bens, data.avisos)
    return ler_entrada(path)
