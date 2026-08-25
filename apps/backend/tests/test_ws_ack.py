"""websocket_manager: acuse de mensajes al KDS y alerta por timeout (S2 2.9)."""

from unittest.mock import AsyncMock

from app.websocket_manager import ConnectionInfo, WebSocketManager


def _conn_kds(manager: WebSocketManager, user_id=1) -> ConnectionInfo:
    ws = AsyncMock()
    conn = ConnectionInfo(websocket=ws, user_id=user_id, user_role="cocina", sucursal_id=1)
    manager.connections["kds"].append(conn)
    return conn


async def test_notify_pedido_created_adjunta_message_id_para_kds():
    manager = WebSocketManager()
    conn = _conn_kds(manager)

    await manager.notify_pedido_created({"id": 42, "sucursal_id": 1})

    assert len(conn.pending_acks) == 1
    (message_id, (sent_at, pedido_id)) = next(iter(conn.pending_acks.items()))
    assert pedido_id == 42

    sent_payload = conn.websocket.send_text.call_args_list[0].args[0]
    assert message_id in sent_payload


async def test_ack_message_limpia_el_pendiente():
    manager = WebSocketManager()
    conn = _conn_kds(manager)
    await manager.notify_pedido_created({"id": 42, "sucursal_id": 1})
    message_id = next(iter(conn.pending_acks))

    manager.ack_message(conn.websocket, message_id)

    assert conn.pending_acks == {}


async def test_otros_grupos_no_llevan_message_id():
    """Solo KDS trackea acuse — caja/mesero/admin reciben el mensaje normal."""
    manager = WebSocketManager()
    ws = AsyncMock()
    conn = ConnectionInfo(websocket=ws, user_id=2, user_role="cajero", sucursal_id=1)
    manager.connections["caja"].append(conn)

    await manager.notify_pedido_created({"id": 42, "sucursal_id": 1})

    assert conn.pending_acks == {}


async def test_avisar_acks_vencidos_notifica_pasado_el_timeout(monkeypatch):
    import time as time_module

    manager = WebSocketManager()
    conn = _conn_kds(manager)
    await manager.notify_pedido_created({"id": 7, "sucursal_id": 1})
    conn.websocket.send_text.reset_mock()

    # Simular que ya pasaron >60s desde el envío.
    monkeypatch.setattr(time_module, "monotonic", lambda: time_module.perf_counter() + 1000)

    await manager._avisar_acks_vencidos()

    assert conn.websocket.send_text.await_count == 1
    payload = conn.websocket.send_text.call_args_list[0].args[0]
    assert '"type": "ack_timeout"' in payload or '"ack_timeout"' in payload
    assert "7" in payload


async def test_avisar_acks_vencidos_no_notifica_si_no_paso_el_timeout():
    manager = WebSocketManager()
    conn = _conn_kds(manager)
    await manager.notify_pedido_created({"id": 7, "sucursal_id": 1})
    conn.websocket.send_text.reset_mock()

    await manager._avisar_acks_vencidos()

    assert conn.websocket.send_text.await_count == 0
