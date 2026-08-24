import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import Usuario
from app.utils.timezone import get_mexico_now
from app.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()


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


@router.websocket("/ws/{client_type}")
async def websocket_endpoint(
    websocket: WebSocket, client_type: str, token: str = Query(...), db: Session = Depends(get_db)
):
    """
    Endpoint principal de WebSocket para diferentes tipos de clientes

    Args:
        client_type: Tipo de cliente (kds, caja, mesero)
        token: JWT token para autenticación
    """

    # Validar que el client_type es válido
    valid_client_types = ["kds", "caja", "mesero"]
    if client_type not in valid_client_types:
        await websocket.close(code=4000, reason="Invalid client type")
        return

    try:
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
        await websocket.close(code=4001, reason=e.detail)

    except Exception as e:
        # Error inesperado
        logger.error(f"Unexpected error in websocket endpoint: {e}")
        await websocket.close(code=4002, reason="Internal server error")

    finally:
        # Limpiar la conexión del manager
        await websocket_manager.disconnect(websocket)


@router.get("/ws/stats")
async def get_websocket_stats():
    """
    Endpoint para obtener estadísticas de conexiones WebSocket activas
    Útil para monitoreo y debugging
    """
    return {
        "status": "active",
        "connections": websocket_manager.get_connection_stats(),
        "timestamp": get_mexico_now().isoformat(),
    }
