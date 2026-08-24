@echo off
title Prueba de Impresora - La Hidrocálida
echo ==========================================
echo   PRUEBA DE IMPRESORA
echo   Restaurante La Hidrocálida
echo ==========================================
echo.

echo 🔧 Verificando si Python está disponible...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado
    echo Por favor instale Python desde https://python.org
    pause
    exit /b 1
)
echo ✅ Python disponible

echo.
echo 🖨️  Ejecutando prueba de impresión...
python -c "
from core.printer_manager import printer_manager
success = printer_manager.test_printer()
if success:
    print('✅ Prueba de impresión exitosa')
else:
    print('❌ Prueba de impresión fallida')
    print('   Verifique que la impresora esté conectada')
    print('   Revise los logs en logs/print_service.log')
"
echo.
echo 💡 Si la prueba falló:
echo    - Verifique que la impresora esté conectada
echo    - Revise el nombre de la impresora en config/settings.py
echo    - Consulte los logs en logs/print_service.log

pause