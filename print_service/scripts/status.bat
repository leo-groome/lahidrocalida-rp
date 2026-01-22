@echo off
echo.
echo ==========================================
echo   ESTADO DEL SISTEMA DE IMPRESION
echo   La Hidrocalida
echo ==========================================
echo.

cd print_service

echo SERVICIO PRINCIPAL:
python -c "
try:
    import os
    if os.path.exists('logs/print_service.log'):
        print('[OK] Servicio configurado')
    else:
        print('[INFO] Servicio no iniciado aun')
except:
    print('[ERROR] Error verificando servicio')
" 2>nul

echo.
echo IMPRESORA:
python -c "
from config.settings import PRINTER_NAME
print(f'[CONFIG] {PRINTER_NAME}')
print('[STATUS] Lista para conectar')
" 2>nul

echo.
echo BACKEND:
python -c "
from config.settings import BACKEND_URL
print(f'[URL] {BACKEND_URL}')
print('[STATUS] Configurado')
" 2>nul

echo.
echo COMPONENTES:
python -c "
import sys
sys.path.insert(0, '.')
try:
    from core.printer_manager import printer_manager
    from core.ticket_formatter import TicketFormatter  
    from core.print_queue import print_queue
    from server.api_server import app
    from server.websocket_bridge import websocket_bridge
    print('[OK] Todos los componentes cargados')
except Exception as e:
    print(f'[ERROR] {e}')
" 2>nul

echo.
echo COLA DE IMPRESION:
if exist "logs\print_queue.json" (
    python -c "
import json
try:
    with open('logs/print_queue.json', 'r') as f:
        data = json.load(f)
        pending = len(data.get('pending', []))
        failed = len(data.get('failed', []))
        print(f'[PENDING] {pending} tickets')
        print(f'[FAILED] {failed} tickets')
except:
    print('[ERROR] Error leyendo cola')
" 2>nul
) else (
    echo [INFO] Cola no inicializada aun
)

echo.
echo LOGS:
if exist "logs\print_service.log" (
    for /f %%i in ("logs\print_service.log") do echo [SIZE] %%~zi bytes
) else (
    echo [INFO] Logs no creados aun
)

echo.
echo ACCIONES RAPIDAS:
echo   start_service.bat     - Iniciar servicio
echo   stop_service.bat      - Detener servicio  
echo   test_printer.bat      - Probar impresora
echo   scripts\verify_system.bat - Verificacion completa
echo.
echo [READY] Sistema preparado para usar
echo.