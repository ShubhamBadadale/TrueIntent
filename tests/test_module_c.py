import pytest

from ml import predict_module_c
from ml.predict_module_c import analyze_message

@pytest.fixture(autouse=True)
def missing_model(monkeypatch):
    # Missing artifacts must abstain, regardless of keyword hits.
    monkeypatch.setattr(predict_module_c, "_load_ml_model", lambda: None)


def _result(text: str) -> dict:
    # Disable live page fetching for deterministic, offline-safe tests.
    return analyze_message(text, fetch_live_page=False)


def test_fear_keywords_do_not_replace_missing_model():
    """No unvalidated keyword score is presented as an ML assessment."""
    res = _result(
        "You are under investigation for money laundering. "
        "Stay on the line and do not disconnect. "
        "This is a CBI officer issuing an arrest warrant."
    )

    assert res["signature"] == "none", f"Got {res}"
    assert isinstance(res["score"], float)
    assert 0.0 <= res["score"] <= 1.0
    assert not res['text_assessed']
    assert 'not assessed' in res['ml_status']
    assert isinstance(res["reasons"], list) and len(res["reasons"]) > 0


def test_greed_keywords_do_not_replace_missing_model():
    """Abstain even when old greed keywords match."""
    res = _result(
        "Limited time offer! Guaranteed returns — double your money "
        "with our exclusive stock tip. Join our trading group now."
    )

    assert res["signature"] == "none", f"Got {res}"
    assert isinstance(res["score"], float)
    assert 0.0 <= res["score"] <= 1.0
    assert not res['text_assessed']
    assert isinstance(res["reasons"], list) and len(res["reasons"]) > 0


def test_clean_message_is_also_unassessed_without_model():
    """Numeric compatibility placeholder is never a benign prediction."""
    res = _result("Hey, are we still meeting for lunch tomorrow? Let me know!")

    assert res["signature"] == "none", f"Got {res}"
    assert isinstance(res["score"], float)
    assert 0.0 <= res["score"] <= 1.0
    assert res["score"] < 0.3, f"Expected low score for clean message, got {res}"
    assert not res['text_assessed']


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
    """Without a model, text assessment is explicitly unavailable."""
    res = _result("Hello, just checking in.")
    assert "ml_status" in res
    assert "unavailable" in res["ml_status"]
