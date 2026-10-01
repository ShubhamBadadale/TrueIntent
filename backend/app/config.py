"""Environment-driven configuration.

Every value has a safe default so the API starts with no configuration at all.
Nothing here is a secret and nothing is echoed back to clients: see
`docs/LIMITATIONS.md` and the sanitiser in `ml.error_safety`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

API_VERSION = 'v1'
API_PREFIX = '/api/v1'

_TRUTHY = {'1', 'true', 'yes', 'on'}
_FALSY = {'0', 'false', 'no', 'off'}


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    return default if value is None or value.strip() == '' else value.strip()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == '':
        return default
    token = raw.strip().lower()
    if token in _TRUTHY:
        return True
    if token in _FALSY:
        return False
    # An unparseable flag must not silently loosen or tighten behaviour.
    return default


def _env_int(name: str, default: int, *, minimum: int = 1, maximum: int = 2 ** 31 - 1) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == '':
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def _env_list(name: str) -> tuple[str, ...]:
    raw = os.environ.get(name, '')
    return tuple(item.strip() for item in raw.split(',') if item.strip())


def _env_float(name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == '':
        return default
    try:
        value = float(raw.strip())
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the process configuration."""

    environment: str
    host: str
    port: int
    log_level: str
    log_format: str
    request_id_header: str
    cors_origins: tuple[str, ...]
    cors_allow_localhost: bool
    cors_allow_credentials: bool
    cors_allow_methods: tuple[str, ...]
    max_url_chars: int
    max_text_chars: int
    max_image_bytes: int
    max_image_pixels: int
    max_request_bytes: int
    ocr_timeout_seconds: int
    readiness_cache_ttl: float
    _is_production: bool = field(default=False, repr=False)

    @property
    def is_production(self) -> bool:
        return self._is_production

    def public_summary(self) -> dict:
        """Configuration that is safe to log or return: names and effective
        limits only. No values that could carry a host, path or credential."""
        return {
            'environment': self.environment,
            'api_version': API_VERSION,
            'log_level': self.log_level,
            'log_format': self.log_format,
            'cors_origin_count': len(self.cors_origins),
            'cors_allow_localhost': self.cors_allow_localhost,
            'cors_allow_credentials': self.cors_allow_credentials,
            'limits': {
                'url_chars': self.max_url_chars,
                'text_chars': self.max_text_chars,
                'image_bytes': self.max_image_bytes,
                'image_pixels': self.max_image_pixels,
                'request_bytes': self.max_request_bytes,
                'ocr_timeout_seconds': self.ocr_timeout_seconds,
            },
        }


def load_settings() -> Settings:
    environment = _env_str('TRUEINTENT_ENV', 'development').lower()
    if environment not in {'development', 'test', 'staging', 'production'}:
        environment = 'development'
    production = environment == 'production'
    return Settings(
        environment=environment,
        host=_env_str('TRUEINTENT_HOST', '127.0.0.1'),
        port=_env_int('TRUEINTENT_PORT', 8000, minimum=1, maximum=65535),
        log_level=_env_str('TRUEINTENT_LOG_LEVEL', 'INFO').upper(),
        log_format=_env_str('TRUEINTENT_LOG_FORMAT', 'text').lower(),
        request_id_header=_env_str('TRUEINTENT_REQUEST_ID_HEADER', 'X-Request-ID'),
        cors_origins=_env_list('TRUEINTENT_CORS_ORIGINS'),
        # A regex fallback is a development convenience, not a deployment
        # posture: production must enumerate origins explicitly.
        cors_allow_localhost=_env_bool(
            'TRUEINTENT_CORS_ALLOW_LOCALHOST', not production),
        cors_allow_credentials=_env_bool('TRUEINTENT_CORS_ALLOW_CREDENTIALS', False),
        cors_allow_methods=_env_list('TRUEINTENT_CORS_ALLOW_METHODS')
                             or ('GET', 'POST', 'OPTIONS'),
        max_url_chars=_env_int('TRUEINTENT_MAX_URL_CHARS', 8192, minimum=16, maximum=1 << 16),
        max_text_chars=_env_int('TRUEINTENT_MAX_TEXT_CHARS', 20000, minimum=16, maximum=1 << 20),
        max_image_bytes=_env_int('TRUEINTENT_MAX_IMAGE_BYTES', 10 * 1024 * 1024,
                                 minimum=1, maximum=64 * 1024 * 1024),
        max_image_pixels=_env_int('TRUEINTENT_MAX_IMAGE_PIXELS', 10_000_000,
                                  minimum=10_000, maximum=200_000_000),
        # Headroom above the largest single upload for multipart framing and
        # ordinary JSON bodies. Anything larger is rejected at the gate.
        max_request_bytes=_env_int('TRUEINTENT_MAX_REQUEST_BYTES', 12 * 1024 * 1024,
                                   minimum=1, maximum=256 * 1024 * 1024),
        ocr_timeout_seconds=_env_int('TRUEINTENT_OCR_TIMEOUT_SECONDS', 15,
                                     minimum=1, maximum=120),
        readiness_cache_ttl=_env_float('TRUEINTENT_READINESS_CACHE_TTL', 15.0,
                                       minimum=0.0, maximum=600.0),
        _is_production=production,
    )


SETTINGS = load_settings()