"""Normalización de tickets a WebP sin EXIF ni GPS."""

import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from app.services.storage import MAX_ADJUNTO_BYTES, AdjuntoInvalido

register_heif_opener()
MAX_PIXELES = 40_000_000


def normalizar_imagen(datos: bytes) -> bytes:
    """Decodifica, aplica orientación y limita resolución antes de guardar."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(datos)) as source:
                if source.width * source.height > MAX_PIXELES:
                    raise AdjuntoInvalido("La imagen tiene demasiados píxeles")
                source.load()
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((1600, 1600))
                # Una imagen nueva evita propagar metadata del decodificador.
                clean = Image.new("RGB", image.size)
                clean.paste(image)
                output = io.BytesIO()
                clean.save(output, format="WEBP", quality=80)
                result = output.getvalue()
                if len(result) > MAX_ADJUNTO_BYTES:
                    raise AdjuntoInvalido("La imagen convertida supera el límite")
                return result
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise AdjuntoInvalido(
            "No se pudo leer la imagen. Usa una foto JPG, PNG, WebP o HEIC válida."
        ) from exc
