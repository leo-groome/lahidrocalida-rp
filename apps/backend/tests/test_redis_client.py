"""app/core/redis.py: ausencia de Redis es un modo válido, nunca lanza."""

from app.core.redis import check_redis, get_redis


def test_get_redis_none_sin_redis_url(monkeypatch):
    monkeypatch.setattr("app.core.redis.settings.REDIS_URL", None)
    monkeypatch.setattr("app.core.redis._client", None)
    assert get_redis() is None


async def test_check_redis_false_sin_redis_url(monkeypatch):
    monkeypatch.setattr("app.core.redis.settings.REDIS_URL", None)
    monkeypatch.setattr("app.core.redis._client", None)
    assert await check_redis() is False


async def test_check_redis_false_si_no_responde(monkeypatch):
    # Puerto sin nada escuchando: connect_timeout de 2s hace fallar el ping.
    monkeypatch.setattr("app.core.redis.settings.REDIS_URL", "redis://localhost:1")
    monkeypatch.setattr("app.core.redis._client", None)
    assert await check_redis() is False
