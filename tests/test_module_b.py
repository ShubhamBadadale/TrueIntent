import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.predict_module_b import check_url


def _result(url: str) -> dict:
    # Disable live page fetching for deterministic, offline-safe tests.
    return check_url(url, fetch_live_page=False)


def test_safe_url_low_score():
    """Clearly safe URL should score low with no risk reasons."""
    res = _result("https://www.google.com/search?q=test")

    assert isinstance(res["score"], float)
    assert 0.0 <= res["score"] <= 1.0
    assert isinstance(res["reasons"], list)
    assert res["score"] < 0.3, f"Expected low score for safe URL, got {res}"
    assert res["reasons"] == [], f"Expected no reasons for safe URL, got {res['reasons']}"


def test_ip_based_url_flagged_suspicious():
    """Clearly suspicious IP-based URL should score high with IP reason."""
    res = _result("http://192.168.1.1/verify-account")

    assert isinstance(res["score"], float)
    assert 0.0 <= res["score"] <= 1.0
    assert isinstance(res["reasons"], list)
    assert res["score"] >= 0.4, f"Expected high score for IP-based URL, got {res}"
    assert any("IP address" in r for r in res["reasons"]), (
        f"Expected IP-address reason, got {res['reasons']}"
    )


def test_edge_case_short_ambiguous_url():
    """Very short/ambiguous URL must not crash and must return valid shape."""
    res = _result("http://t.co/abc")

    assert isinstance(res, dict)
    assert "score" in res and "reasons" in res
    assert isinstance(res["score"], float)
    assert 0.0 <= res["score"] <= 1.0
    assert isinstance(res["reasons"], list)
    assert all(isinstance(r, str) for r in res["reasons"])


def test_typosquatting_detection():
    """Brand-lookalike domain should be flagged as typosquatting."""
    res = _result("http://hdfcbaank-login.xyz/update-kyc")

    assert res["score"] >= 0.35, f"Expected elevated score for typosquat URL, got {res}"
    assert any("typosquatting" in r.lower() or "spoofing" in r.lower() for r in res["reasons"]), (
        f"Expected typosquatting reason, got {res['reasons']}"
    )


def test_long_url_and_suspicious_chars():
    """Long URL with obfuscation characters should accumulate risk."""
    long_url = "http://example.com/" + "a" * 80 + "?q=%20@test"
    res = _result(long_url)

    assert res["score"] >= 0.3, f"Expected elevated score for long/obfuscated URL, got {res}"
    assert any("long" in r.lower() for r in res["reasons"]), (
        f"Expected length reason, got {res['reasons']}"
    )


def test_ml_status_reports_rules_only_when_dataset_pending():
    """Without data/raw/module_b_urls.csv, ML component must report rules-only/pending."""
    dataset_path = os.path.join("data", "raw", "module_b_urls.csv")
    if os.path.exists(dataset_path):
        import pytest
        pytest.skip("Dataset present — ML combined mode expected, skipping pending check.")
    res = _result("https://www.google.com/")
    assert "ml_status" in res
    assert "rules_only" in res["ml_status"]
    assert "pending" in res["ml_status"].lower()
