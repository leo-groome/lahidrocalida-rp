import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.deps import require_roles
from app.models import Usuario
from app.utils.timezone import get_mexico_now
from app.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# Segundos que el server espera el mensaje `{"type": "auth", ...}` tras aceptar
# el handshake. Corto: una conexión sin autenticar consume un slot del server.
AUTH_TIMEOUT_SECONDS = 10


async def get_user_from_token(token: str, db: Session) -> Usuario:
    """Validar token JWT y obtener usuario para WebSocket"""
    try:
        # Decodificar el token JWT usando la misma lógica que auth.py
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        usuario_id: int = payload.get("sub")

        if not usuario_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")

        # Buscar usuario en la base de datos
        user = db.query(Usuario).filter(Usuario.id == usuario_id, Usuario.activo == True).first()

        if not user:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        return user

    except JWTError as e:
        logger.error(f"JWT Error validating WebSocket token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Error validating WebSocket token: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication")


async def _safe_close(websocket: WebSocket, code: int, reason: str) -> None:
    """Cerrar sin propagar: el peer puede haberse ido ya (cierre durante auth)."""
    try:
        await websocket.close(code=code, reason=reason)
    except Exception:  # noqa: BLE001 - cerrar es best-effort
        pass


async def _receive_auth_token(websocket: WebSocket) -> str:
    """Esperar el primer mensaje de la conexión y extraer el JWT.

    Protocolo: el cliente NO manda el token en la URL (el query string del
    handshake queda en texto plano en los access logs del proxy). Conecta sin
    credenciales y manda como primer frame:

        {"type": "auth", "token": "<jwt>"}

    Errores → HTTPException 401, que el caller traduce a close(4001).
    """
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=401, detail="Auth timeout")
    except WebSocketDisconnect:
        raise HTTPException(status_code=401, detail="Disconnected before auth")

    try:
        message = json.loads(raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid auth message")

    if not isinstance(message, dict) or message.get("type") != "auth":
        raise HTTPException(status_code=401, detail="Expected auth message")

    token = message.get("token")
    if not token or not isinstance(token, str):
        raise HTTPException(status_code=401, detail="Missing token")

    return token


@router.websocket("/ws/{client_type}")
async def websocket_endpoint(websocket: WebSocket, client_type: str, db: Session = Depends(get_db)):
    """
    Endpoint principal de WebSocket para diferentes tipos de clientes

    Args:
        client_type: Tipo de cliente (kds, caja, mesero)

    Autenticación: primer mensaje `{"type": "auth", "token": "<jwt>"}` dentro de
    AUTH_TIMEOUT_SECONDS. Token inválido/ausente/tardío → close(4001).
    """

    # Validar que el client_type es válido
    valid_client_types = ["kds", "caja", "mesero"]
    if client_type not in valid_client_types:
        await websocket.close(code=4000, reason="Invalid client type")
        return

    try:
        # Aceptar el handshake para poder recibir el frame de auth. La conexión
        # no queda registrada en el manager hasta que el token valida.
        await websocket.accept()

        token = await _receive_auth_token(websocket)

        # Autenticar usuario
        user = await get_user_from_token(token, db)

        # Intentar conectar al WebSocket
        connection_success = await websocket_manager.connect(
            websocket=websocket,
            client_type=client_type,
            user_id=user.id,
            user_role=user.rol,
            sucursal_id=user.sucursal_id,
        )

        if not connection_success:
            return

        try:
            # Mantener la conexión abierta y manejar mensajes entrantes
            while True:
                # Recibir mensajes del cliente (principalmente para heartbeat)
                data = await websocket.receive_text()

                # Procesar mensajes especiales
                try:
                    message = json.loads(data) if data else {}

                    if message.get("type") == "ping":
                        # Responder a ping con pong
                        pong_response = {"type": "pong", "timestamp": get_mexico_now().isoformat()}
                        await websocket.send_text(json.dumps(pong_response))

                        # Actualizar último ping en el manager (zombie cleanup)
                        websocket_manager.update_last_ping(websocket)

                except Exception as e:
                    logger.warning(f"Error processing message from client: {e}")
                    # No cerrar la conexión por errores de mensajes no críticos
                    continue

        except WebSocketDisconnect:
            logger.info(f"Client disconnected: user={user.id}, type={client_type}")

        except Exception as e:
            logger.error(f"Unexpected error in WebSocket connection: {e}")

    except HTTPException as e:
        # Error de autenticación
        await _safe_close(websocket, code=4001, reason=e.detail)

    except Exception as e:
        # Error inesperado
        logger.error(f"Unexpected error in websocket endpoint: {e}")
        await _safe_close(websocket, code=4002, reason="Internal server error")

    finally:
        # Limpiar la conexión del manager
        await websocket_manager.disconnect(websocket)


@router.get("/ws/stats", dependencies=[Depends(require_roles("administrador"))])
async def get_websocket_stats():
    """
    Endpoint para obtener estadísticas de conexiones WebSocket activas
    Útil para monitoreo y debugging. Solo administrador: expone conteo de
    sesiones activas por sucursal/rol.
    """
    return {
        "status": "active",
        "connections": websocket_manager.get_connection_stats(),
        "timestamp": get_mexico_now().isoformat(),
    }
