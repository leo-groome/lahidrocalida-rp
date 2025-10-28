"""Add kds_name column to platillos table

Revision ID: 001_add_kds_name
Revises: 
Create Date: 2025-10-28 13:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_kds_name'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('platillos', sa.Column('kds_name', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('platillos', 'kds_name')
