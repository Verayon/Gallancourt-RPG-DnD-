"""cria tabelas de combate

Revision ID: 5f89f793abd3
Revises: f3b9aac95f27
Create Date: 2026-11-02 14:24:59.442637

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f89f793abd3'
down_revision: Union[str, Sequence[str], None] = 'f3b9aac95f27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "combates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pagina_rel_docs", sa.String(length=300), nullable=False),
        sa.Column("rodada", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("turno_participante_id", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("finalizado_em", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_combates_pagina_rel_docs", "combates", ["pagina_rel_docs"])

    op.create_table(
        "combate_participantes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("combate_id", sa.Integer(), sa.ForeignKey("combates.id"), nullable=False),
        sa.Column("ficha_id", sa.Integer(), sa.ForeignKey("fichas.id"), nullable=False),
        sa.Column("nome_exibicao", sa.String(length=200), nullable=True),
        sa.Column("iniciativa_base", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("iniciativa_desempate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("acao_usada", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("acao_bonus_usada", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reacao_usada", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("concentrando_em", sa.String(length=200), nullable=True),
        sa.Column("death_save_sucessos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("death_save_falhas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("copia_pv_atual", sa.Integer(), nullable=True),
        sa.Column("copia_pv_temporario", sa.Integer(), nullable=True),
    )

    op.create_table(
        "combate_participante_condicoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "participante_id", sa.Integer(), sa.ForeignKey("combate_participantes.id"),
            nullable=False,
        ),
        sa.Column("nome", sa.String(length=30), nullable=False),
    )

    op.create_table(
        "combate_log_entradas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("combate_id", sa.Integer(), sa.ForeignKey("combates.id"), nullable=False),
        sa.Column("rodada", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("combate_log_entradas")
    op.drop_table("combate_participante_condicoes")
    op.drop_table("combate_participantes")
    op.drop_index("ix_combates_pagina_rel_docs", table_name="combates")
    op.drop_table("combates")
