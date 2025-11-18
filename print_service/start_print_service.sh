#!/bin/bash

echo "🖨️ Iniciando Servicio de Impresión - La Hidrocálida"
echo "=================================================="
echo

# Verificar que existe el archivo del servidor
if [ ! -f "print_server.py" ]; then
    echo "❌ No se encuentra print_server.py"
    echo "   Asegúrate de estar en la carpeta print_service/"
    exit 1
fi

# Verificar puerto 3001
if lsof -Pi :3001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ Puerto 3001 ocupado. Deteniendo proceso anterior..."
    pkill -f "print_server.py" 2>/dev/null || true
    sleep 2
fi

# Intentar instalar dependencias si no están
echo "📦 Verificando dependencias..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

# Verificar Flask
$PYTHON_CMD -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⬇️ Instalando Flask..."
    $PYTHON_CMD -m pip install flask flask-cors --user 2>/dev/null || {
        echo "❌ Error instalando Flask. Ejecuta manualmente:"
        echo "   pip install flask flask-cors"
        exit 1
    }
fi

echo "🚀 Iniciando servidor en puerto 3001..."
echo "   🌐 Endpoint: http://localhost:3001"
echo "   🛑 Presiona Ctrl+C para detener"
echo

# Iniciar servidor
$PYTHON_CMD print_server.py