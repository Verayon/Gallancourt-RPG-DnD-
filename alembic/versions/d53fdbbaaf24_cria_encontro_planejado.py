"""cria encontro planejado

Revision ID: d53fdbbaaf24
Revises: 37903f5c1000
Create Date: 2026-11-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd53fdbbaaf24'
down_revision: Union[str, Sequence[str], None] = '37903f5c1000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'encontros_planejados',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pagina_rel_docs', sa.String(length=300), nullable=False),
        sa.Column('nome', sa.String(length=200), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_encontros_planejados_pagina_rel_docs'), 'encontros_planejados', ['pagina_rel_docs'],
    )
    op.create_table(
        'encontro_participantes_planejados',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('encontro_id', sa.Integer(), nullable=False),
        sa.Column('ficha_id', sa.Integer(), nullable=False),
        sa.Column('nome_exibicao', sa.String(length=200), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['encontro_id'], ['encontros_planejados.id']),
        sa.ForeignKeyConstraint(['ficha_id'], ['fichas.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('encontro_participantes_planejados')
    op.drop_index(op.f('ix_encontros_planejados_pagina_rel_docs'), table_name='encontros_planejados')
    op.drop_table('encontros_planejados')
