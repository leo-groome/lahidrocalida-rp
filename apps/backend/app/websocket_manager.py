import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Tuple

from fastapi import WebSocket

from app.utils.timezone import get_mexico_now

logger = logging.getLogger(__name__)

# Segundos sin acuse de un mensaje al KDS antes de avisarle (vía "ack_timeout")
# que puede estar perdiendo eventos silenciosamente — la propia conexión WS
# sigue "viva" (no es un zombie: puede seguir mandando pings), pero un mensaje
# que el cliente nunca acusó es indistinguible de uno perdido en tránsito.
ACK_TIMEOUT_SECONDS = 60


class ConnectionInfo:
    def __init__(self, websocket: WebSocket, user_id: int, user_role: str, sucursal_id: int):
        self.websocket = websocket
        self.user_id = user_id
        self.user_role = user_role
        self.sucursal_id = sucursal_id
        self.connected_at = get_mexico_now()
        self.last_ping = get_mexico_now()
        # message_id -> (enviado_en, pedido_id). Solo se puebla para KDS
        # (ver _broadcast_to_group) — es el único cliente para el que S2 pide
        # esta alerta.
        self.pending_acks: Dict[str, Tuple[float, Optional[int]]] = {}


class WebSocketManager:
    def __init__(self):
        # Organizar conexiones por tipo de cliente
        self.connections: Dict[str, List[ConnectionInfo]] = {
            "kds": [],  # Kitchen Display System
            "caja": [],  # Cashier/Point of Sale
            "mesero": [],  # Waiters
            "admin": [],  # Administrators (receive all updates)
        }

        # Mapeo de roles a grupos permitidos
        self.role_to_groups = {
            "cocina": ["kds"],
            "cajero": ["caja"],
            "mesero": ["mesero"],
            "administrador": ["kds", "caja", "mesero", "admin"],
        }

    def _get_allowed_groups(self, user_role: str) -> List[str]:
        """Obtiene los grupos permitidos para un rol específico"""
        return self.role_to_groups.get(user_role, [])

    def update_last_ping(self, websocket: WebSocket):
        """Actualiza el timestamp del último ping recibido para una conexión"""
        for client_type, connections in self.connections.items():
            for conn in connections:
                if conn.websocket == websocket:
                    conn.last_ping = get_mexico_now()
                    return

    async def _cleanup_zombies(self):
        """Hilo de fondo que remueve conexiones silenciosas (sin pings en 120s)"""
        while True:
            await asyncio.sleep(30)
            now = get_mexico_now()

            for client_type, connections in list(self.connections.items()):
                # Filtrar conexiones vivas vs zombies
                alive = []
                for conn in connections:
                    # 120 segundos sin ping = zombie
                    if (now - conn.last_ping).total_seconds() > 120:
                        logger.warning(
                            f"Cerrando conexión zombie: user={conn.user_id}, type={client_type}"
                        )
                        try:
                            # Intentar cerrar la conexión (puede que ya esté cerrada del lado del cliente)
                            await conn.websocket.close(code=4008, reason="Ping timeout")
                        except Exception:
                            pass
                    else:
                        alive.append(conn)

                self.connections[client_type] = alive

            await self._avisar_acks_vencidos()

    async def _avisar_acks_vencidos(self) -> None:
        """Avisa a cada conexión KDS qué pedidos llevan >60s sin acuse.

        La conexión sigue "viva" para _cleanup_zombies (puede seguir
        respondiendo pings) pero un mensaje nunca acusado es indistinguible
        de uno perdido en tránsito — esto le da a la UI una señal para
        alertar en vez de confiar ciegamente en el feed de WS.
        """
        now = time.monotonic()
        for conn in self.connections.get("kds", []):
            vencidos = sorted(
                {
                    pedido_id
                    for _message_id, (sent_at, pedido_id) in conn.pending_acks.items()
                    if pedido_id is not None and (now - sent_at) > ACK_TIMEOUT_SECONDS
                }
            )
            if vencidos:
                logger.warning(
                    "KDS user=%s sin acuse >%ss para pedidos %s",
                    conn.user_id,
                    ACK_TIMEOUT_SECONDS,
                    vencidos,
                )
                await self._send_to_connection(
                    conn,
                    {
                        "type": "ack_timeout",
                        "data": {"pedido_ids": vencidos, "timestamp": get_mexico_now().isoformat()},
                    },
                )

    async def connect(
        self, websocket: WebSocket, client_type: str, user_id: int, user_role: str, sucursal_id: int
    ):
        """Registrar un cliente WebSocket ya aceptado y autenticado.

        PRECONDICIÓN: el caller ya hizo `await websocket.accept()`. El handshake
        se acepta antes de autenticar porque el token llega como primer mensaje
        de la conexión (ver `websocket_routes.websocket_endpoint`), no en el
        query string. Este método NO acepta la conexión.
        """
        try:
            # Validar que el rol tiene permisos para este tipo de cliente
            allowed_groups = self._get_allowed_groups(user_role)
            if client_type not in allowed_groups:
                await websocket.close(code=4003, reason="Unauthorized for this client type")
                return False

            connection_info = ConnectionInfo(websocket, user_id, user_role, sucursal_id)
            self.connections[client_type].append(connection_info)

            logger.info(
                f"WebSocket connected: user={user_id}, role={user_role}, type={client_type}, sucursal={sucursal_id}"
            )

            # Enviar mensaje de bienvenida
            await self._send_to_connection(
                connection_info,
                {
                    "type": "connection_established",
                    "data": {"client_type": client_type, "timestamp": get_mexico_now().isoformat()},
                },
            )

            return True

        except Exception as e:
            logger.error(f"Error connecting WebSocket: {e}")
            return False

    async def disconnect(self, websocket: WebSocket):
        """Desconectar un cliente WebSocket"""
        for client_type, connections in self.connections.items():
            self.connections[client_type] = [
                conn for conn in connections if conn.websocket != websocket
            ]
        logger.info("WebSocket disconnected")

    async def _send_to_connection(self, connection: ConnectionInfo, message: dict):
        """Enviar mensaje a una conexión específica"""
        try:
            await connection.websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.warning(f"Failed to send message to connection {connection.user_id}: {e}")
            return False

    async def _broadcast_to_group(
        self,
        client_type: str,
        message: dict,
        sucursal_id: Optional[int] = None,
        pedido_id: Optional[int] = None,
    ):
        """Enviar mensaje a todos los clientes de un grupo específico en paralelo.

        `pedido_id`: solo para client_type="kds" — adjunta un `message_id` al
        envelope y lo registra como pendiente de acuse en cada conexión a la
        que se envió con éxito (ver `ack_message` y `_cleanup_zombies`).
        """
        if client_type not in self.connections:
            return

        connections = self.connections[client_type]

        # Filtrar por sucursal si se especifica
        if sucursal_id is not None:
            connections = [conn for conn in connections if conn.sucursal_id == sucursal_id]

        if not connections:
            return

        message_id = None
        envelope = message
        if client_type == "kds" and pedido_id is not None:
            message_id = uuid.uuid4().hex
            envelope = {**message, "message_id": message_id}

        # Crear tareas para enviar simultáneamente usando asyncio.gather
        tasks = [self._send_to_connection(conn, envelope) for conn in connections]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Encontrar conexiones que fallaron y procesarlas
        failed_connections = []
        now = time.monotonic()
        for conn, success in zip(connections, results):
            if not success or isinstance(success, Exception):
                failed_connections.append(conn)
            elif message_id is not None:
                conn.pending_acks[message_id] = (now, pedido_id)

        # Limpiar conexiones fallidas
        for failed_conn in failed_connections:
            if failed_conn in self.connections[client_type]:
                self.connections[client_type].remove(failed_conn)

    def ack_message(self, websocket: WebSocket, message_id: str) -> None:
        """Registrar el acuse de un mensaje enviado a esta conexión."""
        for connections in self.connections.values():
            for conn in connections:
                if conn.websocket == websocket:
                    conn.pending_acks.pop(message_id, None)
                    return

    async def notify_pedido_created(self, pedido_data: dict):
        """Notificar creación de nuevo pedido"""
        message = {
            "type": "pedido_created",
            "data": {"pedido": pedido_data, "timestamp": get_mexico_now().isoformat()},
        }

        sucursal_id = pedido_data.get("sucursal_id")

        # Notificar a KDS (cocina ve nuevos pedidos)
        await self._broadcast_to_group("kds", message, sucursal_id, pedido_id=pedido_data.get("id"))

        # Notificar a CAJA (necesita ver todos los pedidos nuevos para overview)
        await self._broadcast_to_group("caja", message, sucursal_id)

        # Notificar a MESEROS (necesitan actualizar mesas ocupadas en tiempo real)
        await self._broadcast_to_group("mesero", message, sucursal_id)

        # Notificar a administradores
        await self._broadcast_to_group("admin", message, sucursal_id)

        logger.info(f"Notified pedido created: {pedido_data.get('id', 'unknown')}")

    async def notify_pedido_estado_changed(
        self, pedido_id: int, nuevo_estado: str, pedido_data: dict
    ):
        """Notificar cambio de estado de pedido"""
        message = {
            "type": "pedido_estado_changed",
            "data": {
                "pedido_id": pedido_id,
                "nuevo_estado": nuevo_estado,
                "pedido": pedido_data,
                "timestamp": get_mexico_now().isoformat(),
            },
        }

        sucursal_id = pedido_data.get("sucursal_id")

        # CAJA y MESERO necesitan VER TODOS los cambios para el overview y seguimiento completo
        await self._broadcast_to_group("caja", message, sucursal_id)
        await self._broadcast_to_group("mesero", message, sucursal_id)

        # Lógica de notificación específica por estado
        if nuevo_estado in ["pendiente", "preparando"]:
            # Notificar a cocina
            await self._broadcast_to_group("kds", message, sucursal_id, pedido_id=pedido_id)

        elif nuevo_estado == "listo":
            await self._broadcast_to_group("kds", message, sucursal_id, pedido_id=pedido_id)

        elif nuevo_estado == "entregado":
            await self._broadcast_to_group("kds", message, sucursal_id, pedido_id=pedido_id)

        elif nuevo_estado == "cuenta_solicitada":
            pass

        elif nuevo_estado == "pagado":
            # Notificar a todos (pedido completado)
            await self._broadcast_to_group("kds", message, sucursal_id, pedido_id=pedido_id)

        elif nuevo_estado == "cancelado":
            # Notificar a todos
            await self._broadcast_to_group("kds", message, sucursal_id, pedido_id=pedido_id)

        elif nuevo_estado == "dividido":
            # Notificar a todos para que retiren el pedido original
            await self._broadcast_to_group("kds", message, sucursal_id, pedido_id=pedido_id)

        # Siempre notificar a administradores
        await self._broadcast_to_group("admin", message, sucursal_id)

        logger.info(f"Notified pedido estado changed: {pedido_id} -> {nuevo_estado}")

    async def notify_articulo_estado_changed(
        self, pedido_id: int, articulo_id: int, nuevo_estado: str, pedido_data: dict
    ):
        """Notificar cambio de estado de artículo individual"""
        message = {
            "type": "articulo_estado_changed",
            "data": {
                "pedido_id": pedido_id,
                "articulo_id": articulo_id,
                "nuevo_estado": nuevo_estado,
                "pedido": pedido_data,
                "timestamp": get_mexico_now().isoformat(),
            },
        }

        sucursal_id = pedido_data.get("sucursal_id")

        # CAJA y MESERO necesitan ver progreso de artículos para overview completo
        await self._broadcast_to_group("caja", message, sucursal_id)
        await self._broadcast_to_group("mesero", message, sucursal_id)

        # Notificar principalmente a KDS y admin
        await self._broadcast_to_group("kds", message, sucursal_id, pedido_id=pedido_id)
        await self._broadcast_to_group("admin", message, sucursal_id)

        logger.info(
            f"Notified articulo estado changed: pedido={pedido_id}, articulo={articulo_id} -> {nuevo_estado}"
        )

    async def notify_print_ticket(self, pedido_data: dict):
        """Notificar solicitud de impresión manual de ticket"""
        message = {
            "type": "print_ticket",
            "data": {
                "pedido_id": pedido_data.get("id"),
                "pedido": pedido_data,
                "timestamp": get_mexico_now().isoformat(),
            },
        }
        sucursal_id = pedido_data.get("sucursal_id")
        # Enviar al grupo de caja para que el print_service local lo procese
        await self._broadcast_to_group("caja", message, sucursal_id)
        logger.info(
            f"Notified print ticket for order display #: {pedido_data.get('numero_display', 'N/A')}"
        )

    def get_connection_stats(self) -> dict:
        """Obtener estadísticas de conexiones activas"""
        stats = {}
        for client_type, connections in self.connections.items():
            stats[client_type] = {
                "total_connections": len(connections),
                "connections_by_role": {},
                "connections_by_sucursal": {},
            }

            for conn in connections:
                # Por rol
                role = conn.user_role
                if role not in stats[client_type]["connections_by_role"]:
                    stats[client_type]["connections_by_role"][role] = 0
                stats[client_type]["connections_by_role"][role] += 1

                # Por sucursal
                sucursal = conn.sucursal_id
                if sucursal not in stats[client_type]["connections_by_sucursal"]:
                    stats[client_type]["connections_by_sucursal"][sucursal] = 0
                stats[client_type]["connections_by_sucursal"][sucursal] += 1

        return stats


# Instancia global del manager
websocket_manager = WebSocketManager()
