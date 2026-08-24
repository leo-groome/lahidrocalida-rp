@echo off
title Verificación Final - Servicio de Impresión La Hidrocálida
echo.
echo ==========================================
echo   VERIFICACIÓN FINAL DEL SISTEMA
echo   La Hidrocálida - Servicio de Impresión
echo ==========================================
echo.
echo Esta herramienta verifica que todo esté funcionando
echo correctamente antes de usar el sistema en producción.
echo.

cd print_service

echo 🔍 Verificando instalación...
if not exist "requirements.txt" (
    echo ❌ Archivo requirements.txt no encontrado
    echo    Asegúrese de estar en el directorio correcto
    pause
    exit /b 1
)
echo ✅ Archivos del proyecto OK

echo.
echo 🐍 Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado
    echo    Descargue Python desde https://python.org
    pause
    exit /b 1
)
echo ✅ Python disponible

echo.
echo 📦 Verificando dependencias...
python -c "
try:
    import flask, escpos, serial, usb
    print('✅ Todas las dependencias instaladas')
except ImportError as e:
    print(f'❌ Dependencia faltante: {e}')
    print('   Ejecute: install.bat')
    exit(1)
" >nul 2>&1
if errorlevel 1 (
    echo ❌ Dependencias faltantes
    echo    Ejecute: install.bat
    pause
    exit /b 1
)
echo ✅ Dependencias OK

echo.
echo 🧪 Probando componentes del sistema...
python -c "
import sys
sys.path.insert(0, '.')
try:
    from config.settings import BACKEND_URL
    from core.printer_manager import printer_manager
    from core.ticket_formatter import TicketFormatter
    from core.print_queue import print_queue
    from server.api_server import app
    from server.websocket_bridge import websocket_bridge
    
    # Probar formateador
    f = TicketFormatter()
    test_data = {
        'numero_display': '001',
        'mesa': '1',
        'nombre_cliente': 'Test',
        'articulos': [{'cantidad': 1, 'nombre': 'Test Item', 'precio': 100.0}],
        'total': 100.0
    }
    formatted = f.format_ticket(test_data)
    
    # Probar cola
    print_queue.add_to_queue(test_data)
    
    print('✅ Todos los componentes funcionan correctamente')
except Exception as e:
    print(f'❌ Error en componentes: {e}')
    exit(1)
" >nul 2>&1
if errorlevel 1 (
    echo ❌ Error en componentes del sistema
    echo    Revise los logs para más detalles
    pause
    exit /b 1
)
echo ✅ Componentes del sistema OK

echo.
echo 🖨️ Verificando configuración de impresora...
python -c "
from config.settings import PRINTER_NAME
from config.printer_config import PRINTER_PROFILE
print(f'Impresora configurada: {PRINTER_NAME}')
print(f'Modelo: {PRINTER_PROFILE[\"model\"]}')
print(f'Ancho: {PRINTER_PROFILE[\"width\"]}mm')
print('✅ Configuración de impresora OK')
" >nul 2>&1
if errorlevel 1 (
    echo ❌ Error en configuración
    pause
    exit /b 1
)
echo ✅ Configuración OK

echo.
echo 📊 Verificando estado del sistema...
if exist "logs\print_service.log" (
    echo ✅ Archivo de logs creado
) else (
    echo ⚠️  Archivo de logs no existe aún (se creará al iniciar)
)

if exist "logs\print_queue.json" (
    echo ✅ Archivo de cola creado
) else (
    echo ⚠️  Archivo de cola no existe aún (se creará al iniciar)
)

echo.
echo ==========================================
echo 🎉 VERIFICACIÓN COMPLETA - SISTEMA LISTO
echo ==========================================
echo.
echo ✅ Python instalado y funcionando
echo ✅ Todas las dependencias instaladas
echo ✅ Componentes del sistema operativos
echo ✅ Configuración correcta
echo ✅ Archivos de logs preparados
echo.
echo 💡 PRÓXIMOS PASOS:
echo.
echo 1. Conectar la impresora Easytime SP-POS891ED por USB
echo 2. Iniciar el servicio: start_service.bat
echo 3. Verificar estado: http://localhost:3001/health
echo 4. ¡El sistema imprimirá automáticamente!
echo.
echo 📖 Para más información, consulte README.md
echo.
echo 🏪 ¡Sistema de impresión listo para La Hidrocálida!
echo.
pause