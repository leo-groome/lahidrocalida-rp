"""
Puente WebSocket para integración automática con el backend
"""
import asyncio
import websockets
import json
import threading
from datetime import datetime
from config.settings import WEBSOCKET_URL
from core.printer_manager import printer_manager
from core.print_queue import print_queue

class WebSocketBridge:
    def __init__(self, websocket_url=None):
        """
        Inicializa el puente WebSocket

        Args:
            websocket_url (str): URL del WebSocket del backend
        """
        self.websocket_url = websocket_url or WEBSOCKET_URL
        self.is_running = False
        self.websocket = None

    async def connect(self):
        """Conecta al WebSocket del backend"""
        try:
            print(f"[CONNECT] Conectando a WebSocket: {self.websocket_url}")
            self.websocket = await websockets.connect(self.websocket_url)
            self.is_running = True
            print("[OK] Conectado al WebSocket del backend")
        except Exception as e:
            print(f"[ERROR] Error de conexion WebSocket: {e}")
            self.is_running = False

    async def listen(self):
        """Escucha mensajes del WebSocket"""
        try:
            while self.is_running and self.websocket:
                message = await self.websocket.recv()
                await self.handle_message(message)
        except Exception as e:
            print(f"[ERROR] Error escuchando WebSocket: {e}")

    async def handle_message(self, message):
        """
        Maneja un mensaje recibido del WebSocket

        Args:
            message (str): Mensaje JSON recibido
        """
        try:
            data = json.loads(message)
            print(f"[MSG] Mensaje recibido: {data}")

            # Verificar si es un evento de cambio de estado
            if isinstance(data, dict) and 'type' in data:
                if data['type'] == 'pedido_status_changed':
                    await self.handle_pedido_status_change(data)

        except json.JSONDecodeError:
            print("[WARN] Mensaje no valido JSON")
        except Exception as e:
            print(f"[ERROR] Error manejando mensaje: {e}")

    async def handle_pedido_status_change(self, data):
        """
        Maneja el cambio de estado de un pedido

        Args:
            data (dict): Datos del evento
        """
        try:
            # Verificar si el estado es 'cuenta_solicitada'
            if data.get('estado') == 'cuenta_solicitada':
                pedido_data = data.get('pedido', {})
                print(f"[PRINT] Solicitud de impresion para pedido #{pedido_data.get('numero_display', 'N/A')}")

                # Agregar a la cola de impresión
                print_queue.add_to_queue(pedido_data)

                # Procesar cola inmediatamente
                print_queue.process_queue(printer_manager)

        except Exception as e:
            print(f"[ERROR] Error manejando cambio de estado: {e}")

    def start(self):
        """Inicia el puente WebSocket en un hilo separado"""
        def run():
            try:
                # Crear nuevo bucle de eventos para este hilo
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Ejecutar conexión
                loop.run_until_complete(self.connect())
            except Exception as e:
                print(f"[ERROR] Error en hilo WebSocket: {e}")

        # Iniciar en hilo separado
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        print("[START] Puente WebSocket iniciado")

# Instancia global del puente WebSocket
websocket_bridge = WebSocketBridge()