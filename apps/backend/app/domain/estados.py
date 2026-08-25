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
(origen -> destino) son tarea de S2 y no viven aquí todavía.
"""

from enum import StrEnum

__all__ = ["EstadoPedido", "EstadoArticuloPedido", "EstadoTurno"]


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
