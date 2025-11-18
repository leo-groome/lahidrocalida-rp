@echo off
echo ========================================
echo   INSTALADOR LA HIDROCALIDA - IMPRESION
echo ========================================
echo.

echo [1/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado. Instalando Python...
    echo Por favor descarga e instala Python desde: https://python.org
    pause
    exit /b 1
) else (
    echo ✅ Python encontrado
)

echo.
echo [2/4] Instalando dependencias...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Error instalando dependencias
    pause
    exit /b 1
) else (
    echo ✅ Dependencias instaladas
)

echo.
echo [3/4] Creando archivos de control...
echo @echo off > start_print_service.bat
echo title Servicio de Impresion - La Hidrocalida >> start_print_service.bat
echo echo ======================================== >> start_print_service.bat
echo echo   SERVICIO DE IMPRESION - LA HIDROCALIDA >> start_print_service.bat
echo echo ======================================== >> start_print_service.bat
echo echo. >> start_print_service.bat
echo echo Verificando puerto 3001... >> start_print_service.bat
echo netstat -an ^| find "3001" ^>nul >> start_print_service.bat
echo if not errorlevel 1 ^( >> start_print_service.bat
echo     echo Cerrando servicio anterior... >> start_print_service.bat
echo     taskkill /f /im python.exe ^>nul 2^>^&1 >> start_print_service.bat
echo     timeout /t 2 /nobreak ^>nul >> start_print_service.bat
echo ^) >> start_print_service.bat
echo echo Iniciando servidor en puerto 3001... >> start_print_service.bat
echo echo Endpoint: http://localhost:3001 >> start_print_service.bat
echo echo Presiona Ctrl+C para detener >> start_print_service.bat
echo echo. >> start_print_service.bat
echo python print_server.py >> start_print_service.bat
echo pause >> start_print_service.bat

echo ✅ Acceso directo creado: start_print_service.bat

echo.
echo [4/4] Probando servicio...
echo Iniciando servicio de prueba (se cerrará en 5 segundos)...
timeout /t 5 /nobreak >nul
start /min python print_server.py
timeout /t 3 /nobreak >nul
taskkill /f /im python.exe >nul 2>&1

echo.
echo ========================================
echo ✅ INSTALACION COMPLETADA
echo ========================================
echo.
echo Para usar el servicio:
echo 1. Conecta la impresora térmica
echo 2. Ejecuta: start_print_service.bat
echo 3. Abre el navegador con el sistema
echo.
echo El servicio estará en: http://localhost:3001
echo ========================================
pause