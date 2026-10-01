"""Readiness probes: honest per-component status without changing serving.

Every probe uses the same loaders the serving path uses, so `/ready` reports
what a request would actually experience. Probes never raise; they return a
status triple. Results are cached for a short TTL because unpickling is not
free — the cache only ever makes the answer staler, never more optimistic
than the last real probe (a component that was failing stays failing until
the TTL expires and a fresh probe disagrees).

Statuses:
- ``ok`` — the component serves real answers.
- ``degraded`` — the component serves, but only a fallback (rules-only,
  fixed weights). Requests still succeed.
- ``unavailable`` — the component's endpoints will answer 503 with a reason.
- ``error`` — the component is actively broken (e.g. a corrupt artifact that
  raises instead of falling back). The deployment is not ready.

``detail`` strings are fixed, client-safe sentences; no paths, versions of
local files, or exception text ever leave the process here.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass

from backend.app.config import SETTINGS
from backend.app.observability import get_logger

logger = get_logger(__name__)

_OK = 'ok'
_DEGRADED = 'degraded'
_UNAVAILABLE = 'unavailable'
_ERROR = 'error'


@dataclass(frozen=True)
class ComponentStatus:
    name: str
    status: str
    detail: str

    def to_dict(self) -> dict:
        return {'name': self.name, 'status': self.status, 'detail': self.detail}


_CACHE: dict[str, tuple[float, ComponentStatus]] = {}


def reset_cache() -> None:
    _CACHE.clear()


def _cached(name: str, probe) -> ComponentStatus:
    now = time.monotonic()
    hit = _CACHE.get(name)
    if hit is not None and now - hit[0] < SETTINGS.readiness_cache_ttl:
        return hit[1]
    try:
        status = probe()
    except Exception:  # A probe must never take /ready down with it.
        logger.exception('Readiness probe %r failed unexpectedly', name)
        status = ComponentStatus(name, _ERROR, 'Readiness probe failed unexpectedly.')
    _CACHE[name] = (now, status)
    return status


def probe_module_a() -> ComponentStatus:
    from ml.features_module_a import ModuleAUnavailableError
    from ml.predict_module_a import load_model

    try:
        load_model()
    except ModuleAUnavailableError:
        return ComponentStatus(
            'module_a', _UNAVAILABLE,
            'Benchmark artifact absent or incompatible; the benchmark endpoint answers 503.',
        )
    except Exception:
        logger.exception('Module A probe failed')
        return ComponentStatus(
            'module_a', _ERROR, 'Benchmark artifact could not be inspected.')
    return ComponentStatus('module_a', _OK, 'Benchmark artifact loaded.')


def probe_module_b() -> ComponentStatus:
    from ml.predict_module_b import _load_ml_model

    try:
        artifact = _load_ml_model()
    except Exception:
        logger.exception('Module B probe failed')
        return ComponentStatus('module_b', _ERROR, 'URL classifier could not be inspected.')
    if artifact is None:
        return ComponentStatus(
            'module_b', _DEGRADED,
            'Classifier artifact absent; offline rules serve with rules_only status.',
        )
    return ComponentStatus('module_b', _OK, 'URL classifier active.')


def probe_module_c() -> ComponentStatus:
    from ml.predict_module_c import _load_ml_model

    try:
        artifact = _load_ml_model()
    except Exception:
        logger.exception('Module C probe failed')
        return ComponentStatus('module_c', _ERROR, 'Message model could not be inspected.')
    if artifact is None:
        return ComponentStatus(
            'module_c', _UNAVAILABLE,
            'Message model absent; text and screenshot analysis answer 503.',
        )
    return ComponentStatus('module_c', _OK, 'Message model active.')


def probe_module_d() -> ComponentStatus:
    from ml.predict_module_d import ModuleDUnavailableError, _load_learned_model

    try:
        artifact = _load_learned_model()
    except ModuleDUnavailableError:
        return ComponentStatus(
            'module_d', _ERROR,
            'Fusion artifact is corrupt or incompatible; unified scoring raises.',
        )
    except Exception:
        logger.exception('Module D probe failed')
        return ComponentStatus('module_d', _ERROR, 'Fusion model could not be inspected.')
    if artifact is None:
        return ComponentStatus(
            'module_d', _DEGRADED,
            'Learned policy absent; fixed-weight fallback serves and says so.',
        )
    return ComponentStatus('module_d', _OK, 'Learned fusion policy active.')


def probe_ocr() -> ComponentStatus:
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return ComponentStatus(
            'ocr', _UNAVAILABLE, 'pytesseract is not installed; text flows are unaffected.',
        )
    from ml.ocr_module_c import resolve_tesseract_command

    binary = resolve_tesseract_command()
    if not binary:
        return ComponentStatus(
            'ocr', _UNAVAILABLE,
            'Tesseract engine binary not found; screenshot analysis answers 503.',
        )
    return ComponentStatus('ocr', _OK, 'Tesseract engine reachable.')


_PROBE_NAMES = ('module_a', 'module_b', 'module_c', 'module_d', 'ocr')


def collect_statuses() -> list[ComponentStatus]:
    """Probe every component, in a fixed order, with the TTL cache.

    Probes resolve by name at call time (not from a frozen tuple) so tests can
    substitute a single probe without touching the others.
    """
    module = sys.modules[__name__]
    return [_cached(name, getattr(module, f'probe_{name}')) for name in _PROBE_NAMES]


def overall_status(statuses: list[ComponentStatus]) -> tuple[str, bool, bool]:
    """Return (status_word, degraded, ready).

    ``ready`` is False only when a component is actively broken. A deployment
    with missing-but-honest models is degraded, not down: that is the designed
    operating mode on a clean checkout.
    """
    states = {status.status for status in statuses}
    if _ERROR in states:
        return 'not_ready', True, False
    if _UNAVAILABLE in states or _DEGRADED in states:
        return 'degraded', True, True
    return 'ready', False, True


def failing_component(statuses: list[ComponentStatus]) -> ComponentStatus | None:
    for status in statuses:
        if status.status == _ERROR:
            return status
    return None
