#!/usr/bin/env python3
"""
Script para agregar columnas de propinas a la tabla pedidos.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from app.db.session import engine


def main():
    print("🔄 Agregando columnas de propinas a la tabla pedidos...")

    # SQL para agregar columnas si no existen
    sql_commands = [
        """
        ALTER TABLE pedidos 
        ADD COLUMN IF NOT EXISTS propina_efectivo DECIMAL(8,2) DEFAULT 0
        """,
        """
        ALTER TABLE pedidos 
        ADD COLUMN IF NOT EXISTS propina_tarjeta DECIMAL(8,2) DEFAULT 0
        """,
    ]

    try:
        with engine.connect() as conn:
            for sql in sql_commands:
                print(f"  Ejecutando: {sql[:50]}...")
                conn.execute(text(sql))
                conn.commit()

            print("✅ Columnas agregadas exitosamente")

            # Verificar que las columnas existan
            check_sql = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'pedidos' 
            AND column_name IN ('propina_efectivo', 'propina_tarjeta')
            """
            result = conn.execute(text(check_sql))
            columns = result.fetchall()

            print(f"📊 Columnas verificadas: {[col[0] for col in columns]}")

    except Exception as e:
        print(f"❌ Error ejecutando migración: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
