"""Reconciliación de jornada: cierra automáticamente lo que quedó abierto de
una jornada anterior (turnos de caja, registros de asistencia).

Se invoca de forma perezosa — nunca por cron ni blacklist — desde
`get_current_user`, los 3 endpoints de login, y `iniciar_turno`. Idempotente:
llamarla varias veces sobre el mismo estado produce el mismo resultado que
llamarla una vez (un turno ya cerrado no vuelve a matchear `estado==abierto`;
una asistencia ya marcada recalcula los mismos valores).

Nunca inventa horas ni cifras de caja: lo que cierra queda marcado para
revisión humana (`requiere_revision`/`cerrado_automatico`), no con datos
reales adivinados.
"""

from datetime import timedelta

from sqlalchemy.orm import Session

from app.domain.estados import MAX_HORAS_JORNADA, EstadoTurno
from app.models import RegistroAsistencia, Turno, Usuario
from app.utils.timezone import get_mexico_now, jornada_de, rango_jornada, to_mexico_aware

MAX_HORAS_JORNADA_DELTA = timedelta(hours=MAX_HORAS_JORNADA)


def reconciliar_jornada(db: Session, sucursal_id: int) -> None:
    """Cierra turnos y asistencias huérfanos de una jornada anterior en `sucursal_id`."""
    ahora = get_mexico_now()
    jornada_actual = jornada_de(ahora)

    turno_abierto = (
        db.query(Turno)
        .filter(Turno.sucursal_id == sucursal_id, Turno.estado == EstadoTurno.ABIERTO)
        .first()
    )
    if turno_abierto and jornada_de(turno_abierto.fecha_apertura) != jornada_actual:
        turno_abierto.estado = EstadoTurno.CERRADO
        turno_abierto.fecha_cierre = ahora
        turno_abierto.cerrado_automatico = True
        turno_abierto.total_final = None
        turno_abierto.diferencia = None

    huerfanos = (
        db.query(RegistroAsistencia)
        .join(Usuario, Usuario.id == RegistroAsistencia.usuario_id)
        .filter(
            Usuario.sucursal_id == sucursal_id,
            RegistroAsistencia.fecha_salida.is_(None),
            RegistroAsistencia.cierre_automatico.is_(False),
        )
        .all()
    )
    for registro in huerfanos:
        jornada_entrada = jornada_de(registro.fecha_entrada)
        if jornada_entrada == jornada_actual:
            continue

        _, fin_jornada_entrada = rango_jornada(jornada_entrada)
        limite_max_horas = to_mexico_aware(registro.fecha_entrada) + MAX_HORAS_JORNADA_DELTA
        estimada = min(limite_max_horas, fin_jornada_entrada)

        registro.cierre_automatico = True
        registro.requiere_revision = True
        registro.fecha_salida_estimada = estimada
        # fecha_salida se deja NULL a propósito: no se inventa la hora real.

    db.commit()
