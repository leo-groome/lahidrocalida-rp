"""jornada: sesiones_validas_desde, columnas de cierre automático, backfill de huérfanos

Revision ID: baca83828037
Revises: 799190d9c93b
Create Date: 2026-08-25 20:43:05.107698

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "baca83828037"
down_revision: Union[str, None] = "799190d9c93b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Revocación selectiva de sesiones (S3.3): un JWT con `iat` anterior a
    # este valor se rechaza en get_current_user, aunque no haya expirado.
    op.add_column(
        "usuarios", sa.Column("sesiones_validas_desde", sa.DateTime(timezone=True), nullable=True)
    )

    # Asistencia: nunca se inventa la hora real de salida al reconciliar una
    # jornada anterior — se marca para revisión humana en su lugar (S3.7).
    op.add_column(
        "registros_asistencia",
        sa.Column(
            "cierre_automatico", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "registros_asistencia",
        sa.Column(
            "requiere_revision", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "registros_asistencia",
        sa.Column("fecha_salida_estimada", sa.DateTime(timezone=True), nullable=True),
    )

    # Turnos: mismo principio para cifras de caja (S3.8). La columna
    # `diferencia` YA existe en el schema real (mirror de prod del baseline
    # 1af66464b276) — el ORM simplemente nunca la mapeaba
    # (`_get_turno_diferencia` hacía `getattr(turno, "diferencia", None)`,
    # siempre None). `models.py` ya la mapea desde S3; aquí solo se agrega
    # la columna nueva de este sprint.
    op.add_column(
        "turnos",
        sa.Column(
            "cerrado_automatico", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )

    # Backfill (S3.9): marcar como requiere_revision los registros de
    # asistencia que quedaron abiertos (fecha_salida IS NULL) de una jornada
    # que ya no es la vigente — jornada [05:00, 05:00) hora México. No se
    # borran, no se inventa fecha_salida: solo se deja fecha_salida_estimada
    # (entrada + 16h, acotada al fin de la jornada de entrada) para que un
    # admin la confirme vía PATCH /asistencia/{id}/confirmar-salida.
    op.execute(
        sa.text("""
            UPDATE registros_asistencia
            SET requiere_revision = true,
                cierre_automatico = true,
                fecha_salida_estimada = LEAST(
                    fecha_entrada + interval '16 hours',
                    date_trunc('day', (fecha_entrada AT TIME ZONE 'America/Mexico_City') - interval '5 hours')
                        + interval '1 day 5 hours'
                )
            WHERE fecha_salida IS NULL
              AND fecha_entrada < (
                    CASE
                        WHEN EXTRACT(HOUR FROM now() AT TIME ZONE 'America/Mexico_City') < 5
                            THEN date_trunc('day', now() AT TIME ZONE 'America/Mexico_City' - interval '1 day') + interval '5 hours'
                        ELSE date_trunc('day', now() AT TIME ZONE 'America/Mexico_City') + interval '5 hours'
                    END
              );
        """)
    )

    # Mismo criterio para turnos huérfanos: cerrar el estado sin inventar
    # total_final/diferencia.
    op.execute(
        sa.text("""
            UPDATE turnos
            SET estado = 'cerrado',
                fecha_cierre = now(),
                cerrado_automatico = true,
                total_final = NULL,
                diferencia = NULL
            WHERE estado = 'abierto'
              AND fecha_apertura < (
                    CASE
                        WHEN EXTRACT(HOUR FROM now() AT TIME ZONE 'America/Mexico_City') < 5
                            THEN date_trunc('day', now() AT TIME ZONE 'America/Mexico_City' - interval '1 day') + interval '5 hours'
                        ELSE date_trunc('day', now() AT TIME ZONE 'America/Mexico_City') + interval '5 hours'
                    END
              );
        """)
    )

    # Cierra a nivel DB la carrera de dos check-in/check-out simultáneos
    # (S3.5): a lo más un registro "realmente abierto" (sin cierre_automatico)
    # por usuario. Un huérfano ya reconciliado (cierre_automatico=true,
    # fecha_salida todavía NULL a propósito) no cuenta para esta unicidad —
    # si no, bloquearía el check-in de hoy hasta que un admin lo revisara.
    op.create_index(
        "idx_asistencia_abierta_usuario",
        "registros_asistencia",
        ["usuario_id"],
        unique=True,
        postgresql_where=sa.text("fecha_salida IS NULL AND cierre_automatico = false"),
    )


def downgrade() -> None:
    op.drop_index("idx_asistencia_abierta_usuario", table_name="registros_asistencia")
    op.drop_column("turnos", "cerrado_automatico")
    op.drop_column("registros_asistencia", "fecha_salida_estimada")
    op.drop_column("registros_asistencia", "requiere_revision")
    op.drop_column("registros_asistencia", "cierre_automatico")
    op.drop_column("usuarios", "sesiones_validas_desde")
    # El backfill no se revierte (lossy) — convención ya establecida en
    # 799190d9c93b.
