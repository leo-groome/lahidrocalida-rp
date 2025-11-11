from typing import Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

class ConnectionInfo:
    def __init__(self, websocket: WebSocket, user_id: int, user_role: str, sucursal_id: int):
        self.websocket = websocket
        self.user_id = user_id
        self.user_role = user_role
        self.sucursal_id = sucursal_id
        self.connected_at = datetime.now()
        self.last_ping = datetime.now()

class WebSocketManager:
    def __init__(self):
        # Organizar conexiones por tipo de cliente
        self.connections: Dict[str, List[ConnectionInfo]] = {
            "kds": [],      # Kitchen Display System
            "caja": [],     # Cashier/Point of Sale
            "mesero": [],   # Waiters
            "admin": []     # Administrators (receive all updates)
        }
        
        # Mapeo de roles a grupos permitidos
        self.role_to_groups = {
            "cocina": ["kds"],
            "cajero": ["caja"],
            "mesero": ["mesero"],
            "administrador": ["kds", "caja", "mesero", "admin"]
        }
    
    def _get_allowed_groups(self, user_role: str) -> List[str]:
        """Obtiene los grupos permitidos para un rol específico"""
        return self.role_to_groups.get(user_role, [])
    
    async def connect(self, websocket: WebSocket, client_type: str, user_id: int, user_role: str, sucursal_id: int):
        """Conectar un nuevo cliente WebSocket"""
        try:
            # Validar que el rol tiene permisos para este tipo de cliente
            allowed_groups = self._get_allowed_groups(user_role)
            if client_type not in allowed_groups:
                await websocket.close(code=4003, reason="Unauthorized for this client type")
                return False
            
            await websocket.accept()
            
            connection_info = ConnectionInfo(websocket, user_id, user_role, sucursal_id)
            self.connections[client_type].append(connection_info)
            
            logger.info(f"WebSocket connected: user={user_id}, role={user_role}, type={client_type}, sucursal={sucursal_id}")
            
            # Enviar mensaje de bienvenida
            await self._send_to_connection(connection_info, {
                "type": "connection_established",
                "data": {
                    "client_type": client_type,
                    "timestamp": datetime.now().isoformat()
                }
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket: {e}")
            return False
    
    async def disconnect(self, websocket: WebSocket):
        """Desconectar un cliente WebSocket"""
        for client_type, connections in self.connections.items():
            self.connections[client_type] = [
                conn for conn in connections 
                if conn.websocket != websocket
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
    
    async def _broadcast_to_group(self, client_type: str, message: dict, sucursal_id: Optional[int] = None):
        """Enviar mensaje a todos los clientes de un grupo específico"""
        if client_type not in self.connections:
            return
        
        connections = self.connections[client_type]
        
        # Filtrar por sucursal si se especifica
        if sucursal_id is not None:
            connections = [conn for conn in connections if conn.sucursal_id == sucursal_id]
        
        # Enviar a todas las conexiones válidas
        failed_connections = []
        for connection in connections:
            success = await self._send_to_connection(connection, message)
            if not success:
                failed_connections.append(connection)
        
        # Limpiar conexiones fallidas
        for failed_conn in failed_connections:
            if failed_conn in self.connections[client_type]:
                self.connections[client_type].remove(failed_conn)
    
    async def notify_pedido_created(self, pedido_data: dict):
        """Notificar creación de nuevo pedido"""
        message = {
            "type": "pedido_created",
            "data": {
                "pedido": pedido_data,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        sucursal_id = pedido_data.get("sucursal_id")
        
        # Notificar a KDS (cocina ve nuevos pedidos)
        await self._broadcast_to_group("kds", message, sucursal_id)
        
        # Notificar a CAJA (necesita ver todos los pedidos nuevos para overview)
        await self._broadcast_to_group("caja", message, sucursal_id)
        
        # Notificar a administradores
        await self._broadcast_to_group("admin", message, sucursal_id)
        
        logger.info(f"Notified pedido created: {pedido_data.get('id', 'unknown')}")
    
    async def notify_pedido_estado_changed(self, pedido_id: int, nuevo_estado: str, pedido_data: dict):
        """Notificar cambio de estado de pedido"""
        message = {
            "type": "pedido_estado_changed",
            "data": {
                "pedido_id": pedido_id,
                "nuevo_estado": nuevo_estado,
                "pedido": pedido_data,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        sucursal_id = pedido_data.get("sucursal_id")
        
        # CAJA necesita VER TODOS los cambios para el overview y seguimiento completo
        await self._broadcast_to_group("caja", message, sucursal_id)
        
        # Lógica de notificación específica por estado
        if nuevo_estado in ["pendiente", "preparando"]:
            # Notificar a cocina
            await self._broadcast_to_group("kds", message, sucursal_id)
        
        elif nuevo_estado == "listo":
            # Notificar a meseros (para que sepan que pueden entregar)
            await self._broadcast_to_group("mesero", message, sucursal_id)
            await self._broadcast_to_group("kds", message, sucursal_id)
        
        elif nuevo_estado == "entregado":
            # Notificar a meseros y KDS
            await self._broadcast_to_group("kds", message, sucursal_id)
            await self._broadcast_to_group("mesero", message, sucursal_id)
        
        elif nuevo_estado == "cuenta_solicitada":
            # Notificar a meseros (ya notificado a caja arriba)
            await self._broadcast_to_group("mesero", message, sucursal_id)
        
        elif nuevo_estado == "pagado":
            # Notificar a todos (pedido completado)
            await self._broadcast_to_group("kds", message, sucursal_id)
            await self._broadcast_to_group("mesero", message, sucursal_id)
        
        elif nuevo_estado == "cancelado":
            # Notificar a todos
            await self._broadcast_to_group("kds", message, sucursal_id)
            await self._broadcast_to_group("mesero", message, sucursal_id)
        
        # Siempre notificar a administradores
        await self._broadcast_to_group("admin", message, sucursal_id)
        
        logger.info(f"Notified pedido estado changed: {pedido_id} -> {nuevo_estado}")
    
    async def notify_articulo_estado_changed(self, pedido_id: int, articulo_id: int, nuevo_estado: str, pedido_data: dict):
        """Notificar cambio de estado de artículo individual"""
        message = {
            "type": "articulo_estado_changed",
            "data": {
                "pedido_id": pedido_id,
                "articulo_id": articulo_id,
                "nuevo_estado": nuevo_estado,
                "pedido": pedido_data,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        sucursal_id = pedido_data.get("sucursal_id")
        
        # CAJA necesita ver progreso de artículos para overview completo
        await self._broadcast_to_group("caja", message, sucursal_id)
        
        # Notificar principalmente a KDS y admin
        await self._broadcast_to_group("kds", message, sucursal_id)
        await self._broadcast_to_group("admin", message, sucursal_id)
        
        # Si todos los artículos están listos, también notificar a meseros
        if nuevo_estado == "listo":
            await self._broadcast_to_group("mesero", message, sucursal_id)
        
        logger.info(f"Notified articulo estado changed: pedido={pedido_id}, articulo={articulo_id} -> {nuevo_estado}")
    
    def get_connection_stats(self) -> dict:
        """Obtener estadísticas de conexiones activas"""
        stats = {}
        for client_type, connections in self.connections.items():
            stats[client_type] = {
                "total_connections": len(connections),
                "connections_by_role": {},
                "connections_by_sucursal": {}
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