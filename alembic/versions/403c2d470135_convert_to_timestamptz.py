"""convert_to_timestamptz

Revision ID: 403c2d470135
Revises: 8967024cbc4c
Create Date: 2026-02-04 21:27:03.325358

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '403c2d470135'
down_revision: Union[str, None] = '8967024cbc4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert naive timestamps to timestamptz assuming they are in America/Mexico_City
    # This correctly shifts them to UTC in the database.
    
    # Table: pedidos
    op.execute("ALTER TABLE pedidos ALTER COLUMN fecha_creacion TYPE TIMESTAMPTZ USING fecha_creacion AT TIME ZONE 'America/Mexico_City'")
    op.execute("ALTER TABLE pedidos ALTER COLUMN fecha_pago TYPE TIMESTAMPTZ USING fecha_pago AT TIME ZONE 'America/Mexico_City'")
    
    # Table: gastos
    op.execute("ALTER TABLE gastos ALTER COLUMN fecha_gasto TYPE TIMESTAMPTZ USING fecha_gasto AT TIME ZONE 'America/Mexico_City'")
    
    # Table: turnos
    op.execute("ALTER TABLE turnos ALTER COLUMN fecha_apertura TYPE TIMESTAMPTZ USING fecha_apertura AT TIME ZONE 'America/Mexico_City'")
    op.execute("ALTER TABLE turnos ALTER COLUMN fecha_cierre TYPE TIMESTAMPTZ USING fecha_cierre AT TIME ZONE 'America/Mexico_City'")


def downgrade() -> None:
    # Convert back to naive timestamps
    # Note: This will lose the timezone information (it will stay in UTC but without the offset)
    
    op.execute("ALTER TABLE pedidos ALTER COLUMN fecha_creacion TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE pedidos ALTER COLUMN fecha_pago TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE gastos ALTER COLUMN fecha_gasto TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE turnos ALTER COLUMN fecha_apertura TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE turnos ALTER COLUMN fecha_cierre TYPE TIMESTAMP WITHOUT TIME ZONE")
