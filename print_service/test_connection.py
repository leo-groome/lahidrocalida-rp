#!/usr/bin/env python3
"""
Script de prueba para verificar la conexión con el servicio de impresión
La Hidrocálida - Sistema POS
"""

import requests
import json
import time

PRINT_SERVICE_URL = 'http://localhost:3001'

def test_health_endpoint():
    """Prueba el endpoint de health check"""
    try:
        print("🔍 Probando health check...")
        response = requests.get(f'{PRINT_SERVICE_URL}/health', timeout=5)
        
        if response.status_code == 200:
            print("✅ Health check: OK")
            return True
        else:
            print(f"❌ Health check falló: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar al servicio de impresión")
        print("   Asegúrate de que el servidor esté ejecutándose en puerto 3001")
        return False
    except Exception as e:
        print(f"❌ Error en health check: {e}")
        return False

def test_print_endpoint():
    """Prueba el endpoint de impresión con datos de ejemplo"""
    try:
        print("🖨️ Probando impresión de ticket de ejemplo...")
        
        # Datos de prueba
        test_ticket = {
            "numero_display": "999",
            "mesa": "TEST",
            "nombre_cliente": "Cliente de Prueba",
            "articulos": [
                {
                    "cantidad": 2,
                    "nombre": "Pozole Rojo Grande",
                    "precio": 120.00,
                    "modificaciones": "Extra picante"
                },
                {
                    "cantidad": 1,
                    "nombre": "Agua de Jamaica",
                    "precio": 35.00,
                    "modificaciones": None
                }
            ],
            "total": 275.00
        }
        
        response = requests.post(
            f'{PRINT_SERVICE_URL}/print',
            json=test_ticket,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Ticket de prueba enviado exitosamente")
            print(f"   Resultado: {result}")
            return True
        else:
            print(f"❌ Error en impresión: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   Detalle: {error_detail}")
            except:
                print(f"   Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en prueba de impresión: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("🧪 PRUEBA DE SERVICIO DE IMPRESIÓN")
    print("=" * 50)
    print()
    
    # Verificar que el servicio esté en línea
    if not test_health_endpoint():
        print()
        print("💡 SOLUCIÓN:")
        print("1. Ve a la carpeta print_service/")
        print("2. Ejecuta: chmod +x start_print_service.sh")
        print("3. Ejecuta: ./start_print_service.sh")
        print("4. Espera a que aparezca 'Running on http://localhost:3001'")
        print("5. Vuelve a ejecutar este script")
        return False
    
    print()
    
    # Probar impresión
    success = test_print_endpoint()
    
    print()
    print("=" * 50)
    
    if success:
        print("✅ TODAS LAS PRUEBAS PASARON")
        print()
        print("🎉 El servicio de impresión está funcionando correctamente!")
        print("   Ahora puedes usar el sistema de caja para imprimir tickets.")
    else:
        print("❌ ALGUNAS PRUEBAS FALLARON")
        print()
        print("🔧 VERIFICACIONES:")
        print("1. El servidor de impresión está en puerto 3001")
        print("2. La impresora térmica está conectada y configurada")
        print("3. Los drivers de la impresora están instalados")
        
    return success

if __name__ == "__main__":
    main()