"""adiciona tipo_acao e favorito de equipamento

Revision ID: 37903f5c1000
Revises: 10019a169cdd
Create Date: 2026-11-04 11:15:02.050385

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37903f5c1000'
down_revision: Union[str, Sequence[str], None] = '10019a169cdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('equipamentos', sa.Column('tipo_acao', sa.String(length=20), nullable=True))
    op.add_column('magias', sa.Column('tipo_acao', sa.String(length=20), nullable=True))
    op.add_column('habilidades', sa.Column('tipo_acao', sa.String(length=20), nullable=True))
    op.add_column('ficha_equipamentos', sa.Column('favorito', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('ficha_equipamentos', 'favorito')
    op.drop_column('habilidades', 'tipo_acao')
    op.drop_column('magias', 'tipo_acao')
    op.drop_column('equipamentos', 'tipo_acao')
