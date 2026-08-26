"""Rate limiting para los endpoints de login.

Ventana deslizante de intentos FALLIDOS por clave: un usuario legítimo que se
equivoca dos veces y entra a la tercera nunca ve un 429, mientras que un
atacante consume su presupuesto con cada intento.

Backend: Redis si hay `REDIS_URL` configurada (comparte estado entre
workers/réplicas — necesario detrás del proxy de Railway con >1 worker), con
fallback automático a memoria si Redis no está configurada o falla en
runtime. La superficie pública (`enforce_login_rate_limit`,
`register_login_failure`, `clear_login_failures`, `client_ip`) no cambia de
nombre ni parámetros — solo pasa a `async def` porque ahora puede hacer I/O
real de red.
"""

import logging
import threading
import time
from collections import deque
from typing import Deque, Dict, Protocol

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# Máximo de claves rastreadas en memoria antes de forzar una barrida de
# expirados. Cota la memoria frente a un atacante que rota IPs para inflar el
# diccionario. No aplica al backend Redis (usa EXPIRE nativo por clave).
_MAX_TRACKED_KEYS = 10_000


class RateLimiterBackend(Protocol):
    async def retry_after(self, key: str) -> int: ...
    async def register_failure(self, key: str) -> None: ...
    async def clear(self, key: str) -> None: ...
    async def reset(self) -> None: ...


class InMemorySlidingWindowLimiter:
    """Ventana deslizante en memoria del proceso. Estado por-worker: no se
    comparte entre réplicas (deuda conocida, es el fallback de
    RedisSlidingWindowLimiter, no el backend primario en producción)."""

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> Deque[float]:
        hits = self._hits.get(key)
        if hits is None:
            hits = deque()
            self._hits[key] = hits
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        return hits

    def _sweep(self, now: float) -> None:
        cutoff = now - self.window_seconds
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]:
            del self._hits[key]

    async def retry_after(self, key: str) -> int:
        """Segundos hasta que la clave vuelva a tener presupuesto, o 0 si ya tiene."""
        now = time.monotonic()
        with self._lock:
            hits = self._prune(key, now)
            if len(hits) < self.max_attempts:
                return 0
            return max(1, int(hits[0] + self.window_seconds - now) + 1)

    async def register_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            if len(self._hits) > _MAX_TRACKED_KEYS:
                self._sweep(now)
            self._prune(key, now).append(now)

    async def clear(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    async def reset(self) -> None:
        """Borra todo el estado. Para fixtures de test."""
        with self._lock:
            self._hits.clear()


class RedisSlidingWindowLimiter:
    """Ventana deslizante sobre un sorted set por clave: el score es el
    timestamp del intento, lo que permite podar (ZREMRANGEBYSCORE) y contar
    (ZCARD) en O(log n). EXPIRE hace que Redis limpie solo las claves
    inactivas — reemplaza el `_sweep`/`_MAX_TRACKED_KEYS` manual del backend
    en memoria."""

    def __init__(self, redis_client, max_attempts: int, window_seconds: int, prefix="ratelimit:"):
        self._redis = redis_client
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    async def retry_after(self, key: str) -> int:
        full_key = self._key(key)
        now = time.time()
        cutoff = now - self.window_seconds
        await self._redis.zremrangebyscore(full_key, 0, cutoff)
        count = await self._redis.zcard(full_key)
        if count < self.max_attempts:
            return 0
        oldest = await self._redis.zrange(full_key, 0, 0, withscores=True)
        oldest_ts = oldest[0][1] if oldest else now
        return max(1, int(oldest_ts + self.window_seconds - now) + 1)

    async def register_failure(self, key: str) -> None:
        full_key = self._key(key)
        now = time.time()
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.zadd(full_key, {str(now): now})
            pipe.expire(full_key, self.window_seconds)
            await pipe.execute()

    async def clear(self, key: str) -> None:
        await self._redis.delete(self._key(key))

    async def reset(self) -> None:
        """Borra todas las claves con el prefijo. Solo para tests — SCAN, no
        KEYS, para no bloquear Redis si algún día hay volumen real."""
        async for full_key in self._redis.scan_iter(match=f"{self._prefix}*"):
            await self._redis.delete(full_key)


class FallbackRateLimiter:
    """Envuelve un backend Redis + uno en memoria: si cualquier operación
    contra Redis lanza (timeout, conexión rechazada — Redis configurado pero
    caído en este momento, no solo ausente), esa llamada puntual degrada al
    backend en memoria en vez de tumbar el login."""

    def __init__(self, primary: RedisSlidingWindowLimiter, fallback: InMemorySlidingWindowLimiter):
        self._primary = primary
        self._fallback = fallback
        self.max_attempts = primary.max_attempts
        self.window_seconds = primary.window_seconds

    async def retry_after(self, key: str) -> int:
        try:
            return await self._primary.retry_after(key)
        except Exception:
            logger.warning("Redis no disponible para rate limit, usando fallback en memoria")
            return await self._fallback.retry_after(key)

    async def register_failure(self, key: str) -> None:
        try:
            await self._primary.register_failure(key)
        except Exception:
            logger.warning("Redis no disponible para rate limit, usando fallback en memoria")
            await self._fallback.register_failure(key)

    async def clear(self, key: str) -> None:
        try:
            await self._primary.clear(key)
        except Exception:
            logger.warning("Redis no disponible para rate limit, usando fallback en memoria")
        await self._fallback.clear(key)

    async def reset(self) -> None:
        try:
            await self._primary.reset()
        except Exception:
            logger.warning("Redis no disponible para rate limit, usando fallback en memoria")
        await self._fallback.reset()


def _build_login_limiter() -> RateLimiterBackend:
    from app.core.redis import get_redis

    redis_client = get_redis()
    fallback = InMemorySlidingWindowLimiter(max_attempts=8, window_seconds=300)
    if redis_client is None:
        return fallback
    primary = RedisSlidingWindowLimiter(redis_client, max_attempts=8, window_seconds=300)
    return FallbackRateLimiter(primary, fallback)


# Un intento fallido cada ~37s sostenidos: irrelevante para un humano que teclea
# mal su NIP, letal para fuerza-bruta (un espacio de 4 dígitos tardaría ~4 días).
login_limiter = _build_login_limiter()


def client_ip(request: Request) -> str:
    """IP del cliente.

    NO se lee X-Forwarded-For: el header lo controla el cliente y confiarlo sin
    un proxy de confianza declarado convierte el límite por IP en decorativo
    (basta mandar un XFF distinto en cada intento). Cuando el backend quede
    detrás del proxy de Railway y haga falta la IP real, se introduce una
    whitelist de proxies confiables — no un `headers.get()` a secas.
    """
    return request.client.host if request.client else "unknown"


async def enforce_login_rate_limit(request: Request, identity: str | None = None) -> list[str]:
    """Lanza 429 si la IP o la cuenta objetivo agotaron su presupuesto.

    Devuelve las claves a marcar con `register_failure` si el login falla. Se
    limita por IP y por cuenta objetivo para que rotar de IP no permita seguir
    atacando la misma cuenta indefinidamente.
    """
    keys = [f"ip:{client_ip(request)}"]
    if identity:
        keys.append(f"user:{identity}")

    for key in keys:
        delay = await login_limiter.retry_after(key)
        if delay:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos fallidos. Espera antes de reintentar.",
                headers={"Retry-After": str(delay)},
            )
    return keys


