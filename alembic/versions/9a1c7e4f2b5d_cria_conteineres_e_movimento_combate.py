"""cria contêineres de equipamento e movimento no combate

Revision ID: 9a1c7e4f2b5d
Revises: d3909c5da329
Create Date: 2026-11-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a1c7e4f2b5d'
down_revision: Union[str, Sequence[str], None] = 'd3909c5da329'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('equipamentos', sa.Column('e_container', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('equipamentos', sa.Column('capacidade_kg', sa.Double(), nullable=True))
    op.add_column('ficha_equipamentos', sa.Column('guardado_em_vinculo_id', sa.Integer(), nullable=True))
    with op.batch_alter_table('ficha_equipamentos') as batch_op:
        batch_op.create_foreign_key(
            'fk_ficha_equipamentos_guardado_em_vinculo_id',
            'ficha_equipamentos', ['guardado_em_vinculo_id'], ['id'],
        )
    op.add_column(
        'combate_participantes',
        sa.Column('movimento_usado', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('combate_participantes', 'movimento_usado')
    with op.batch_alter_table('ficha_equipamentos') as batch_op:
        batch_op.drop_constraint('fk_ficha_equipamentos_guardado_em_vinculo_id', type_='foreignkey')
    op.drop_column('ficha_equipamentos', 'guardado_em_vinculo_id')
    op.drop_column('equipamentos', 'capacidade_kg')
    op.drop_column('equipamentos', 'e_container')
