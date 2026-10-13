"""uber_eats_corte_turno: columnas de corte Uber Eats en turnos

Revision ID: c3f1a9d27e50
Revises: 8b7414ff1a0e
Create Date: 2026-10-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f1a9d27e50"
down_revision: Union[str, None] = "8b7414ff1a0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Uber Eats no se cobra en Caja (depósito a tarjeta): el corte lo reporta
    # aparte, fuera del efectivo esperado. `pedidos.estado` es varchar sin
    # CHECK, así que el estado `entregado_repartidor` no requiere migración.
    op.add_column(
        "turnos",
        sa.Column("pedidos_uber", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "turnos",
        sa.Column("ventas_uber", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("turnos", "ventas_uber")
    op.drop_column("turnos", "pedidos_uber")
