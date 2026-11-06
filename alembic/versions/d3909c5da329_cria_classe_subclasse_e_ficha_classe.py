"""cria classe, subclasse e ficha_classe

Revision ID: d3909c5da329
Revises: 2924ba8716ff
Create Date: 2026-11-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3909c5da329'
down_revision: Union[str, Sequence[str], None] = '2924ba8716ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'classes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('dado_vida', sa.Integer(), nullable=False),
        sa.Column('atributo_conjuracao', sa.String(length=20), nullable=True),
        sa.Column('progressao_conjuracao', sa.String(length=10), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome'),
    )
    op.create_index(op.f('ix_classes_nome'), 'classes', ['nome'])
    op.create_table(
        'subclasses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('classe_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=150), nullable=False),
        sa.ForeignKeyConstraint(['classe_id'], ['classes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'classe_features',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('classe_id', sa.Integer(), nullable=False),
        sa.Column('subclasse_id', sa.Integer(), nullable=True),
        sa.Column('nivel', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=200), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['classe_id'], ['classes.id']),
        sa.ForeignKeyConstraint(['subclasse_id'], ['subclasses.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'ficha_classes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ficha_id', sa.Integer(), nullable=False),
        sa.Column('classe_id', sa.Integer(), nullable=False),
        sa.Column('subclasse_id', sa.Integer(), nullable=True),
        sa.Column('nivel', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['ficha_id'], ['fichas.id']),
        sa.ForeignKeyConstraint(['classe_id'], ['classes.id']),
        sa.ForeignKeyConstraint(['subclasse_id'], ['subclasses.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('ficha_classes')
    op.drop_table('classe_features')
    op.drop_table('subclasses')
    op.drop_index(op.f('ix_classes_nome'), table_name='classes')
    op.drop_table('classes')
