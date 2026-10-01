"""Response envelopes for the ``/api/v1`` contract.

Success:
    {"success": true, "data": {...}, "meta": {"request_id": "...", "api_version": "v1"}}

Failure:
    {"success": false, "error": {"code": "...", "message": "...",
                                 "module": "...", "details": {...}},
     "meta": {"request_id": "...", "api_version": "v1"}}

A failure always carries ``meta`` too: a mobile client that logs an error needs
the correlation ID as much as it does on success.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.config import API_VERSION
from backend.app.errors import AppError
from backend.app.safety import contains_forbidden, redact_paths

_GENERIC_FAILURE = 'The request could not be completed. Please retry.'


class ResponseMeta(BaseModel):
    """Envelope metadata present on every response."""

    model_config = ConfigDict(extra='forbid')

    request_id: str = Field(description='Correlation ID, also sent as X-Request-ID')
    api_version: str = Field(default=API_VERSION)


class ErrorBody(BaseModel):
    """Failure payload. `message` is safe to show to an end user."""

    model_config = ConfigDict(extra='forbid')

    code: str = Field(description='Stable machine-readable error identifier')
    message: str = Field(description='Human-readable, safe to display')
    module: str | None = Field(default=None, description='Which module produced the failure')
    details: dict[str, Any] = Field(default_factory=dict)


def _client_safe_message(exc: AppError) -> str:
    """Final gate before a message leaves the process.

    `AppError.message` is authored in `errors.py` and normally never carries
    upstream exception text. This guards the cases where one slips through: an
    internal error, a traceback marker, or a filesystem path.
    """
    if exc.derived_from_exception:
        return _GENERIC_FAILURE
    message = exc.message
    if contains_forbidden(message):
        return _GENERIC_FAILURE
    if '\\' in message or '://' not in message and _looks_like_path(message):
        message = redact_paths(message)
    return message or _GENERIC_FAILURE


def _looks_like_path(message: str) -> bool:
    return any(part.startswith('/') and len(part) > 1 for part in message.split())


def success_body(data: dict[str, Any], request_id: str) -> dict[str, Any]:
    return {
        'success': True,
        'data': data,
        'meta': ResponseMeta(request_id=request_id).model_dump(),
    }


def error_body(exc: AppError, request_id: str) -> dict[str, Any]:
    return {
        'success': False,
        'error': ErrorBody(
            code=exc.code,
            message=_client_safe_message(exc),
            module=exc.module,
            details=exc.details,
        ).model_dump(),
        'meta': ResponseMeta(request_id=request_id).model_dump(),
    }


class ErrorEnvelope(BaseModel):
    """Shape of a failure body, for OpenAPI documentation and client models."""

    model_config = ConfigDict(extra='forbid')

    success: bool = False
    error: ErrorBody
    meta: ResponseMeta