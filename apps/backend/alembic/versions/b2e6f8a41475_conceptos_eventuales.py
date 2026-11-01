"""Conceptos eventuales base (imprevistos) para cada sucursal."""

from alembic import op

revision = "b2e6f8a41475"
down_revision = "a1d5e7f30364"
branch_labels = None
depends_on = None

CONCEPTOS = ("Mantenimiento y reparaciones", "Otros gastos indirectos")


def upgrade():
    for nombre in CONCEPTOS:
        op.execute(
            f"INSERT INTO conceptos_gasto (sucursal_id, nombre, frecuencia, activo) "
            f"SELECT id, '{nombre}', 'eventual', true FROM sucursales "
            f"ON CONFLICT (sucursal_id, nombre) DO NOTHING"
        )


def downgrade():
    # Solo borra los que ningún gasto usa; los usados se conservan.
    nombres = ", ".join(f"'{n}'" for n in CONCEPTOS)
    op.execute(
        f"DELETE FROM conceptos_gasto WHERE frecuencia = 'eventual' AND nombre IN ({nombres}) "
        f"AND id NOT IN (SELECT concepto_id FROM gastos WHERE concepto_id IS NOT NULL)"
    )
