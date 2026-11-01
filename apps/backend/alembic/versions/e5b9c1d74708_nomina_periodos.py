"""Periodos de nómina semanal y sus líneas por empleado."""

import sqlalchemy as sa

from alembic import op

revision = "e5b9c1d74708"
down_revision = "d4a8b0c63697"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nomina_periodos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sucursal_id", sa.Integer(), sa.ForeignKey("sucursales.id"), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False, server_default="borrador"),
        sa.Column("pagado_en", sa.DateTime(timezone=True)),
        sa.Column("pagado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id")),
        sa.UniqueConstraint(
            "sucursal_id", "fecha_inicio", name="uq_nomina_periodo_sucursal_inicio"
        ),
    )
    op.create_index("ix_nomina_periodos_id", "nomina_periodos", ["id"])
    op.create_table(
        "nomina_lineas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "periodo_id",
            sa.Integer(),
            sa.ForeignKey("nomina_periodos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("dias_esperados", sa.Integer(), nullable=False),
        sa.Column("dias_trabajados", sa.Integer(), nullable=False),
        sa.Column("faltas", sa.Integer(), nullable=False),
        sa.Column("horas_trabajadas", sa.DECIMAL(6, 2), nullable=False),
        sa.Column("horas_extra", sa.DECIMAL(5, 2), nullable=False),
        sa.Column("base", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("septimo", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("extra_monto", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("bonos", sa.DECIMAL(10, 2), nullable=False, server_default="0"),
        sa.Column("descuentos", sa.DECIMAL(10, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("metodo_pago", sa.String(10), nullable=False, server_default="efectivo"),
        sa.Column("sale_de_caja", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notas", sa.Text()),
        sa.Column("gasto_id", sa.Integer(), sa.ForeignKey("gastos.id", ondelete="SET NULL")),
        sa.UniqueConstraint("periodo_id", "usuario_id", name="uq_nomina_linea_usuario"),
    )
    op.create_index("ix_nomina_lineas_periodo_id", "nomina_lineas", ["periodo_id"])


def downgrade():
    op.drop_index("ix_nomina_lineas_periodo_id", table_name="nomina_lineas")
    op.drop_table("nomina_lineas")
    op.drop_index("ix_nomina_periodos_id", table_name="nomina_periodos")
    op.drop_table("nomina_periodos")
