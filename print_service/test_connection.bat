@echo off
title Test de Conexión - La Hidrocálida
echo ==========================================
echo   TEST DE SERVICIO DE IMPRESIÓN
echo ==========================================
echo.

echo 🔍 Verificando si Python está disponible...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado
    echo Por favor instala Python desde https://python.org
    pause
    exit /b 1
)
echo ✅ Python disponible

echo.
echo 🔍 Verificando si el servicio está ejecutándose...
netstat -an | find "3001" >nul
if errorlevel 1 (
    echo ❌ Servicio no está ejecutándose en puerto 3001
    echo.
    echo 💡 SOLUCIÓN:
    echo 1. Ejecuta: start_print_service.bat
    echo 2. Espera a ver "Running on http://localhost:3001"
    echo 3. Vuelve a ejecutar este test
    echo.
    pause
    exit /b 1
)
echo ✅ Servicio ejecutándose en puerto 3001

echo.
echo 🧪 Ejecutando test de conexión...
python test_connection.py
if errorlevel 1 (
    echo.
    echo ❌ Test falló - revisar configuración
    pause
    exit /b 1
)

echo.
echo ==========================================
echo ✅ TODAS LAS PRUEBAS PASARON
echo ==========================================
echo.
echo 🎉 El servicio de impresión está listo!
echo    Puedes usar el sistema de caja normalmente.
echo.
pause