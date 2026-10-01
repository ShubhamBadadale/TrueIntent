"""Unit tests for the hardening primitives: redaction, config parsing,
request-ID validation, boundary guards and diagnostics logic.

These cover the code paths that integration tests cannot reach without
rewriting the process environment or faking the filesystem.
"""
from __future__ import annotations

import pytest

from backend.app import safety
from backend.app.config import load_settings
from backend.app.observability import sanitise_request_id


# -----------------------------------------------------------------------------
# safety.redact_paths / safe_exception_message
# -----------------------------------------------------------------------------
def test_redact_paths_masks_windows_and_posix():
    assert safety.redact_paths(r"failed at C:\secret\models\x.pkl") == \
        "failed at <redacted>"
    assert safety.redact_paths("failed at /var/lib/secret/x.pkl") == \
        "failed at <redacted>"
    assert safety.redact_paths("plain message") == "plain message"
    assert safety.redact_paths("") == ""


def test_safe_exception_message_prefers_the_fallback():
    assert safety.safe_exception_message(ValueError(""), "fallback") == "fallback"
    assert safety.safe_exception_message(
        RuntimeError("Traceback (most recent call last): boom"), "fallback") == "fallback"
    assert safety.safe_exception_message(
        OSError("bad file C:\\tmp\\x"), "fallback") == "fallback"
    assert safety.safe_exception_message(ValueError("short and clean"), "fallback") == \
        "short and clean"
    assert safety.safe_exception_message(ValueError("x" * 500), "fallback") == "fallback"


def test_assert_no_internal_detail_accepts_api_shapes():
    safety.assert_no_internal_detail('{"detail": "Not Found"}')
    safety.assert_no_internal_detail(
        '{"message": "Invalid URL. Expected an HTTP(S) address such as https://example.com/login."}'
    )
    safety.assert_no_internal_detail('{"path": "/api/v1/analyze/url"}')
    with pytest.raises(AssertionError):
        safety.assert_no_internal_detail('File "C:\\a\\b.py", line 3')
    with pytest.raises(AssertionError):
        safety.assert_no_internal_detail("open failed: /etc/trueintent/key")


def test_envelope_never_carries_derived_text():
    from backend.app.envelope import error_body
    from backend.app.errors import InternalError

    body = error_body(InternalError("kaboom at C:\\secret\\x"), "rid")
    assert body["error"]["message"] == "The request could not be completed. Please retry."
    assert body["meta"]["request_id"] == "rid"


# -----------------------------------------------------------------------------
# config parsing
# -----------------------------------------------------------------------------
def test_config_parses_typed_env(monkeypatch):
    monkeypatch.setenv("TRUEINTENT_PORT", "9001")
    monkeypatch.setenv("TRUEINTENT_CORS_ORIGINS", "https://a.example, https://b.example ")
    monkeypatch.setenv("TRUEINTENT_CORS_ALLOW_LOCALHOST", "false")
    monkeypatch.setenv("TRUEINTENT_MAX_URL_CHARS", "4096")
    settings = load_settings()
    assert settings.port == 9001
    assert settings.cors_origins == ("https://a.example", "https://b.example")
    assert settings.cors_allow_localhost is False
    assert settings.max_url_chars == 4096


def test_config_rejects_garbage_and_clamps(monkeypatch):
    monkeypatch.setenv("TRUEINTENT_PORT", "not-a-port")
    monkeypatch.setenv("TRUEINTENT_CORS_ALLOW_LOCALHOST", "maybe")
    monkeypatch.setenv("TRUEINTENT_MAX_IMAGE_BYTES", "-5")
    settings = load_settings()
    assert settings.port == 8000
    assert settings.cors_allow_localhost is True  # development default
    assert settings.max_image_bytes >= 1


def test_config_production_defaults_to_explicit_origins(monkeypatch):
    monkeypatch.setenv("TRUEINTENT_ENV", "production")
    settings = load_settings()
    assert settings.is_production is True
    assert settings.cors_allow_localhost is False
    assert settings.cors_origins == ()
    summary = settings.public_summary()
    assert summary["cors_origin_count"] == 0
    assert "127.0.0.1" not in str(summary)


# -----------------------------------------------------------------------------
# request IDs
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("candidate", [
    "mobile-client-123", "a" * 64, "req_1.2:3-4", "X-Request-ID",
])
def test_safe_request_ids_pass_through(candidate):
    assert sanitise_request_id(candidate) == candidate