async def register_login_failure(keys: list[str]) -> None:
    for key in keys:
        await login_limiter.register_failure(key)


async def clear_login_failures(keys: list[str]) -> None:
    """Limpia el presupuesto de la CUENTA tras un login exitoso.

    La clave de IP se deja intacta a propósito: si se limpiara, un atacante con
    credenciales válidas de una cuenta cualquiera podría resetear su cupo de IP
    entre tandas de adivinanzas contra otras cuentas.
    """
    for key in keys:
        if key.startswith("user:"):
            await login_limiter.clear(key)


# Mismo limiter subyacente que el login (comparte Redis/memoria), pero con
# prefijo de clave distinto: `verificar_pin_admin` protege un PIN de 4
# dígitos usado para autorizar acciones desde una sesión YA autenticada
# (cancelar cuenta, borrar artículo, editar propina, ver analíticas) — sin
# este límite, cualquier mesero/cajero con JWT válido podría probar los
# 10 000 PIN posibles sin fricción, ya que ese endpoint no pasa por
# `enforce_login_rate_limit` (que solo cubre los flujos de login).
async def enforce_pin_rate_limit(request: Request, identity: str) -> list[str]:
    """Lanza 429 si la IP o la cuenta que intenta el PIN agotaron su presupuesto.

    Se limita por IP y por la cuenta que ESTÁ INTENTANDO el PIN (no por el
    admin objetivo, que ni siquiera se conoce hasta hacer match) — así rotar
    de sesión mesero/cajero no da presupuesto extra.
    """
    keys = [f"pin-ip:{client_ip(request)}", f"pin-user:{identity}"]
    for key in keys:
        delay = await login_limiter.retry_after(key)
        if delay:
            logger.warning("Rate limit de PIN de administrador agotado: clave=%s", key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos de PIN incorrectos. Espera antes de reintentar.",
                headers={"Retry-After": str(delay)},
            )
    return keys


async def register_pin_failure(keys: list[str]) -> None:
    for key in keys:
        await login_limiter.register_failure(key)


async def clear_pin_success(keys: list[str]) -> None:
    for key in keys:
        if key.startswith("pin-user:"):
            await login_limiter.clear(key)
