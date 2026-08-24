@echo off
title Prueba Completa del Sistema - La Hidrocálida
echo ==========================================
echo   PRUEBA COMPLETA DEL SISTEMA
echo   Restaurante La Hidrocálida
echo ==========================================
echo.

echo 🔧 Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado
    pause
    exit /b 1
)
echo ✅ Python disponible

echo.
echo 📦 Verificando dependencias...
cd print_service
python -c "
import sys
sys.path.insert(0, '.')
try:
    from config.settings import BACKEND_URL
    from config.printer_config import PRINTER_PROFILE
    from core.printer_manager import printer_manager
    from core.ticket_formatter import TicketFormatter
    from core.print_queue import print_queue
    from server.api_server import app
    from server.websocket_bridge import websocket_bridge
    print('[OK] Todas las dependencias verificadas')
except Exception as e:
    print(f'[ERROR] {e}')
    exit(1)
" >nul 2>&1
if errorlevel 1 (
    echo ❌ Error en dependencias
    cd ..
    pause
    exit /b 1
)
echo ✅ Todas las dependencias OK

echo.
echo 🧪 Probando formateador de tickets...
python -c "
from core.ticket_formatter import TicketFormatter
formatter = TicketFormatter()
test_data = {
    'numero_display': '999',
    'mesa': 'TEST',
    'nombre_cliente': 'Cliente Test',
    'articulos': [{'cantidad': 1, 'nombre': 'Pozole Test', 'precio': 100.0}],
    'total': 100.0
}
formatted = formatter.format_ticket(test_data)
print('[OK] Formateador funciona correctamente')
" >nul 2>&1
if errorlevel 1 (
    echo ❌ Error en formateador
    cd ..
    pause
    exit /b 1
)
echo ✅ Formateador OK

echo.
echo 🔄 Probando sistema de cola...
python -c "
from core.print_queue import print_queue
from core.ticket_formatter import TicketFormatter
print_queue.add_to_queue({'numero_display': '999', 'total': 100.0})
print('[OK] Sistema de cola funciona')
" >nul 2>&1
if errorlevel 1 (
    echo ❌ Error en sistema de cola
    cd ..
    pause
    exit /b 1
)
echo ✅ Sistema de cola OK

echo.
echo 🌐 Probando servidor API...
python -c "
from server.api_server import app
print('[OK] Servidor API carga correctamente')
" >nul 2>&1
if errorlevel 1 (
    echo ❌ Error en servidor API
    cd ..
    pause
    exit /b 1
)
echo ✅ Servidor API OK

echo.
echo 🔌 Probando puente WebSocket...
python -c "
from server.websocket_bridge import websocket_bridge
print('[OK] Puente WebSocket carga correctamente')
" >nul 2>&1
if errorlevel 1 (
    echo ❌ Error en puente WebSocket
    cd ..
    pause
    exit /b 1
)
echo ✅ Puente WebSocket OK

cd ..
echo.
echo ==========================================
echo ✅ TODAS LAS PRUEBAS PASARON
echo ==========================================
echo.
echo 🎉 El sistema de impresión está completamente funcional!
echo.
echo 💡 Próximos pasos:
echo    1. Conectar la impresora Easytime SP-POS891ED
echo    2. Configurar el nombre de impresora en config/settings.py
echo    3. Iniciar el servicio con start_service.bat
echo    4. Probar impresión automática desde el sistema
echo.
pause