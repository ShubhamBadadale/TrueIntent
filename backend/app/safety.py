"""Redaction helpers that keep internal detail out of client-visible strings.

Server logs may carry diagnostic detail; HTTP response bodies may not. These
helpers are the single place where that boundary is enforced, so a new call site
cannot accidentally leak a path, an environment value or a traceback.
"""
from __future__ import annotations

import os
import re

#: Replacement token substituted for anything path-shaped.
REDACTED = '<redacted>'

_WINDOWS_PATH = re.compile(r'(?:[A-Za-z]:\\|\\\\)[^\s\'"<>|,;)\]]*')
_POSIX_PATH = re.compile(r'(?<![\w.])/(?:[\w.+@-]+/)*[\w.+@-]+')
#: `KEY=value` / `KEY: value` pairs that look like configuration.
_ENV_ASSIGNMENT = re.compile(
    r'\b(?:[A-Z][A-Z0-9_]{2,})(?:=|:)\s*\S+'
)

#: Substrings that must never appear in a response body.
_FORBIDDEN_FRAGMENTS = (
    'Traceback (most recent call last)',
    'File "',
    'site-packages',
    '  File "/',
)


def redact_paths(text: str) -> str:
    """Replace filesystem paths and config assignments with a token."""
    if not text:
        return text
    cleaned = _WINDOWS_PATH.sub(REDACTED, text)
    cleaned = _POSIX_PATH.sub(REDACTED, cleaned)
    cleaned = _ENV_ASSIGNMENT.sub(REDACTED, cleaned)
    return cleaned


def contains_forbidden(text: str) -> bool:
    """True when a string looks like it leaks internals."""
    if not text:
        return False
    return any(fragment in text for fragment in _FORBIDDEN_FRAGMENTS)


def safe_exception_message(exc: BaseException, fallback: str, *, limit: int = 300) -> str:
    """A client-safe rendering of an exception message.

    Prefers the fallback: upstream exception text is only used when it is short,
    carries no path or traceback marker, and does not echo this process's
    environment.
    """
    raw = str(exc).strip()
    if not raw:
        return fallback
    if contains_forbidden(raw):
        return fallback
    redacted = redact_paths(raw)
    if REDACTED in redacted and not raw.startswith(REDACTED):
        # A path was removed; a partially redacted message reads as noise.
        return fallback
    if len(redacted) > limit:
        return fallback
    for name, value in os.environ.items():
        # Only guard against echoing a value that looks like a credential or a
        # filesystem location. Ordinary settings must not censor normal prose.
        if len(value) < 8:
            continue
        if ('/' in value or '\\' in value) and value in redacted:
            return fallback
    return redacted


#: URLs are redacted from the checked text first: only a bare path is evidence
#: of a leak, never the path part of an address the API itself mentions.
_URL = re.compile(r'https?://[^\s\'"<>]+')

#: API routes are not filesystem paths.
_API_PATH = re.compile(r'^/(?:api/|check-|health|ready|docs|openapi\.json|redoc)')


def assert_no_internal_detail(payload: str, *, where: str = 'response') -> None:
    """Guard used by the test suite: raise if a body would leak internals."""
    if contains_forbidden(payload):
        raise AssertionError(f'{where} leaked internal detail: {payload[:200]!r}')
    for match in _WINDOWS_PATH.finditer(payload):
        raise AssertionError(f'{where} leaked a Windows path: {match.group(0)!r}')
    scrubbed = _URL.sub('', payload)
    for match in _POSIX_PATH.finditer(scrubbed):
        candidate = match.group(0)
        # API paths such as "/api/v1/analyze/url" are not filesystem paths.
        if _API_PATH.match(candidate) or candidate == '/':
            continue
        raise AssertionError(f'{where} leaked a filesystem path: {candidate!r}')