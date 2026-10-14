"""Límite real de bytes antes del parser multipart y de sus archivos temporales."""

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY_ADJUNTO = 9 * 1024 * 1024


class AdjuntoBodyLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or not scope["path"].rstrip("/").endswith("/adjuntos")
        ):
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        length = headers.get(b"content-length")
        if length is not None and (not length.isdigit() or int(length) > MAX_BODY_ADJUNTO):
            return await JSONResponse(
                status_code=413, content={"detail": "Archivo demasiado grande"}
            )(scope, receive, send)
        # Acumular como máximo 9 MB: incluye clientes chunked o headers falsos.
        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > MAX_BODY_ADJUNTO:
                return await JSONResponse(
                    status_code=413, content={"detail": "Archivo demasiado grande"}
                )(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        delivered = False

        async def bounded_receive() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)
