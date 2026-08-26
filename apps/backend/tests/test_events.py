"""Cola de eventos WS (app/events.py): no bloquea el request, no lanza."""

import asyncio
from unittest.mock import AsyncMock

from app.events import WsEvent, enqueue_event, event_consumer


def test_importar_events_sin_loop_corriendo_no_lanza():
    """Antes, importar app.main (que arrastra websocket_manager) fuera de un
    loop corriendo lanzaba RuntimeError por el asyncio.create_task en
    WebSocketManager.__init__. Ya no debería haber ningún side-effect de
    import: `app.events` y `app.websocket_manager` se importan tal cual en
    este módulo de test, que no corre dentro de un loop."""
    from app import events as _  # noqa: F401
    from app import websocket_manager as _wm  # noqa: F401


async def test_enqueue_event_no_lanza_con_cola_llena(monkeypatch):
    cola_de_prueba: asyncio.Queue = asyncio.Queue(maxsize=1)
    monkeypatch.setattr("app.events._queue", cola_de_prueba)

    enqueue_event(WsEvent(type="pedido_created", payload={"pedido_data": {}}))
    # La cola ya está llena (maxsize=1); esto no debe lanzar QueueFull.
    enqueue_event(WsEvent(type="pedido_created", payload={"pedido_data": {}}))

    assert cola_de_prueba.qsize() == 1


async def test_event_consumer_despacha_al_websocket_manager(monkeypatch):
    # Cola nueva por test: la global vive bind-eada al loop del test anterior
    # (pytest-asyncio crea un loop por test) y Queue no permite cruzarlos.
    cola_de_prueba: asyncio.Queue = asyncio.Queue(maxsize=1000)
    monkeypatch.setattr("app.events._queue", cola_de_prueba)
    # Sin Redis: fuerza el fan-out local directo (si el entorno tiene
    # REDIS_URL seteada, el consumer publicaría en vez de despachar aquí).
    monkeypatch.setattr("app.core.redis.settings.REDIS_URL", None)

    mock_wm = AsyncMock()
    monkeypatch.setattr("app.websocket_manager.websocket_manager", mock_wm)

    payload = {"pedido_data": {"id": 1, "sucursal_id": 1}}
    enqueue_event(WsEvent(type="pedido_created", payload=payload))

    stop_event = asyncio.Event()

    async def _detener_tras_drenar():
        await cola_de_prueba.join()
        stop_event.set()

    await asyncio.gather(event_consumer(stop_event), _detener_tras_drenar())

    mock_wm.notify_pedido_created.assert_awaited_once_with(pedido_data=payload["pedido_data"])


async def test_event_consumer_no_muere_si_el_despacho_lanza(monkeypatch):
    cola_de_prueba: asyncio.Queue = asyncio.Queue(maxsize=1000)
    monkeypatch.setattr("app.events._queue", cola_de_prueba)
    monkeypatch.setattr("app.core.redis.settings.REDIS_URL", None)

    mock_wm = AsyncMock()
    mock_wm.notify_pedido_created.side_effect = RuntimeError("boom")
    monkeypatch.setattr("app.websocket_manager.websocket_manager", mock_wm)

    enqueue_event(WsEvent(type="pedido_created", payload={"pedido_data": {}}))

    stop_event = asyncio.Event()

    async def _detener_tras_drenar():
        await cola_de_prueba.join()
        stop_event.set()

    # No debe propagar la excepción del despacho.
    await asyncio.gather(event_consumer(stop_event), _detener_tras_drenar())


async def test_event_consumer_degrada_a_local_si_publish_a_redis_falla(monkeypatch):
    """Redis configurado pero caído a medio vuelo (publish lanza): el evento
    no se pierde, cae al fan-out local en vez de propagar la excepción."""
    cola_de_prueba: asyncio.Queue = asyncio.Queue(maxsize=1000)
    monkeypatch.setattr("app.events._queue", cola_de_prueba)

    mock_redis_client = AsyncMock()
    mock_redis_client.publish.side_effect = ConnectionError("redis caído")
    monkeypatch.setattr("app.core.redis.get_redis", lambda: mock_redis_client)

    mock_wm = AsyncMock()
    monkeypatch.setattr("app.websocket_manager.websocket_manager", mock_wm)

    payload = {"pedido_data": {"id": 9}}
    enqueue_event(WsEvent(type="pedido_created", payload=payload))

    stop_event = asyncio.Event()

    async def _detener_tras_drenar():
        await cola_de_prueba.join()
        stop_event.set()

    await asyncio.gather(event_consumer(stop_event), _detener_tras_drenar())

    mock_wm.notify_pedido_created.assert_awaited_once_with(pedido_data=payload["pedido_data"])
