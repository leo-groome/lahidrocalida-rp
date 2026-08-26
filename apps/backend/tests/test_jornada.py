"""jornada_de()/rango_jornada(): la jornada operativa corre [05:00, 05:00)
hora México, no medianoche a medianoche. El borde de las 05:00 es el caso que
importa — un minuto antes o después cambia a qué día de jornada pertenece.
"""

from datetime import date, datetime

from app.utils.timezone import MEXICO_TZ, jornada_de, rango_jornada


def test_jornada_de_antes_del_corte_pertenece_al_dia_anterior():
    ts = datetime(2026, 8, 25, 4, 59, tzinfo=MEXICO_TZ)
    assert jornada_de(ts) == date(2026, 8, 24)


def test_jornada_de_en_el_corte_pertenece_al_dia_actual():
    ts = datetime(2026, 8, 25, 5, 0, tzinfo=MEXICO_TZ)
    assert jornada_de(ts) == date(2026, 8, 25)


def test_jornada_de_a_media_tarde_pertenece_al_dia_actual():
    ts = datetime(2026, 8, 25, 15, 30, tzinfo=MEXICO_TZ)
    assert jornada_de(ts) == date(2026, 8, 25)


def test_jornada_de_acepta_naive_asumiendo_mexico():
    ts = datetime(2026, 8, 25, 4, 0)
    assert jornada_de(ts) == date(2026, 8, 24)


def test_rango_jornada_cubre_5am_a_5am_del_dia_siguiente():
    inicio, fin = rango_jornada(date(2026, 8, 25))
    assert inicio == datetime(2026, 8, 25, 5, 0, tzinfo=MEXICO_TZ)
    assert fin == datetime(2026, 8, 26, 5, 0, tzinfo=MEXICO_TZ)
