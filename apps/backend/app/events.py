"""Cola de eventos WS: desacopla el commit de DB del envío por WebSocket, y
distribuye esos eventos entre workers/réplicas vía Redis pub/sub.

Antes, cada endpoint hacía `await websocket_manager.notify_*(...)` en línea, lo
que bloqueaba el event loop del request con el envío real a cada conexión
(`_send_to_connection` -> `websocket.send_text`). `enqueue_event` es síncrono y
no bloqueante: el endpoint solo mete el evento en memoria y responde. Un
consumidor de background (arrancado en `lifespan`, ver app/main.py) drena la
cola.

Con >1 worker, cada proceso tiene su propio `WebSocketManager` en memoria con
conexiones distintas: un evento generado en el worker A nunca llegaría a un
cliente conectado al worker B. Por eso, si hay Redis configurado, el consumidor
publica en el canal "ws:events" en vez de despachar localmente, y un
`redis_subscriber` (corriendo en todos los workers, incluido el que publicó)
es el único que efectivamente entrega a las conexiones WS locales — así todos
los workers usan el mismo camino de código. Sin Redis, se degrada a fan-out
local directo (comportamiento de un solo proceso).
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Literal

logger = logging.getLogger(__name__)

REDIS_CHANNEL = "ws:events"

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


async def _dispatch_local(event: WsEvent) -> None:
    from app.websocket_manager import websocket_manager

    await _DISPATCH[event.type](websocket_manager, event.payload)


async def event_consumer(stop_event: "asyncio.Event") -> None:
    """Drena la cola y distribuye cada evento.

    Con Redis disponible, publica en `REDIS_CHANNEL` y depende de
    `redis_subscriber` (en este mismo proceso u otro) para la entrega real —
    así el originador no duplica el despacho. Si el publish falla o no hay
    Redis, despacha localmente como fallback.

    Arrancado como task desde `lifespan`. Se detiene cuando `stop_event` se
    marca (shutdown), sin cancelar un despacho a medias.
    """
    from app.core.redis import get_redis

    while not stop_event.is_set():
        try:
            event = await asyncio.wait_for(_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
        try:
            redis_client = get_redis()
            if redis_client is not None:
                try:
                    await redis_client.publish(
                        REDIS_CHANNEL,
                        json.dumps({"type": event.type, "payload": event.payload}),
                    )
                except Exception:
                    logger.warning(
                        "Publish a Redis falló, fan-out local de respaldo", exc_info=True
                    )
                    await _dispatch_local(event)
            else:
                await _dispatch_local(event)
        except Exception:
            logger.exception("Error despachando evento WS %s", event.type)
        finally:
            _queue.task_done()


async def redis_subscriber(stop_event: "asyncio.Event") -> None:
    """Suscriptor Redis: entrega a las conexiones WS locales de este worker
    los eventos publicados por cualquier worker (incluido este mismo).

    No-op si no hay Redis configurado — sin Redis, `event_consumer` ya
    despacha localmente por su cuenta.
    """
    from app.core.redis import get_redis

    redis_client = get_redis()
    if redis_client is None:
        return

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(REDIS_CHANNEL)
    try:
        while not stop_event.is_set():
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            except Exception:
                logger.warning("Error leyendo de Redis pub/sub", exc_info=True)
                await asyncio.sleep(1.0)
                continue
            if message is None:
                continue
            try:
                data = json.loads(message["data"])
                await _dispatch_local(WsEvent(type=data["type"], payload=data["payload"]))
            except Exception:
                logger.exception("Error procesando mensaje de Redis pub/sub")
    finally:
        await pubsub.unsubscribe(REDIS_CHANNEL)
        await pubsub.aclose()
