"""Liveness and readiness.

- ``GET /`` — service identity, unchanged from the original contract.
- ``GET /health`` — liveness: 200 whenever the process answers. Used by the
  Docker healthcheck. It says nothing about models; that is ``/ready``'s job.
- ``GET /ready`` — readiness: 200 when the API can serve (possibly degraded),
  503 with the same body shape when a component is actively broken.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app import diagnostics
from backend.app.config import API_VERSION
from backend.app.envelope import error_body, success_body
from backend.app.errors import ModelUnavailable
from backend.app.observability import get_request_id

router = APIRouter(tags=['health'])

SERVICE_NAME = 'TrueIntent API'
APP_VERSION = '0.2.0'


@router.get('/')
def root():
    return {'status': 'ok', 'service': SERVICE_NAME, 'version': APP_VERSION}


@router.get('/health')
def health():
    return {'status': 'ok'}


@router.get('/ready')
def ready():
    """Component diagnostics with honest degraded/not-ready semantics."""
    request_id = get_request_id() or ''
    statuses = diagnostics.collect_statuses()
    status_word, degraded, ready_ok = diagnostics.overall_status(statuses)
    data = {
        'status': status_word,
        'service': SERVICE_NAME,
        'api_version': API_VERSION,
        'degraded': degraded,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'components': [status.to_dict() for status in statuses],
    }
    if ready_ok:
        return JSONResponse(status_code=200, content=success_body(data, request_id))
    failing = diagnostics.failing_component(statuses)
    exc = ModelUnavailable(
        f'{SERVICE_NAME} is not ready: {failing.name} requires attention.'
        if failing is not None else f'{SERVICE_NAME} is not ready.',
        module=failing.name if failing is not None else None,
        details={'readiness': data},
    )
    return JSONResponse(status_code=503, content=error_body(exc, request_id))
