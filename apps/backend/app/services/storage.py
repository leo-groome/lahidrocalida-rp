"""Storage de adjuntos (fotos de tickets de gastos).

Dos backends detrás de la misma interfaz async:
- `LocalStorage`: disco (desarrollo y tests). Nunca en producción: el disco de
  Railway es efímero.
- `R2Storage`: Cloudflare R2 vía API S3 (aioboto3), bucket privado.

Las llaves las genera el servidor (`<prefijo>/<uuid4>.<ext>`); el cliente nunca
influye en la ruta, así que no hay path traversal posible.
"""

import asyncio
import uuid
from pathlib import Path
from typing import Optional, Protocol

from app.core.config import settings

MAX_ADJUNTO_BYTES = 8 * 1024 * 1024  # 8 MB

# content_type -> extensión
_TIPOS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
}

_HEIC_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"heim", b"heis"}


class AdjuntoInvalido(ValueError):
    """El contenido no es una imagen permitida."""


def detectar_tipo(cabecera: bytes) -> str:
    """Tipo MIME por magic bytes (nunca por extensión ni Content-Type del cliente)."""
    if cabecera[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if cabecera[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if cabecera[:4] == b"RIFF" and cabecera[8:12] == b"WEBP":
        return "image/webp"
    if cabecera[4:8] == b"ftyp" and cabecera[8:12] in _HEIC_BRANDS:
        return "image/heic"
    raise AdjuntoInvalido("Formato no permitido. Usa JPG, PNG, WebP o HEIC.")


def generar_llave(prefijo: str, content_type: str) -> str:
    return f"{prefijo}/{uuid.uuid4().hex}.{_TIPOS[content_type]}"


class Storage(Protocol):
    async def guardar(self, llave: str, datos: bytes, content_type: str) -> None: ...

    async def leer(self, llave: str) -> bytes: ...

    async def borrar(self, llave: str) -> None: ...


class LocalStorage:
    def __init__(self, base_dir: str):
        self.base = Path(base_dir).resolve()

    def _ruta(self, llave: str) -> Path:
        ruta = (self.base / llave).resolve()
        if not ruta.is_relative_to(self.base):  # defensa en profundidad
            raise ValueError("Llave fuera del directorio de storage")
        return ruta

    async def guardar(self, llave: str, datos: bytes, content_type: str) -> None:
        ruta = self._ruta(llave)

        def _write() -> None:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(datos)

        await asyncio.to_thread(_write)

    async def leer(self, llave: str) -> bytes:
        return await asyncio.to_thread(self._ruta(llave).read_bytes)

    async def borrar(self, llave: str) -> None:
        ruta = self._ruta(llave)
        await asyncio.to_thread(lambda: ruta.unlink(missing_ok=True))


class R2Storage:
    def __init__(self, endpoint: str, bucket: str, access_key: str, secret_key: str):
        import aioboto3  # import perezoso: dev/tests locales no lo necesitan

        self._session = aioboto3.Session()
        self._endpoint = endpoint
        self._bucket = bucket
        self._access_key = access_key
        self._secret_key = secret_key

    def _client(self):
        return self._session.client(
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            region_name="auto",
        )

    async def guardar(self, llave: str, datos: bytes, content_type: str) -> None:
        async with self._client() as s3:
            await s3.put_object(
                Bucket=self._bucket, Key=llave, Body=datos, ContentType=content_type
            )

    async def leer(self, llave: str) -> bytes:
        async with self._client() as s3:
            resp = await s3.get_object(Bucket=self._bucket, Key=llave)
            return await resp["Body"].read()

    async def borrar(self, llave: str) -> None:
        async with self._client() as s3:
            await s3.delete_object(Bucket=self._bucket, Key=llave)


_storage: Optional[Storage] = None


def get_storage() -> Storage:
    """Dependencia FastAPI: backend según `STORAGE_BACKEND` (singleton)."""
    global _storage
    if _storage is None:
        if settings.STORAGE_BACKEND == "r2":
            faltan = [
                n
                for n in ("R2_ENDPOINT", "R2_BUCKET", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")
                if not getattr(settings, n)
            ]
            if faltan:
                raise RuntimeError(f"STORAGE_BACKEND=r2 requiere: {', '.join(faltan)}")
            _storage = R2Storage(
                settings.R2_ENDPOINT,  # type: ignore[arg-type]
                settings.R2_BUCKET,  # type: ignore[arg-type]
                settings.R2_ACCESS_KEY_ID,  # type: ignore[arg-type]
                settings.R2_SECRET_ACCESS_KEY,  # type: ignore[arg-type]
            )
        else:
            if settings.ENVIRONMENT == "production":
                # El disco de Railway es efímero: guardar tickets ahí los
                # perdería en silencio en el siguiente deploy. Mejor fallar fuerte.
                raise RuntimeError(
                    "STORAGE_BACKEND=local no está permitido en producción; "
                    "configura STORAGE_BACKEND=r2 y las variables R2_*"
                )
            _storage = LocalStorage(settings.STORAGE_LOCAL_DIR)
    return _storage
