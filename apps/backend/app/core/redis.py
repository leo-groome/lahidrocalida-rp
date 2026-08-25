"""Cliente Redis compartido: fan-out de eventos WS entre workers/réplicas y
(en 2.3) backend del rate limiter.

Ausencia de REDIS_URL es un modo de operación válido, no un error de arranque:
el sistema degrada a fan-out local (un solo proceso, como hoy) sin Redis.
"""

import logging
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Optional["aioredis.Redis"] = None


def get_redis() -> Optional["aioredis.Redis"]:
    """Cliente Redis compartido, o None si REDIS_URL no está configurada."""
    global _client
    if not settings.REDIS_URL:
        return None
    if _client is None:
        _client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _client


async def check_redis() -> bool:
    """True si hay REDIS_URL configurada y Redis responde a PING."""
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(await client.ping())
    except Exception:
        logger.warning("Redis no disponible", exc_info=True)
        return False


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
