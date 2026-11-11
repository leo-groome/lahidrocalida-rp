"""Cálculo de nómina semanal: horas de asistencia × tarifa por hora / por hora extra.

Funciones puras (sin DB) para poder probar cada regla por separado. El periodo
de pago va de martes a lunes (el lunes es descanso pero pertenece a la semana
que cierra); las jornadas siguen el corte operativo de las 05:00.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from typing import Iterable

from app.domain.estados import MAX_HORAS_JORNADA
from app.utils.timezone import MEXICO_TZ, jornada_de, to_mexico_aware

CENTAVOS = Decimal("0.01")
# Una entrada de menos de esto no cuenta como día trabajado (checada por error).
MIN_HORAS_DIA = Decimal("1")
# Las extras se pagan en bloques de cuarto de hora, para que 8h07m no sume extras.
BLOQUE_EXTRA = Decimal("0.25")


@dataclass(frozen=True)
class Reglas:
    tarifa_hora: Decimal
    tarifa_hora_extra: Decimal
    horas_jornada: Decimal


@dataclass(frozen=True)
class Montos:
    base: Decimal
    extra_monto: Decimal


def _q(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def horas_por_jornada(
    registros: Iterable[tuple],
) -> dict[date, Decimal]:
    """Suma horas por jornada operativa. `registros`: (fecha_entrada, fecha_salida)."""
    horas: dict[date, Decimal] = {}
    for entrada, salida in registros:
        entrada, salida = to_mexico_aware(entrada), to_mexico_aware(salida)
        h = min(Decimal(str((salida - entrada).total_seconds() / 3600)), Decimal(MAX_HORAS_JORNADA))
        if h <= 0:
            continue
        dia = jornada_de(entrada)
        horas[dia] = horas.get(dia, Decimal(0)) + h
    return horas


def horas_proyectadas(entrada: datetime) -> Decimal:
    """Horas hasta medianoche para una salida de nómina registrada a las 23:59."""
    entrada = to_mexico_aware(entrada)
    fin = datetime.combine(jornada_de(entrada) + timedelta(days=1), time.min, tzinfo=MEXICO_TZ)
    h = Decimal(str((fin - entrada).total_seconds() / 3600))
    return min(max(h, Decimal(0)), Decimal(MAX_HORAS_JORNADA))


def salida_para_nomina(salida: datetime, cierre_por_nomina: bool) -> datetime:
    """Incluye el último minuto solo en cierres de asistencia por nómina."""
    return salida + timedelta(minutes=1) if cierre_por_nomina else salida


def proyeccion_abiertas(
    cerrados: Iterable[tuple], abiertas: Iterable[datetime], horas_jornada: Decimal
) -> tuple[Decimal, Decimal]:
    """(horas, horas extra) que suma la semana al proyectar las entradas abiertas hasta 23:59.

    Es el delta contra lo ya confirmado: se aplica igual a líneas calculadas y a las que el
    admin ajustó a mano. `cerrados`: (fecha_entrada, fecha_salida); `abiertas`: fecha_entrada.
    """
    confirmado = horas_por_jornada(cerrados)
    _, extra0, horas0 = dias_y_extras(confirmado, horas_jornada)
    proyectado = dict(confirmado)
    for entrada in abiertas:
        dia = jornada_de(entrada)
        proyectado[dia] = proyectado.get(dia, Decimal(0)) + horas_proyectadas(entrada)
    _, extra1, horas1 = dias_y_extras(proyectado, horas_jornada)
    return horas1 - horas0, extra1 - extra0


def dias_y_extras(
    horas_dia: dict[date, Decimal], horas_jornada: Decimal
) -> tuple[int, Decimal, Decimal]:
    """(días trabajados, horas extra, horas totales) de una semana."""
    trabajados = {d: h for d, h in horas_dia.items() if h >= MIN_HORAS_DIA}
    extra = Decimal(0)
    for h in trabajados.values():
        _, extra_dia = desglose_jornada(h, horas_jornada)
        extra += extra_dia
    total = sum(trabajados.values(), Decimal(0))
    return len(trabajados), extra, _q(total)


def desglose_jornada(horas: Decimal, horas_jornada: Decimal) -> tuple[Decimal, Decimal]:
    """Devuelve horas normales y extras pagables para una jornada."""
    if horas < MIN_HORAS_DIA:
        return Decimal(0), Decimal(0)
    exceso = max(Decimal(0), horas - horas_jornada)
    extra = (exceso / BLOQUE_EXTRA).to_integral_value(rounding=ROUND_FLOOR) * BLOQUE_EXTRA
    return horas - extra, extra


def calcular_montos(reglas: Reglas, horas_trabajadas: Decimal, horas_extra: Decimal) -> Montos:
    """Pago por horas normales y por horas extra (sin bonos ni descuentos)."""
    normales = max(Decimal(0), horas_trabajadas - horas_extra)
    return Montos(
        base=_q(normales * reglas.tarifa_hora),
        extra_monto=_q(horas_extra * reglas.tarifa_hora_extra),
    )


def total_linea(montos: Montos, bonos: Decimal, descuentos: Decimal) -> Decimal:
    return max(Decimal(0), _q(montos.base + montos.extra_monto + bonos - descuentos))


def faltas(dias_trabajados: int, dias_esperados: int) -> int:
    return max(0, dias_esperados - dias_trabajados)
