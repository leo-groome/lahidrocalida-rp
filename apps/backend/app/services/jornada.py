"""Reconciliación de jornada de asistencia: registra la salida automática (00:30 hora
México) de quien no la registró y marca como anomalía lo que no se puede resolver.

Se invoca de forma perezosa — nunca por cron ni blacklist — desde
`get_current_user`, los logins, `/auth/asistencia` e `iniciar_turno`. La salida
automática es determinista (siempre las 00:30 de esa noche, sin importar cuándo corra
la reconciliación), así que no necesita cron. Idempotente: un registro ya cerrado no
vuelve a matchear `fecha_salida IS NULL`.

Los turnos de caja NO se cierran aquí: el cajero cierra y reabre a mano al contar el
fondo. Los cierres con hora inventada se evitan: lo que no cabe en la regla de las
00:30 queda marcado `requiere_revision` para que un admin confirme la hora real.
"""

from datetime import datetime, time, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.domain.estados import MAX_HORAS_JORNADA
from app.models import RegistroAsistencia, Usuario
from app.utils.timezone import (
    MEXICO_TZ,
    get_mexico_now,
    jornada_de,
    rango_jornada,
    to_mexico_aware,
)

MAX_HORAS_JORNADA_DELTA = timedelta(hours=MAX_HORAS_JORNADA)

# A esta hora (hora México, de la madrugada siguiente a la jornada) el
# restaurante ya cerró: a quien no registró salida se le registra esta.
HORA_SALIDA_AUTOMATICA = time(0, 30)
# Un "turno" de menos de esto no es una jornada real (p. ej. una entrada a las
# 00:06): se deja como anomalía para que un admin la revise en vez de inventar 24 min.
MIN_DURACION_AUTOCIERRE = timedelta(hours=1)


def salida_automatica(entrada: datetime) -> Optional[datetime]:
    """Hora de salida automática (00:30 de la madrugada que cierra la jornada de
    `entrada`), o None si la regla no aplica: entrada demasiado temprana (> MAX_HORAS_JORNADA
    de turno), demasiado cercana al corte (< 1 h) o ya pasada de las 00:30."""
    entrada = to_mexico_aware(entrada)
    corte = datetime.combine(
        jornada_de(entrada) + timedelta(days=1), HORA_SALIDA_AUTOMATICA, tzinfo=MEXICO_TZ
    )
    duracion = corte - entrada
    if duracion < MIN_DURACION_AUTOCIERRE or duracion > MAX_HORAS_JORNADA_DELTA:
        return None
    return corte


def reconciliar_jornada(db: Session, sucursal_id: int, ahora: Optional[datetime] = None) -> None:
    """Reconcilia asistencias abiertas de la sucursal `sucursal_id`:

    1. Pasadas las 00:30, a quien no registró salida se le registra la salida a las
       00:30 (`cierre_automatico=True`, cuenta para horas; sin revisión).
    2. Si esa regla no aplica y la jornada de la entrada ya terminó, queda como anomalía
       (`requiere_revision`, sin `fecha_salida`) hasta que un admin confirme la real.

    NOTA: Los turnos de caja NUNCA se cierran automáticamente; permanecen abiertos
    hasta que el cajero realice su cierre manual (el cajero reabre de inmediato
    tras contar el fondo).
    """
    ahora = ahora or get_mexico_now()
    jornada_actual = jornada_de(ahora)

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
        corte = salida_automatica(registro.fecha_entrada)
        if corte is not None:
            if ahora >= corte:
                registro.fecha_salida = corte
                registro.cierre_automatico = True
                registro.requiere_revision = False
                registro.fecha_salida_estimada = None
            continue  # antes del corte sigue trabajando

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


def backfill_salidas_automaticas(db: Session, aplicar: bool = False) -> list[tuple[int, datetime]]:
    """Aplica la regla de las 00:30 a las anomalías ya existentes (registros que el
    esquema anterior dejó con `fecha_salida` NULL + `requiere_revision`). Devuelve
    [(registro_id, salida)] de los que se resolverían; solo escribe si `aplicar`.
    Los que la regla no cubre (p. ej. >16 h) se dejan para revisión humana."""
    pendientes = (
        db.query(RegistroAsistencia)
        .filter(
            RegistroAsistencia.fecha_salida.is_(None),
            RegistroAsistencia.cierre_automatico.is_(True),
            RegistroAsistencia.requiere_revision.is_(True),
        )
        .order_by(RegistroAsistencia.id)
        .all()
    )
    resueltos: list[tuple[int, datetime]] = []
    for registro in pendientes:
        salida = salida_automatica(registro.fecha_entrada)
        if salida is None:
            continue
        resueltos.append((registro.id, salida))
        if aplicar:
            registro.fecha_salida = salida
            registro.requiere_revision = False
            registro.fecha_salida_estimada = None
    if aplicar:
        db.commit()
    return resueltos
