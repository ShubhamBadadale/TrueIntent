"""Per-request context (correlation ID) and structured logging.

Request IDs are generated here, validated on the way in, and attached to the
response so a client can quote them. Log records carry the same ID, which is
what makes a user-reported failure traceable.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

from backend.app.config import SETTINGS

_request_id: ContextVar[str | None] = ContextVar('trueintent_request_id', default=None)
_start_time: ContextVar[float | None] = ContextVar('trueintent_start_time', default=None)

#: Only conservative characters are accepted from a client, so a request ID can
#: never be used to forge log lines or inject headers.
SAFE_REQUEST_ID = re.compile(r'\A[A-Za-z0-9._:-]{1,64}\Z')

#: Keys promoted from `extra=` into the structured log record.
_CONTEXT_FIELDS = (
    'request_id', 'method', 'path', 'status_code', 'duration_ms',
    'error_code', 'client_ip', 'user_agent', 'content_length',
)


def new_request_id() -> str:
    return uuid.uuid4().hex


def sanitise_request_id(candidate: str | None) -> str | None:
    """Accept an inbound request ID only when it is safe to echo and log."""
    if not candidate:
        return None
    value = candidate.strip()
    return value if SAFE_REQUEST_ID.match(value) else None


def set_request_id(value: str | None):
    """Set the current request ID, returning the token for later reset."""
    return _request_id.set(value)


def get_request_id() -> str | None:
    return _request_id.get()


def set_start_time(value: float | None):
    """Set the request start clock, returning the token for later reset."""
    return _start_time.set(value)


def get_start_time() -> float | None:
    return _start_time.get()


def elapsed_ms() -> float | None:
    started = _start_time.get()
    if started is None:
        return None
    return round((time.perf_counter() - started) * 1000, 2)


class ContextFilter(logging.Filter):
    """Attach the current request ID and duration to every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'request_id'):
            record.request_id = get_request_id()
        for field in _CONTEXT_FIELDS:
            if not hasattr(record, field):
                setattr(record, field, None)
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line, for log shipping."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            'ts': self.formatTime(record, '%Y-%m-%dT%H:%M:%S%z'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': getattr(record, 'request_id', None),
        }
        for field in _CONTEXT_FIELDS[1:]:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            # Full detail belongs in the log, never in an HTTP response body.
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable single line, with the request ID up front."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, 'request_id', None) or '-'
        base = f'{self.formatTime(record, "%H:%M:%S")} {record.levelname:<7} {request_id} ' \
               f'{record.name}: {record.getMessage()}'
        extras = []
        for field in _CONTEXT_FIELDS[1:]:
            value = getattr(record, field, None)
            if value is not None:
                extras.append(f'{field}={value}')
        if extras:
            base += ' | ' + ' '.join(extras)
        if record.exc_info:
            base += '\n' + self.formatException(record.exc_info)
        return base


def configure_logging() -> None:
    """Install the project formatter on the root and uvicorn loggers."""
    level = getattr(logging, SETTINGS.log_level, logging.INFO)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter() if SETTINGS.log_format == 'json' else TextFormatter())
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)

    # uvicorn installs its own handlers; route them through ours instead so a
    # request ID is never missing from an access log line.
    for name in ('uvicorn', 'uvicorn.error', 'uvicorn.access'):
        logger = logging.getLogger(name)
        for existing in list(logger.handlers):
            logger.removeHandler(existing)
        logger.addHandler(handler)
        logger.propagate = False
        logger.setLevel(level)
    logging.getLogger('uvicorn.access').propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)