"""Reconcile new PDF reports with an existing auction."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from .entrada import (
    bulk_lots,
    group_for_source,
    normalize_lot,
    normalize_source,
    suggest_section,
)
from .models import Asset, Group, Issue, LawLot, Lot, ReportData, norm
from .pdfs import PdfError, parse_asset_report, parse_law


@dataclass
class AlteracaoBem:
    bem: Asset
    campos: dict[str, tuple[object, object]]


@dataclass
class PlanoAtualizacao:
    novos: list[Asset] = field(default_factory=list)
    alterados: list[AlteracaoBem] = field(default_factory=list)
    ausentes: list[Asset] = field(default_factory=list)
    novos_lotes: list[Lot] = field(default_factory=list)
    novos_grupos: list[Group] = field(default_factory=list)
    avisos: list[Issue] = field(default_factory=list)

    @property
    def tem_mudancas(self) -> bool:
        return bool(
            self.novos
            or self.alterados
            or self.novos_lotes
            or self.novos_grupos
        )

    def aplicar(self, data: ReportData) -> ReportData:
        """Apply the plan to the in-memory auction."""
        nomes = {norm(grupo.nome) for grupo in data.grupos}
        for grupo in self.novos_grupos:
            if norm(grupo.nome) not in nomes:
                data.grupos.append(grupo)
                nomes.add(norm(grupo.nome))
        for alteracao in self.alterados:
            for campo, (_, novo) in alteracao.campos.items():
                setattr(alteracao.bem, campo, novo)
        numeros = {normalize_lot(lote.numero) for lote in data.lotes}
        for lote in self.novos_lotes:
            if normalize_lot(lote.numero) not in numeros:
                data.lotes.append(lote)
                numeros.add(normalize_lot(lote.numero))
        existentes = {id(bem) for bem in data.bens}
        for bem in self.novos:
            if id(bem) not in existentes:
                data.bens.append(bem)
        return data


def _grupo_para_origem(
    data: ReportData, plano: PlanoAtualizacao, origem: str
) -> Group:
    nome = normalize_source(origem)
    for grupo in data.grupos:
        if norm(grupo.nome) == norm(nome):
            return grupo
    for grupo in plano.novos_grupos:
        if norm(grupo.nome) == norm(nome):
            return grupo
    grupo = group_for_source(nome)
    plano.novos_grupos.append(grupo)
    return grupo


def _grupo_do_lote(
    data: ReportData,
    plano: PlanoAtualizacao,
    law: LawLot,
) -> Group:
    vinculados = [
        bem
        for bem in data.bens
        if bem.lote and normalize_lot(bem.lote) == normalize_lot(law.numero)
    ]
    vinculados += [
        bem for bem in plano.novos if bem.lote == normalize_lot(law.numero)
    ]
    contagem = Counter(bem.origem for bem in vinculados if bem.origem)
    if contagem:
        origem = contagem.most_common(1)[0][0]
    elif law.categoria == "Hospitalar":
        origem = "Saúde"
    else:
        origem = "Prefeitura"
    return _grupo_para_origem(data, plano, origem)


def _codigos_ambiguos(
    existentes: dict[tuple[str, str], Asset],
    recebidos: dict[tuple[str, str], Asset],
) -> set[str]:
    origens: dict[str, set[str]] = {}
    for origem, codigo in set(existentes) | set(recebidos):
        origens.setdefault(codigo, set()).add(origem)
    return {codigo for codigo, valores in origens.items() if len(valores) > 1}


def _sugerir_lotes(
    plano: PlanoAtualizacao,
    law_lots: list[LawLot],
    ambiguos: set[str],
) -> None:
    por_codigo = {
        lote.codigo_bem: lote for lote in law_lots if lote.codigo_bem
    }
    bulk = bulk_lots(law_lots)
    for bem in plano.novos:
        if bem.codigo in ambiguos:
            continue
        law = por_codigo.get(bem.codigo)
        if law is not None:
            bem.lote = normalize_lot(law.numero)
            continue
        if bem.categoria == "Veículos":
            continue
        if norm(bem.origem) == "SAUDE" and bulk.get("Hospitalar"):
            bem.lote = normalize_lot(bulk["Hospitalar"].numero)
        elif bem.categoria == "Informática" and bulk.get("Informática"):
            bem.lote = normalize_lot(bulk["Informática"].numero)
        elif bem.categoria == "Mobiliário" and bulk.get("Mobiliário"):
            bem.lote = normalize_lot(bulk["Mobiliário"].numero)
        elif bem.categoria == "Hospitalar" and bulk.get("Hospitalar"):
            bem.lote = normalize_lot(bulk["Hospitalar"].numero)


def planejar_atualizacao(
    data: ReportData,
    relatorios: list[tuple[str, str | Path]],
    pl: str | Path | None = None,
) -> PlanoAtualizacao:
    """Compare new PDFs with the current auction without changing it."""
    if not relatorios:
        raise ValueError("Selecione pelo menos um relatório para atualizar.")

    plano = PlanoAtualizacao()
    origens: list[str] = []
    recebidos: dict[tuple[str, str], Asset] = {}
    for label, caminho in relatorios:
        origem = normalize_source(label)
        origens.append(origem)
        try:
            bens_pdf = parse_asset_report(caminho, origem)
        except PdfError as exc:
            raise ValueError(str(exc)) from exc
        for bem in bens_pdf:
            if not bem.codigo:
                continue
            chave = (norm(bem.origem), bem.codigo)
            if chave in recebidos:
                plano.avisos.append(
                    Issue(
                        "aviso",
                        f"O código {bem.codigo} ({origem}) aparece mais de uma "
                        "vez no PDF; mantive a primeira ocorrência.",
                    )
                )
                continue
            recebidos[chave] = bem

    law_lots: list[LawLot] = []
    if pl:
        try:
            law_lots = parse_law(pl)
        except PdfError as exc:
            raise ValueError(str(exc)) from exc

    existentes: dict[tuple[str, str], Asset] = {}
    for bem in data.bens:
        if bem.codigo:
            chave = (norm(bem.origem), bem.codigo)
            existentes.setdefault(chave, bem)

    for chave, novo in recebidos.items():
        atual = existentes.get(chave)
        if atual is None:
            plano.novos.append(novo)
            continue
        campos: dict[str, tuple[object, object]] = {}
        if novo.tipo and novo.tipo != atual.tipo:
            campos["tipo"] = (atual.tipo, novo.tipo)
        if novo.descricao and novo.descricao != atual.descricao:
            campos["descricao"] = (atual.descricao, novo.descricao)
        if (
            novo.valor_contabil is not None
            and novo.valor_contabil != atual.valor_contabil
        ):
            campos["valor_contabil"] = (
                atual.valor_contabil,
                novo.valor_contabil,
            )
        if campos:
            plano.alterados.append(AlteracaoBem(atual, campos))

    origens_recebidas = {norm(origem) for origem in origens}
    for chave, atual in existentes.items():
        if chave[0] not in origens_recebidas:
            continue
        if chave not in recebidos:
            plano.ausentes.append(atual)

    ambiguos = _codigos_ambiguos(existentes, recebidos)
    if law_lots:
        _sugerir_lotes(plano, law_lots, ambiguos)

    for origem in origens:
        _grupo_para_origem(data, plano, origem)

    existentes_lotes = {
        normalize_lot(lote.numero) for lote in data.lotes
    }
    for law in law_lots:
        numero = normalize_lot(law.numero)
        if numero in existentes_lotes:
            continue
        grupo = _grupo_do_lote(data, plano, law)
        plano.novos_lotes.append(
            Lot(
                numero=numero,
                valor=Decimal("0.00"),
                valor_informado=False,
                grupo=grupo.nome,
                secao=suggest_section(law),
                valor_avaliado=law.valor_avaliado,
                descricao_pl=law.descricao,
            )
        )
        existentes_lotes.add(numero)

    if ambiguos:
        por_codigo = {
            lote.codigo_bem: lote for lote in law_lots if lote.codigo_bem
        }
        for codigo in sorted(ambiguos & set(por_codigo)):
            plano.avisos.append(
                Issue(
                    "aviso",
                    f"O código {codigo} aparece em mais de uma origem; "
                    f"o lote {por_codigo[codigo].numero} não foi aplicado "
                    "automaticamente aos bens novos.",
                )
            )

    sem_lote = [bem for bem in plano.novos if not bem.lote]
    if sem_lote:
        exemplos = ", ".join(
            f"{bem.codigo or '(sem código)'} ({bem.origem or 'sem origem'})"
            for bem in sem_lote[:10]
        )
        restante = "" if len(sem_lote) <= 10 else f" e mais {len(sem_lote) - 10}"
        plano.avisos.append(
            Issue(
                "aviso",
                f"{len(sem_lote)} bem(ns) novo(s) ficaram sem lote: "
                f"{exemplos}{restante}.",
            )
        )

    if plano.ausentes:
        exemplos = ", ".join(
            f"{bem.codigo} ({bem.origem or 'sem origem'})"
            for bem in plano.ausentes[:10]
        )
        restante = (
            ""
            if len(plano.ausentes) <= 10
            else f" e mais {len(plano.ausentes) - 10}"
        )
        plano.avisos.append(
            Issue(
                "aviso",
                f"{len(plano.ausentes)} bem(ns) do banco não apareceram nos "
                f"PDFs: {exemplos}{restante}. Eles foram mantidos.",
            )
        )

    for lote in plano.novos_lotes:
        tem_bens = any(
            bem.lote and normalize_lot(bem.lote) == normalize_lot(lote.numero)
            for bem in data.bens
        ) or any(bem.lote == lote.numero for bem in plano.novos)
        if not tem_bens:
            plano.avisos.append(
                Issue(
                    "aviso",
                    f"Lote {lote.numero} do projeto de lei não tem bens "
                    "associados. Confira antes de exportar.",
                )
            )

    return plano
