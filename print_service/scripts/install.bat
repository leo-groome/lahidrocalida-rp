@echo off
title Instalación del Servicio de Impresión - La Hidrocálida
echo ==========================================
echo   INSTALACIÓN DEL SERVICIO DE IMPRESIÓN
echo   Restaurante La Hidrocálida
echo ==========================================
echo.

echo 🔧 Verificando requisitos previos...
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
echo 📦 Instalando dependencias...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ❌ Error instalando dependencias
    pause
    exit /b 1
)
echo ✅ Dependencias instaladas

echo.
echo 📁 Creando directorios necesarios...
if not exist "logs" mkdir logs
echo ✅ Directorios creados

echo.
echo 🖨️  Configurando impresora por defecto...
echo Configurando impresora "Generic / Text Only" como predeterminada
echo Si desea usar otra impresora, modifique config/settings.py
echo.

echo 🎉 Instalación completada exitosamente!
echo.
echo 💡 Para iniciar el servicio:
echo    1. Ejecute start_service.bat
echo    2. O use: python printer_service.py
echo.
echo 📋 Siguientes pasos:
echo    - Configure el nombre de su impresora en config/settings.py
echo    - Verifique que la impresora esté conectada
echo    - Pruebe con test_printer.bat

pause