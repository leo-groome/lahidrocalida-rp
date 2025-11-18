#!/usr/bin/env python3
"""
Script para agregar todas las variaciones de pozoles a la base de datos
Ejecutar desde el directorio backend: python agregar_pozoles_script.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configurar path para importar desde el proyecto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_database_url():
    """Obtener URL de la base de datos desde variables de entorno"""
    from app.core.config import settings
    return settings.DATABASE_URL

def crear_pozoles():
    """Crear todas las variaciones de pozoles con las nuevas proteínas"""
    
    # Configuración de precios por proteína y tamaño
    precios = {
        'Puerco': {'Infantil': 75.00, 'Regular': 95.00, 'Grande': 115.00},
        'Surtida': {'Infantil': 75.00, 'Regular': 95.00, 'Grande': 115.00},
        'Pollo': {'Infantil': 85.00, 'Regular': 110.00, 'Grande': 130.00},
        'Mixta': {'Infantil': 85.00, 'Regular': 110.00, 'Grande': 130.00},
    }
    
    # Configuración de nomenclatura KDS
    kds_tamaños = {'Infantil': 'Inf', 'Regular': 'Med', 'Grande': 'Gde'}
    
    tamaños = ['Infantil', 'Regular', 'Grande']
    colores = ['Verde', 'Blanco', 'Rojo'] 
    proteinas_nuevas = ['Surtida', 'Mixta']  # Solo agregamos las nuevas
    
    # Crear conexión a la base de datos
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        pozoles_agregados = []
        
        for color in colores:
            for proteina in proteinas_nuevas:
                for tamaño in tamaños:
                    nombre = f"Pozole {tamaño} {color} {proteina}"
                    descripcion = f"Delicioso pozole tradicional {color.lower()} con carne {proteina.lower()}"
                    precio = precios[proteina][tamaño]
                    kds_name = f"{kds_tamaños[tamaño]} {color} {proteina}"
                    
                    # Verificar si ya existe
                    existing = session.execute(
                        text("SELECT id FROM platillos WHERE nombre = :nombre"),
                        {"nombre": nombre}
                    ).fetchone()
                    
                    if existing:
                        print(f"⚠️  Ya existe: {nombre}")
                        continue
                    
                    # Insertar nuevo pozole
                    session.execute(text("""
                        INSERT INTO platillos (nombre, descripcion, precio, categoria, kds_name, estado)
                        VALUES (:nombre, :descripcion, :precio, 'Pozole', :kds_name, 'disponible')
                    """), {
                        "nombre": nombre,
                        "descripcion": descripcion,
                        "precio": precio,
                        "kds_name": kds_name
                    })
                    
                    pozoles_agregados.append(f"{nombre} - ${precio}")
                    print(f"✅ Agregado: {nombre} - ${precio} (KDS: {kds_name})")
        
        # Confirmar cambios
        session.commit()
        print(f"\n🎉 ¡Completado! Se agregaron {len(pozoles_agregados)} nuevas variaciones de pozole.")
        
        # Mostrar resumen
        print("\n📊 Resumen de pozoles agregados:")
        for pozole in pozoles_agregados:
            print(f"   • {pozole}")
            
        # Verificar total en BD
        total = session.execute(
            text("SELECT COUNT(*) FROM platillos WHERE categoria = 'Pozole'")
        ).scalar()
        print(f"\n📈 Total de pozoles en la base de datos: {total}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("🍲 Agregando nuevas variaciones de pozoles...")
    print("=" * 50)
    crear_pozoles()
    print("=" * 50)
    print("✨ Proceso completado!")