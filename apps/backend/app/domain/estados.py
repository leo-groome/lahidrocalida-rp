"""Fuente única de verdad para los estados de Pedido, ArticuloPedido y Turno.

Los valores string son EXACTAMENTE los que ya existen en la base de datos
(columnas `pedidos.estado`, `articulos_pedido.estado_item`, `turnos.estado`,
todas `String` con CHECK constraints). Cambiar o renombrar un valor rompe
datos existentes: solo se agregan valores nuevos vía migración Alembic.

`StrEnum` (Python 3.11+) hace que cada miembro sea un `str` real, así que
comparaciones y queries SQLAlchemy funcionan sin `.value`:

    Pedido.estado == EstadoPedido.PAGADO
    Pedido.estado.in_(EstadoPedido.terminales())

Alcance S1: definición del vocabulario. Las transiciones válidas
(origen -> destino) eran tarea de S2 — ver `TRANSICIONES_PEDIDO` y
`transicion_permitida` más abajo.
"""

from enum import StrEnum

__all__ = [
    "EstadoPedido",
    "EstadoArticuloPedido",
    "EstadoTurno",
    "TRANSICIONES_PEDIDO",
    "transicion_permitida",
    "MAX_HORAS_JORNADA",
]

# Tope duro de horas por jornada — usado por reconciliar_jornada (S3) y como
# recorte defensivo en cualquier cálculo de horas trabajadas, para que un
# registro corrupto (o sin cerrar por días) no infle nómina.
MAX_HORAS_JORNADA = 16


class EstadoPedido(StrEnum):
    """Estados de `pedidos.estado`."""

    PENDIENTE = "pendiente"
    PREPARANDO = "preparando"
    LISTO = "listo"
    ENTREGADO = "entregado"
    CUENTA_SOLICITADA = "cuenta_solicitada"
    PAGADO = "pagado"
    CANCELADO = "cancelado"
    DIVIDIDO = "dividido"

    @classmethod
    def terminales(cls) -> frozenset["EstadoPedido"]:
        """Estados finales: el pedido ya no admite modificaciones."""
        return frozenset({cls.PAGADO, cls.CANCELADO, cls.DIVIDIDO})

    @classmethod
    def activos(cls) -> frozenset["EstadoPedido"]:
        """Estados en los que el pedido sigue vivo en operación."""
        return frozenset(cls) - cls.terminales()


# Destino -> roles que pueden mover un pedido a ese estado. Igual que el
# `allowed_transitions` que vivía inline en routers/pedidos.py antes de S2,
# pero ahora combinado con una validación real de origen (ver
# `transicion_permitida`): antes nada impedía cambiar el estado de un pedido
# ya en un estado terminal (pagado/cancelado/dividido), el único chequeo era
# "¿el rol puede poner este destino?", sin mirar el origen.
TRANSICIONES_PEDIDO: dict[EstadoPedido, frozenset[str]] = {
    EstadoPedido.PENDIENTE: frozenset({"mesero", "cocina", "administrador"}),
    EstadoPedido.PREPARANDO: frozenset({"cocina", "administrador"}),
    EstadoPedido.LISTO: frozenset({"cocina", "administrador"}),
    EstadoPedido.ENTREGADO: frozenset({"mesero", "cajero", "cocina", "administrador"}),
    EstadoPedido.CUENTA_SOLICITADA: frozenset({"mesero", "cajero", "administrador"}),
    EstadoPedido.PAGADO: frozenset({"cajero", "administrador"}),
    EstadoPedido.CANCELADO: frozenset({"cajero", "administrador"}),
    # Alcanzable manualmente por administrador (menú de estado en Caja) además
    # de vía /dividir y /dividir_por_montos, que lo setean directo sin pasar
    # por esta tabla.
    EstadoPedido.DIVIDIDO: frozenset({"administrador"}),
}


def transicion_permitida(origen: str, destino: str, rol: str) -> bool:
    """True si `rol` puede mover un pedido en estado `origen` a `destino`.

    Un pedido en estado terminal (`EstadoPedido.terminales()`) no admite
    ninguna transición más, sin importar el rol: es el bug que cierra esta
    validación, antes solo se miraba el destino.
    """
    try:
        origen_enum = EstadoPedido(origen)
    except ValueError:
        return False
    if origen_enum in EstadoPedido.terminales():
        return False
    try:
        destino_enum = EstadoPedido(destino)
    except ValueError:
        return False
    return rol in TRANSICIONES_PEDIDO.get(destino_enum, frozenset())


class EstadoArticuloPedido(StrEnum):
    """Estados de `articulos_pedido.estado_item` (flujo de cocina)."""

    PENDIENTE = "pendiente"
    PREPARANDO = "preparando"
    LISTO = "listo"
    ENTREGADO = "entregado"


class EstadoTurno(StrEnum):
    """Estados de `turnos.estado`."""

    ABIERTO = "abierto"
    CERRADO = "cerrado"
