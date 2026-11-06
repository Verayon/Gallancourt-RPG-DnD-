"""cria lugares, sessão ao vivo, interações e rolagens (Master's Shield)

Revision ID: 7b2e4c9a1f6d
Revises: 9a1c7e4f2b5d
Create Date: 2026-11-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b2e4c9a1f6d'
down_revision: Union[str, Sequence[str], None] = '9a1c7e4f2b5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'lugares',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('pagina_rel_docs', sa.String(length=300), nullable=True),
        sa.Column('lugar_pai_id', sa.Integer(), nullable=True),
        sa.Column('canonico', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['lugar_pai_id'], ['lugares.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_lugares_slug'), 'lugares', ['slug'], unique=True)

    op.create_table(
        'sessoes_ao_vivo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pagina_rel_docs', sa.String(length=300), nullable=False),
        sa.Column('ano', sa.Integer(), nullable=True),
        sa.Column('mes', sa.String(length=30), nullable=True),
        sa.Column('dia', sa.Integer(), nullable=True),
        sa.Column('hora', sa.Integer(), nullable=True),
        sa.Column('minuto', sa.Integer(), nullable=True),
        sa.Column('lugar_atual_id', sa.Integer(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['lugar_atual_id'], ['lugares.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_sessoes_ao_vivo_pagina_rel_docs'), 'sessoes_ao_vivo', ['pagina_rel_docs'], unique=True,
    )

    op.create_table(
        'interacoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pagina_rel_docs', sa.String(length=300), nullable=False),
        sa.Column('combate_id', sa.Integer(), nullable=True),
        sa.Column('lugar_id', sa.Integer(), nullable=True),
        sa.Column('ano', sa.Integer(), nullable=True),
        sa.Column('mes', sa.String(length=30), nullable=True),
        sa.Column('dia', sa.Integer(), nullable=True),
        sa.Column('hora', sa.Integer(), nullable=True),
        sa.Column('minuto', sa.Integer(), nullable=True),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('pericia_ou_atributo', sa.String(length=50), nullable=True),
        sa.Column('cd', sa.Integer(), nullable=True),
        sa.Column('sucesso', sa.Boolean(), nullable=True),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['combate_id'], ['combates.id']),
        sa.ForeignKeyConstraint(['lugar_id'], ['lugares.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_interacoes_pagina_rel_docs'), 'interacoes', ['pagina_rel_docs'])

    op.create_table(
        'interacao_participantes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('interacao_id', sa.Integer(), nullable=False),
        sa.Column('ficha_id', sa.Integer(), nullable=False),
        sa.Column('papel', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['interacao_id'], ['interacoes.id']),
        sa.ForeignKeyConstraint(['ficha_id'], ['fichas.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'rolagens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('interacao_id', sa.Integer(), nullable=False),
        sa.Column('dado', sa.String(length=30), nullable=False),
        sa.Column('vantagem', sa.String(length=15), nullable=True),
        sa.Column('resultado_bruto', sa.Integer(), nullable=True),
        sa.Column('resultado_total', sa.Integer(), nullable=True),
        sa.Column('online', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(['interacao_id'], ['interacoes.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('rolagens')
    op.drop_table('interacao_participantes')
    op.drop_index(op.f('ix_interacoes_pagina_rel_docs'), table_name='interacoes')
    op.drop_table('interacoes')
    op.drop_index(op.f('ix_sessoes_ao_vivo_pagina_rel_docs'), table_name='sessoes_ao_vivo')
    op.drop_table('sessoes_ao_vivo')
    op.drop_index(op.f('ix_lugares_slug'), table_name='lugares')
    op.drop_table('lugares')
