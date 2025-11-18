@echo off
title Detener Servicio - La Hidrocálida
echo ==========================================
echo   DETENIENDO SERVICIO DE IMPRESIÓN
echo ==========================================
echo.

echo 🔍 Buscando procesos del servicio de impresión...
tasklist | find "python.exe" >nul
if errorlevel 1 (
    echo ℹ️ No hay procesos Python ejecutándose
    echo.
    goto :end
)

echo 📋 Procesos Python encontrados:
tasklist | find "python.exe"
echo.

echo 🛑 Deteniendo servidor de impresión...
taskkill /f /im python.exe >nul 2>&1
if errorlevel 1 (
    echo ⚠️ No se pudieron detener algunos procesos
) else (
    echo ✅ Procesos detenidos
)

echo.
echo 🔍 Verificando puerto 3001...
timeout /t 2 /nobreak >nul
netstat -an | find "3001" >nul
if errorlevel 1 (
    echo ✅ Puerto 3001 liberado
) else (
    echo ⚠️ Puerto 3001 aún en uso
)

:end
echo.
echo ==========================================
echo ✅ SERVICIO DETENIDO
echo ==========================================
echo.
echo Para iniciar nuevamente:
echo    start_print_service.bat
echo.
pause