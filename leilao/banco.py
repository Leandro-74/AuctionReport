"""SQLite persistence for auction folders."""

from __future__ import annotations

import hashlib
import re
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .entrada import build_results, normalize_lot, normalize_source
from .models import Asset, Conta, Group, Lot, ReportData, norm
from .money import parse_money

BANCO_NOME = "leilao.db"
PASTA_DOCUMENTOS = "documentos"
PASTA_EXPORTACOES = "exportacoes"
SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    nome TEXT NOT NULL DEFAULT '',
    ano INTEGER,
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS grupos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    aba TEXT NOT NULL DEFAULT '',
    ordem INTEGER NOT NULL DEFAULT 0,
    titulo TEXT NOT NULL DEFAULT '',
    subtitulo TEXT NOT NULL DEFAULT '',
    conta TEXT NOT NULL DEFAULT '',
    agencia TEXT NOT NULL DEFAULT '',
    conta_corrente TEXT NOT NULL DEFAULT '',
    cnpj TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS contas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    titulo TEXT NOT NULL DEFAULT '',
    descricao TEXT NOT NULL DEFAULT '',
    agencia TEXT NOT NULL DEFAULT '',
    conta_corrente TEXT NOT NULL DEFAULT '',
    cnpj TEXT NOT NULL DEFAULT '',
    ordem INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS lotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    grupo_id INTEGER NOT NULL REFERENCES grupos(id) ON DELETE RESTRICT,
    conta_id INTEGER REFERENCES contas(id) ON DELETE RESTRICT,
    valor_venda TEXT NOT NULL,
    secao TEXT NOT NULL DEFAULT 'Bens em Geral',
    valor_avaliado TEXT,
    descricao_pl TEXT NOT NULL DEFAULT '',
    observacao TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS bens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lote_id INTEGER REFERENCES lotes(id) ON DELETE SET NULL,
    tipo TEXT NOT NULL DEFAULT 'Bens Móveis',
    codigo TEXT NOT NULL DEFAULT '',
    conta_credito TEXT NOT NULL DEFAULT '',
    conta_debito TEXT NOT NULL DEFAULT '',
    descricao TEXT NOT NULL,
    valor_contabil TEXT,
    origem TEXT NOT NULL DEFAULT '',
    categoria TEXT NOT NULL DEFAULT 'Outros',
    observacao TEXT NOT NULL DEFAULT '',
    ativo INTEGER NOT NULL DEFAULT 1,
    ordem INTEGER NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_bens_origem_codigo
    ON bens(origem, codigo) WHERE codigo <> '';
CREATE INDEX IF NOT EXISTS idx_bens_lote ON bens(lote_id);

