"""cria recurso de combate e cargas de item

Revision ID: 2924ba8716ff
Revises: d53fdbbaaf24
Create Date: 2026-11-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2924ba8716ff'
down_revision: Union[str, Sequence[str], None] = 'd53fdbbaaf24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('equipamentos', sa.Column('cargas_maximo', sa.Integer(), nullable=True))
    op.add_column('ficha_equipamentos', sa.Column('cargas_atual', sa.Integer(), nullable=True))
    op.create_table(
        'combate_participante_recursos_copia',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('participante_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('referencia', sa.Integer(), nullable=False),
        sa.Column('maximo', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('usado', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['participante_id'], ['combate_participantes.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('combate_participante_recursos_copia')
    op.drop_column('ficha_equipamentos', 'cargas_atual')
    op.drop_column('equipamentos', 'cargas_maximo')
