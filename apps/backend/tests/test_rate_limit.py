"""Rate limiting de los endpoints que verifican NIP/password."""

import os

import pytest

from app.core.rate_limit import (
    FallbackRateLimiter,
    InMemorySlidingWindowLimiter,
    RedisSlidingWindowLimiter,
    login_limiter,
)

TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL")


def _login_simple(client, user_id, pin="0000"):
    return client.post("/auth/login-simple", json={"user_id": str(user_id), "pin": pin})


def test_login_simple_devuelve_429_tras_agotar_intentos(client, seed):
    user_id = seed["usuario"].id

    codigos = [_login_simple(client, user_id).status_code for _ in range(20)]

    assert 429 in codigos, f"nunca se disparó el rate limit: {codigos}"
    # Los primeros intentos deben pasar como 401 (credencial mala), no como 429:
    # un 429 desde el intento 1 significaría que el limiter está mal calibrado.
    assert codigos[0] == 401
    # Una vez disparado, no se "des-dispara" dentro de la misma ventana.
    primer_429 = codigos.index(429)
    assert set(codigos[primer_429:]) == {429}


def test_429_incluye_retry_after(client, seed):
    user_id = seed["usuario"].id
    respuesta = None
    for _ in range(20):
        r = _login_simple(client, user_id)
        if r.status_code == 429:
            respuesta = r
            break

    assert respuesta is not None
    retry_after = respuesta.headers.get("Retry-After")
    assert retry_after is not None
    assert 0 < int(retry_after) <= login_limiter.window_seconds + 1


async def test_limite_por_cuenta_persiste_al_rotar_de_ip(client, seed):
    """Rotar de IP no debe devolver presupuesto contra la MISMA cuenta."""
    user_id = seed["usuario"].id
    for _ in range(20):
        _login_simple(client, user_id)

    # Simula otra IP: la clave `ip:` es distinta, pero la clave `user:` sigue quemada.
    await login_limiter.clear("ip:testclient")

    assert _login_simple(client, user_id).status_code == 429


def test_login_admin_tambien_esta_limitado(client):
    codigos = [
        client.post(
            "/auth/login-admin", json={"email": "admin@x.com", "password": "malo"}
        ).status_code
        for _ in range(20)
    ]
    assert 429 in codigos, f"login-admin sin rate limit: {codigos}"


def test_login_oauth2_tambien_esta_limitado(client, seed):
    codigos = [
        client.post(
            "/auth/login", data={"username": str(seed["usuario"].id), "password": "malo"}
        ).status_code
        for _ in range(20)
    ]
    assert 429 in codigos, f"/auth/login sin rate limit: {codigos}"


def test_asistencia_tambien_esta_limitada(client, seed):
    """El clock-in por NIP es el mismo oráculo de fuerza-bruta y además escribe."""
    codigos = [
        client.post(
            "/auth/asistencia", json={"usuario_id": seed["usuario"].id, "pin": "0000"}
        ).status_code
        for _ in range(20)
    ]
    assert 429 in codigos, f"/auth/asistencia sin rate limit: {codigos}"


def test_login_exitoso_no_consume_presupuesto(client, db_session, seed):
    """Un usuario legítimo que teclea mal y luego acierta no queda bloqueado."""
    from app.auth import get_password_hash
    from app.models import Usuario

    usuario = Usuario(
        nombre="Mesero OK",
        pin=get_password_hash("4321"),
        rol="mesero",
        sucursal_id=seed["sucursal"].id,
        activo=True,
    )
    db_session.add(usuario)
    db_session.commit()

    # Falla, acierta, repetido: sin la limpieza por cuenta esto acabaría en 429.
    for _ in range(6):
        assert _login_simple(client, usuario.id, "1111").status_code == 401
        assert _login_simple(client, usuario.id, "4321").status_code == 200


async def test_fallback_degrada_a_memoria_si_redis_lanza(monkeypatch):
    """Redis configurado pero caído en runtime: el login no debe fallar duro,
    degrada a memoria por-llamada (no solo cuando REDIS_URL está ausente)."""
    fallback = InMemorySlidingWindowLimiter(max_attempts=3, window_seconds=60)

    class _RedisRoto:
        async def zremrangebyscore(self, *a, **kw):
            raise ConnectionError("redis caído")

        def pipeline(self, *a, **kw):
            raise ConnectionError("redis caído")

    primary = RedisSlidingWindowLimiter(_RedisRoto(), max_attempts=3, window_seconds=60)
    limiter = FallbackRateLimiter(primary, fallback)

    # No debe lanzar ConnectionError, debe caer al backend en memoria.
    assert await limiter.retry_after("ip:1.2.3.4") == 0
    for _ in range(3):
        await limiter.register_failure("ip:1.2.3.4")
    assert await limiter.retry_after("ip:1.2.3.4") > 0


@pytest.mark.skipif(
    not TEST_REDIS_URL, reason="TEST_REDIS_URL no configurada, se salta test de integración"
)
async def test_redis_limiter_comparte_estado_entre_workers():
    """Justifica la migración: dos instancias de RedisSlidingWindowLimiter
    (simulando 2 workers) contra el mismo Redis comparten el conteo — el
    limiter en memoria de S1 NO lo haría en este mismo escenario."""
    import redis.asyncio as aioredis

    conn_worker_a = aioredis.from_url(TEST_REDIS_URL, decode_responses=True)
    conn_worker_b = aioredis.from_url(TEST_REDIS_URL, decode_responses=True)

    limiter_a = RedisSlidingWindowLimiter(
        conn_worker_a, max_attempts=3, window_seconds=60, prefix="test-ratelimit-shared:"
    )
    limiter_b = RedisSlidingWindowLimiter(
        conn_worker_b, max_attempts=3, window_seconds=60, prefix="test-ratelimit-shared:"
    )

    key = "user:compartido"
    try:
        await limiter_a.clear(key)
        await limiter_a.register_failure(key)
        await limiter_b.register_failure(key)
        await limiter_a.register_failure(key)

        # El tercer fallo (visto por A) ya agotó el presupuesto compartido con B.
        assert await limiter_b.retry_after(key) > 0
    finally:
        await limiter_a.clear(key)
        await conn_worker_a.aclose()
        await conn_worker_b.aclose()
