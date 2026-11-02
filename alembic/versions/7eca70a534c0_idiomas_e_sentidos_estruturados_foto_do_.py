"""idiomas e sentidos estruturados, foto do monstro, deslocamento numerico

Revision ID: 7eca70a534c0
Revises: 13c43b36be0a
Create Date: 2026-10-30 00:49:49.006527

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7eca70a534c0'
down_revision: Union[str, Sequence[str], None] = '13c43b36be0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _migrar_dados(connection) -> None:
    """Transfere os valores dos campos de texto antigos (deslocamento/idiomas/sentidos) para as
    tabelas novas, e limpa o "(NN PE)" do CR — roda DEPOIS de criar as tabelas/colunas novas e
    ANTES de apagar as colunas antigas, pra nada se perder."""
    cache_idioma: dict[str, int] = {}
    cache_sentido: dict[str, int] = {}

    def _id_catalogo(tabela: str, cache: dict[str, int], nome: str) -> int:
        nome = nome.strip()
        if nome in cache:
            return cache[nome]
        existente = connection.execute(
            sa.text(f"SELECT id FROM {tabela} WHERE nome = :n"), {"n": nome},
        ).fetchone()
        if existente:
            cache[nome] = existente[0]
        else:
            r = connection.execute(sa.text(f"INSERT INTO {tabela} (nome) VALUES (:n)"), {"n": nome})
            cache[nome] = r.lastrowid
        return cache[nome]

    linhas = connection.execute(
        sa.text("SELECT id, cr, deslocamento, idiomas, sentidos FROM fichas_monstro"),
    ).fetchall()

    for ficha_id, cr, deslocamento, idiomas, sentidos in linhas:
        if cr:
            cr_limpo = re.sub(r"\s*\(.*\)\s*$", "", cr).strip()
            connection.execute(
                sa.text("UPDATE fichas_monstro SET cr = :cr WHERE id = :id"), {"cr": cr_limpo, "id": ficha_id},
            )

        desloc_m, desloc_extra = 9.0, None
        if deslocamento:
            m = re.match(r"^\s*(\d+(?:[.,]\d+)?)\s*m\b\s*(.*)$", deslocamento)
            if m:
                desloc_m = float(m.group(1).replace(",", "."))
                desloc_extra = m.group(2).strip(" ,()") or None
            else:
                desloc_extra = deslocamento
        connection.execute(
            sa.text("UPDATE fichas_monstro SET deslocamento_m = :m, deslocamento_extra = :e WHERE id = :id"),
            {"m": desloc_m, "e": desloc_extra, "id": ficha_id},
        )

        for pedaco in (idiomas or "").split(","):
            pedaco = pedaco.strip()
            if not pedaco:
                continue
            idioma_id = _id_catalogo("idiomas", cache_idioma, pedaco)
            connection.execute(
                sa.text("INSERT INTO ficha_idiomas (ficha_id, idioma_id) VALUES (:f, :i)"),
                {"f": ficha_id, "i": idioma_id},
            )

        for pedaco in (sentidos or "").split(","):
            pedaco = pedaco.strip()
            if not pedaco:
                continue
            m = re.match(r"^(.*?)\s+(\d+(?:[.,]\d+)?\s*m?)$", pedaco)
            tipo, valor = (m.group(1).strip(), m.group(2).strip()) if m else (pedaco, None)
            sentido_id = _id_catalogo("sentidos", cache_sentido, tipo)
            connection.execute(
                sa.text("INSERT INTO ficha_sentidos (ficha_id, sentido_id, valor) VALUES (:f, :s, :v)"),
                {"f": ficha_id, "s": sentido_id, "v": valor},
            )


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('idiomas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_idiomas_nome'), 'idiomas', ['nome'], unique=True)
    op.create_table('sentidos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sentidos_nome'), 'sentidos', ['nome'], unique=True)
    op.create_table('ficha_idiomas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ficha_id', sa.Integer(), nullable=False),
    sa.Column('idioma_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['ficha_id'], ['fichas_monstro.id'], ),
    sa.ForeignKeyConstraint(['idioma_id'], ['idiomas.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ficha_sentidos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ficha_id', sa.Integer(), nullable=False),
    sa.Column('sentido_id', sa.Integer(), nullable=False),
    sa.Column('valor', sa.String(length=50), nullable=True),
    sa.ForeignKeyConstraint(['ficha_id'], ['fichas_monstro.id'], ),
    sa.ForeignKeyConstraint(['sentido_id'], ['sentidos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('fichas_monstro', sa.Column('deslocamento_m', sa.Double(), nullable=False, server_default='9'))
    op.add_column('fichas_monstro', sa.Column('deslocamento_extra', sa.String(length=150), nullable=True))
    # (sem alter_column no tipo de `cr`: SQLite não impõe tamanho de VARCHAR nem suporta ALTER
    # COLUMN TYPE — o encurtamento de 20 para 10 chars é só cosmético no lado do SQLAlchemy.)
    op.add_column('monstros', sa.Column('foto', sa.String(length=300), nullable=True))

    _migrar_dados(op.get_bind())

    op.drop_column('fichas_monstro', 'deslocamento')
    op.drop_column('fichas_monstro', 'idiomas')
    op.drop_column('fichas_monstro', 'sentidos')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('monstros', 'foto')
    op.add_column('fichas_monstro', sa.Column('sentidos', sa.VARCHAR(length=300), nullable=True))
    op.add_column('fichas_monstro', sa.Column('idiomas', sa.VARCHAR(length=200), nullable=True))
    op.add_column('fichas_monstro', sa.Column('deslocamento', sa.VARCHAR(length=100), nullable=True))
    op.drop_column('fichas_monstro', 'deslocamento_extra')
    op.drop_column('fichas_monstro', 'deslocamento_m')
    op.drop_table('ficha_sentidos')
    op.drop_table('ficha_idiomas')
    op.drop_index(op.f('ix_sentidos_nome'), table_name='sentidos')
    op.drop_table('sentidos')
    op.drop_index(op.f('ix_idiomas_nome'), table_name='idiomas')
    op.drop_table('idiomas')
    # ### end Alembic commands ###
