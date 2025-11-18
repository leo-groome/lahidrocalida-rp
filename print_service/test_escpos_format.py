#!/usr/bin/env python3
"""
Script de prueba para verificar formato ESC/POS
Prueba directamente la función de formateo sin servidor
"""

import requests
import json

def test_print_service():
    """Prueba el servicio de impresión con endpoint de test"""
    
    print("🧪 TESTING LA HIDROCÁLIDA - FORMATO ESC/POS")
    print("=" * 50)
    
    # Datos de prueba
    test_url = "http://localhost:3001/test-format"
    
    try:
        print("📡 Enviando petición de test al servidor...")
        response = requests.post(test_url, json={}, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Test completado exitosamente!")
            print(f"📊 Comandos encontrados: {result['commands_found']}/{result['commands_total']}")
            print(f"🖨️ Impresión exitosa: {'SÍ' if result['print_success'] else 'NO'}")
            print(f"📏 Tamaño de datos: {result['data_length']} chars")
            
            print("\n🔍 Detalle de comandos ESC/POS:")
            for cmd, found in result['commands_detail'].items():
                status = "✅" if found else "❌"
                print(f"   {status} {cmd}")
            
            if result['commands_found'] == result['commands_total']:
                print("\n🎉 ¡TODOS los comandos ESC/POS están presentes!")
            else:
                print(f"\n⚠️  Faltan {result['commands_total'] - result['commands_found']} comandos")
                
        else:
            print(f"❌ Error en servidor: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar al servidor de impresión")
        print("   ¿Está corriendo python print_server.py?")
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

def test_real_ticket():
    """Prueba con un ticket real"""
    
    print("\n" + "=" * 50)
    print("🎫 TESTING CON TICKET REAL")
    print("=" * 50)
    
    real_ticket = {
        "numero_display": "042",
        "mesa": "23",
        "nombre_cliente": "Juan Pérez",
        "articulos": [
            {
                "cantidad": 2,
                "nombre": "Pozole Rojo Grande",
                "precio": 120.00,
                "modificaciones": "Extra picante, sin orégano, con limón extra"
            },
            {
                "cantidad": 1,
                "nombre": "Quesadilla de Flor",
                "precio": 45.00,
                "modificaciones": None
            },
            {
                "cantidad": 3,
                "nombre": "Refresco Coca Cola",
                "precio": 25.00,
                "modificaciones": None
            }
        ],
        "total": 360.00
    }
    
    print_url = "http://localhost:3001/print"
    
    try:
        print("📡 Enviando ticket real al servidor...")
        response = requests.post(print_url, json=real_ticket, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Ticket real impreso exitosamente!")
            print(f"🎯 Método: {result.get('method', 'N/A')}")
            print(f"📄 Pedido: #{result.get('pedido', 'N/A')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_print_service()
    test_real_ticket()
    
    print("\n" + "=" * 50)
    print("🎯 INSTRUCCIONES:")
    print("1. Verifica que el servidor esté corriendo: python print_server.py")
    print("2. Revisa los logs del servidor para ver comandos ESC/POS")
    print("3. Si la impresora está conectada, debe imprimir con formato")
    print("4. Si no hay formato, verifica la conexión USB/puerto")
    print("=" * 50)