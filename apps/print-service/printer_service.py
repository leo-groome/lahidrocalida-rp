#!/usr/bin/env python3
"""
Servicio de impresión principal para La Hidrocálida
"""
import os
import sys
import logging

# Cargar variables de entorno desde archivo .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config.settings import LOG_FILE, LOG_LEVEL
from server.websocket_bridge import websocket_bridge
from server.api_server import app
from core.printer_manager import printer_manager
from core.print_queue import print_queue

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Punto de entrada principal del servicio de impresión"""
    print("[START] Iniciando servicio de impresion La Hidrocalida...")

    try:
        # Deshabilitado puente WS (las peticiones de impresión las realiza directamente la aplicación cliente)
        # websocket_bridge.start()

        # Iniciar servidor API
        print("[API] Servicio disponible en: http://localhost:3001")
        print("[HEALTH] Health check: http://localhost:3001/health")
        print("[PRINT] Impresion: POST http://localhost:3001/print")
        print("[STOP] Presiona Ctrl+C para detener")

        # Ejecutar servidor Flask
        app.run(host='localhost', port=3001, debug=False)

    except KeyboardInterrupt:
        print("\n[BYE] Servicio de impresion detenido por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"[FATAL] Error fatal en el servicio: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()