"""cria raças e liga fonte_id/pagina_rel_docs nos catálogos

Revision ID: 4f8a2d6c9e13
Revises: 7b2e4c9a1f6d
Create Date: 2026-11-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f8a2d6c9e13'
down_revision: Union[str, Sequence[str], None] = '7b2e4c9a1f6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('fontes', sa.Column('importado_em', sa.DateTime(), nullable=True))
    op.add_column('fontes', sa.Column('arquivo_origem', sa.String(length=300), nullable=True))

    op.create_table(
        'racas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('raca_pai_id', sa.Integer(), nullable=True),
        sa.Column('fonte_id', sa.Integer(), nullable=True),
        sa.Column('pagina_rel_docs', sa.String(length=300), nullable=True),
        sa.Column('tamanho', sa.String(length=50), nullable=True),
        sa.Column('deslocamento', sa.Integer(), nullable=True),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['raca_pai_id'], ['racas.id']),
        sa.ForeignKeyConstraint(['fonte_id'], ['fontes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_racas_nome'), 'racas', ['nome'])

    op.create_table(
        'raca_tracos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('raca_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=200), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['raca_id'], ['racas.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.add_column('fichas', sa.Column('raca_id', sa.Integer(), nullable=True))
    with op.batch_alter_table('fichas') as batch_op:
        batch_op.create_foreign_key('fk_fichas_raca_id', 'racas', ['raca_id'], ['id'])

    op.add_column('equipamentos', sa.Column('fonte_id', sa.Integer(), nullable=True))
    op.add_column('magias', sa.Column('fonte_id', sa.Integer(), nullable=True))
    op.add_column('habilidades', sa.Column('fonte_id', sa.Integer(), nullable=True))
    op.add_column('pericias', sa.Column('fonte_id', sa.Integer(), nullable=True))
    op.add_column('classes', sa.Column('fonte_id', sa.Integer(), nullable=True))
    op.add_column('classes', sa.Column('pagina_rel_docs', sa.String(length=300), nullable=True))
    with op.batch_alter_table('equipamentos') as batch_op:
        batch_op.create_foreign_key('fk_equipamentos_fonte_id', 'fontes', ['fonte_id'], ['id'])
    with op.batch_alter_table('magias') as batch_op:
        batch_op.create_foreign_key('fk_magias_fonte_id', 'fontes', ['fonte_id'], ['id'])
    with op.batch_alter_table('habilidades') as batch_op:
        batch_op.create_foreign_key('fk_habilidades_fonte_id', 'fontes', ['fonte_id'], ['id'])
    with op.batch_alter_table('pericias') as batch_op:
        batch_op.create_foreign_key('fk_pericias_fonte_id', 'fontes', ['fonte_id'], ['id'])
    with op.batch_alter_table('classes') as batch_op:
        batch_op.create_foreign_key('fk_classes_fonte_id', 'fontes', ['fonte_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('classes') as batch_op:
        batch_op.drop_constraint('fk_classes_fonte_id', type_='foreignkey')
    with op.batch_alter_table('pericias') as batch_op:
        batch_op.drop_constraint('fk_pericias_fonte_id', type_='foreignkey')
    with op.batch_alter_table('habilidades') as batch_op:
        batch_op.drop_constraint('fk_habilidades_fonte_id', type_='foreignkey')
    with op.batch_alter_table('magias') as batch_op:
        batch_op.drop_constraint('fk_magias_fonte_id', type_='foreignkey')
    with op.batch_alter_table('equipamentos') as batch_op:
        batch_op.drop_constraint('fk_equipamentos_fonte_id', type_='foreignkey')
    op.drop_column('classes', 'pagina_rel_docs')
    op.drop_column('classes', 'fonte_id')
    op.drop_column('pericias', 'fonte_id')
    op.drop_column('habilidades', 'fonte_id')
    op.drop_column('magias', 'fonte_id')
    op.drop_column('equipamentos', 'fonte_id')

    with op.batch_alter_table('fichas') as batch_op:
        batch_op.drop_constraint('fk_fichas_raca_id', type_='foreignkey')
    op.drop_column('fichas', 'raca_id')

    op.drop_table('raca_tracos')
    op.drop_index(op.f('ix_racas_nome'), table_name='racas')
    op.drop_table('racas')

    op.drop_column('fontes', 'arquivo_origem')
    op.drop_column('fontes', 'importado_em')
