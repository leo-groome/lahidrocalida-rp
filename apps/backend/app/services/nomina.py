"""Cálculo de nómina semanal: horas de asistencia × tarifa por hora / por hora extra.

Funciones puras (sin DB) para poder probar cada regla por separado. El periodo
de pago va de martes a lunes (el lunes es descanso pero pertenece a la semana
que cierra); las jornadas siguen el corte operativo de las 05:00.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from typing import Iterable

from app.domain.estados import MAX_HORAS_JORNADA
from app.utils.timezone import jornada_de, to_mexico_aware

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


def dias_y_extras(
    horas_dia: dict[date, Decimal], horas_jornada: Decimal
) -> tuple[int, Decimal, Decimal]:
    """(días trabajados, horas extra, horas totales) de una semana."""
    trabajados = {d: h for d, h in horas_dia.items() if h >= MIN_HORAS_DIA}
    extra = Decimal(0)
    for h in trabajados.values():
        exceso = max(Decimal(0), h - horas_jornada)
        extra += (exceso / BLOQUE_EXTRA).to_integral_value(rounding=ROUND_FLOOR) * BLOQUE_EXTRA
    total = sum(trabajados.values(), Decimal(0))
    return len(trabajados), extra, _q(total)


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
