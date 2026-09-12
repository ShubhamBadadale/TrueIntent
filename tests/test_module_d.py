import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from ml.predict_module_a import predict_module_a
from ml.predict_module_b import check_url
from ml.predict_module_c import analyze_message
from ml.predict_module_d import compute_unified_score


LOW_TXN = {
    "amount": 500.0,
    "timestamp": "2026-09-12T14:00:00Z",
    "device_id": "dev_0001",
    "is_active_call": False,
    "transaction_velocity": 1,
}
HIGH_TXN = {
    "amount": 80000.0,
    "timestamp": "2026-09-12T02:30:00Z",
    "device_id": "dev_new_9999",
    "is_active_call": True,
    "transaction_velocity": 7,
}
FEAR_TEXT = (
    "You are under investigation for money laundering. "
    "Stay on the line and do not disconnect."
)
CLEAN_TEXT = "Hey, are we still meeting for lunch tomorrow? Let me know!"


def _mod_a(txn):
    return {"score": predict_module_a(txn), "transaction": txn}


def _mod_b(url):
    return check_url(url, fetch_live_page=False)


def _mod_c(text):
    res = analyze_message(text, fetch_live_page=False)
    res["text"] = text  # context for Module C token attribution
    return res


def test_low_risk_combination_returns_low():
    res = compute_unified_score(
        _mod_a(LOW_TXN),
        _mod_b("https://www.google.com/search?q=test"),
        _mod_c(CLEAN_TEXT),
    )

    assert res["tier"] == "Low", f"Got {res}"
    assert isinstance(res["score"], float) and 0.0 <= res["score"] <= 1.0
    assert isinstance(res["explanation"], str) and len(res["explanation"]) > 0
    # All three ran -> none skipped, all named as contributing.
    assert "Modules skipped: none" in res["explanation"]
    assert "Module A" in res["explanation"]
    assert "Module B" in res["explanation"]
    assert "Module C" in res["explanation"]


def test_high_risk_combination_returns_critical():
    res = compute_unified_score(
        _mod_a(HIGH_TXN),
        _mod_b("http://hdfcbaank-login.xyz/update-kyc"),
        _mod_c(FEAR_TEXT),
    )

    assert res["tier"] == "Critical", f"Got {res}"
    assert res["score"] >= 0.75
    expl = res["explanation"].lower()
    assert len(res["explanation"]) > 0
    # Correct contributing signals referenced:
    # Module A: SHAP on the XGBoost model must surface a transaction factor.
    assert any(s in expl for s in (
        "active call", "transfer amount", "rapid burst",
        "unrecognised device", "late-night", "transaction risk score",
    )), f"Missing Module A signal in: {res['explanation']}"
    # Module B: brand-mimic link.
    assert any(s in expl for s in ("brand", "link risk score")), (
        f"Missing Module B signal in: {res['explanation']}"
    )
    # Module C: authority-impersonation language.
    assert any(s in expl for s in ("authority", "impersonation", "message risk score")), (
        f"Missing Module C signal in: {res['explanation']}"
    )


def test_skipped_modules_reported_honestly():
    """Transaction-only check: B and C must be reported skipped, never implied."""
    res = compute_unified_score(_mod_a(LOW_TXN), None, None)

    assert res["tier"] in ("Low", "Medium", "High", "Critical")
    assert "Module A" in res["explanation"]
    assert "Module B (no URL submitted)" in res["explanation"]
    assert "Module C (no message submitted)" in res["explanation"]
    # The contributing section must not name modules that never ran.
    contrib_section = res["explanation"].split("Modules contributing:")[1].split("Modules skipped:")[0]
    assert "Module B" not in contrib_section and "Module C" not in contrib_section


def test_no_modules_raises_instead_of_false_verdict():
    with pytest.raises(ValueError):
        compute_unified_score(None, None, None)


def test_accepts_plain_float_scores():
    res = compute_unified_score(0.9, 0.8, 0.85)
    assert res["tier"] == "Critical"
    assert res["explanation"]
