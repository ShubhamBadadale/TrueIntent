"""End-to-end integration tests: full user flows across API + Modules A-D.

Unlike the unit tests (one module in isolation), these tests drive the real
FastAPI endpoints via TestClient — the same endpoints the React portal calls —
and assert coherence with the underlying modules. Needs fastapi/httpx
(backend venv); skipped otherwise.
"""

from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi required for integration tests")
httpx = pytest.importorskip("httpx", reason="httpx required for TestClient")

from fastapi.testclient import TestClient

from backend.app.main import app
from ml.predict_module_b import check_url
from ml.predict_module_c import analyze_message

client = TestClient(app)

ROOT = Path(__file__).resolve().parents[1]
PHISH_URL = "http://hdfcbaank-login.xyz/update-kyc"
IP_URL = "http://192.168.1.1/verify-account"
SAFE_URL = "https://www.google.com/search?q=test"
FEAR_TEXT = (
    "You are under investigation for money laundering. "
    "Stay on the line and do not disconnect."
)
# Demo fixture; its score is not evidence of real-world fraud detection.
MODEST_TXN = {
    "amount": 8000.0,
    "timestamp": "2026-09-12T14:00:00Z",
    "device_id": "dev_0001",
    "is_active_call": True,
    "transaction_velocity": 2,
}


# --- 1. URL flow: frontend -> API -> Module B coherence -----------------------
def test_url_flow_matches_module_b_rules():
    """Phishing URL through POST /check-url must equal Module B's verdict."""
    api = client.post("/check-url", json={"url": PHISH_URL})
    assert api.status_code == 200, api.text
    body = api.json()

    direct = check_url(PHISH_URL, fetch_live_page=False)
    assert body["score"] == direct["score"]
    assert body["reasons"] == direct["reasons"]
    # Coherent with the rules: typosquat + high-risk TLD flagged, risky score.
    assert body["score"] >= 0.4
    assert any("brand" in r.lower() or "typosquatting" in r.lower() for r in body["reasons"])


def test_url_flow_safe_url_coherence():
    api = client.post("/check-url", json={"url": SAFE_URL})
    assert api.status_code == 200, api.text
    body = api.json()
    assert body["score"] < 0.3
    assert body["reasons"] == check_url(SAFE_URL, fetch_live_page=False)["reasons"]


# --- 2. Message flow: Module C must trigger Module B internally ---------------
@pytest.mark.skipif(
    not (Path(__file__).resolve().parent.parent / "ml/models/module_c.pkl").exists(),
    reason="Train Module C (ml/train_module_c.py) to run model-backed integration tests",
)
def test_message_with_embedded_url_folds_in_module_b():
    """Scam phrase + suspicious URL: signature from text, score reflects BOTH."""
    text = (
        "You are under investigation. Update your KYC here: "
        f"{IP_URL} immediately, do not disconnect."
    )
    api = client.post("/check-message", data={"text": text})
    assert api.status_code == 200, api.text
    body = api.json()

    direct_c = analyze_message(text, fetch_live_page=False)
    direct_b = check_url(IP_URL, fetch_live_page=False)
    text_only = analyze_message(FEAR_TEXT, fetch_live_page=False)

    assert body["signature"] == "fear_authority"  # text psychology detected
    assert body["score"] == direct_c["score"]  # API == module, no drift
    assert any("URL" in r for r in body["reasons"])  # Module B evidence folded in
    # Combined score reflects both signals (max of the two channels).
    assert body["score"] >= direct_b["score"]
    assert body["score"] >= text_only["score"]


def test_combined_rejects_obsolete_transaction_fusion():
    response = client.post(
        "/check-combined", json={"transaction": MODEST_TXN, "text": FEAR_TEXT}
    )
    assert response.status_code == 422
    assert "fusion is disabled" in response.json()["detail"]


# --- 4. Frontend wiring: portal calls the routes that exist -------------------
def test_frontend_api_client_matches_backend_routes():
    """No-browser check that the React portal targets real backend endpoints."""
    client_src = (ROOT / "frontend" / "src" / "api.js").read_text(encoding="utf-8")
    # OpenAPI paths, not app.routes: included routers are represented
    # opaquely on app.routes in current Starlette, while the schema lists the
    # served, documented surface.
    route_paths = set(app.openapi().get("paths", {}))
    for endpoint in ("/check-url", "/check-message", "/check-transaction",
                     "/api/v1/analyze/url", "/api/v1/analyze/message",
                     "/api/v1/analyze/image", "/api/v1/analyze/combined",
                     "/api/v1/module-a/benchmark", "/health", "/ready"):
        assert endpoint in route_paths, f"Backend has no route {endpoint}"
    for endpoint in ("/check-url", "/check-message", "/check-transaction"):
        assert endpoint in client_src, f"Frontend api.js never calls {endpoint}"
