"""Smoke test R2: solo crea una imagen sintética bajo audit/ y la elimina.

Desde apps/backend: uv run python -m scripts.verify_r2_storage
Opcional: R2_AUDIT_PUBLIC_URLS contiene dominios públicos a comprobar separados por coma.
Nunca muestra credenciales ni ejecuta operaciones sobre objetos existentes.
"""

import asyncio
import io
import os
import sys
from uuid import uuid4

import httpx
from botocore.exceptions import ClientError
from PIL import Image

from app.core.config import settings
from app.services.storage import R2Storage


async def verificar() -> None:
    names = ("R2_ENDPOINT", "R2_BUCKET", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")
    missing = [name for name in names if not getattr(settings, name)]
    if missing:
        raise RuntimeError("Faltan variables: " + ", ".join(missing))
    storage = R2Storage(*(getattr(settings, name) for name in names))
    key = f"audit/{uuid4().hex}.webp"
    output = io.BytesIO()
    Image.new("RGB", (32, 24), "blue").save(output, "WEBP")
    data = output.getvalue()
    try:
        await storage.guardar(key, data, "image/webp")
        assert await storage.leer(key) == data, "Contenido leído diferente"
        print("R2: subida y lectura verificadas")
        domains = [
            url.strip().rstrip("/")
            for url in os.environ.get("R2_AUDIT_PUBLIC_URLS", "").split(",")
            if url.strip()
        ]
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            for domain in domains:
                response = await client.get(f"{domain}/{key}")
                if response.status_code == 200:
                    raise RuntimeError(
                        "El objeto de prueba es accesible públicamente; deshabilita ese acceso"
                    )
                print(f"Dominio público: HTTP {response.status_code}")
                if response.headers.get("cf-mitigated") == "challenge":
                    print("Cloudflare presenta un challenge; esto no demuestra autenticación")
                print("El dominio no entregó el objeto; revisar además política de acceso y r2.dev")
        if not domains:
            print("Privacidad: pendiente de comprobar dominios y r2.dev en Cloudflare")
    finally:
        await storage.borrar(key)
    try:
        await storage.leer(key)
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in {"NoSuchKey", "404"}:
            raise
    else:
        raise RuntimeError("El objeto de prueba sigue existiendo después del borrado")
    print("R2: borrado verificado")


if __name__ == "__main__":
    try:
        asyncio.run(verificar())
    except Exception as exc:
        # Los mensajes del SDK pueden incluir endpoint/account: no imprimirlos.
        if isinstance(exc, (RuntimeError, AssertionError)):
            print(str(exc), file=sys.stderr)
        else:
            print(
                f"La prueba falló ({type(exc).__name__}); revisar configuración/conectividad",
                file=sys.stderr,
            )
        sys.exit(1)
