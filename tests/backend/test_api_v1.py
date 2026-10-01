"""Integration tests for the versioned ``/api/v1`` contract.

Covers every major endpoint in both generations plus the properties the
hardening pass promises:

* envelope shape on success (``success`` / ``data`` / ``meta``) and failure
  (``success`` / ``error`` / ``meta``), with the request ID echoed in the
  ``X-Request-ID`` header and in ``meta``;
* one error object per failure class (400/404/405/413/415/422/500/503);
* no stack traces, filesystem paths or environment values in any response;
* magic-byte MIME verification, bounded uploads, and the request-size gate;
* ``/health`` and ``/ready`` behaviour;
* the frozen legacy contract (flat bodies, ``{"detail": ...}`` errors).

Model-backed tests skip honestly when the gitignored artifacts are absent,
exactly like the legacy suite.
"""
from __future__ import annotations

import dataclasses
import io
import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="fastapi required for API tests")
pytest.importorskip("httpx", reason="httpx required for TestClient")

from fastapi.testclient import TestClient

from backend.app import diagnostics, safety
from backend.app.main import app, create_app

client = TestClient(app)

ROOT = Path(__file__).resolve().parents[2]
requires_module_c = pytest.mark.skipif(
    not (ROOT / "ml/models/module_c.pkl").exists(),
    reason="Train Module C (ml/train_module_c.py) to run model-backed API tests",
)

FEAR_TEXT = (
    "You are under investigation for money laundering. "
    "Stay on the line and do not disconnect."
)
PHISH_URL = "http://hdfcbaank-login.xyz/update-kyc"
IP_URL = "http://192.168.1.1/verify-account"
SAFE_URL = "https://www.google.com/search?q=test"


def _png_bytes(size=(100, 50)) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def _assert_envelope_success(response, *, request_id_header=True):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], dict)
    assert body["meta"]["api_version"] == "v1"
    header_id = response.headers.get("x-request-id")
    assert header_id, "X-Request-ID missing"
    assert body["meta"]["request_id"] == header_id
    if request_id_header:
        return body, header_id
    return body


def _assert_envelope_error(response, status, code):
    assert response.status_code == status, response.text
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == code, body
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert "module" in body["error"] and "details" in body["error"]
    assert body["meta"]["api_version"] == "v1"
    header_id = response.headers.get("x-request-id")
    assert header_id, "X-Request-ID missing on error"
    assert body["meta"]["request_id"] == header_id
    safety.assert_no_internal_detail(response.text, where=f"{status} {code}")
    return body


# -----------------------------------------------------------------------------
# /health and /ready
# -----------------------------------------------------------------------------
def test_health_is_flat_and_stable():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_reports_components_honestly():
    r = client.get("/ready")
    assert r.status_code in (200, 503), r.text
    body = r.json()
    assert body["meta"]["api_version"] == "v1"
    if r.status_code == 200:
        assert body["success"] is True
        payload = body["data"]
        assert payload["status"] in ("ready", "degraded")
    else:
        payload = body["error"]["details"]["readiness"]
        assert payload["status"] == "not_ready"
    assert {c["name"] for c in payload["components"]} == {
        "module_a", "module_b", "module_c", "module_d", "ocr",
    }
    for component in payload["components"]:
        assert component["status"] in ("ok", "degraded", "unavailable", "error")
        assert isinstance(component["detail"], str) and component["detail"]
    safety.assert_no_internal_detail(r.text, where="/ready")


def test_ready_reports_corrupt_fusion_artifact_as_not_ready(monkeypatch):
    from backend.app.diagnostics import ComponentStatus

    diagnostics.reset_cache()
    monkeypatch.setattr(
        diagnostics, "probe_module_d",
        lambda: ComponentStatus("module_d", "error", "Fusion artifact is corrupt."),
    )
    try:
        r = client.get("/ready")
        assert r.status_code == 503, r.text
        body = r.json()
        assert body["success"] is False
        assert body["error"]["code"] == "model_unavailable"
        assert body["error"]["module"] == "module_d"
        assert body["meta"]["api_version"] == "v1"
        assert r.headers.get("x-request-id") == body["meta"]["request_id"]
        safety.assert_no_internal_detail(r.text, where="/ready 503")
    finally:
        diagnostics.reset_cache()


