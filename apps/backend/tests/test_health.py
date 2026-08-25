"""GET /health/redis: disabled sin REDIS_URL, error si Redis no responde."""

import os

import pytest

from app.core.config import settings

TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL")


def test_health_redis_disabled_sin_redis_url(client, monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", None)
    r = client.get("/health/redis")
    assert r.status_code == 200
    assert r.json() == {"status": "disabled"}


def test_health_redis_error_si_no_responde(client, monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:1")
    monkeypatch.setattr("app.core.redis._client", None)
    r = client.get("/health/redis")
    assert r.status_code == 200
    assert r.json() == {"status": "error"}


@pytest.mark.skipif(
    not TEST_REDIS_URL, reason="TEST_REDIS_URL no configurada, se salta test de integración"
)
def test_health_redis_ok_con_redis_real(client, monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", TEST_REDIS_URL)
    monkeypatch.setattr("app.core.redis._client", None)
    r = client.get("/health/redis")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
