#!/bin/bash

echo "========================================"
echo "  INSTALADOR LA HIDROCALIDA - IMPRESION"
echo "========================================"
echo

# Verificar Python
echo "[1/4] Verificando Python..."
if command -v python3 &> /dev/null; then
    echo "✅ Python encontrado: $(python3 --version)"
elif command -v python &> /dev/null; then
    echo "✅ Python encontrado: $(python --version)"
else
    echo "❌ Python no encontrado. Por favor instala Python 3"
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "CentOS/RHEL: sudo yum install python3 python3-pip"
    echo "macOS: brew install python3"
    exit 1
fi

# Instalar dependencias
echo
echo "[2/4] Instalando dependencias..."
if command -v python3 &> /dev/null; then
    python3 -m pip install -r requirements.txt
else
    python -m pip install -r requirements.txt
fi

if [ $? -eq 0 ]; then
    echo "✅ Dependencias instaladas"
else
    echo "❌ Error instalando dependencias"
    exit 1
fi

# Crear script de inicio
echo
echo "[3/4] Creando script de inicio..."
cat > start_print_service.sh << 'EOF'
#!/bin/bash
echo "Iniciando servicio de impresión La Hidrocálida..."
echo "Presiona Ctrl+C para detener"

if command -v python3 &> /dev/null; then
    python3 print_server.py
else
    python print_server.py
fi
EOF

chmod +x start_print_service.sh
echo "✅ Script creado: start_print_service.sh"

# Probar servicio
echo
echo "[4/4] Instalación completada"

echo
echo "========================================"
echo "✅ INSTALACION COMPLETADA"
echo "========================================"
echo
echo "Para usar el servicio:"
echo "1. Conecta la impresora térmica"
echo "2. Ejecuta: ./start_print_service.sh"
echo "3. Abre el navegador con el sistema"
echo
echo "El servicio estará en: http://localhost:3001"
echo "========================================"