# -----------------------------------------------------------------------------
# /api/v1/analyze/url
# -----------------------------------------------------------------------------
def test_v1_url_success_envelope():
    body, _ = _assert_envelope_success(
        client.post("/api/v1/analyze/url", json={"url": PHISH_URL})
    )
    data = body["data"]
    assert 0.0 <= data["score"] <= 1.0
    assert data["risk_index"] == round(data["score"] * 100)
    assert isinstance(data["reasons"], list) and data["reasons"]
    assert data["ml_status"] == "active"


def test_v1_url_safe_scores_low():
    body, _ = _assert_envelope_success(
        client.post("/api/v1/analyze/url", json={"url": SAFE_URL})
    )
    assert body["data"]["score"] < 0.3
    assert body["data"]["risk_index"] < 30


def test_v1_url_rejects_malformed():
    body = _assert_envelope_error(
        client.post("/api/v1/analyze/url", json={"url": "not a url"}),
        422, "invalid_url",
    )
    assert body["error"]["module"] == "module_b"


def test_v1_url_rejects_empty_and_oversize():
    _assert_envelope_error(
        client.post("/api/v1/analyze/url", json={"url": "   "}), 422, "validation_error",
    )
    _assert_envelope_error(
        client.post("/api/v1/analyze/url", json={"url": "https://example.com/" + "x" * 9000}),
        422, "invalid_url",
    )


# -----------------------------------------------------------------------------
# /api/v1/analyze/message
# -----------------------------------------------------------------------------
@requires_module_c
def test_v1_message_success_envelope():
    body, _ = _assert_envelope_success(
        client.post("/api/v1/analyze/message", json={"text": FEAR_TEXT})
    )
    data = body["data"]
    assert data["signature"] == "fear_authority"
    assert data["score"] >= 0.5
    assert data["text_assessed"] is True
    assert data["risk_index"] == round(data["score"] * 100)


def test_v1_message_rejects_blank_and_oversize():
    # Blank input fails schema shape checks, exactly like the legacy route.
    _assert_envelope_error(
        client.post("/api/v1/analyze/message", json={"text": "   "}),
        422, "validation_error",
    )
    _assert_envelope_error(
        client.post("/api/v1/analyze/message", json={"text": "x" * 20001}),
        422, "validation_error",
    )


def test_v1_message_unassessed_model_is_503(monkeypatch):
    import backend.app.services as services_mod

    monkeypatch.setattr(
        services_mod, "analyze_text",
        lambda *a, **k: {"score": 0.0, "signature": "none", "reasons": [],
                         "ml_status": "unavailable", "text_assessed": False},
    )
    _assert_envelope_error(
        client.post("/api/v1/analyze/message", json={"text": "hello"}),
        503, "message_not_assessed",
    )


# -----------------------------------------------------------------------------
# /api/v1/analyze/image
# -----------------------------------------------------------------------------
def _fake_image_result(**overrides):
    result = {
        "score": 0.75,
        "signature": "greed_opportunity",
        "reasons": ["Matched greed/opportunity pattern: 'guaranteed returns'"],
        "ml_status": "mocked",
        "intent": "investment_scam",
        "intent_probabilities": {"investment_scam": 0.75},
        "rule_evidence": [],
        "text_assessed": True,
        "ocr_text": "Limited time! Guaranteed returns.",
        "ocr_status": "ok",
    }
    result.update(overrides)
    return result


