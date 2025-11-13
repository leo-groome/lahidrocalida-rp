#!/usr/bin/env python3
"""
Servicio de impresión local para La Hidrocálida
Escucha en puerto 3001 y maneja impresora térmica ESC/POS
"""

import json
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Permitir requests desde el frontend

def generate_escpos_commands(ticket_data):
    """Genera comandos ESC/POS optimizados para impresora térmica 80mm (48 chars)"""
    
    # Comandos ESC/POS para impresora térmica
    ESC = '\x1b'
    GS = '\x1d'
    INIT = ESC + '@'  # Inicializar impresora
    BOLD_ON = ESC + 'E1'  # Negrita ON
    BOLD_OFF = ESC + 'E0'  # Negrita OFF
    CENTER = ESC + 'a1'  # Centrar texto
    LEFT = ESC + 'a0'  # Alinear izquierda
    RIGHT = ESC + 'a2'  # Alinear derecha
    DOUBLE_WIDTH = GS + '!01'  # Doble ancho
    DOUBLE_HEIGHT = GS + '!10'  # Doble altura
    DOUBLE_BOTH = GS + '!11'  # Doble ancho y altura
    NORMAL_SIZE = GS + '!00'  # Tamaño normal
    SMALL_FONT = ESC + 'M1'  # Fuente pequeña
    NORMAL_FONT = ESC + 'M0'  # Fuente normal
    CUT = GS + 'V1'  # Cortar papel
    LINE_FEED = '\n'
    
    # Líneas decorativas para 48 chars
    DOUBLE_LINE = '═' * 48
    SINGLE_LINE = '─' * 48
    DOT_LINE = '·' * 48
    STAR_LINE = '★' + '─' * 46 + '★'
    
    # Construir ticket para restaurante (48 chars width)
    commands = []
    commands.append(INIT)
    
    # ENCABEZADO DEL RESTAURANTE
    commands.append(LINE_FEED)
    commands.append(CENTER)
    commands.append(STAR_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    commands.append(DOUBLE_BOTH + BOLD_ON + "LA HIDROCÁLIDA" + BOLD_OFF + NORMAL_SIZE + LINE_FEED)
    commands.append(LINE_FEED)
    commands.append(BOLD_ON + "☾ POZOLERÍA TRADICIONAL ☽" + BOLD_OFF + LINE_FEED)
    commands.append("Auténticos sabores mexicanos" + LINE_FEED)
    commands.append(LINE_FEED)
    commands.append(STAR_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    
    # INFORMACIÓN DEL PEDIDO
    commands.append(LEFT)
    commands.append(BOLD_ON + "ORDEN #" + str(ticket_data.get('numero_display', 'N/A')).zfill(3) + BOLD_OFF)
    
    # Fecha en la misma línea
    fecha = datetime.now().strftime('%d/%m/%Y')
    hora = datetime.now().strftime('%H:%M')
    fecha_line = f"ORDEN #{str(ticket_data.get('numero_display', 'N/A')).zfill(3)}"
    fecha_right = f"{fecha} {hora}"
    spaces = 48 - len(fecha_line) - len(fecha_right)
    commands.append(LEFT)
    commands.append(BOLD_ON + fecha_line + BOLD_OFF + " " * spaces + fecha_right + LINE_FEED)
    
    commands.append(SINGLE_LINE + LINE_FEED)
    
    # Mesa y Cliente con mejor spacing
    if ticket_data.get('mesa'):
        mesa_line = f"Mesa: {ticket_data['mesa']}"
        commands.append(mesa_line + LINE_FEED)
    
    if ticket_data.get('nombre_cliente'):
        cliente_line = f"Cliente: {ticket_data['nombre_cliente']}"
        commands.append(cliente_line + LINE_FEED)
    
    commands.append(SINGLE_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    
    # DETALLES DEL PEDIDO
    commands.append(CENTER + BOLD_ON + "~ DETALLES DEL PEDIDO ~" + BOLD_OFF + LINE_FEED)
    commands.append(LEFT)
    commands.append(DOT_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    
    # Productos con formato mejorado
    for i, articulo in enumerate(ticket_data.get('articulos', []), 1):
        cantidad = articulo.get('cantidad', 1)
        nombre = articulo.get('nombre', 'Producto')
        precio_unitario = float(articulo.get('precio', 0))
        precio_total = cantidad * precio_unitario
        
        # Línea principal del producto
        commands.append(BOLD_ON + f"{i}. {nombre}" + BOLD_OFF + LINE_FEED)
        
        # Cantidad y precios
        cant_precio = f"   {cantidad} x ${precio_unitario:.2f}"
        total_str = f"${precio_total:.2f}"
        spaces = 48 - len(cant_precio) - len(total_str)
        commands.append(cant_precio + " " * spaces + total_str + LINE_FEED)
        
        # Modificaciones en línea separada
        if articulo.get('modificaciones'):
            mod_text = articulo['modificaciones']
            # Dividir modificaciones largas en líneas de 44 chars
            lines = []
            while len(mod_text) > 44:
                cut_pos = mod_text.rfind(' ', 0, 44)
                if cut_pos == -1:
                    cut_pos = 44
                lines.append(mod_text[:cut_pos])
                mod_text = mod_text[cut_pos:].strip()
            if mod_text:
                lines.append(mod_text)
            
            for line in lines:
                commands.append(f"   > {line}" + LINE_FEED)
        
        commands.append(LINE_FEED)  # Espacio entre productos
    
    # TOTALES
    commands.append(DOT_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    
    total = float(ticket_data.get('total', 0))
    
    # Total destacado y centrado
    commands.append(CENTER)
    commands.append(DOUBLE_LINE + LINE_FEED)
    commands.append(DOUBLE_WIDTH + BOLD_ON + f"TOTAL: ${total:.2f}" + BOLD_OFF + NORMAL_SIZE + LINE_FEED)
    commands.append(DOUBLE_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    
    # MENSAJE DE AGRADECIMIENTO
    commands.append("¡MUCHAS GRACIAS!" + LINE_FEED)
    commands.append("Por elegirnos para disfrutar" + LINE_FEED)
    commands.append("de nuestros auténticos pozoles" + LINE_FEED)
    commands.append(LINE_FEED)
    
    # INFORMACIÓN DEL RESTAURANTE
    commands.append(LEFT)
    commands.append(SMALL_FONT)
    commands.append("♨ Especialidades de la casa:" + LINE_FEED)
    commands.append("  • Pozole Rojo Tradicional" + LINE_FEED)
    commands.append("  • Pozole Blanco Casero" + LINE_FEED)
    commands.append("  • Tostadas y Garnachas" + LINE_FEED)
    commands.append(NORMAL_FONT)
    commands.append(LINE_FEED)
    
    # REDES SOCIALES Y CONTACTO
    commands.append(CENTER)
    commands.append("☆ Síguenos en redes sociales ☆" + LINE_FEED)
    commands.append("@lahidrocalida_oficial" + LINE_FEED)
    commands.append(LINE_FEED)
    commands.append("¿Te gustó nuestro servicio?" + LINE_FEED)
    commands.append("Déjanos tu reseña ⭐⭐⭐⭐⭐" + LINE_FEED)
    commands.append(LINE_FEED)
    
    # PIE DE PÁGINA
    commands.append(SMALL_FONT)
    commands.append("Sistema POS v1.0 - La Hidrocálida" + LINE_FEED)
    commands.append(f"Impreso: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}" + LINE_FEED)
    commands.append(NORMAL_FONT)
    commands.append(LINE_FEED)
    commands.append(DOT_LINE + LINE_FEED)
    commands.append(LINE_FEED)
    commands.append(LINE_FEED)
    commands.append(LINE_FEED)
    
    # Cortar papel
    commands.append(CUT)
    
    return ''.join(commands)

def print_to_device(data, device_path='/dev/usb/lp0'):
    """Envía datos a la impresora"""
    try:
        # En Windows, usar 'PRN' o el nombre del puerto
        # En Linux/Mac, usar /dev/usb/lp0 o similar
        
        # Detectar sistema operativo
        import platform
        system = platform.system().lower()
        
        if system == 'windows':
            # Windows - intentar diferentes puertos
            possible_ports = ['PRN', 'LPT1', 'COM1']
            for port in possible_ports:
                try:
                    with open(port, 'wb') as printer:
                        printer.write(data.encode('cp437', errors='replace'))
                    logger.info(f"✅ Impreso exitosamente en {port}")
                    return True
                except Exception as e:
                    logger.warning(f"❌ No se pudo imprimir en {port}: {e}")
                    continue
        else:
            # Linux/Mac
            possible_devices = ['/dev/usb/lp0', '/dev/ttyUSB0', '/dev/ttyACM0']
            for device in possible_devices:
                try:
                    with open(device, 'w') as printer:
                        printer.write(data)
                    logger.info(f"✅ Impreso exitosamente en {device}")
                    return True
                except Exception as e:
                    logger.warning(f"❌ No se pudo imprimir en {device}: {e}")
                    continue
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error general de impresión: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check del servicio"""
    return jsonify({
        "status": "ok",
        "service": "La Hidrocálida Print Service",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/print', methods=['POST'])
def print_ticket():
    """Endpoint principal para imprimir tickets"""
    try:
        # Obtener datos del ticket
        ticket_data = request.get_json()
        
        if not ticket_data:
            return jsonify({"error": "No se recibieron datos del ticket"}), 400
        
        logger.info(f"📄 Procesando impresión del pedido #{ticket_data.get('numero_display', 'N/A')}")
        
        # Generar comandos ESC/POS
        escpos_data = generate_escpos_commands(ticket_data)
        
        # Intentar imprimir
        success = print_to_device(escpos_data)
        
        if success:
            logger.info("🖨️ Ticket impreso exitosamente")
            return jsonify({
                "status": "success",
                "message": "Ticket impreso exitosamente",
                "pedido": ticket_data.get('numero_display', 'N/A')
            })
        else:
            logger.error("❌ No se pudo imprimir el ticket")
            return jsonify({
                "status": "error", 
                "message": "No se pudo acceder a la impresora"
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Error en impresión: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error interno: {str(e)}"
        }), 500

@app.route('/test', methods=['POST'])
def test_print():
    """Endpoint para imprimir un ticket de prueba"""
    test_data = {
        "numero_display": "999",
        "mesa": "TEST",
        "nombre_cliente": "Prueba del Sistema",
        "articulos": [
            {
                "cantidad": 1,
                "nombre": "Pozole Rojo Grande",
                "precio": 120.00,
                "modificaciones": "Prueba de impresión - Extra picante, sin orégano"
            },
            {
                "cantidad": 1,
                "nombre": "Agua de Horchata",
                "precio": 30.00,
                "modificaciones": "Sin canela"
            },
            {
                "cantidad": 1,
                "nombre": "Orden de Tostadas",
                "precio": 45.00,
                "modificaciones": None
            }
        ],
        "total": 195.00
    }
    
    # Reutilizar lógica de impresión
    request.json = test_data
    return print_ticket()

if __name__ == '__main__':
    print("🚀 Iniciando servicio de impresión La Hidrocálida...")
    print("📡 Servicio disponible en: http://localhost:3001")
    print("🔍 Health check: http://localhost:3001/health")
    print("🧪 Test de impresión: POST http://localhost:3001/test")
    print("🖨️ Impresión: POST http://localhost:3001/print")
    print("⏹️  Presiona Ctrl+C para detener")
    
    try:
        app.run(host='0.0.0.0', port=3001, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Servicio de impresión detenido")
        sys.exit(0)