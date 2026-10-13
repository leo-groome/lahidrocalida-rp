"""gasto_adjuntos: fotos de tickets de gastos

Revision ID: d7a2e4b91c13
Revises: c3f1a9d27e50
Create Date: 2026-10-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7a2e4b91c13"
down_revision: Union[str, None] = "c3f1a9d27e50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gasto_adjuntos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "gasto_id", sa.Integer(), sa.ForeignKey("gastos.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("sucursal_id", sa.Integer(), sa.ForeignKey("sucursales.id"), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("subido_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("storage_key", name="uq_gasto_adjuntos_storage_key"),
    )
    op.create_index("ix_gasto_adjuntos_gasto_id", "gasto_adjuntos", ["gasto_id"])


def downgrade() -> None:
    op.drop_index("ix_gasto_adjuntos_gasto_id", table_name="gasto_adjuntos")
    op.drop_table("gasto_adjuntos")
