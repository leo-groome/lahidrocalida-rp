"""Adjuntos idempotentes y outbox durable de limpieza."""

import sqlalchemy as sa

from alembic import op

revision = "f9c4d6e01253"
down_revision = "e8b3c5d90142"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("gasto_adjuntos", sa.Column("client_request_id", sa.String(36)))
    op.add_column("gasto_adjuntos", sa.Column("payload_hash", sa.String(64)))
    op.create_unique_constraint(
        "uq_adjunto_gasto_request", "gasto_adjuntos", ["gasto_id", "client_request_id"]
    )
    op.create_table(
        "storage_borrados",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("storage_key", sa.String(255), unique=True, nullable=False),
        sa.Column("intentos", sa.Integer(), nullable=False),
        sa.Column("ultimo_error", sa.Text()),
        sa.Column("proximo_intento", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("storage_borrados")
    op.drop_constraint("uq_adjunto_gasto_request", "gasto_adjuntos", type_="unique")
    op.drop_column("gasto_adjuntos", "payload_hash")
    op.drop_column("gasto_adjuntos", "client_request_id")
