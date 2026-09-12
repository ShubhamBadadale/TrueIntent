"""FastAPI endpoint tests (TestClient). Skipped where fastapi/httpx missing."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi required for API tests")
httpx = pytest.importorskip("httpx", reason="httpx required for TestClient")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

FEAR_TEXT = (
    "You are under investigation for money laundering. "
    "Stay on the line and do not disconnect."
)
VALID_TXN = {
    "amount": 45000.0,
    "timestamp": "2026-09-12T03:15:00Z",
    "device_id": "dev_test_123",
    "is_active_call": True,
    "transaction_velocity": 4,
}


# --- POST /check-url ---
def test_check_url_safe_success():
    r = client.post("/check-url", json={"url": "https://www.google.com/search?q=test"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert 0.0 <= body["score"] < 0.3
    assert isinstance(body["reasons"], list)


def test_check_url_malformed_error():
    r = client.post("/check-url", json={"url": "not a url"})
    assert r.status_code == 422, r.text
    assert "invalid url" in r.json()["detail"].lower()


def test_check_url_missing_field_error():
    r = client.post("/check-url", json={})
    assert r.status_code == 422, r.text


# --- POST /check-message (text) ---
def test_check_message_text_success():
    r = client.post("/check-message", data={"text": FEAR_TEXT})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["signature"] == "fear_authority"
    assert body["score"] >= 0.5


def test_check_message_no_input_error():
    r = client.post("/check-message", data={})
    assert r.status_code == 400, r.text
    assert "text" in r.json()["detail"].lower()


def test_check_message_unreadable_image_error():
    r = client.post(
        "/check-message",
        files={"image": ("evil.txt", b"this is not an image", "image/png")},
    )
    assert r.status_code == 400, r.text


def test_check_message_image_success_mocked(monkeypatch):
    """Image flow with OCR mocked (no Tesseract binary needed)."""
    import app.main as main_mod

    def fake_analyze_image(_content, fetch_live_page=False):
        return {
            "score": 0.75,
            "signature": "greed_opportunity",
            "reasons": ["Matched greed/opportunity pattern: 'guaranteed returns'"],
            "ml_status": "mocked",
            "ocr_text": "Limited time! Guaranteed returns.",
            "ocr_status": "ok",
        }

    monkeypatch.setattr(main_mod, "analyze_image", fake_analyze_image)
    from PIL import Image
    import io

    buf = io.BytesIO()
    Image.new("RGB", (100, 50), "white").save(buf, format="PNG")
    buf.seek(0)
    r = client.post("/check-message", files={"image": ("chat.png", buf, "image/png")})
    assert r.status_code == 200, r.text
    assert r.json()["signature"] == "greed_opportunity"


# --- POST /check-transaction ---
def test_check_transaction_success():
    r = client.post("/check-transaction", json=VALID_TXN)
    assert r.status_code == 200, r.text
    assert 0.0 <= r.json()["score"] <= 1.0


def test_check_transaction_missing_field_error():
    bad = dict(VALID_TXN)
    del bad["amount"]
    r = client.post("/check-transaction", json=bad)
    assert r.status_code == 422, r.text


def test_check_transaction_negative_amount_error():
    bad = dict(VALID_TXN, amount=-50.0)
    r = client.post("/check-transaction", json=bad)
    assert r.status_code == 422, r.text


# --- POST /check-combined ---
def test_check_combined_low_success():
    r = client.post(
        "/check-combined",
        json={
            "url": "https://www.google.com/",
            "text": "Hey, are we still meeting for lunch tomorrow?",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tier"] == "Low"
    assert "Module B" in body["explanation"] and "Module C" in body["explanation"]
    assert "Module A (no transaction submitted)" in body["explanation"]


def test_check_combined_empty_error():
    r = client.post("/check-combined", json={})
    assert r.status_code == 422, r.text


# --- CORS ---
def test_cors_allows_local_frontend():
    r = client.get("/", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