def test_v1_image_success_envelope(monkeypatch):
    import backend.app.services as services_mod

    def fake(_content, *, declared_type=None, filename=None):
        return _fake_image_result()

    monkeypatch.setattr(services_mod, "analyze_image_content", fake)
    body, _ = _assert_envelope_success(
        client.post("/api/v1/analyze/image",
                    files={"image": ("chat.png", _png_bytes(), "image/png")})
    )
    data = body["data"]
    assert data["signature"] == "greed_opportunity"
    assert data["ocr_status"] == "ok"
    assert "Guaranteed returns" in data["ocr_text"]
    assert data["risk_index"] == 75


def test_v1_image_rejects_undeclared_and_mismatched_types():
    # Declared type outside the allowlist -> 415.
    r = client.post("/api/v1/analyze/image",
                    files={"image": ("chat.png", _png_bytes(), "text/plain")})
    _assert_envelope_error(r, 415, "unsupported_media_type")
    # Declared PNG but garbage bytes -> 400.
    r = client.post("/api/v1/analyze/image",
                    files={"image": ("chat.png", b"not an image at all" * 4, "image/png")})
    body = _assert_envelope_error(r, 400, "unreadable_image")
    assert body["error"]["module"] == "module_c"
    # Declared PNG but JPEG bytes -> 400 mismatch.
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(buf, format="JPEG")
    r = client.post("/api/v1/analyze/image",
                    files={"image": ("chat.png", buf.getvalue(), "image/png")})
    _assert_envelope_error(r, 400, "unreadable_image")


def test_v1_image_rejects_oversize_part(monkeypatch):
    import dataclasses

    from backend.app import validation as validation_mod
    from backend.app.config import SETTINGS

    small = dataclasses.replace(SETTINGS, max_image_bytes=100)
    monkeypatch.setattr(validation_mod, "SETTINGS", small)
    r = client.post("/api/v1/analyze/image",
                    files={"image": ("chat.png", _png_bytes(), "image/png")})
    body = _assert_envelope_error(r, 413, "payload_too_large")
    assert body["error"]["details"]["max_bytes"] == 100


# -----------------------------------------------------------------------------
# /api/v1/analyze/combined
# -----------------------------------------------------------------------------
@requires_module_c
def test_v1_combined_success_envelope():
    body, _ = _assert_envelope_success(
        client.post("/api/v1/analyze/combined", json={
            "url": "https://www.google.com/",
            "text": "Hey, are we still meeting for lunch tomorrow?",
        })
    )
    data = body["data"]
    assert data["tier"] == "Low"
    assert "Module B" in data["explanation"] and "Module C" in data["explanation"]
    assert "Module A (no transaction submitted)" in data["explanation"]
    assert set(data["modules"]) == {"module_b", "module_c"}


def test_v1_combined_refuses_transaction_field():
    r = client.post("/api/v1/analyze/combined", json={
        "transaction": {"amount": 8000}, "text": "hello",
    })
    body = _assert_envelope_error(r, 422, "validation_error")
    assert "fusion" in body["error"]["details"].get("hint", "").lower()


def test_v1_combined_requires_evidence():
    _assert_envelope_error(
        client.post("/api/v1/analyze/combined", json={}), 422, "validation_error",
    )
    _assert_envelope_error(
        client.post("/api/v1/analyze/combined", json={"url": "   ", "text": "  "}),
        422, "validation_error",
    )


# -----------------------------------------------------------------------------
# /api/v1/module-a/*
# -----------------------------------------------------------------------------
def test_v1_module_a_contract():
    from ml.features_module_a import FEATURE_CONTRACT
    body, _ = _assert_envelope_success(client.get("/api/v1/module-a/contract"))
    assert body["data"] == {
        "version": FEATURE_CONTRACT["version"],
        "artifact_version": FEATURE_CONTRACT["artifact_version"],
        "model_version": FEATURE_CONTRACT["model_version"],
        "features": ["amount"],
        "feature_order": ["amount"],
        "dataset_id": FEATURE_CONTRACT["dataset_id"],
        "preprocessing_version": FEATURE_CONTRACT["preprocessing_version"],
        "amount_unit": "ieee_cis_source",
        "expected_units": {"amount": "ieee_cis_source", "amount_unit": "ieee_cis_source"},
        "scope": "ieee_cis_amount_only_benchmark",
    }


