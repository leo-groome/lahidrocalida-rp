"""Frecuencia 'cada N días' en conceptos e imprevistos base adicionales."""

import sqlalchemy as sa

from alembic import op

revision = "c3f7a9b52586"
down_revision = "b2e6f8a41475"
branch_labels = None
depends_on = None

NUEVOS = ("Desazolve y plomería", "Herramientas y equipo")


def upgrade():
    op.add_column("conceptos_gasto", sa.Column("intervalo_dias", sa.Integer()))
    for nombre in NUEVOS:
        op.execute(
            f"INSERT INTO conceptos_gasto (sucursal_id, nombre, frecuencia, activo) "
            f"SELECT id, '{nombre}', 'eventual', true FROM sucursales "
            f"ON CONFLICT (sucursal_id, nombre) DO NOTHING"
        )


def downgrade():
    nombres = ", ".join(f"'{n}'" for n in NUEVOS)
    op.execute(
        f"DELETE FROM conceptos_gasto WHERE frecuencia = 'eventual' AND nombre IN ({nombres}) "
        f"AND id NOT IN (SELECT concepto_id FROM gastos WHERE concepto_id IS NOT NULL)"
    )
    op.drop_column("conceptos_gasto", "intervalo_dias")
