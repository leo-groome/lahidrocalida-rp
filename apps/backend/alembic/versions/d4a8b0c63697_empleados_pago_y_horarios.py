"""Sueldo y horario laboral por empleado."""

import sqlalchemy as sa

from alembic import op

revision = "d4a8b0c63697"
down_revision = "c3f7a9b52586"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "empleados_pago",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("sucursal_id", sa.Integer(), sa.ForeignKey("sucursales.id"), nullable=False),
        sa.Column("tipo_pago", sa.String(20), nullable=False),
        sa.Column("tarifa_diaria", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("horas_jornada", sa.DECIMAL(4, 2), nullable=False, server_default="8"),
        sa.Column("dias_laborales_semana", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("paga_septimo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sueldo_semanal_fijo", sa.DECIMAL(10, 2)),
        sa.Column("multiplicador_extra", sa.DECIMAL(3, 2), nullable=False, server_default="1.00"),
        sa.UniqueConstraint("usuario_id"),
        sa.CheckConstraint(
            "tipo_pago <> 'semanal_fijo' OR sueldo_semanal_fijo IS NOT NULL",
            name="ck_empleado_pago_fijo_requiere_sueldo",
        ),
    )
    op.create_index("ix_empleados_pago_id", "empleados_pago", ["id"])
    op.create_table(
        "horarios_empleado",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("sucursal_id", sa.Integer(), sa.ForeignKey("sucursales.id"), nullable=False),
        sa.Column("dia_semana", sa.Integer(), nullable=False),
        sa.Column("hora_entrada", sa.Time(), nullable=False),
        sa.Column("hora_salida", sa.Time(), nullable=False),
        sa.UniqueConstraint("usuario_id", "dia_semana", name="uq_horario_usuario_dia"),
    )
    op.create_index("ix_horarios_empleado_usuario_id", "horarios_empleado", ["usuario_id"])


def downgrade():
    op.drop_index("ix_horarios_empleado_usuario_id", table_name="horarios_empleado")
    op.drop_table("horarios_empleado")
    op.drop_index("ix_empleados_pago_id", table_name="empleados_pago")
    op.drop_table("empleados_pago")
