@echo off
title Iniciar Servicio de Impresión - La Hidrocálida
echo ==========================================
echo   INICIAR SERVICIO DE IMPRESIÓN
echo   Restaurante La Hidrocálida
echo ==========================================
echo.

echo 🔧 Verificando si Python está disponible...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado
    echo Por favor instale Python desde https://python.org
    echo Asegúrese de marcar "Add to PATH" durante la instalación
    pause
    exit /b 1
)
echo ✅ Python disponible

echo.
echo 🚀 Iniciando servicio de impresión...
echo.
echo Acceda a la siguiente URL para verificar el estado:
echo http://localhost:3001/health
echo.
echo Para detener el servicio, presione Ctrl+C

python printer_service.py