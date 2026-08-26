"""unique constraint (pedido_id, client_request_id) en articulos_pedido

Revision ID: 799190d9c93b
Revises: 1af66464b276
Create Date: 2026-08-25 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "799190d9c93b"
down_revision: Union[str, None] = "1af66464b276"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # De String(36) a String(72): cada fila ahora guarda
    # "<client_request_id>:<índice>" (ver app/routers/pedidos.py,
    # agregar_articulos_pedido) — un batch de varios artículos comparte el
    # client_request_id del request, así que el índice distingue cada fila
    # dentro del mismo pedido para que la unicidad tenga sentido.
    op.alter_column(
        "articulos_pedido",
        "client_request_id",
        existing_type=sa.String(length=36),
        type_=sa.String(length=72),
        existing_nullable=True,
    )
    op.create_unique_constraint(
        "uq_articulo_pedido_client_request_id",
        "articulos_pedido",
        ["pedido_id", "client_request_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_articulo_pedido_client_request_id", "articulos_pedido", type_="unique")
    op.alter_column(
        "articulos_pedido",
        "client_request_id",
        existing_type=sa.String(length=72),
        type_=sa.String(length=36),
        existing_nullable=True,
    )
