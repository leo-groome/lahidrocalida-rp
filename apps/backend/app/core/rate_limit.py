"""Rate limiting en memoria para los endpoints de login.

Por qué en memoria y no Redis: Redis está provisionado pero no entra hasta S2.
Este limiter es la misma clase de deviation conocida que el WS manager en
memoria — estado por proceso, se pierde en cada deploy y no se comparte entre
réplicas. Es una mejora real sobre el estado actual (cero fricción para
fuerza-bruta de un NIP de 4-6 dígitos) y se reemplaza por el backend de Redis
en S2 sin cambiar la superficie de llamada (`check` / `register_failure` /
`clear`).

Se cuentan solo los intentos FALLIDOS: un usuario legítimo que se equivoca dos
veces y entra a la tercera nunca ve un 429, mientras que un atacante consume su
presupuesto con cada intento.
"""

import threading
import time
from collections import deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

# Máximo de claves rastreadas antes de forzar una barrida de expirados. Cota la
# memoria frente a un atacante que rota IPs para inflar el diccionario.
_MAX_TRACKED_KEYS = 10_000


class SlidingWindowLimiter:
    """Ventana deslizante de intentos fallidos por clave."""

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

    def retry_after(self, key: str) -> int:
        """Segundos hasta que la clave vuelva a tener presupuesto, o 0 si ya tiene."""
        now = time.monotonic()
        with self._lock:
            hits = self._prune(key, now)
            if len(hits) < self.max_attempts:
                return 0
            return max(1, int(hits[0] + self.window_seconds - now) + 1)

    def register_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            if len(self._hits) > _MAX_TRACKED_KEYS:
                self._sweep(now)
            self._prune(key, now).append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def reset(self) -> None:
        """Borra todo el estado. Para fixtures de test."""
        with self._lock:
            self._hits.clear()


# Un intento fallido cada ~37s sostenidos: irrelevante para un humano que teclea
# mal su NIP, letal para fuerza-bruta (un espacio de 4 dígitos tardaría ~4 días).
login_limiter = SlidingWindowLimiter(max_attempts=8, window_seconds=300)


def client_ip(request: Request) -> str:
    """IP del cliente.

    NO se lee X-Forwarded-For: el header lo controla el cliente y confiarlo sin
    un proxy de confianza declarado convierte el límite por IP en decorativo
    (basta mandar un XFF distinto en cada intento). Cuando el backend quede
    detrás del proxy de Railway y haga falta la IP real, se introduce una
    whitelist de proxies confiables — no un `headers.get()` a secas.
    """
    return request.client.host if request.client else "unknown"


def enforce_login_rate_limit(request: Request, identity: str | None = None) -> list[str]:
    """Lanza 429 si la IP o la cuenta objetivo agotaron su presupuesto.

    Devuelve las claves a marcar con `register_failure` si el login falla. Se
    limita por IP y por cuenta objetivo para que rotar de IP no permita seguir
    atacando la misma cuenta indefinidamente.
    """
    keys = [f"ip:{client_ip(request)}"]
    if identity:
        keys.append(f"user:{identity}")

    for key in keys:
        delay = login_limiter.retry_after(key)
        if delay:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos fallidos. Espera antes de reintentar.",
                headers={"Retry-After": str(delay)},
            )
    return keys


def register_login_failure(keys: list[str]) -> None:
    for key in keys:
        login_limiter.register_failure(key)


def clear_login_failures(keys: list[str]) -> None:
    """Limpia el presupuesto de la CUENTA tras un login exitoso.

    La clave de IP se deja intacta a propósito: si se limpiara, un atacante con
    credenciales válidas de una cuenta cualquiera podría resetear su cupo de IP
    entre tandas de adivinanzas contra otras cuentas.
    """
    for key in keys:
        if key.startswith("user:"):
            login_limiter.clear(key)
