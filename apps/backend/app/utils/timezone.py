from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

MEXICO_TZ = ZoneInfo("America/Mexico_City")

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
