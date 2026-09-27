"""Linha de log JSON por requisicao (issue #103, parent #101).

Decisao de topic-aws-observability (#99): o backend escreve no stdout uma
linha JSON por requisicao a ``/v1/*``, no mesmo formato no Compose e na
AWS (CloudWatch Logs le o stdout do container ECS), para depurar uma
busca de ponta a ponta. Campos::

    {"ts", "method", "path", "status", "duration_ms",
     "user_id", "trace_id", "search_request_id"}

Campos sem valor saem como ``"-"`` (nunca omitidos, nunca ``null``).

- ``user_id``: lido de ``request.state.user_id``. Hoje (``AUTH_MODE=none``)
  ninguem preenche e sai ``"-"``; o futuro modulo de auth (#104,
  ``AUTH_MODE=cognito``) grava ali o claim ``username`` do token.
- ``trace_id``: header ``X-Amzn-Trace-Id`` posto pelo ALB, repassado como
  veio.
- ``search_request_id``: lido de ``request.state.search_request_id``, que
  so ``POST /v1/search`` preenche (igual ao ``request_id`` do envelope,
  liga a linha a ``SearchExecution`` e ao replay).

A linha nunca contem corpo, query string, headers (``Authorization``
incluso) nem texto da consulta - so os campos acima. O ``path`` e o da
rota sem query string.

Implementado como middleware ASGI puro (nao ``BaseHTTPMiddleware``) para
compartilhar o mesmo ``scope["state"]`` com a rota e para ver a excecao
de um 500 antes do ``ServerErrorMiddleware`` do Starlette.
"""

import json
import sys
import time
from datetime import UTC, datetime

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_EMPTY = "-"


def mark_search_request(request: Request, request_id: str) -> None:
    """Liga a linha de log desta requisicao ao ``request_id`` da busca."""
    request.state.search_request_id = request_id


class RequestLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/v1/"):
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        status = 500

        async def _send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, _send)
        finally:
            _write_line(scope, status, started)


def _write_line(scope: Scope, status: int, started: float) -> None:
    state = scope.get("state") or {}
    line = {
        "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "method": scope["method"],
        "path": scope["path"],
        "status": status,
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        "user_id": state.get("user_id") or _EMPTY,
        "trace_id": _header(scope, b"x-amzn-trace-id") or _EMPTY,
        "search_request_id": state.get("search_request_id") or _EMPTY,
    }
    sys.stdout.write(json.dumps(line, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value.decode("latin-1")
    return None
