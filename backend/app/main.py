"""TrueIntent FastAPI backend — Modules A-D wiring.

Run from the repo root (the single documented command):

    .\\.venv\\Scripts\\python.exe -m backend --port 8000

Two route generations share one service layer:

* ``/api/v1/*`` — the mobile-ready contract. Successes return
  ``{"success": true, "data": {...}, "meta": {...}}``; failures return
  ``{"success": false, "error": {...}, "meta": {...}}``.
* ``/check-*`` — frozen legacy routes returning the original flat bodies and
  ``{"detail": ...}`` errors, so existing clients keep working unchanged.

``/health`` (liveness) and ``/ready`` (readiness) complete the surface.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app import health, legacy_routes, v1_routes
from backend.app.config import API_VERSION, SETTINGS, Settings
from backend.app.envelope import error_body
from backend.app.errors import (
    STATUS_CODE_MAP,
    AppError,
    ErrorCode,
    InternalError,
    ValidationFailed,
)
from backend.app.middleware import RequestContextMiddleware, RequestSizeMiddleware
from backend.app.observability import configure_logging, get_logger, get_request_id
from backend.app.safety import redact_paths
from backend.app.services import FUSION_DISABLED_MESSAGE

logger = get_logger(__name__)

_LOCALHOST_ORIGIN_REGEX = r'http://(localhost|127\.0\.0\.1)(:\d+)?'


def _is_v1(request: Request) -> bool:
    return request.url.path.startswith('/api/v1')


def _request_id() -> str:
    return get_request_id() or 'unknown'


def _validation_details(exc: RequestValidationError) -> dict:
    """Field-level failure summary without echoing submitted values.

    ``errors()`` entries contain the offending ``input`` (message text, URLs)
    and sometimes ``ctx`` — neither is returned. Only location, message and
    error type cross the boundary.
    """
    fields = []
    saw_transaction = False
    for entry in exc.errors():
        loc = entry.get('loc', ())
        parts = [str(part) for part in loc if str(part) != 'body']
        if any(part == 'transaction' for part in parts):
            saw_transaction = True
        fields.append({
            'field': '.'.join(parts),
            'message': str(entry.get('msg', '')),
            'type': str(entry.get('type', '')),
        })
    details: dict = {'fields': fields}
    if saw_transaction:
        # The v1 combined schema has no transaction field at all; explain why.
        details['hint'] = FUSION_DISABLED_MESSAGE
    return details


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = _request_id()
    logger.warning(
        'request failed: %s', exc.code,
        extra={'request_id': request_id, 'method': request.method,
               'path': request.url.path, 'status_code': exc.status_code,
               'error_code': exc.code},
    )
    if _is_v1(request):
        return JSONResponse(
            status_code=exc.status_code, content=error_body(exc, request_id),
        )
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.message})


async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = _request_id()
    logger.warning(
        'request validation failed',
        extra={'request_id': request_id, 'method': request.method,
               'path': request.url.path, 'status_code': 422,
               'error_code': ErrorCode.VALIDATION_ERROR},
    )
    if _is_v1(request):
        err = ValidationFailed(
            'The request was not valid.', details=_validation_details(exc),
        )
        return JSONResponse(status_code=422, content=error_body(err, request_id))
    from fastapi.encoders import jsonable_encoder

    return JSONResponse(
        status_code=422, content={'detail': jsonable_encoder(exc.errors())},
    )


async def _http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = _request_id()
    code = STATUS_CODE_MAP.get(exc.status_code, ErrorCode.VALIDATION_ERROR)
    if _is_v1(request):
        err = AppError(
            _default_v1_message(exc.status_code, exc.detail),
            code=code, status_code=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code, content=error_body(err, request_id),
        )
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})


def _default_v1_message(status_code: int, detail) -> str:
    if status_code == 404:
        return 'Unknown endpoint.'
    if status_code == 405:
        return 'Method not allowed for this endpoint.'
    if isinstance(detail, str) and detail and len(detail) <= 300:
        return redact_paths(detail)
    if status_code == 413:
        return 'Request body is larger than this deployment accepts.'
    if status_code == 415:
        return 'Unsupported media type.'
    return 'The request could not be completed.'


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = _request_id()
    # Full traceback stays in the server log. The client gets nothing but a
    # correlation ID and a retry instruction.
    logger.error(
        'unhandled exception for %s %s', request.method, request.url.path,
        exc_info=True,
        extra={'request_id': request_id, 'method': request.method,
               'path': request.url.path, 'status_code': 500,
               'error_code': ErrorCode.INTERNAL_ERROR},
    )
    # The header is set explicitly here: the ServerErrorMiddleware invokes this
    # handler outside the request-context middleware, so its send-wrapper never
    # runs for these responses.
    headers = {SETTINGS.request_id_header: request_id}
    if _is_v1(request):
        return JSONResponse(
            status_code=500,
            content=error_body(InternalError('Unexpected failure.'), request_id),
            headers=headers,
        )
    return JSONResponse(
        status_code=500,
        content={'detail': 'Internal server error. Please retry.'},
        headers=headers,
    )


def _configure_cors(app: FastAPI, settings: Settings) -> None:
    origins = [origin for origin in settings.cors_origins]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=list(settings.cors_allow_methods),
            allow_headers=['*'],
        )
        logger.info('CORS: %d explicit origin(s)', len(origins))
    elif settings.cors_allow_localhost:
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=_LOCALHOST_ORIGIN_REGEX,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=list(settings.cors_allow_methods),
            allow_headers=['*'],
        )
        logger.info('CORS: local development origins only')
    else:
        logger.warning('CORS: no origins configured; browsers cannot call this API')
    if settings.is_production and not origins:
        logger.warning(
            'Production without TRUEINTENT_CORS_ORIGINS: same-origin and '
            'non-browser clients only.'
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Accepts explicit settings so tests can vary CORS."""
    settings = settings or SETTINGS
    configure_logging()

    app = FastAPI(
        title='TrueIntent API',
        version='0.2.0',
        description=(
            'Multi-channel fraud-intent analysis. `/api/v1/*` is the versioned '
            'contract; `/check-*` routes are frozen for compatibility.'
        ),
    )

    app.add_middleware(RequestSizeMiddleware, max_bytes=settings.max_request_bytes)
    app.add_middleware(
        RequestContextMiddleware, request_id_header=settings.request_id_header,
    )
    _configure_cors(app, settings)

    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_handler)
    app.add_exception_handler(Exception, _unhandled_handler)

    app.include_router(health.router)
    app.include_router(v1_routes.router)
    app.include_router(legacy_routes.router)

    logger.info(
        'TrueIntent API ready (api_version=%s, environment=%s)',
        API_VERSION, settings.environment,
        extra={'api_version': API_VERSION},
    )
    return app


# The module-level application: `backend.app.main:app`.
app = create_app()


if __name__ == '__main__':  # pragma: no cover - use `python -m backend`
    import uvicorn

    uvicorn.run(
        'backend.app.main:app', host=SETTINGS.host, port=SETTINGS.port, log_config=None,
    )
