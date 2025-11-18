@echo off
title Inicio Rápido - La Hidrocálida
color 0A
echo ==========================================
echo   LA HIDROCÁLIDA - SISTEMA DE IMPRESIÓN
echo ==========================================
echo.

echo 🚀 INICIO RÁPIDO DEL SERVICIO
echo.
echo Seleccione una opción:
echo.
echo [1] Iniciar servicio de impresión
echo [2] Probar conexión y impresión  
echo [3] Detener servicio
echo [4] Ver estado del servicio
echo [5] Reinstalar dependencias
echo [6] Salir
echo.
set /p "opcion=Ingrese su opción (1-6): "

if "%opcion%"=="1" goto :iniciar
if "%opcion%"=="2" goto :probar
if "%opcion%"=="3" goto :detener
if "%opcion%"=="4" goto :estado
if "%opcion%"=="5" goto :reinstalar
if "%opcion%"=="6" goto :salir
goto :error

:iniciar
echo.
echo 🚀 Iniciando servicio de impresión...
start "Servicio La Hidrocálida" start_print_service.bat
echo ✅ Servicio iniciado en nueva ventana
echo.
goto :menu_continuar

:probar
echo.
echo 🧪 Ejecutando pruebas...
call test_connection.bat
goto :menu_continuar

:detener
echo.
echo 🛑 Deteniendo servicio...
call stop_print_service.bat
goto :menu_continuar

:estado
echo.
echo 📊 ESTADO DEL SERVICIO
echo ----------------------
echo.
netstat -an | find "3001" >nul
if errorlevel 1 (
    echo ❌ Servicio NO está ejecutándose
    echo.
    echo Para iniciar: Opción 1
) else (
    echo ✅ Servicio está ejecutándose en puerto 3001
    echo.
    echo Verificando respuesta...
    curl -s http://localhost:3001/health >nul 2>&1
    if errorlevel 1 (
        echo ⚠️ Puerto ocupado pero servicio no responde
    ) else (
        echo ✅ Servicio funcionando correctamente
    )
)
echo.
tasklist | find "python.exe" >nul
if not errorlevel 1 (
    echo 📋 Procesos Python activos:
    tasklist | find "python.exe"
)
echo.
goto :menu_continuar

:reinstalar
echo.
echo 🔄 Reinstalando dependencias...
call install.bat
goto :menu_continuar

:error
echo.
echo ❌ Opción inválida. Por favor seleccione 1-6.
echo.
timeout /t 2 /nobreak >nul
goto :inicio_rapido

:menu_continuar
echo.
echo ¿Qué desea hacer ahora?
echo.
echo [1] Volver al menú principal
echo [2] Salir
echo.
set /p "continuar=Seleccione (1-2): "
if "%continuar%"=="1" (
    cls
    goto :inicio_rapido
)
goto :salir

:inicio_rapido
cls
echo ==========================================
echo   LA HIDROCÁLIDA - SISTEMA DE IMPRESIÓN
echo ==========================================
echo.

echo 🚀 INICIO RÁPIDO DEL SERVICIO
echo.
echo Seleccione una opción:
echo.
echo [1] Iniciar servicio de impresión
echo [2] Probar conexión y impresión  
echo [3] Detener servicio
echo [4] Ver estado del servicio
echo [5] Reinstalar dependencias
echo [6] Salir
echo.
set /p "opcion=Ingrese su opción (1-6): "

if "%opcion%"=="1" goto :iniciar
if "%opcion%"=="2" goto :probar
if "%opcion%"=="3" goto :detener
if "%opcion%"=="4" goto :estado
if "%opcion%"=="5" goto :reinstalar
if "%opcion%"=="6" goto :salir
goto :error

:salir
echo.
echo 👋 ¡Hasta luego!
echo.
echo Para usar el sistema:
echo 1. Asegúrate que el servicio esté ejecutándose
echo 2. Abre el navegador con el sistema de caja
echo 3. Los tickets se imprimirán automáticamente
echo.
pause
exit