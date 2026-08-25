"""Protocolo de auth del WebSocket: el JWT viaja como primer frame, no en la URL.

El handshake WS es un GET HTTP; un `?token=` deja el JWT de sesión en texto
plano en los access logs del proxy (Railway). El server ahora acepta el
handshake sin credenciales y exige `{"type": "auth", "token": "<jwt>"}` como
primer mensaje.
"""

import json

import pytest
from fastapi import WebSocketDisconnect

from app.core.config import settings


def _jwt_para(usuario_id: int) -> str:
    from jose import jwt

    # `sub` como string, igual que routers/auth.py al emitir el token real.
    return jwt.encode({"sub": str(usuario_id)}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def test_ws_sin_frame_de_auth_no_recibe_nada(client):
    """Un primer mensaje que no es auth cierra la conexión (4001)."""
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/mesero") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            ws.receive_text()

    assert exc.value.code == 4001


def test_ws_token_invalido_cierra_4001(client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/mesero") as ws:
            ws.send_text(json.dumps({"type": "auth", "token": "no-es-un-jwt"}))
            ws.receive_text()

    assert exc.value.code == 4001


def test_ws_token_valido_conecta(client, seed):
    """Token válido en el primer frame → connection_established."""
    with client.websocket_connect("/ws/mesero") as ws:
        ws.send_text(json.dumps({"type": "auth", "token": _jwt_para(seed["usuario"].id)}))
        mensaje = json.loads(ws.receive_text())

    assert mensaje["type"] == "connection_established"
    assert mensaje["data"]["client_type"] == "mesero"
