"""Identificar salidas fijadas al pagar nómina."""

import sqlalchemy as sa

from alembic import op

revision = "a81c0f29b345"
down_revision = "f6c0d2e85819"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "registros_asistencia",
        sa.Column("cierre_por_nomina_en", sa.DateTime(timezone=True), nullable=True),
    )
    for nombre, precision in (
        ("tarifa_hora_pagada", 10),
        ("tarifa_extra_pagada", 10),
        ("jornada_pagada", 5),
    ):
        op.add_column("nomina_lineas", sa.Column(nombre, sa.Numeric(precision, 2), nullable=True))


def downgrade():
    for nombre in ("tarifa_hora_pagada", "tarifa_extra_pagada", "jornada_pagada"):
        op.drop_column("nomina_lineas", nombre)
    op.drop_column("registros_asistencia", "cierre_por_nomina_en")
