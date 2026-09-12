import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.predict_module_c import analyze_message


def _result(text: str) -> dict:
    # Disable live page fetching for deterministic, offline-safe tests.
    return analyze_message(text, fetch_live_page=False)


def test_fear_authority_signature():
    """Fear/authority (digital-arrest style) message must be flagged."""
    res = _result(
        "You are under investigation for money laundering. "
        "Stay on the line and do not disconnect. "
        "This is a CBI officer issuing an arrest warrant."
    )

    assert res["signature"] == "fear_authority", f"Got {res}"
    assert isinstance(res["score"], float)
    assert 0.0 <= res["score"] <= 1.0
    assert res["score"] >= 0.5, f"Expected high score for fear message, got {res}"
    assert isinstance(res["reasons"], list) and len(res["reasons"]) > 0


def test_greed_opportunity_signature():
    """Greed/opportunity (fake-trading style) message must be flagged."""
    res = _result(
        "Limited time offer! Guaranteed returns — double your money "
        "with our exclusive stock tip. Join our trading group now."
    )

    assert res["signature"] == "greed_opportunity", f"Got {res}"
    assert isinstance(res["score"], float)
    assert 0.0 <= res["score"] <= 1.0
    assert res["score"] >= 0.5, f"Expected high score for greed message, got {res}"
    assert isinstance(res["reasons"], list) and len(res["reasons"]) > 0


def test_clean_legitimate_message():
    """Benign message should score low with signature 'none'."""
    res = _result("Hey, are we still meeting for lunch tomorrow? Let me know!")

    assert res["signature"] == "none", f"Got {res}"
    assert isinstance(res["score"], float)
    assert 0.0 <= res["score"] <= 1.0
    assert res["score"] < 0.3, f"Expected low score for clean message, got {res}"


def test_embedded_url_folded_into_score():
    """A clean text with a phishing URL must get a boosted score + URL reasons."""
    res = _result(
        "Please update your KYC here: http://192.168.1.1/verify-account thanks"
    )

    assert isinstance(res["score"], float)
    assert 0.0 <= res["score"] <= 1.0
    assert res["score"] >= 0.4, f"Expected URL-boosted score, got {res}"
    assert any("URL" in r for r in res["reasons"]), (
        f"Expected URL evidence in reasons, got {res['reasons']}"
    )


def test_empty_message_edge_case():
    """Empty/whitespace input must not crash and must return valid shape."""
    res = _result("   ")

    assert isinstance(res, dict)
    assert res["signature"] == "none"
    assert isinstance(res["score"], float)
    assert 0.0 <= res["score"] <= 1.0
    assert isinstance(res["reasons"], list)


def test_ml_status_reports_placeholder_when_dataset_pending():
    """Without Module C datasets/model, ML component must report rules-only/pending."""
    sms_path = os.path.join("data", "raw", "sms_spam_collection.csv")
    sig_path = os.path.join("data", "raw", "signature_examples.csv")
    model_path = os.path.join("ml", "models", "module_c.pkl")
    if os.path.exists(sms_path) or os.path.exists(sig_path) or os.path.exists(model_path):
        import pytest
        pytest.skip("Module C dataset/model present — ML mode expected, skipping pending check.")
    res = _result("Hello, just checking in.")
    assert "ml_status" in res
    assert "rules_only" in res["ml_status"]
