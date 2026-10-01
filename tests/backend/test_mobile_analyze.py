"""Backend tests for the mobile contract: POST /api/v1/analyze (JSON) and
POST /api/v1/analyze/screenshot (multipart).

Every test sends the exact request shape the future mobile application will
send: JSON bodies with `url`/`message`/`text`/`active_call`, and multipart
forms with an `image` file plus optional fields.
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="fastapi required for API tests")
pytest.importorskip("httpx", reason="httpx required for TestClient")

from fastapi.testclient import TestClient

from backend.app import safety
from backend.app.main import app

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
LUNCH_TEXT = "Hey, are we still meeting for lunch tomorrow?"
PHISH_URL = "http://hdfcbaank-login.xyz/update-kyc"
SAFE_URL = "https://www.google.com/search?q=test"


def _png_bytes(size=(100, 50)) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def _ok(response):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["meta"]["api_version"] == "v1"
    header_id = response.headers.get("x-request-id")
    assert header_id and body["meta"]["request_id"] == header_id
    return body["data"]


def _err(response, status, code):
    assert response.status_code == status, response.text
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == code, body
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    safety.assert_no_internal_detail(response.text, where=f"{status} {code}")
    return body


def _check_mobile_shape(data, *, expect_url, expect_message, expect_ocr):
    for key in ("tier", "risk_level", "score", "risk_index", "summary",
                "explanation", "analyzed_modules", "contributing_modules",
                "unavailable_modules", "evidence", "warnings", "fusion_version",
                "limitations", "recommended_action", "safety_actions",
                "url_findings", "message_findings", "ocr_findings", "details"):
        assert key in data, f"missing mobile field {key}"
    assert data["tier"] == data["risk_level"]
    assert data["tier"] in ("Low", "Medium", "High", "Critical")
    assert 0.0 <= data["score"] <= 1.0
    assert data["risk_index"] == round(data["score"] * 100)
    assert data["summary"].startswith(data["risk_level"])
    assert isinstance(data["safety_actions"], list) and data["safety_actions"]
    assert (data["url_findings"] is not None) == expect_url
    assert (data["message_findings"] is not None) == expect_message
    assert (data["ocr_findings"] is not None) == expect_ocr
    if expect_url:
        assert 0.0 <= data["url_findings"]["score"] <= 1.0
    if not (expect_url or expect_message or expect_ocr):
        raise AssertionError("mobile verdict with no findings")


# -----------------------------------------------------------------------------
# POST /api/v1/analyze — JSON
# -----------------------------------------------------------------------------
def test_mobile_url_only():
    data = _ok(client.post("/api/v1/analyze", json={"url": PHISH_URL}))
    _check_mobile_shape(data, expect_url=True, expect_message=False, expect_ocr=False)
    assert "module_b" in data["analyzed_modules"]
    assert "module_c" in data["unavailable_modules"]
    assert data["risk_level"] in ("High", "Critical")


def test_mobile_url_only_safe_scores_low_at_module_level():
    # Module B itself scores a benign URL low; the fused single-channel level
    # depends on the deployment's fusion artifact, so only structural fusion
    # properties are asserted here.
    data = _ok(client.post("/api/v1/analyze", json={"url": SAFE_URL}))
    _check_mobile_shape(data, expect_url=True, expect_message=False, expect_ocr=False)
    assert data["url_findings"]["score"] < 0.3
    assert data["risk_level"] == data["tier"]
    assert data["summary"].startswith(data["risk_level"])


@requires_module_c
def test_mobile_message_only():
    data = _ok(client.post("/api/v1/analyze", json={"message": LUNCH_TEXT}))
    _check_mobile_shape(data, expect_url=False, expect_message=True, expect_ocr=False)
    assert "module_c" in data["analyzed_modules"]
    assert "module_b" in data["unavailable_modules"]
    assert data["risk_level"] == "Low"


@requires_module_c
def test_mobile_text_alias_and_equal_pair():
    by_alias = _ok(client.post("/api/v1/analyze", json={"text": LUNCH_TEXT}))
    assert by_alias["message_findings"] is not None
    both = _ok(client.post("/api/v1/analyze",
                           json={"message": LUNCH_TEXT, "text": LUNCH_TEXT}))
    assert both["message_findings"] is not None


def test_mobile_message_text_conflict_is_422():
    _err(client.post("/api/v1/analyze",
                     json={"message": "hello", "text": "different"}),
         422, "validation_error")


@requires_module_c
def test_mobile_url_and_message():
    data = _ok(client.post("/api/v1/analyze", json={"url": SAFE_URL, "message": LUNCH_TEXT}))
    _check_mobile_shape(data, expect_url=True, expect_message=True, expect_ocr=False)
    assert set(data["analyzed_modules"]) == {"module_b", "module_c"}
    assert data["risk_level"] == "Low"


@requires_module_c
def test_mobile_suspicious_pair_is_not_low():
    data = _ok(client.post("/api/v1/analyze", json={"url": PHISH_URL, "message": FEAR_TEXT}))
    assert data["risk_level"] in ("High", "Critical")
    assert "pause" in data["recommended_action"].lower() or \
        "stop" in data["recommended_action"].lower()


def test_mobile_active_call_round_trips():
    data = _ok(client.post("/api/v1/analyze",
                           json={"url": SAFE_URL, "active_call": True}))
    assert data["url_findings"] is not None
    assert any("call" in w.lower() for w in data["warnings"])


def test_mobile_requires_evidence():
    _err(client.post("/api/v1/analyze", json={}), 422, "validation_error")
    _err(client.post("/api/v1/analyze", json={"url": "   ", "message": "  "}),
         422, "validation_error")


def test_mobile_refuses_transaction_field():
    body = _err(client.post("/api/v1/analyze",
                            json={"transaction": {"amount": 1}, "message": "hi"}),
                422, "validation_error")
    assert "fusion" in body["error"]["details"].get("hint", "").lower()


def test_mobile_rejects_bad_types_and_sizes():
    _err(client.post("/api/v1/analyze", json={"url": SAFE_URL, "active_call": "yes"}),
         422, "validation_error")
    _err(client.post("/api/v1/analyze", json={"url": "not a url"}), 422, "invalid_url")
    _err(client.post("/api/v1/analyze",
                     json={"url": "https://example.com/" + "x" * 9000}),
         422, "invalid_url")
    _err(client.post("/api/v1/analyze", json={"message": "x" * 20001}),
         422, "validation_error")


def test_mobile_message_unavailable_is_503_not_low(monkeypatch):
    import backend.app.services as services_mod

    monkeypatch.setattr(
        services_mod, "analyze_text",
        lambda *a, **k: {"score": 0.0, "signature": "none", "reasons": [],
                         "ml_status": "unavailable", "text_assessed": False},
    )
    _err(client.post("/api/v1/analyze", json={"message": "hello"}),
         503, "message_not_assessed")


def test_mobile_request_id_round_trip():
    r = client.post("/api/v1/analyze", json={"url": SAFE_URL},
                    headers={"X-Request-ID": "mobile-app-1"})
    assert r.status_code == 200
    assert r.headers["x-request-id"] == "mobile-app-1"
    assert r.json()["meta"]["request_id"] == "mobile-app-1"


# -----------------------------------------------------------------------------
# POST /api/v1/analyze/screenshot — multipart
# -----------------------------------------------------------------------------
def _fake_image_result(**overrides):
    result = {
        "score": 0.75,
        "text_score": 0.75,
        "embedded_url_score": 0.0,
        "signature": "greed_opportunity",
        "reasons": ["Matched greed/opportunity pattern: 'guaranteed returns'"],
        "ml_status": "mocked",
        "intent": "investment_scam",
        "intent_probabilities": {"investment_scam": 0.75},
        "rule_evidence": [],
        "heuristic_evidence": [],
        "text_assessed": True,
        "ocr_text": "Limited time! Guaranteed returns.",
        "ocr_status": "ok",
    }
    result.update(overrides)
    return result


def _post_screenshot(monkeypatch, **form):
    import backend.app.services as services_mod

    monkeypatch.setattr(
        services_mod, "analyze_image_content",
        lambda _c, *, declared_type=None, filename=None: _fake_image_result(),
    )
    files, data = {}, {}
    for key, value in form.items():
        if isinstance(value, tuple):
            files[key] = value
        else:
            data[key] = value
    return client.post("/api/v1/analyze/screenshot", files=files, data=data)


def test_mobile_screenshot_only(monkeypatch):
    r = _post_screenshot(monkeypatch, image=("chat.png", _png_bytes(), "image/png"))
    data = _ok(r)
    _check_mobile_shape(data, expect_url=False, expect_message=False, expect_ocr=True)
    assert data["ocr_findings"]["ocr_status"] == "ok"
    assert "Guaranteed returns" in data["ocr_findings"]["ocr_text"]
    assert "module_c" in data["analyzed_modules"]


def test_mobile_screenshot_alias_field(monkeypatch):
    r = _post_screenshot(monkeypatch, screenshot=("chat.png", _png_bytes(), "image/png"))
    assert _ok(r)["ocr_findings"] is not None


def test_mobile_screenshot_with_url(monkeypatch):
    r = _post_screenshot(monkeypatch,
                         image=("chat.png", _png_bytes(), "image/png"),
                         url=SAFE_URL)
    data = _ok(r)
    _check_mobile_shape(data, expect_url=True, expect_message=False, expect_ocr=True)
    assert set(data["analyzed_modules"]) == {"module_b", "module_c"}


def test_mobile_screenshot_with_message_picks_higher(monkeypatch):
    import backend.app.services as services_mod
    import ml.predict_module_d as fusion_mod

    # Pin the transparent fusion path so the worst-of expectation is exact.
    monkeypatch.setattr(fusion_mod, "_load_learned_model", lambda: None)
    monkeypatch.setattr(
        services_mod, "analyze_image_content",
        lambda _c, *, declared_type=None, filename=None: _fake_image_result(score=0.2,
                                                                            text_score=0.2),
    )
    monkeypatch.setattr(
        services_mod, "analyze_text",
        lambda *a, **k: dict(_fake_image_result(), score=0.9, text_score=0.9,
                             ocr_text=None, ocr_status=None),
    )
    r = client.post("/api/v1/analyze/screenshot",
                    files={"image": ("chat.png", _png_bytes(), "image/png")},
                    data={"message": "guaranteed returns now"})
    data = _ok(r)
    assert data["message_findings"] is not None and data["ocr_findings"] is not None
    assert data["score"] == pytest.approx(0.9)


def test_mobile_screenshot_requires_evidence():
    _err(client.post("/api/v1/analyze/screenshot", files={}, data={}),
         400, "missing_input")


def test_mobile_screenshot_rejects_conflicts():
    png = ("chat.png", _png_bytes(), "image/png")
    _err(client.post("/api/v1/analyze/screenshot",
                     files={"image": png, "screenshot": png}),
         400, "conflicting_input")
    _err(client.post("/api/v1/analyze/screenshot",
                     files={"image": png},
                     data={"message": "a", "text": "b"}),
         400, "conflicting_input")


def test_mobile_screenshot_rejects_bad_inputs(monkeypatch):
    import backend.app.services as services_mod
    import ml.predict_module_d as fusion_mod

    png = ("chat.png", _png_bytes(), "image/png")
    _err(client.post("/api/v1/analyze/screenshot",
                     files={"image": ("chat.png", b"not an image" * 8, "image/png")}),
         400, "unreadable_image")
    _err(client.post("/api/v1/analyze/screenshot",
                     files={"image": ("chat.txt", _png_bytes(), "text/plain")}),
         415, "unsupported_media_type")
    _err(client.post("/api/v1/analyze/screenshot", files={"image": png},
                     data={"active_call": "maybe"}),
         422, "validation_error")
    # Case-insensitive 'true' parses; fusion pinned for a stable level.
    monkeypatch.setattr(fusion_mod, "_load_learned_model", lambda: None)
    monkeypatch.setattr(
        services_mod, "analyze_image_content",
        lambda _c, *, declared_type=None, filename=None: _fake_image_result(
            score=0.1, text_score=0.1),
    )
    assert _ok(client.post(
        "/api/v1/analyze/screenshot", files={"image": png},
        data={"url": SAFE_URL, "active_call": "TrUe"}))["risk_level"] == "Low"


def test_mobile_screenshot_ocr_engine_missing_is_503():
    from ml.ocr_module_c import resolve_tesseract_command

    if resolve_tesseract_command() is not None:
        pytest.skip("tesseract present; degradation path covered by mocks")
    body = _err(client.post("/api/v1/analyze/screenshot",
                            files={"image": ("chat.png", _png_bytes(), "image/png")}),
                503, "ocr_unavailable")
    assert "paste" in body["error"]["message"].lower()


def test_mobile_screenshot_rejects_oversize_part(monkeypatch):
    import dataclasses

    from backend.app import validation as validation_mod
    from backend.app.config import SETTINGS

    small = dataclasses.replace(SETTINGS, max_image_bytes=100)
    monkeypatch.setattr(validation_mod, "SETTINGS", small)
    body = _err(client.post("/api/v1/analyze/screenshot",
                            files={"image": ("chat.png", _png_bytes(), "image/png")}),
                413, "payload_too_large")
    assert body["error"]["details"]["max_bytes"] == 100


# -----------------------------------------------------------------------------
# Service unit tests (no HTTP): worst-of text channels, graceful empties
# -----------------------------------------------------------------------------
def test_service_mobile_picks_higher_text_channel(monkeypatch):
    import backend.app.services as services_mod
    import ml.predict_module_d as fusion_mod

    monkeypatch.setattr(fusion_mod, "_load_learned_model", lambda: None)
    monkeypatch.setattr(services_mod, "analyze_text",
                        lambda *a, **k: dict(_fake_image_result(), score=0.9,
                                             text_score=0.9, ocr_text=None,
                                             ocr_status=None))
    monkeypatch.setattr(services_mod, "analyze_image_content",
                        lambda *a, **k: _fake_image_result(score=0.2, text_score=0.2))
    result = services_mod.analyze_mobile(url=None, message="x", active_call=None,
                                         image={"content": _png_bytes(),
                                                "declared_type": "image/png",
                                                "filename": "chat.png"})
    assert result["score"] == pytest.approx(0.9)
    assert result["message_result"] is not None and result["image_result"] is not None
    assert result["summary"].startswith("Critical")
    assert result["safety_actions"]


def test_service_mobile_empty_is_missing_input():
    import backend.app.services as services_mod

    with pytest.raises(Exception) as exc:
        services_mod.analyze_mobile(url=None, message="  ", image=None, active_call=None)
    assert getattr(exc.value, "code", "") == "missing_input"


# -----------------------------------------------------------------------------
# OpenAPI documents both mobile operations with examples
# -----------------------------------------------------------------------------
def test_openapi_documents_mobile_endpoints():
    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    paths = spec.json()["paths"]
    assert "/api/v1/analyze" in paths
    assert "/api/v1/analyze/screenshot" in paths
    post = paths["/api/v1/analyze"]["post"]
    assert post["requestBody"]["content"]["application/json"]["schema"][
        "$ref"].endswith("MobileAnalyzeRequest")
    schemas = spec.json()["components"]["schemas"]
    assert "MobileAnalyzeRequest" in schemas and "MobileAnalyzeData" in schemas
    examples = schemas["MobileAnalyzeRequest"].get("examples", [])
    assert any("message" in e for e in examples)
