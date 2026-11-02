"""pericias estruturadas, sentidos numericos, percepcao passiva

Revision ID: 4ec46f860d54
Revises: 7eca70a534c0
Create Date: 2026-10-30 17:21:52.107597

"""
import re
from pathlib import Path
from typing import Sequence, Union

import yaml
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ec46f860d54'
down_revision: Union[str, Sequence[str], None] = '7eca70a534c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# alembic/versions/<este arquivo>.py -> raiz do projeto (mesmo cálculo de alembic/env.py).
_RAIZ = Path(__file__).resolve().parents[2]

# Nomes do catálogo de sentidos ANTES desta migração (ver investigação com o autor): o texto
# original de várias criaturas já dizia "Visão às escuras 18 m (sem visão além deste raio)" —
# frase que descreve Visão às cegas (cego fora do alcance), não Visão no escuro; e "Visão às
# cegas" (usado pelos dragões jovens) é o mesmo sentido que "Visão cega" (morcegos, enxame de
# insetos), só com nome diferente por causa de como a migração anterior dividiu o texto peça por
# peça. Consolida os três num só: "Visão cega".
_NOME_PERCEPCAO_PASSIVA = "Percepção passiva"
_NOMES_CEGO_PARA_MERGE = ["Visão às escuras 18 m (sem visão além deste raio)", "Visão às cegas"]
_NOME_CEGO_CANONICO = "Visão cega"


def _id_por_nome(connection, tabela: str, nome: str) -> int | None:
    linha = connection.execute(
        sa.text(f"SELECT id FROM {tabela} WHERE nome = :n"), {"n": nome},
    ).fetchone()
    return linha[0] if linha else None


def _extrair_numero(texto: str | None) -> float | None:
    if not texto:
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", texto)
    return float(m.group(0).replace(",", ".")) if m else None


def _migrar_sentidos_e_percepcao(connection) -> None:
    """Roda DEPOIS de criar `ficha_sentidos.valor_num` e `fichas_monstro.percepcao_passiva`, e
    ANTES de apagar `ficha_sentidos.valor` (texto) — nada se perde."""
    # 1) Converte o texto de cada vínculo pra número (ex.: "18 m" -> 18.0). O vínculo malformado
    #    ("Visão às escuras 18 m...") não tem valor próprio — o número está só no nome do
    #    catálogo — então extrai dali antes de descartar o nome.
    id_malformado = _id_por_nome(connection, "sentidos", _NOMES_CEGO_PARA_MERGE[0])
    for ficha_id, vinculo_id, sentido_id, valor_texto in connection.execute(
        sa.text("SELECT ficha_id, id, sentido_id, valor FROM ficha_sentidos"),
    ).fetchall():
        numero = _extrair_numero(valor_texto)
        if numero is None and sentido_id == id_malformado:
            numero = _extrair_numero(_NOMES_CEGO_PARA_MERGE[0])
        connection.execute(
            sa.text("UPDATE ficha_sentidos SET valor_num = :v WHERE id = :id"),
            {"v": numero, "id": vinculo_id},
        )

    # 2) Funde os três nomes de "cego fora do alcance" num só (ver nota acima).
    id_canonico = _id_por_nome(connection, "sentidos", _NOME_CEGO_CANONICO)
    for nome_antigo in _NOMES_CEGO_PARA_MERGE:
        id_antigo = _id_por_nome(connection, "sentidos", nome_antigo)
        if id_antigo is None:
            continue
        connection.execute(
            sa.text("UPDATE ficha_sentidos SET sentido_id = :novo WHERE sentido_id = :velho"),
            {"novo": id_canonico, "velho": id_antigo},
        )
        connection.execute(sa.text("DELETE FROM sentidos WHERE id = :id"), {"id": id_antigo})

    # 3) Percepção passiva: sai do catálogo de Sentidos, vira coluna própria de FichaMonstro
    #    (toda criatura tem uma — não é uma "escolha" de sentido especial).
    id_percepcao = _id_por_nome(connection, "sentidos", _NOME_PERCEPCAO_PASSIVA)
    if id_percepcao is not None:
        for ficha_id, valor_texto in connection.execute(
            sa.text("SELECT ficha_id, valor FROM ficha_sentidos WHERE sentido_id = :s"),
            {"s": id_percepcao},
        ).fetchall():
            numero = _extrair_numero(valor_texto)
            if numero is not None:
                connection.execute(
                    sa.text("UPDATE fichas_monstro SET percepcao_passiva = :v WHERE id = :id"),
                    {"v": int(numero), "id": ficha_id},
                )
        connection.execute(sa.text("DELETE FROM ficha_sentidos WHERE sentido_id = :s"), {"s": id_percepcao})
        connection.execute(sa.text("DELETE FROM sentidos WHERE id = :id"), {"id": id_percepcao})


def _normalizar(texto: str) -> str:
    import unicodedata
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return sem_acento.strip().lower()