def test_v1_module_a_benchmark_success(benchmark_model):
    body, _ = _assert_envelope_success(
        client.post("/api/v1/module-a/benchmark", json={
            "amount": 45000.0, "amount_unit": "ieee_cis_source",
        })
    )
    data = body["data"]
    assert 0.0 <= data["score"] <= 1.0
    assert data["analysis_scope"] == "ieee_cis_amount_only_benchmark"
    assert "risk_index" not in data


def test_v1_module_a_benchmark_requires_explicit_unit():
    # Missing unit: schema-level refusal, no silent default.
    _assert_envelope_error(
        client.post("/api/v1/module-a/benchmark", json={"amount": 500}),
        422, "validation_error",
    )
    # Explicit INR: semantic refusal naming the problem.
    body = _assert_envelope_error(
        client.post("/api/v1/module-a/benchmark", json={"amount": 500, "amount_unit": "INR"}),
        422, "amount_unit_rejected",
    )
    assert body["error"]["module"] == "module_a"
    assert "INR" in body["error"]["message"]


def test_v1_module_a_benchmark_rejects_boolean_amount():
    _assert_envelope_error(
        client.post("/api/v1/module-a/benchmark",
                    json={"amount": True, "amount_unit": "ieee_cis_source"}),
        422, "validation_error",
    )


# -----------------------------------------------------------------------------
# Error handling, request IDs, framework errors
# -----------------------------------------------------------------------------
def test_request_id_round_trips_on_success_and_error():
    r = client.post("/api/v1/analyze/url", json={"url": SAFE_URL},
                    headers={"X-Request-ID": "mobile-client-123"})
    assert r.status_code == 200
    assert r.headers["x-request-id"] == "mobile-client-123"
    assert r.json()["meta"]["request_id"] == "mobile-client-123"

    r = client.post("/api/v1/analyze/url", json={"url": "not a url"},
                    headers={"X-Request-ID": "mobile-client-456"})
    assert r.status_code == 422
    assert r.headers["x-request-id"] == "mobile-client-456"
    assert r.json()["meta"]["request_id"] == "mobile-client-456"


def test_unsafe_request_id_is_replaced():
    evil = "abc\nSet-Cookie: hacked=1"
    r = client.post("/api/v1/analyze/url", json={"url": SAFE_URL},
                    headers={"X-Request-ID": evil})
    assert r.status_code == 200
    header_id = r.headers["x-request-id"]
    assert header_id != evil
    assert "\n" not in header_id
    assert r.json()["meta"]["request_id"] == header_id


def test_v1_unknown_route_and_method():
    r = client.get("/api/v1/does-not-exist")
    _assert_envelope_error(r, 404, "not_found")
    r = client.get("/api/v1/analyze/url")
    _assert_envelope_error(r, 405, "method_not_allowed")
    # Legacy keeps the flat shape on the same framework errors.
    r = client.get("/does-not-exist")
    assert r.status_code == 404
    assert set(r.json()) == {"detail"}


def test_internal_errors_never_leak(monkeypatch):
    import backend.app.services as services_mod

    def boom(*args, **kwargs):
        raise RuntimeError("kaboom at C:\\secret\\models\\module_x.pkl")

    # The ServerErrorMiddleware always re-raises after responding, so the
    # non-raising client is needed to inspect the 500 body itself.
    quiet = TestClient(app, raise_server_exceptions=False)
    monkeypatch.setattr(services_mod, "analyze_url", boom)
    r = quiet.post("/api/v1/analyze/url", json={"url": SAFE_URL})
    body = _assert_envelope_error(r, 500, "internal_error")
    assert "kaboom" not in body["error"]["message"]
    assert "secret" not in r.text

    r = quiet.post("/check-url", json={"url": SAFE_URL})
    assert r.status_code == 500
    assert r.json() == {"detail": "URL analysis failed unexpectedly. Please retry."}
    safety.assert_no_internal_detail(r.text, where="legacy 500")


