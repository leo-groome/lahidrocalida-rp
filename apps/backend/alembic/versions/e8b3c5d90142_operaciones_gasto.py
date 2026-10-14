"""Registro durable de idempotencia de gastos."""

import sqlalchemy as sa

from alembic import op

revision = "e8b3c5d90142"
down_revision = "d7a2e4b91c13"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "operaciones_gasto",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sucursal_id", sa.Integer(), sa.ForeignKey("sucursales.id"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("client_request_id", sa.String(36), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("gasto_id", sa.Integer(), sa.ForeignKey("gastos.id", ondelete="SET NULL")),
        sa.UniqueConstraint(
            "sucursal_id", "client_request_id", name="uq_operacion_gasto_sucursal_request"
        ),
    )


def downgrade():
    op.drop_table("operaciones_gasto")
