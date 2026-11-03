"""adiciona campos avancados de ficha

Revision ID: 10019a169cdd
Revises: 5f89f793abd3
Create Date: 2026-11-02 19:42:39.458236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10019a169cdd'
down_revision: Union[str, Sequence[str], None] = '5f89f793abd3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'ficha_resistencias_dano',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ficha_id', sa.Integer(), sa.ForeignKey('fichas.id'), nullable=False),
        sa.Column('nome', sa.String(length=30), nullable=False),
        sa.Column('modo', sa.String(length=15), nullable=False),
    )
    op.add_column('ficha_habilidades', sa.Column('favorito', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('ficha_habilidades', sa.Column('usos_maximo', sa.Integer(), nullable=True))
    op.add_column('ficha_habilidades', sa.Column('usos_restantes', sa.Integer(), nullable=True))
    op.add_column('ficha_habilidades', sa.Column('tipo_descanso', sa.String(length=10), nullable=True))
    op.add_column('ficha_magias', sa.Column('favorito', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('fichas', sa.Column('subclasse', sa.String(length=150), nullable=True))
    op.add_column('fichas', sa.Column('investigacao_passiva', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('fichas', sa.Column('intuicao_passiva', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('fichas', sa.Column('cd_conjuracao', sa.Integer(), nullable=True))
    op.add_column('fichas', sa.Column('bonus_ataque_magico', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('fichas', 'bonus_ataque_magico')
    op.drop_column('fichas', 'cd_conjuracao')
    op.drop_column('fichas', 'intuicao_passiva')
    op.drop_column('fichas', 'investigacao_passiva')
    op.drop_column('fichas', 'subclasse')
    op.drop_column('ficha_magias', 'favorito')
    op.drop_column('ficha_habilidades', 'tipo_descanso')
    op.drop_column('ficha_habilidades', 'usos_restantes')
    op.drop_column('ficha_habilidades', 'usos_maximo')
    op.drop_column('ficha_habilidades', 'favorito')
    op.drop_table('ficha_resistencias_dano')
