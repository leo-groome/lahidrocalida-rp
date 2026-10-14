import pytest

from app.services.adjunto_body_limit import AdjuntoBodyLimitMiddleware


@pytest.mark.parametrize("path", ["/gastos/1/adjuntos", "/gastos/1/adjuntos/"])
@pytest.mark.parametrize("length", [None, b"1"])
async def test_limita_bytes_reales_antes_del_parser(monkeypatch, path, length):
    monkeypatch.setattr("app.services.adjunto_body_limit.MAX_BODY_ADJUNTO", 10)
    called = False

    async def downstream(scope, receive, send):
        nonlocal called
        called = True

    messages = iter(
        [
            {"type": "http.request", "body": b"123456", "more_body": True},
            {"type": "http.request", "body": b"123456", "more_body": False},
        ]
    )

    async def receive():
        return next(messages)

    output = []

    async def send(message):
        output.append(message)

    await AdjuntoBodyLimitMiddleware(downstream)(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [] if length is None else [(b"content-length", length)],
        },
        receive,
        send,
    )
    assert not called
    assert output[0]["status"] == 413


async def test_body_pequeno_sin_content_length_llega_al_parser():
    received = []

    async def downstream(scope, receive, send):
        received.append(await receive())

    async def receive():
        return {"type": "http.request", "body": b"ok", "more_body": False}

    async def send(message):
        pass

    await AdjuntoBodyLimitMiddleware(downstream)(
        {"type": "http", "method": "POST", "path": "/gastos/1/adjuntos", "headers": []},
        receive,
        send,
    )
    assert received[0]["body"] == b"ok"
