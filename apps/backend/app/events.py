"""Cola de eventos WS: desacopla el commit de DB del envío por WebSocket.

Antes, cada endpoint hacía `await websocket_manager.notify_*(...)` en línea, lo
que bloqueaba el event loop del request con el envío real a cada conexión
(`_send_to_connection` -> `websocket.send_text`). `enqueue_event` es síncrono y
no bloqueante: el endpoint solo mete el evento en memoria y responde. Un
consumidor de background (arrancado en `lifespan`, ver app/main.py) drena la
cola y hace el envío real fuera del ciclo request/response.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Literal

logger = logging.getLogger(__name__)

EventType = Literal[
    "pedido_created",
    "pedido_estado_changed",
    "articulo_estado_changed",
    "print_ticket",
]


@dataclass
class WsEvent:
    type: EventType
    payload: dict[str, Any]


# maxsize acotado: si el consumidor muere o se atasca, un backlog sin límite
# se comería la memoria del proceso. Preferible descartar eventos (el KDS
# resincroniza vía `connection_open` / polling) a tumbar el servicio.
_queue: "asyncio.Queue[WsEvent]" = asyncio.Queue(maxsize=1000)


def enqueue_event(event: WsEvent) -> None:
    """Encola un evento desde un endpoint. Nunca bloquea ni lanza."""
    try:
        _queue.put_nowait(event)
    except asyncio.QueueFull:
        logger.warning("Cola de eventos WS llena, descartando evento %s", event.type)


_DISPATCH = {
    "pedido_created": lambda wm, p: wm.notify_pedido_created(**p),
    "pedido_estado_changed": lambda wm, p: wm.notify_pedido_estado_changed(**p),
    "articulo_estado_changed": lambda wm, p: wm.notify_articulo_estado_changed(**p),
    "print_ticket": lambda wm, p: wm.notify_print_ticket(**p),
}


async def event_consumer(stop_event: "asyncio.Event") -> None:
    """Drena la cola y despacha cada evento a `websocket_manager`.

    Arrancado como task desde `lifespan`. Se detiene cuando `stop_event` se
    marca (shutdown), sin cancelar un despacho a medias.
    """
    from app.websocket_manager import websocket_manager

    while not stop_event.is_set():
        try:
            event = await asyncio.wait_for(_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
        try:
            await _DISPATCH[event.type](websocket_manager, event.payload)
        except Exception:
            logger.exception("Error despachando evento WS %s", event.type)
        finally:
            _queue.task_done()
