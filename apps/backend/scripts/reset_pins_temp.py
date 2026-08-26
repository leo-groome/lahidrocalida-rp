#!/usr/bin/env python3
"""
reset_pins_temp.py — Reset masivo de PINs post-migración
=====================================================
Uso:
    cd apps/backend
    uv run python scripts/reset_pins_temp.py

PINs asignados:
    - administrador → 9999
    - todos los demás (mesero, cajero, cocina, compras) → 1111

El script lee DATABASE_URL del .env local. Si apunta a Postgres local en vez de Neon,
pásala manualmente:
    DATABASE_URL="postgresql://..." uv run python scripts/reset_pins_temp.py
"""

import os
import sys

from passlib.context import CryptContext
from sqlalchemy import create_engine, text

# ── Cargar DATABASE_URL ────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    try:
        from dotenv import load_dotenv

        load_dotenv()
        DATABASE_URL = os.environ.get("DATABASE_URL")
    except ImportError:
        pass

if not DATABASE_URL:
    print("❌ DATABASE_URL no definida.")
    print("   Edita el .env o pásala como variable de entorno:")
    print('   DATABASE_URL="postgresql://..." uv run python scripts/reset_pins_temp.py')
    sys.exit(1)

# ── Passlib (idéntico a producción) ───────────────────────────────────────────
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)

PIN_STAFF = "1111"
PIN_ADMIN = "9999"


def main():
    print("=" * 55)
    print("  RESET DE PINs — La Hidrocálida POS")
    print("=" * 55)
    print(f"  DB: {DATABASE_URL[:40]}...")
    print()

    engine = create_engine(DATABASE_URL)

    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT id, nombre, rol
                FROM usuarios
                WHERE activo = true
                ORDER BY rol, nombre
            """)
        ).fetchall()

        if not rows:
            print("⚠️  Sin usuarios activos en la base de datos.")
            return

        print(f"{'ID':<6} {'Nombre':<22} {'Rol':<15} {'PIN a asignar'}")
        print("-" * 55)
        for row in rows:
            uid, nombre, rol = row
            pin = PIN_ADMIN if rol == "administrador" else PIN_STAFF
            print(f"{uid:<6} {nombre:<22} {rol:<15} → {pin}")

        print("\n" + "=" * 55)
        confirm = input("¿Aplicar en la base de datos? [s/N]: ").strip().lower()
        if confirm != "s":
            print("❌ Cancelado. Sin cambios.")
            return

        print("\n⏳ Generando hashes Argon2 y actualizando...\n")
        count = 0
        for row in rows:
            uid, nombre, rol = row
            pin = PIN_ADMIN if rol == "administrador" else PIN_STAFF
            new_hash = pwd_context.hash(pin)
            conn.execute(
                text("UPDATE usuarios SET pin = :pin WHERE id = :id"),
                {"pin": new_hash, "id": uid},
            )
            count += 1
            print(f"  ✅  {nombre:<22} ({rol}) → PIN {pin}")

        print(f"\n✅ {count} usuarios actualizados correctamente.")
        print("\n📢 COMUNICA AL PERSONAL:")
        print("   • Mesero / Cajero / Cocina / Compras → PIN: 1111")
        print("   • Administradores                   → PIN: 9999")
        print("\n⚠️  Cambia los PINs desde el panel admin cuanto antes.")
        print("=" * 55)


if __name__ == "__main__":
    main()
