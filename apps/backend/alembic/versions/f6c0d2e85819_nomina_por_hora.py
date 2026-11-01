"""Pago por hora y por hora extra; pago por empleado según su último día."""

import sqlalchemy as sa

from alembic import op

revision = "f6c0d2e85819"
down_revision = "e5b9c1d74708"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("empleados_pago", sa.Column("tarifa_hora", sa.DECIMAL(10, 2)))
    op.add_column("empleados_pago", sa.Column("tarifa_hora_extra", sa.DECIMAL(10, 2)))
    # Equivalente por hora de las reglas anteriores (tarifa diaria / horas de jornada).
    op.execute(
        "UPDATE empleados_pago SET "
        "tarifa_hora = ROUND(tarifa_diaria / horas_jornada, 2), "
        "tarifa_hora_extra = ROUND(tarifa_diaria / horas_jornada * multiplicador_extra, 2)"
    )
    op.alter_column("empleados_pago", "tarifa_hora", nullable=False)
    op.alter_column("empleados_pago", "tarifa_hora_extra", nullable=False)
    op.drop_constraint("ck_empleado_pago_fijo_requiere_sueldo", "empleados_pago", type_="check")
    for col in (
        "tipo_pago",
        "tarifa_diaria",
        "dias_laborales_semana",
        "paga_septimo",
        "sueldo_semanal_fijo",
        "multiplicador_extra",
    ):
        op.drop_column("empleados_pago", col)

    op.drop_column("nomina_lineas", "septimo")
    op.add_column(
        "nomina_lineas",
        sa.Column("horas_ajustadas", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade():
    raise NotImplementedError("Migración de modelo de pago sin vuelta atrás")
