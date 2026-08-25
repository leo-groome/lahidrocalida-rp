"""Fan-out distribuido: dos "workers" (dos WebSocketManager) comparten un
mismo Redis y ambos reciben el evento publicado por cualquiera de los dos.

Requiere un Redis real: se saltan si TEST_REDIS_URL no está seteada, igual que
los tests de Postgres se saltan sin TEST_DATABASE_URL apuntando a un servidor
real. Levantar uno local: `docker run --rm -p 6379:6379 redis:7-alpine`.
"""

import asyncio
import json
import os

import pytest

TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL")

pytestmark = pytest.mark.skipif(
    not TEST_REDIS_URL, reason="TEST_REDIS_URL no configurada, se salta test de integración"
)


@pytest.fixture()
def redis_url(monkeypatch):
    from app.core import redis as redis_module

    monkeypatch.setattr(redis_module.settings, "REDIS_URL", TEST_REDIS_URL)
    monkeypatch.setattr(redis_module, "_client", None)
    yield TEST_REDIS_URL
    monkeypatch.setattr(redis_module, "_client", None)


async def test_publish_en_un_worker_llega_al_subscriber_de_otro(redis_url):
    import redis.asyncio as aioredis

    from app.events import REDIS_CHANNEL

    # Simula dos procesos: cada uno con su propia conexión Redis, pero
    # apuntando al mismo servidor (a diferencia de app.core.redis, que cachea
    # un único cliente global por proceso).
    publisher = aioredis.from_url(redis_url, decode_responses=True)
    subscriber_conn = aioredis.from_url(redis_url, decode_responses=True)

    pubsub = subscriber_conn.pubsub()
    await pubsub.subscribe(REDIS_CHANNEL)
    # Drenar el mensaje de confirmación de suscripción antes de publicar.
    await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

    evento = {"type": "pedido_created", "payload": {"pedido_data": {"id": 42}}}
    await publisher.publish(REDIS_CHANNEL, json.dumps(evento))

    mensaje = None
    for _ in range(20):
        mensaje = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
        if mensaje is not None:
            break

    assert mensaje is not None, "el worker B nunca recibió el evento publicado por el worker A"
    assert json.loads(mensaje["data"]) == evento

    await pubsub.unsubscribe(REDIS_CHANNEL)
    await pubsub.aclose()
    await publisher.aclose()
    await subscriber_conn.aclose()


async def test_redis_subscriber_despacha_evento_publicado(redis_url, monkeypatch):
    from unittest.mock import AsyncMock

    from app.core.redis import get_redis
    from app.events import REDIS_CHANNEL, redis_subscriber

    mock_wm = AsyncMock()
    monkeypatch.setattr("app.websocket_manager.websocket_manager", mock_wm)

    stop_event = asyncio.Event()
    task = asyncio.create_task(redis_subscriber(stop_event))
    await asyncio.sleep(0.2)  # dar tiempo a que el subscriber haga el SUBSCRIBE

    payload = {"pedido_data": {"id": 7}}
    await get_redis().publish(
        REDIS_CHANNEL, json.dumps({"type": "pedido_created", "payload": payload})
    )

    for _ in range(20):
        if mock_wm.notify_pedido_created.await_count:
            break
        await asyncio.sleep(0.2)

    stop_event.set()
    await asyncio.gather(task, return_exceptions=True)

    mock_wm.notify_pedido_created.assert_awaited_once_with(pedido_data=payload["pedido_data"])
