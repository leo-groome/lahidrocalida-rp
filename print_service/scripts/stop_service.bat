@echo off
title Detener Servicio de Impresión - La Hidrocálida
echo ==========================================
echo   DETENER SERVICIO DE IMPRESIÓN
echo   Restaurante La Hidrocálida
echo ==========================================
echo.

echo 🔍 Buscando procesos de Python relacionados...
for /f "tokens=2" %%i in ('tasklist ^| findstr python') do (
    echo Deteniendo proceso PID: %%i
    taskkill /PID %%i /F >nul 2>&1
)

echo.
echo ✅ Servicio de impresión detenido
echo.
echo 💡 Para reiniciar el servicio:
echo    - Ejecute start_service.bat
echo    - O use: python printer_service.py

pause