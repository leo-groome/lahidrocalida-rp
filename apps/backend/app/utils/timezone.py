from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

MEXICO_TZ = ZoneInfo("America/Mexico_City")

# Hora de corte de la jornada operativa: un turno/asistencia que se abre a
# las 04:59 pertenece a la jornada del día anterior; a las 05:00 en adelante,
# a la de hoy. No es un límite de código — es la hora real a la que el
# restaurante suele cerrar, usada aquí como frontera fija.
HORA_CORTE_JORNADA = 5


def get_mexico_now():
    """Retorna el datetime actual en la zona horaria de México (aware)"""
    return datetime.now(MEXICO_TZ)


def get_day_range(target_date):
    """
    Dado un objeto date, retorna el inicio y fin de ese día como aware datetimes
    en la zona horaria de México.
    """
    start = datetime.combine(target_date, datetime.min.time(), tzinfo=MEXICO_TZ)
    end = datetime.combine(target_date + timedelta(days=1), datetime.min.time(), tzinfo=MEXICO_TZ)
    return start, end


def to_mexico_aware(ts: datetime) -> datetime:
    """Normaliza `ts` a aware en hora México. Un datetime naive (p. ej. al
    releer de SQLite, que no preserva tzinfo — Postgres/TIMESTAMPTZ sí) se
    asume ya en hora México, no UTC: así se guarda en toda la app
    (`get_local_datetime`)."""
    return ts.astimezone(MEXICO_TZ) if ts.tzinfo else ts.replace(tzinfo=MEXICO_TZ)


def jornada_de(ts: datetime) -> date:
    """
    Día de jornada operativa al que pertenece `ts`. La jornada del día X
    cubre [05:00 día X, 05:00 día X+1) hora México — cualquier hora del día,
    no solo el horario de cierre habitual.
    """
    ts_local = to_mexico_aware(ts)
    dia = ts_local.date()
    if ts_local.time() < time(HORA_CORTE_JORNADA):
        dia -= timedelta(days=1)
    return dia


def rango_jornada(fecha_jornada: date) -> tuple[datetime, datetime]:
    """Rango [inicio, fin) de la jornada `fecha_jornada`, como aware datetimes."""
    inicio = datetime.combine(fecha_jornada, time(HORA_CORTE_JORNADA), tzinfo=MEXICO_TZ)
    fin = inicio + timedelta(days=1)
    return inicio, fin
