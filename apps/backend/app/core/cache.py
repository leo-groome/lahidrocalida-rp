import time
from typing import Any, Optional


class TTLCache:
    """Caché in-memory simple con TTL. Suficiente para catálogos casi-estáticos
    (menú, proveedores, categorías) en un proceso único; si escalamos a
    múltiples workers/replicas, migrar a Redis."""

    def __init__(self, ttl_seconds: int = 300):
        self._data: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        entry = self._data.get(key)
        if entry is None:
            return None
        if time.monotonic() - entry[0] < self._ttl:
            return entry[1]
        self._data.pop(key, None)
        return None

    def set(self, key: str, value: Any) -> None:
        self._data[key] = (time.monotonic(), value)

    def invalidate(self, key: str) -> None:
        self._data.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        for key in [k for k in self._data if k.startswith(prefix)]:
            self._data.pop(key, None)


platillos_cache = TTLCache(ttl_seconds=300)
catalogos_cache = TTLCache(ttl_seconds=300)