@pytest.mark.parametrize("candidate", [
    None, "", "   ", "a" * 65, "abc\nSet-Cookie: x=1", "has space", "semi;colon",
    "tab\there", "<script>",
])
def test_unsafe_request_ids_are_rejected(candidate):
    assert sanitise_request_id(candidate) is None


# -----------------------------------------------------------------------------
# services boundary guards
# -----------------------------------------------------------------------------
def test_risk_index_clamps():
    from backend.app import services

    assert services.risk_index(0.0) == 0
    assert services.risk_index(0.7944) == 79
    assert services.risk_index(1.0) == 100
    assert services.risk_index(2.0) == 100
    assert services.risk_index(-0.5) == 0


def test_require_assessed_refuses_unassessed():
    from backend.app import services
    from backend.app.errors import MessageNotAssessed

    with pytest.raises(MessageNotAssessed):
        services.require_assessed({"score": 0.0, "text_assessed": False})
    ok = {"score": 0.5, "text_assessed": True}
    assert services.require_assessed(ok) is ok
    missing = {"score": 0.5}
    assert services.require_assessed(missing) is missing


def test_require_image_assessed_is_status_aware():
    from backend.app import services
    from backend.app.errors import MessageNotAssessed

    # Non-ok OCR outcomes carry their own explicit handling downstream.
    assert services.require_image_assessed(
        {"ocr_status": "insufficient_text", "text_assessed": False}
    )["ocr_status"] == "insufficient_text"
    with pytest.raises(MessageNotAssessed):
        services.require_image_assessed({"ocr_status": "ok", "text_assessed": False})


# -----------------------------------------------------------------------------
# validation primitives
# -----------------------------------------------------------------------------
def test_detect_image_type_covers_each_signature():
    from backend.app.validation import detect_image_type

    assert detect_image_type(b"\x89PNG\r\n\x1a\nrest") == "image/png"
    assert detect_image_type(b"\xff\xd8\xffrest") == "image/jpeg"
    assert detect_image_type(b"RIFF\x00\x00\x00\x00WEBPxx") == "image/webp"
    assert detect_image_type(b"BMrest") == "image/bmp"
    assert detect_image_type(b"GIF89a...") is None
    assert detect_image_type(b"") is None


def test_normalize_url_rules():
    from backend.app.errors import InvalidUrl, MissingInput
    from backend.app.validation import normalize_url

    assert normalize_url("https://example.com/login") == "https://example.com/login"
    assert normalize_url("  https://example.com/  ") == "https://example.com/"
    assert normalize_url("http://localhost:8000/health") == "http://localhost:8000/health"
    with pytest.raises(MissingInput):
        normalize_url("   ")
    with pytest.raises(MissingInput):
        normalize_url(None)
    with pytest.raises(InvalidUrl):
        normalize_url("not a url")
    with pytest.raises(InvalidUrl):
        normalize_url("https://example.com\\@evil.com")
    with pytest.raises(InvalidUrl):
        normalize_url("ftp://example.com/file")


# -----------------------------------------------------------------------------
# diagnostics logic
# -----------------------------------------------------------------------------
def test_overall_status_semantics():
    from backend.app.diagnostics import (
        ComponentStatus, failing_component, overall_status,
    )

    ok = [ComponentStatus("m", "ok", "fine")]
    assert overall_status(ok) == ("ready", False, True)
    degraded = ok + [ComponentStatus("n", "unavailable", "missing")]
    assert overall_status(degraded) == ("degraded", True, True)
    broken = ok + [ComponentStatus("n", "error", "corrupt")]
    assert overall_status(broken) == ("not_ready", True, False)
    assert failing_component(broken).name == "n"
    assert failing_component(ok) is None


def test_diagnostics_cache_serves_stale_but_never_optimistic(monkeypatch):
    from backend.app import diagnostics

    calls = {"n": 0}

    def probe():
        calls["n"] += 1
        return diagnostics.ComponentStatus("x", "ok", "fine")

    diagnostics.reset_cache()
    try:
        first = diagnostics._cached("x", probe)
        second = diagnostics._cached("x", probe)
        assert calls["n"] == 1
        assert first is second
    finally:
        diagnostics.reset_cache()
