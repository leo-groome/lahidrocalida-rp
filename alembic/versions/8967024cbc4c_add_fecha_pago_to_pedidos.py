"""add fecha_pago to pedidos

Revision ID: 8967024cbc4c
Revises: 
Create Date: 2026-01-19 05:27:41.524873

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8967024cbc4c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pedidos', sa.Column('fecha_pago', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('pedidos', 'fecha_pago')
