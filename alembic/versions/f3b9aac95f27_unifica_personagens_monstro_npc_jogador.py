"""unifica personagens: monstro, npc e jogador no mesmo schema

Revision ID: f3b9aac95f27
Revises: 4ec46f860d54
Create Date: 2026-10-31 00:00:00.000000

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3b9aac95f27'
down_revision: Union[str, Sequence[str], None] = '4ec46f860d54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _migrar_peso_equipamentos(connection) -> None:
    """`equipamentos.peso` (texto, sempre "<número> kg" nos dados reais) -> `peso_kg` (número).
    Roda DEPOIS de criar `peso_kg` e ANTES de apagar `peso` — nada se perde mesmo se algum valor
    fugir do padrão esperado (fica NULL em vez de travar a migração)."""
    linhas = connection.execute(sa.text("SELECT id, peso FROM equipamentos WHERE peso IS NOT NULL")).fetchall()
    for id_item, peso_texto in linhas:
        m = re.search(r"\d+(?:[.,]\d+)?", peso_texto or "")
        valor = float(m.group(0).replace(",", ".")) if m else None
        connection.execute(
            sa.text("UPDATE equipamentos SET peso_kg = :v WHERE id = :id"), {"v": valor, "id": id_item},
        )


def upgrade() -> None:
    """Upgrade schema."""
    # 1) Renomeia as tabelas principais. SQLite reescreve sozinho as FKs das tabelas de vínculo
    #    que apontavam pra fichas_monstro.id (confirmado numa cópia de teste antes de rodar aqui).
    op.rename_table('monstros', 'personagens')
    op.rename_table('fichas_monstro', 'fichas')

    # 2) Discriminador de tipo — toda linha existente é, de fato, um monstro. A coluna antiga
    #    `tipo` (ex.: "Humanoide (goblinoide)") vira `tipo_criatura` pra não colidir de nome.
    op.execute("ALTER TABLE personagens RENAME COLUMN tipo TO tipo_criatura")
    op.add_column('personagens', sa.Column('tipo', sa.String(length=10), nullable=False, server_default='monstro'))
    op.execute("ALTER TABLE fichas RENAME COLUMN monstro_id TO personagem_id")

    # 3) slug único (tipo, slug), não slug único global — NPC/jogador/monstro não têm checagem de
    #    slug cruzada entre pastas hoje, então um índice único global quebraria dado válido.
    op.drop_index('ix_monstros_slug', table_name='personagens')
    op.create_index('ix_personagens_slug', 'personagens', ['slug'])
    op.create_index('ix_personagens_tipo', 'personagens', ['tipo'])
    # SQLite não suporta ALTER TABLE ADD CONSTRAINT sem o modo batch (copy-and-move) — um índice
    # único cobre a mesma garantia sem precisar disso.
    op.create_index('uq_personagens_tipo_slug', 'personagens', ['tipo', 'slug'], unique=True)

    # 4) Biografia (compartilhada entre as fichas de um personagem, não por variante)
    for coluna, tipo_coluna in [
        ('genero', sa.String(50)), ('idade', sa.String(50)), ('altura', sa.String(50)),
        ('peso_corporal', sa.String(50)), ('olhos', sa.String(50)), ('cabelo', sa.String(50)),
        ('pele', sa.String(50)), ('fe', sa.String(100)),
        ('aparencia', sa.Text()), ('personalidade', sa.Text()), ('traco', sa.Text()),
        ('ideal', sa.Text()), ('vinculo', sa.Text()), ('defeito', sa.Text()),
        ('pessoas_interesse', sa.Text()), ('lugares_interesse', sa.Text()),
    ]:
        op.add_column('personagens', sa.Column(coluna, tipo_coluna, nullable=True))

    # 5) Diário — lista de entradas (data/título/texto), não um texto único.
    op.create_table(
        'personagem_diario_entradas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('personagem_id', sa.Integer(), nullable=False),
        sa.Column('data', sa.String(length=50), nullable=True),
        sa.Column('titulo', sa.String(length=200), nullable=True),
        sa.Column('texto', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['personagem_id'], ['personagens.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    # 6) Campos novos de Ficha
    op.add_column('fichas', sa.Column('nivel', sa.Integer(), nullable=True))
    op.add_column('fichas', sa.Column('xp', sa.Integer(), nullable=True))
    op.add_column('fichas', sa.Column('classe', sa.String(length=150), nullable=True))
    op.add_column('fichas', sa.Column('antecedente', sa.String(length=100), nullable=True))
    op.add_column('fichas', sa.Column('pv_temporario', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('fichas', sa.Column('dados_vida_total', sa.String(length=50), nullable=True))
    op.add_column('fichas', sa.Column('dados_vida_usados', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('fichas', sa.Column('iniciativa_extra', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('fichas', sa.Column('carga_maxima', sa.Double(), nullable=True))
    for moeda in ('moeda_pc', 'moeda_pp', 'moeda_pe', 'moeda_po', 'moeda_pl'):
        op.add_column('fichas', sa.Column(moeda, sa.Integer(), nullable=False, server_default='0'))

    # 7) Tabelas novas ligadas a Ficha
    op.create_table(
        'fichas_espacos_magia',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ficha_id', sa.Integer(), nullable=False),
        sa.Column('nivel', sa.Integer(), nullable=False),
        sa.Column('maximo', sa.Integer(), nullable=False),
        sa.Column('usado', sa.Integer(), nullable=False),
        sa.Column('rotulo', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['ficha_id'], ['fichas.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'fichas_condicoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ficha_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(['ficha_id'], ['fichas.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'fichas_efeitos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ficha_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=200), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('origem', sa.String(length=200), nullable=True),
        sa.Column('duracao', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['ficha_id'], ['fichas.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    # 8) Equipamento.peso (texto) -> peso_kg (número) — todo valor real já segue "<número> kg".
    op.add_column('equipamentos', sa.Column('peso_kg', sa.Double(), nullable=True))
    _migrar_peso_equipamentos(op.get_bind())
    op.drop_column('equipamentos', 'peso')

    # 9) origem_monstro_slug -> origem_personagem_slug (só o nome, sem mudança de comportamento)
    op.execute("ALTER TABLE equipamentos RENAME COLUMN origem_monstro_slug TO origem_personagem_slug")
    op.execute("ALTER TABLE habilidades RENAME COLUMN origem_monstro_slug TO origem_personagem_slug")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE habilidades RENAME COLUMN origem_personagem_slug TO origem_monstro_slug")
    op.execute("ALTER TABLE equipamentos RENAME COLUMN origem_personagem_slug TO origem_monstro_slug")

    op.add_column('equipamentos', sa.Column('peso', sa.VARCHAR(length=50), nullable=True))
    op.execute("UPDATE equipamentos SET peso = printf('%g kg', peso_kg) WHERE peso_kg IS NOT NULL")
    op.drop_column('equipamentos', 'peso_kg')

    op.drop_table('fichas_efeitos')
    op.drop_table('fichas_condicoes')
    op.drop_table('fichas_espacos_magia')

    for moeda in ('moeda_pl', 'moeda_po', 'moeda_pe', 'moeda_pp', 'moeda_pc'):
        op.drop_column('fichas', moeda)
    op.drop_column('fichas', 'carga_maxima')
    op.drop_column('fichas', 'iniciativa_extra')
    op.drop_column('fichas', 'dados_vida_usados')
    op.drop_column('fichas', 'dados_vida_total')
    op.drop_column('fichas', 'pv_temporario')
    op.drop_column('fichas', 'antecedente')
    op.drop_column('fichas', 'classe')
    op.drop_column('fichas', 'xp')
    op.drop_column('fichas', 'nivel')

    op.drop_table('personagem_diario_entradas')

    for coluna in (
        'lugares_interesse', 'pessoas_interesse', 'defeito', 'vinculo', 'ideal', 'traco',
        'personalidade', 'aparencia', 'fe', 'pele', 'cabelo', 'olhos', 'peso_corporal',
        'altura', 'idade', 'genero',
    ):
        op.drop_column('personagens', coluna)

    op.drop_index('uq_personagens_tipo_slug', table_name='personagens')
    op.drop_index('ix_personagens_tipo', table_name='personagens')
    op.drop_index('ix_personagens_slug', table_name='personagens')
    op.create_index('ix_monstros_slug', 'personagens', ['slug'], unique=True)

    op.execute("ALTER TABLE fichas RENAME COLUMN personagem_id TO monstro_id")
    op.drop_column('personagens', 'tipo')
    op.execute("ALTER TABLE personagens RENAME COLUMN tipo_criatura TO tipo")

    op.rename_table('fichas', 'fichas_monstro')
    op.rename_table('personagens', 'monstros')
    # ### end Alembic commands ###