CREATE TABLE IF NOT EXISTS documentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    nome TEXT NOT NULL,
    caminho TEXT NOT NULL,
    hash TEXT NOT NULL,
    importado_em TEXT NOT NULL
);
"""


def _agora() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _texto(value: object) -> str:
    return ("" if value is None else str(value)).strip()


def _decimal_texto(value) -> str | None:
    return None if value is None else str(value)


def _origem_canonica(origem: str) -> str:
    texto = _texto(origem)
    return normalize_source(texto) if texto else ""


def _ano_do_nome(nome: str) -> int | None:
    achado = re.search(r"\b((?:19|20)\d{2})\b", nome or "")
    return int(achado.group(1)) if achado else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def abrir_banco(path: str | Path, *, criar: bool = False):
    """Open a SQLite connection and enable foreign keys."""
    path = Path(path)
    if criar:
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        try:
            conn.executescript(_SCHEMA)
            _migrar_schema(conn)
            _verificar_schema(conn)
        except sqlite3.DatabaseError as exc:
            raise ValueError("O arquivo não é um banco SQLite válido.") from exc
        yield conn
    finally:
        conn.close()


def _migrar_schema(conn: sqlite3.Connection) -> None:
    colunas = {
        row["name"] for row in conn.execute("PRAGMA table_info(lotes)")
    }
    if "conta_id" not in colunas:
        conn.execute(
            "ALTER TABLE lotes ADD COLUMN conta_id INTEGER "
            "REFERENCES contas(id) ON DELETE RESTRICT"
        )
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()


def _verificar_schema(conn: sqlite3.Connection) -> None:
    tabelas = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if (
        "bens" not in tabelas
        or "lotes" not in tabelas
        or "grupos" not in tabelas
        or "contas" not in tabelas
    ):
        raise ValueError(
            "O arquivo não é um banco de leilão válido. "
            "Use a pasta criada pela ferramenta."
        )
    versao = conn.execute("PRAGMA user_version").fetchone()[0]
    if versao > SCHEMA_VERSION:
        raise ValueError(
            f"O banco usa uma versão mais nova ({versao}) do que esta ferramenta "
            f"suporta ({SCHEMA_VERSION})."
        )


def criar_estrutura(pasta: str | Path) -> Path:
    """Create the auction folder layout and return the folder path."""
    pasta = Path(pasta).expanduser()
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / PASTA_DOCUMENTOS).mkdir(exist_ok=True)
    (pasta / PASTA_EXPORTACOES).mkdir(exist_ok=True)
    return pasta


def caminho_banco(pasta: str | Path) -> Path:
    return Path(pasta).expanduser() / BANCO_NOME


def criar_banco(path: str | Path, nome: str = "") -> Path:
    """Create an empty auction database."""
    path = Path(path).expanduser()
    if path.exists() and path.stat().st_size > 0:
        raise ValueError(f"Já existe um banco em {path}.")
    pasta = criar_estrutura(path.parent)
    nome = nome.strip() or pasta.name
    with abrir_banco(path, criar=True) as conn:
        with conn:
            agora = _agora()
            conn.execute(
                "INSERT INTO meta (id, nome, ano, criado_em, atualizado_em) "
                "VALUES (1, ?, ?, ?, ?)",
                (nome, _ano_do_nome(nome), agora, agora),
            )
    return path


def _validar(data: ReportData) -> None:
    grupos: dict[str, str] = {}
    for grupo in data.grupos:
        nome = _texto(grupo.nome)
        if not nome:
            raise ValueError("Há um grupo sem nome.")
        chave = norm(nome)
        if chave in grupos:
            raise ValueError(f"Grupo duplicado: {nome}.")
        grupos[chave] = nome

    contas: set[int] = set()
    nomes_contas: set[str] = set()
    for conta in data.contas:
        nome = _texto(conta.nome)
        if not nome:
            raise ValueError("Há uma conta sem nome.")
        chave = norm(nome)
        if chave in nomes_contas:
            raise ValueError(f"Conta duplicada: {nome}.")
        nomes_contas.add(chave)
        if conta.id is not None:
            contas.add(conta.id)

    lotes: dict[str, str] = {}
    for lote in data.lotes:
        numero = normalize_lot(lote.numero)
        if not numero:
            raise ValueError("Há um lote sem número.")
        if numero in lotes:
            raise ValueError(f"Lote duplicado: {numero}.")
        lotes[numero] = numero
        if norm(lote.grupo) not in grupos:
            raise ValueError(
                f"O lote {numero} aponta para o grupo '{lote.grupo}', "
                "que não existe."
            )
        if lote.conta_id is not None and lote.conta_id not in contas:
            raise ValueError(
                f"O lote {numero} aponta para uma conta que não existe."
            )

    codigos: dict[tuple[str, str], str] = {}
    for bem in data.bens:
        if not _texto(bem.descricao):
            raise ValueError(
                f"O bem {bem.codigo or '(sem código)'} está sem descrição."
            )
        if bem.lote and normalize_lot(bem.lote) not in lotes:
            raise ValueError(
                f"O bem {bem.codigo or '(sem código)'} aponta para o lote "
                f"{bem.lote}, que não existe."
            )
        codigo = _texto(bem.codigo)
        if not codigo:
            continue
        chave = (_origem_canonica(bem.origem), codigo)
        if chave in codigos:
            origem = chave[0] or "sem origem"
            raise ValueError(
                f"O código {codigo} aparece mais de uma vez na origem "
                f"{origem}. Cada patrimônio deve ter uma única linha."
            )
        codigos[chave] = codigo


def _existe(conn: sqlite3.Connection, tabela: str, row_id: int) -> bool:
    row = conn.execute(
        f"SELECT 1 FROM {tabela} WHERE id = ?", (row_id,)
    ).fetchone()
    return row is not None


def _id_por_chave(
    conn: sqlite3.Connection, tabela: str, coluna: str, valor: str
) -> int | None:
    row = conn.execute(
        f"SELECT id FROM {tabela} WHERE {coluna} = ?", (valor,)
    ).fetchone()
    return int(row["id"]) if row is not None else None


def _apagar_ausentes(
    conn: sqlite3.Connection, tabela: str, ids: list[int]
) -> None:
    if not ids:
        conn.execute(f"DELETE FROM {tabela}")
        return
    marcadores = ",".join("?" for _ in ids)
    conn.execute(f"DELETE FROM {tabela} WHERE id NOT IN ({marcadores})", ids)


def _salvar_contas(conn: sqlite3.Connection, data: ReportData) -> None:
    for ordem, conta in enumerate(data.contas):
        valores = (
            _texto(conta.nome),
            _texto(conta.titulo),
            _texto(conta.descricao),
            _texto(conta.agencia),
            _texto(conta.conta_corrente),
            _texto(conta.cnpj),
            ordem,
        )
        if conta.id is None:
            conta.id = _id_por_chave(conn, "contas", "nome", valores[0])
        if conta.id is not None:
            if not _existe(conn, "contas", conta.id):
                raise ValueError(f"A conta '{conta.nome}' não existe mais no banco.")
            conn.execute(
                "UPDATE contas SET nome = ?, titulo = ?, descricao = ?, "
                "agencia = ?, conta_corrente = ?, cnpj = ?, ordem = ? "
                "WHERE id = ?",
                (*valores, conta.id),
            )
        else:
            cursor = conn.execute(
                "INSERT INTO contas (nome, titulo, descricao, agencia, "
                "conta_corrente, cnpj, ordem) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                valores,
            )
            conta.id = int(cursor.lastrowid)
        conta.row = ordem


def _salvar_grupos(conn: sqlite3.Connection, data: ReportData) -> dict[str, int]:
    ids: dict[str, int] = {}
    for grupo in data.grupos:
        valores = (
            _texto(grupo.nome),
            _texto(grupo.aba),
            int(grupo.ordem),
            _texto(grupo.titulo),
            _texto(grupo.subtitulo),
            _texto(grupo.conta),
            _texto(grupo.agencia),
            _texto(grupo.conta_corrente),
            _texto(grupo.cnpj),
        )
        if grupo.id is None:
            grupo.id = _id_por_chave(conn, "grupos", "nome", valores[0])
        if grupo.id is not None:
            if not _existe(conn, "grupos", grupo.id):
                raise ValueError(f"O grupo '{grupo.nome}' não existe mais no banco.")
            conn.execute(
                "UPDATE grupos SET nome = ?, aba = ?, ordem = ?, titulo = ?, "
                "subtitulo = ?, conta = ?, agencia = ?, conta_corrente = ?, "
                "cnpj = ? WHERE id = ?",
                (*valores, grupo.id),
            )
        else:
            cursor = conn.execute(
                "INSERT INTO grupos (nome, aba, ordem, titulo, subtitulo, "
                "conta, agencia, conta_corrente, cnpj) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                valores,
            )
            grupo.id = int(cursor.lastrowid)
        ids[norm(grupo.nome)] = grupo.id
    return ids


def _salvar_lotes(
    conn: sqlite3.Connection, data: ReportData, ids_grupos: dict[str, int]
) -> dict[str, int]:
    ids: dict[str, int] = {}
    for lote in data.lotes:
        numero = normalize_lot(lote.numero)
        lote.numero = numero
        grupo_id = ids_grupos.get(norm(lote.grupo))
        if grupo_id is None:
            raise ValueError(
                f"O lote {numero} aponta para o grupo '{lote.grupo}', "
                "que não existe."
            )
        valores = (
            numero,
            grupo_id,
            lote.conta_id,
            _decimal_texto(lote.valor),
            _texto(lote.secao) or "Bens em Geral",
            _decimal_texto(lote.valor_avaliado),
            _texto(lote.descricao_pl),
            _texto(lote.observacao),
        )
        if lote.id is None:
            lote.id = _id_por_chave(conn, "lotes", "numero", numero)
        if lote.id is not None:
            if not _existe(conn, "lotes", lote.id):
                raise ValueError(f"O lote {numero} não existe mais no banco.")
            conn.execute(
                "UPDATE lotes SET numero = ?, grupo_id = ?, conta_id = ?, "
                "valor_venda = ?, secao = ?, valor_avaliado = ?, "
                "descricao_pl = ?, observacao = ? WHERE id = ?",
                (*valores, lote.id),
            )
        else:
            cursor = conn.execute(
                "INSERT INTO lotes (numero, grupo_id, conta_id, valor_venda, "
                "secao, valor_avaliado, descricao_pl, observacao) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                valores,
            )
            lote.id = int(cursor.lastrowid)
        ids[numero] = lote.id
    return ids


def _salvar_bens(
    conn: sqlite3.Connection, data: ReportData, ids_lotes: dict[str, int]
) -> None:
    for ordem, bem in enumerate(data.bens):
        numero = normalize_lot(bem.lote) if bem.lote else ""
        bem.lote = numero
        lote_id = ids_lotes.get(numero) if numero else None
        if numero and lote_id is None:
            raise ValueError(
                f"O bem {bem.codigo or '(sem código)'} aponta para o lote "
                f"{numero}, que não existe."
            )
        origem = _origem_canonica(bem.origem)
        bem.origem = origem
        codigo = _texto(bem.codigo)
        valores = (
            lote_id,
            _texto(bem.tipo) or "Bens Móveis",
            codigo,
            _texto(bem.conta_credito),
            _texto(bem.conta_debito),
            _texto(bem.descricao),
            _decimal_texto(bem.valor_contabil),
            origem,
            _texto(bem.categoria) or "Outros",
            _texto(bem.observacao),
            ordem,
        )
        if bem.id is None and codigo:
            row = conn.execute(
                "SELECT id FROM bens WHERE origem = ? AND codigo = ?",
                (origem, codigo),
            ).fetchone()
            if row is not None:
                bem.id = int(row["id"])
        if bem.id is not None:
            if not _existe(conn, "bens", bem.id):
                raise ValueError(
                    f"O bem {bem.codigo or '(sem código)'} não existe mais "
                    "no banco."
                )
            conn.execute(
                "UPDATE bens SET lote_id = ?, tipo = ?, codigo = ?, "
                "conta_credito = ?, conta_debito = ?, descricao = ?, "
                "valor_contabil = ?, origem = ?, categoria = ?, "
                "observacao = ?, ordem = ? WHERE id = ?",
                (*valores, bem.id),
            )
        else:
            cursor = conn.execute(
                "INSERT INTO bens (lote_id, tipo, codigo, conta_credito, "
                "conta_debito, descricao, valor_contabil, origem, categoria, "
                "observacao, ordem) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                valores,
            )
            bem.id = int(cursor.lastrowid)
        bem.row = ordem


def salvar_leilao(path: str | Path, data: ReportData) -> ReportData:
    """Persist the full report data and reload it from the database."""
    path = Path(path).expanduser()
    _validar(data)
    if not path.exists():
        criar_banco(path, nome=path.parent.name)

    with abrir_banco(path) as conn:
        with conn:
            _salvar_contas(conn, data)
            ids_grupos = _salvar_grupos(conn, data)
            ids_lotes = _salvar_lotes(conn, data, ids_grupos)
            _salvar_bens(conn, data, ids_lotes)

            _apagar_ausentes(
                conn, "bens", [bem.id for bem in data.bens if bem.id is not None]
            )
            _apagar_ausentes(
                conn, "lotes", [lote.id for lote in data.lotes if lote.id is not None]
            )
            _apagar_ausentes(
                conn, "contas", [conta.id for conta in data.contas if conta.id is not None]
            )
            _apagar_ausentes(
                conn, "grupos", [grupo.id for grupo in data.grupos if grupo.id is not None]
            )
            conn.execute(
                "UPDATE meta SET atualizado_em = ? WHERE id = 1", (_agora(),)
            )
    return carregar_leilao(path)


def _carregar_contas(conn: sqlite3.Connection) -> list[Conta]:
    contas: list[Conta] = []
    for row in conn.execute("SELECT * FROM contas ORDER BY ordem, nome").fetchall():
        contas.append(
            Conta(
                id=int(row["id"]),
                nome=row["nome"],
                titulo=row["titulo"],
                descricao=row["descricao"],
                agencia=row["agencia"],
                conta_corrente=row["conta_corrente"],
                cnpj=row["cnpj"],
                row=int(row["ordem"]),
            )
        )
    return contas


def _carregar_grupos(conn: sqlite3.Connection) -> list[Group]:
    grupos: list[Group] = []
    for row in conn.execute(
        "SELECT * FROM grupos ORDER BY ordem, nome"
    ).fetchall():
        grupos.append(
            Group(
                id=int(row["id"]),
                nome=row["nome"],
                aba=row["aba"],
                ordem=int(row["ordem"]),
                titulo=row["titulo"],
                subtitulo=row["subtitulo"],
                conta=row["conta"],
                agencia=row["agencia"],
                conta_corrente=row["conta_corrente"],
                cnpj=row["cnpj"],
            )
        )
    return grupos


def _carregar_lotes(conn: sqlite3.Connection) -> list[Lot]:
    lotes: list[Lot] = []
    rows = conn.execute(
        "SELECT l.*, g.nome AS grupo_nome "
        "FROM lotes l JOIN grupos g ON g.id = l.grupo_id "
        "ORDER BY l.id"
    ).fetchall()
    for row in rows:
        try:
            valor = parse_money(row["valor_venda"])
            avaliado = (
                parse_money(row["valor_avaliado"])
                if row["valor_avaliado"] not in (None, "")
                else None
            )
        except ValueError as exc:
            raise ValueError(
                f"Valor inválido no lote {row['numero']}: {exc}."
            ) from exc
        lotes.append(
            Lot(
                id=int(row["id"]),
                numero=row["numero"],
                valor=valor,
                grupo=row["grupo_nome"],
                secao=row["secao"],
                valor_avaliado=avaliado,
                descricao_pl=row["descricao_pl"],
                observacao=row["observacao"],
                row=int(row["id"]),
                conta_id=row["conta_id"],
            )
        )
    return lotes


def _carregar_bens(conn: sqlite3.Connection, lotes: list[Lot]) -> list[Asset]:
    numeros = {lote.id: lote.numero for lote in lotes}
    bens: list[Asset] = []
    for row in conn.execute(
        "SELECT * FROM bens WHERE ativo = 1 ORDER BY ordem, id"
    ).fetchall():
        try:
            valor = (
                parse_money(row["valor_contabil"])
                if row["valor_contabil"] not in (None, "")
                else None
            )
        except ValueError as exc:
            raise ValueError(
                f"Valor contábil inválido no bem {row['codigo'] or row['id']}: "
                f"{exc}."
            ) from exc
        bens.append(
            Asset(
                id=int(row["id"]),
                lote=numeros.get(row["lote_id"], ""),
                tipo=row["tipo"],
                codigo=row["codigo"],
                conta_credito=row["conta_credito"],
                conta_debito=row["conta_debito"],
                descricao=row["descricao"],
                valor_contabil=valor,
                origem=row["origem"],
                categoria=row["categoria"],
                observacao=row["observacao"],
                row=int(row["ordem"]),
            )
        )
    return bens


def carregar_leilao(path: str | Path) -> ReportData:
    """Load an auction database, validate it and calculate the split."""
    path = Path(path).expanduser()
    if not path.exists():
        raise ValueError(f"Banco não encontrado: {path}")
    with abrir_banco(path) as conn:
        data = ReportData(
            grupos=_carregar_grupos(conn),
            contas=_carregar_contas(conn),
            lotes=_carregar_lotes(conn),
        )
        data.bens = _carregar_bens(conn, data.lotes)
    build_results(data)
    return data


def criar_leilao(pasta: str | Path, data: ReportData) -> ReportData:
    """Create a new auction database, replacing it only on success."""
    pasta = criar_estrutura(pasta)
    db_path = caminho_banco(pasta)
    if db_path.exists():
        raise ValueError(f"Já existe um leilão em {pasta}.")
    temporario = pasta / f"{BANCO_NOME}.tmp"
    if temporario.exists():
        temporario.unlink()
    criar_banco(temporario, nome=pasta.name)
    try:
        resultado = salvar_leilao(temporario, data)
    except Exception:
        temporario.unlink(missing_ok=True)
        raise
    temporario.replace(db_path)
    return resultado


def migrar_planilha(xlsx_path: str | Path, pasta: str | Path) -> ReportData:
    """Create an auction folder and database from a legacy input workbook."""
    from .entrada import ler_entrada

    data = ler_entrada(xlsx_path)
    return criar_leilao(pasta, data)


def copiar_documentos(
    db_path: str | Path, arquivos: list[tuple[str, str | Path]]
) -> list[dict[str, str]]:
    """Copy source files into the auction folder and record their hashes."""
    db_path = Path(db_path).expanduser()
    pasta = criar_estrutura(db_path.parent)
    docs = pasta / PASTA_DOCUMENTOS
    registros: list[dict[str, str]] = []

    with abrir_banco(db_path) as conn:
        with conn:
            for tipo, origem in arquivos:
                origem = Path(origem).expanduser()
                if not origem.exists():
                    continue
                destino = _destino_documento(docs, origem)
                if not destino.exists():
                    shutil.copy2(origem, destino)
                digest = _sha256(destino)
                relativo = str(destino.relative_to(pasta))
                conn.execute(
                    "INSERT INTO documentos (tipo, nome, caminho, hash, importado_em) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (tipo, destino.name, relativo, digest, _agora()),
                )
                registros.append(
                    {
                        "tipo": tipo,
                        "nome": destino.name,
                        "caminho": relativo,
                        "hash": digest,
                    }
                )
    return registros


def _destino_documento(docs: Path, origem: Path) -> Path:
    destino = docs / origem.name
    if not destino.exists():
        return destino
    origem_hash = _sha256(origem)
    if _sha256(destino) == origem_hash:
        return destino
    contador = 2
    while True:
        candidato = docs / f"{origem.stem} ({contador}){origem.suffix}"
        if not candidato.exists():
            return candidato
        if _sha256(candidato) == origem_hash:
            return candidato
        contador += 1
