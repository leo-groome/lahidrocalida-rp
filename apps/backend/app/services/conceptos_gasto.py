"""Estado de pago (al corriente / pendiente / vencido) de conceptos indirectos."""

from datetime import date, datetime
from typing import Optional

PERIODO_DIAS = {"semanal": 7, "bimestral": 62, "anual": 365}
# Días de anticipación para marcar "pendiente" y de gracia antes de "vencido".
AVISO_DIAS = {"semanal": 1, "bimestral": 7, "anual": 15}
GRACIA_DIAS = {"semanal": 2, "bimestral": 5, "anual": 7}


def estado_concepto(
    frecuencia: str,
    dia_vencimiento: Optional[int],
    ultimo_pago: Optional[datetime],
    hoy: date,
    jornada_de,
    intervalo_dias: Optional[int] = None,
) -> str:
    """`ultimo_pago` es el fecha_gasto del último gasto; `jornada_de` lo pasa a día operativo."""
    if frecuencia == "eventual":
        return "al_corriente"
    ultimo = jornada_de(ultimo_pago) if ultimo_pago else None
    if frecuencia == "mensual":
        if ultimo and (ultimo.year, ultimo.month) == (hoy.year, hoy.month):
            return "al_corriente"
        if dia_vencimiento is None:
            return "pendiente"
        if hoy.day > dia_vencimiento:
            return "vencido"
        return "pendiente" if hoy.day >= dia_vencimiento - 3 else "al_corriente"
    if ultimo is None:
        return "pendiente"
    transcurrido = (hoy - ultimo).days
    if frecuencia == "cada_n_dias":
        periodo = intervalo_dias or 30
        aviso, gracia = min(3, periodo // 4), min(5, periodo // 4)
    else:
        periodo, aviso, gracia = (
            PERIODO_DIAS[frecuencia],
            AVISO_DIAS[frecuencia],
            GRACIA_DIAS[frecuencia],
        )
    if transcurrido > periodo + gracia:
        return "vencido"
    return "pendiente" if transcurrido >= periodo - aviso else "al_corriente"
