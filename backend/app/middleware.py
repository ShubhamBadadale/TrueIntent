"""ASGI middleware: request correlation, access logging, and size gating.

Pure ASGI (not ``BaseHTTPMiddleware``) so the request body stream reaches the
route untouched — a middleware that pre-reads the body would defeat the bounded
upload reads in :mod:`backend.app.validation`.

No request bodies, URLs, message text or headers are ever logged here: the
access line carries the method, path, status, duration and request ID only.
"""
from __future__ import annotations

import time

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.app.config import SETTINGS
from backend.app.errors import PayloadTooLarge
from backend.app.envelope import error_body
from backend.app.observability import (
    _request_id as _request_id_var,
    _start_time as _start_time_var,
    elapsed_ms,
    get_request_id,
    get_logger,
    new_request_id,
    sanitise_request_id,
    set_request_id,
    set_start_time,
)

logger = get_logger(__name__)


class RequestContextMiddleware:
    """Assign/validate the request ID, time the request, log the outcome."""

    def __init__(self, app: ASGIApp, *, request_id_header: str | None = None) -> None:
        self.app = app
        self.request_id_header = request_id_header or SETTINGS.request_id_header
        self._canonical = self.request_id_header.lower().encode('latin-1')
        self._header_bytes = self.request_id_header.encode('latin-1')

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] not in ('http', 'websocket'):
            await self.app(scope, receive, send)
            return

        inbound: str | None = None
        for name, value in scope.get('headers', []):
            if name == self._canonical:
                inbound = value.decode('latin-1')
                break
        request_id = sanitise_request_id(inbound) or new_request_id()

        id_token = set_request_id(request_id)
        time_token = set_start_time(time.perf_counter())
        outcome: dict[str, int | None] = {'status': None}

        async def send_wrapper(message: Message) -> None:
            if message['type'] == 'http.response.start':
                outcome['status'] = message.get('status')
                headers = MutableHeaders(raw=message.setdefault('headers', []))
                headers[self.request_id_header] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            try:
                if scope['type'] == 'http':
                    logger.info(
                        '%s %s -> %s',
                        scope.get('method'),
                        scope.get('path'),
                        outcome['status'],
                        extra={
                            'request_id': request_id,
                            'method': scope.get('method'),
                            'path': scope.get('path'),
                            'status_code': outcome['status'],
                            'duration_ms': elapsed_ms(),
                        },
                    )
            finally:
                _request_id_var.reset(id_token)
                _start_time_var.reset(time_token)


class RequestSizeMiddleware:
    """Reject oversized request bodies at the gate, before anything is read.

    Image uploads are bounded again per part in
    :func:`backend.app.validation.read_upload_bounded`; this ceiling exists so
    that a single enormous ``Content-Length`` (or a slow-drip body with no
    declared length on a JSON route) cannot force an unbounded allocation.

    Failures keep the caller's contract: the v1 envelope on ``/api/v1/*``,
    FastAPI's flat ``{"detail": ...}`` shape everywhere else.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int | None = None) -> None:
        self.app = app
        # An explicit constructor value wins; otherwise the limit follows the
        # process settings at request time (tests can narrow it per case).
        self._override = max_bytes

    @property
    def _limit(self) -> int:
        return self._override if self._override is not None else SETTINGS.max_request_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        declared: int | None = None
        for name, value in scope.get('headers', []):
            if name == b'content-length':
                try:
                    declared = int(value.decode('latin-1'))
                except ValueError:
                    declared = None
                break
        if declared is not None and declared > self._limit:
            message = 'Request body is larger than this deployment accepts.'
            request_id = get_request_id() or new_request_id()
            if scope.get('path', '').startswith('/api/v1'):
                body = error_body(
                    PayloadTooLarge(message, details={'max_bytes': self._limit}),
                    request_id,
                )
            else:
                body = {'detail': message}
            from starlette.responses import JSONResponse

            response = JSONResponse(body, status_code=413)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