def test_request_body_ceiling(monkeypatch):
    from backend.app.config import load_settings

    # Shrink the ceiling through the real environment plumbing: a scoped app
    # built from these settings must refuse the body at the gate.
    monkeypatch.setenv("TRUEINTENT_MAX_REQUEST_BYTES", "512")
    scoped = TestClient(create_app(load_settings()))
    body = {"url": "https://example.com/" + "x" * 500}
    r = scoped.post("/api/v1/analyze/url", json=body)
    _assert_envelope_error(r, 413, "payload_too_large")
    # Legacy keeps its flat shape behind the same gate.
    r = scoped.post("/check-url", json=body)
    assert r.status_code == 413
    assert set(r.json()) == {"detail"}


# -----------------------------------------------------------------------------
# CORS configuration
# -----------------------------------------------------------------------------
def test_cors_default_allows_localhost_but_nothing_else():
    r = client.options(
        "/api/v1/analyze/url",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
    r = client.options(
        "/api/v1/analyze/url",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in r.headers


def test_cors_explicit_origins_from_environment(monkeypatch):
    from backend.app.config import load_settings

    monkeypatch.setenv("TRUEINTENT_CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("TRUEINTENT_CORS_ALLOW_LOCALHOST", "false")
    scoped = TestClient(create_app(load_settings()))
    r = scoped.options(
        "/api/v1/analyze/url",
        headers={"Origin": "https://app.example.com", "Access-Control-Request-Method": "POST"},
    )
    assert r.headers.get("access-control-allow-origin") == "https://app.example.com"
    r = scoped.options(
        "/api/v1/analyze/url",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in r.headers


# -----------------------------------------------------------------------------
# Legacy compatibility spot checks
# -----------------------------------------------------------------------------
def test_legacy_contract_is_unchanged():
    r = client.post("/check-url", json={"url": PHISH_URL})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"score", "reasons", "ml_status"}
    assert "success" not in body

    r = client.post("/check-url", json={"url": "not a url"})
    assert r.status_code == 422
    assert set(r.json()) == {"detail"}


def test_error_bodies_carry_no_internal_detail():
    probes = [
        ("POST", "/api/v1/analyze/url", {"url": "not a url"}),
        ("POST", "/api/v1/analyze/message", {"text": "x" * 20001}),
        ("POST", "/api/v1/analyze/combined", {"transaction": {"amount": 1}}),
        ("POST", "/api/v1/module-a/benchmark", {"amount": -5, "amount_unit": "INR"}),
        ("GET", "/api/v1/does-not-exist", None),
    ]
    for method, path, payload in probes:
        if method == "POST":
            r = client.post(path, json=payload)
        else:
            r = client.get(path)
        assert r.status_code in (400, 404, 405, 413, 415, 422, 500, 503), (path, r.status_code)
        safety.assert_no_internal_detail(r.text, where=path)
        safety.assert_no_internal_detail(json.dumps(r.json()), where=path)


def test_openapi_documents_both_generations():
    paths = set(app.openapi().get("paths", {}))
    for endpoint in (
        "/check-url", "/check-message", "/check-transaction", "/check-combined",
        "/api/v1/analyze/url", "/api/v1/analyze/message", "/api/v1/analyze/image",
        "/api/v1/analyze/combined", "/api/v1/module-a/benchmark",
        "/api/v1/module-a/contract", "/health", "/ready",
    ):
        assert endpoint in paths, f"missing from OpenAPI: {endpoint}"
