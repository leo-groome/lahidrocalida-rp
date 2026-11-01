"""Conceptos de gasto indirecto recurrente."""

import sqlalchemy as sa

from alembic import op

revision = "a1d5e7f30364"
down_revision = "f9c4d6e01253"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "conceptos_gasto",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sucursal_id", sa.Integer(), sa.ForeignKey("sucursales.id"), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("monto_tipico", sa.DECIMAL(10, 2)),
        sa.Column("frecuencia", sa.String(20), nullable=False, server_default="mensual"),
        sa.Column("dia_vencimiento", sa.Integer()),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.UniqueConstraint("sucursal_id", "nombre", name="uq_concepto_gasto_nombre"),
    )
    op.create_index("ix_conceptos_gasto_id", "conceptos_gasto", ["id"])
    op.add_column(
        "gastos",
        sa.Column("concepto_id", sa.Integer(), sa.ForeignKey("conceptos_gasto.id"), nullable=True),
    )
    op.create_index("ix_gastos_concepto_id", "gastos", ["concepto_id"])


def downgrade():
    op.drop_index("ix_gastos_concepto_id", table_name="gastos")
    op.drop_column("gastos", "concepto_id")
    op.drop_index("ix_conceptos_gasto_id", table_name="conceptos_gasto")
    op.drop_table("conceptos_gasto")
