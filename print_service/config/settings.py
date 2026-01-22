import os
from pathlib import Path

# Directorio base del servicio de impresión
BASE_DIR = Path(__file__).resolve().parent.parent

# Configuración del backend
BACKEND_URL = "http://localhost:8000"  # URL por defecto del backend
WEBSOCKET_URL = "ws://localhost:8000/ws/orders"  # WebSocket para eventos de pedidos

# Configuración de impresión
PRINTER_TYPE = "win32"  # Tipo de impresora (win32, serial, network, etc.)
PRINTER_NAME = "Generic / Text Only"  # Nombre de la impresora por defecto

# Configuración de cola de impresión
MAX_RETRY_ATTEMPTS = 5
RETRY_INTERVAL_SECONDS = 30

# Configuración de logs
LOG_LEVEL = "INFO"
LOG_FILE = os.path.join(BASE_DIR, "logs", "print_service.log")

# Configuración del dashboard
DASHBOARD_PORT = 3002
DASHBOARD_HOST = "localhost"