def _semear_pericias(connection) -> dict[str, int]:
    """Cria o catálogo de Perícias a partir de docs/pericias/*.md (front matter `pericia:` +
    título) — mesmo padrão já usado pra Equipamento/Magia a partir de docs/itens, docs/magias.
    Devolve nome normalizado -> id, pra casar com o texto livre antigo de fichas_monstro.pericias."""
    pasta = _RAIZ / "docs" / "pericias"
    ids_por_nome: dict[str, int] = {}
    if not pasta.is_dir():
        return ids_por_nome
    for arquivo in sorted(pasta.glob("*.md")):
        if arquivo.name == "index.md":
            continue
        texto = arquivo.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", texto, re.S)
        if not m:
            continue
        front = yaml.safe_load(m.group(1)) or {}
        dados_pericia = front.get("pericia") or {}
        titulo_m = re.search(r"^#\s+(.+)$", m.group(2), re.M)
        if not titulo_m:
            continue
        nome = titulo_m.group(1).strip()
        r = connection.execute(
            sa.text(
                "INSERT INTO pericias (nome, atributo, fonte, slug_origem) VALUES (:n, :a, :f, :s)"
            ),
            {
                "n": nome, "a": dados_pericia.get("atributo"), "f": dados_pericia.get("fonte"),
                "s": f"pericias/{arquivo.name}",
            },
        )
        ids_por_nome[_normalizar(nome)] = r.lastrowid
    return ids_por_nome


def _migrar_pericias_das_fichas(connection, ids_pericia_por_nome: dict[str, int]) -> None:
    """Lê o texto livre antigo (ex.: "Furtividade +6, Percepção +4") e cria os vínculos
    ficha_pericias com o bônus já pronto pra rolar — roda ANTES de apagar a coluna de texto."""
    linhas = connection.execute(
        sa.text("SELECT id, pericias FROM fichas_monstro WHERE pericias IS NOT NULL"),
    ).fetchall()
    for ficha_id, texto in linhas:
        for pedaco in (texto or "").split(","):
            pedaco = pedaco.strip()
            m = re.match(r"^(.+?)\s*([+-]\s*\d+)$", pedaco)
            if not m:
                continue  # "—" (nenhuma) ou lixo não reconhecido — nada a vincular
            nome, bonus_texto = m.group(1).strip(), m.group(2).replace(" ", "")
            pericia_id = ids_pericia_por_nome.get(_normalizar(nome))
            if pericia_id is None:
                continue  # nome não casou com o catálogo — fica de fora (revisar manualmente)
            connection.execute(
                sa.text("INSERT INTO ficha_pericias (ficha_id, pericia_id, bonus) VALUES (:f, :p, :b)"),
                {"f": ficha_id, "p": pericia_id, "b": int(bonus_texto)},
            )


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('pericias',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=100), nullable=False),
    sa.Column('atributo', sa.String(length=20), nullable=True),
    sa.Column('fonte', sa.String(length=20), nullable=True),
    sa.Column('slug_origem', sa.String(length=200), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pericias_nome'), 'pericias', ['nome'], unique=True)
    op.create_table('ficha_pericias',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ficha_id', sa.Integer(), nullable=False),
    sa.Column('pericia_id', sa.Integer(), nullable=False),
    sa.Column('bonus', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['ficha_id'], ['fichas_monstro.id'], ),
    sa.ForeignKeyConstraint(['pericia_id'], ['pericias.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('fichas_monstro', sa.Column('percepcao_passiva', sa.Integer(), nullable=False, server_default='10'))
    # Coluna nova lado a lado com a antiga (SQLite não suporta ALTER COLUMN TYPE — mesma solução
    # já usada antes): migra os dados, apaga a antiga, renomeia esta pro nome final.
    op.add_column('ficha_sentidos', sa.Column('valor_num', sa.Double(), nullable=True))
    # (sem alter_column no tipo de `cr`: SQLite não impõe tamanho de VARCHAR — ver migração anterior.)

    conexao = op.get_bind()
    _migrar_sentidos_e_percepcao(conexao)
    ids_pericia = _semear_pericias(conexao)
    _migrar_pericias_das_fichas(conexao, ids_pericia)

    op.drop_column('ficha_sentidos', 'valor')
    op.execute("ALTER TABLE ficha_sentidos RENAME COLUMN valor_num TO valor")
    op.drop_column('fichas_monstro', 'pericias')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('fichas_monstro', sa.Column('pericias', sa.VARCHAR(length=300), nullable=True))
    op.add_column('ficha_sentidos', sa.Column('valor_texto', sa.VARCHAR(length=50), nullable=True))
    op.execute("UPDATE ficha_sentidos SET valor_texto = CAST(valor AS TEXT)")
    op.drop_column('ficha_sentidos', 'valor')
    op.execute("ALTER TABLE ficha_sentidos RENAME COLUMN valor_texto TO valor")
    op.drop_column('fichas_monstro', 'percepcao_passiva')
    op.drop_table('ficha_pericias')
    op.drop_index(op.f('ix_pericias_nome'), table_name='pericias')
    op.drop_table('pericias')
    # ### end Alembic commands ###
