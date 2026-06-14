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
            from config.settings import TOKEN
            url = self.websocket_url
            if TOKEN:
                if "?" in url:
                    url += f"&token={TOKEN}"
                else:
                    url += f"?token={TOKEN}"
            
            # Ocultar token en los logs por seguridad
            log_url = url.split("token=")[0] + "token=***" if TOKEN else url
            print(f"[CONNECT] Conectando a WebSocket: {log_url}")
            
            self.websocket = await websockets.connect(url)
            print("[OK] Conectado al WebSocket del backend")
            return True
        except Exception as e:
            print(f"[ERROR] Error de conexion WebSocket: {e}")
            self.websocket = None
            return False

    async def listen(self):
        """Escucha mensajes del WebSocket y maneja la reconexión"""
        while self.is_running:
            try:
                if not self.websocket or self.websocket.closed:
                    success = await self.connect()
                    if not success:
                        await asyncio.sleep(5)
                        continue
                
                message = await self.websocket.recv()
                await self.handle_message(message)
            except websockets.exceptions.ConnectionClosed:
                print("[WARN] Conexión de WebSocket cerrada. Intentando reconectar en 5 segundos...")
                self.websocket = None
                await asyncio.sleep(5)
            except Exception as e:
                print(f"[ERROR] Error escuchando WebSocket: {e}")
                self.websocket = None
                await asyncio.sleep(5)

    async def handle_message(self, message):
        """
        Maneja un mensaje recibido del WebSocket
        """
        try:
            data = json.loads(message)
            event_type = data.get('type')

            if event_type == 'pedido_estado_changed':
                event_data = data.get('data', {})
                nuevo_estado = event_data.get('nuevo_estado')
                if nuevo_estado == 'cuenta_solicitada':
                    pedido = event_data.get('pedido', {})
                    print(f"[PRINT] Solicitud de impresión automática para pedido #{pedido.get('numero_display', 'N/A')}")
                    self.queue_and_print(pedido)

            elif event_type == 'print_ticket':
                event_data = data.get('data', {})
                pedido = event_data.get('pedido', {})
                print(f"[PRINT] Solicitud de impresión manual para pedido #{pedido.get('numero_display', 'N/A')}")
                self.queue_and_print(pedido)

        except json.JSONDecodeError:
            print("[WARN] Mensaje no valido JSON")
        except Exception as e:
            print(f"[ERROR] Error manejando mensaje: {e}")

    def queue_and_print(self, pedido_data):
        """Agrega el pedido a la cola y procesa la impresión"""
        try:
            if not pedido_data:
                print("[WARN] Datos del pedido vacíos, ignorando impresión")
                return
            # Agregar a la cola de impresión
            print_queue.add_to_queue(pedido_data)
            # Procesar cola inmediatamente
            print_queue.process_queue(printer_manager)
        except Exception as e:
            print(f"[ERROR] Error al encolar/imprimir ticket: {e}")

    def start(self):
        """Inicia el puente WebSocket en un hilo separado"""
        def run():
            try:
                # Crear nuevo bucle de eventos para este hilo
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                self.is_running = True
                # Ejecutar la escucha persistente
                loop.run_until_complete(self.listen())
            except Exception as e:
                print(f"[ERROR] Error en hilo WebSocket: {e}")

        # Iniciar en hilo separado
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        print("[START] Puente WebSocket iniciado")

# Instancia global del puente WebSocket
websocket_bridge = WebSocketBridge()