"""Offline classifier integration and data validation; never fetch listed URLs."""
from pathlib import Path

import joblib
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split

pytest.importorskip("sklearn", reason="scikit-learn required for classifier tests")

from ml import predict_module_b as predictor
from ml.generate_module_b_data import generate_module_b_data, validate_urls
from ml.train_module_b import train_module_b
from ml.features_module_b import FEATURE_NAMES, parse_url, registered_domain, url_features


@pytest.fixture(scope="module")
def real_artifact():
    path = Path(__file__).resolve().parents[1] / "ml/models/module_b.pkl"
    if not path.exists():
        pytest.skip("Run generate_module_b_data.py and train_module_b.py for real-data integration tests")
    artifact = joblib.load(path)
    assert artifact["evaluation"]["data_sha256"] == "588f85c75146706a255e8001738b75323443cd062a3c19896df24a999428374f"
    return artifact


@pytest.mark.parametrize("url", [
    # Historical examples for pipeline/API wiring, not accuracy assertions.
    "http://crackedtool.com/b/login.php?l=_JeHFUq_VJOXK0QWHtoGYDw1774256418&fid.13InboxLight.aspxn.1774256418&fid.125289964252813InboxLight99642_Product-userid&userid=",
    "http://iwanarif.lecturer.pens.ac.id/2.%20network%20protocols.pdf",
])
def test_real_classifier_and_blend(real_artifact, monkeypatch, url):
    pipeline = real_artifact["pipeline"]
    probability = pipeline.predict_proba([url])[0, list(pipeline.classes_).index(1)]
    assert 0 <= probability <= 1
    monkeypatch.setattr(predictor, "_load_ml_model", lambda: None)
    rules = predictor.check_url(url, fetch_live_page=False)
    monkeypatch.setattr(predictor, "_load_ml_model", lambda: real_artifact)
    result = predictor.check_url(url, fetch_live_page=False)
    assert result["ml_status"] == "active"
    assert result["score"] == round(0.5 * rules["score"] + 0.5 * probability, 4)
    assert result["reasons"] == rules["reasons"]


def test_real_split_has_no_duplicate_text_leakage(real_artifact):
    path = Path(__file__).resolve().parents[1] / "data/raw/module_b_urls.csv"
    if not path.exists():
        pytest.skip("Raw dataset needed to verify split membership")
    frame = pd.read_csv(path)
    train, test = train_test_split(frame, test_size=0.2, random_state=42, stratify=frame.label)
    assert not set(train.url.str.lower()) & set(test.url.str.lower())
    assert len(test) == real_artifact["evaluation"]["random_split"]["test_rows"]
    disjoint = real_artifact["evaluation"]["registered_domain_disjoint_split"]
    assert disjoint["shared_hostnames"] == 0
    assert disjoint["shared_registered_domains"] == 0


def test_inference_failure_retains_rules(monkeypatch):
    monkeypatch.setattr(predictor, "_load_ml_model", lambda: {"pipeline": object()})
    result = predictor.check_url("http://192.168.1.1/verify-account", False)
    assert result["ml_status"] == "rules_only (ML inference failed)"
    # Rules-only fallback: insecure HTTP (0.20) + raw IP (0.40) +
    # private/internal target (0.25) + suspicious path/query (0.15), capped at 1.0.
    assert result["score"] == pytest.approx(1.0)


def test_loader_missing_and_corrupt_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(predictor, "_ML_MODEL_ARTIFACT", None)
    path = tmp_path / "model.pkl"
    assert predictor._load_ml_model(str(path)) is None
    path.write_bytes(b"not a model")
    assert predictor._load_ml_model(str(path)) is None


def test_ingestion_maps_status_and_removes_duplicates(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("url,status\nhttps://safe.example/,legitimate\nhttp://bad.example/,phishing\nhttp://BAD.example/,phishing\n")
    output = tmp_path / "urls.csv"
    result = generate_module_b_data(source, output)
    assert list(result.columns) == ["url", "label"]
    assert len(result) == 2
    assert output.with_suffix(".metadata.json").exists()


@pytest.mark.parametrize("rows", [
    [("http://a.example", "unknown"), ("http://b.example", "phishing")],
    [(None, "legitimate"), ("http://b.example", "phishing")],
    [("not-a-url", "legitimate"), ("http://b.example", "phishing")],
    [("http://a.example", "legitimate"), ("http://A.example", "phishing")],
    [("http://a.example", "phishing"), ("http://b.example", "phishing")],
])
def test_reject_invalid_data(rows):
    with pytest.raises(ValueError):
        validate_urls(pd.DataFrame(rows, columns=["url", "label"]))


def test_training_roundtrip(tmp_path, monkeypatch):
    # Synthetic unit-test inputs ONLY; not production training or reported metrics.
    rows = [(f"https://library{i}.example/books", "legitimate") for i in range(20)]
    rows += [(f"http://verify{i}.example/login/password", "phishing") for i in range(20)]
    data = tmp_path / "urls.csv"
    model = tmp_path / "model.pkl"
    pd.DataFrame(rows, columns=["url", "label"]).to_csv(data, index=False)
    artifact = train_module_b(str(data), str(model))
    assert artifact["evaluation"]["random_split"]["test_rows"] == 8
    monkeypatch.setattr(predictor, "_ML_MODEL_ARTIFACT", None)
    monkeypatch.setattr(predictor, "_get_model_path", lambda: str(model))
    assert predictor.check_url("https://library99.example/books", False)["ml_status"] == "active"


def test_feature_extraction_is_offline_and_has_fixed_semantics():
    values = url_features("https://xn--bcher-kva.example/login/a%20b?x=123")
    assert len(values) == len(FEATURE_NAMES)
    assert values[0] == len("https://xn--bcher-kva.example/login/a%20b?x=123")
    assert values[1] == len("xn--bcher-kva.example")
    assert values[2] == len("/login/a%20b")
    assert values[8] == 1  # IDN encoded as punycode
    assert values[9] >= 1
    assert values[10] == 1  # percent encoded byte
    assert registered_domain("a.shop.example.co.uk") == "example.co.uk"
    assert parse_url("HTTPS://example.com:443/path").scheme == "https"


def test_inference_uses_shared_url_parser_and_preserves_response_shape(monkeypatch):
    monkeypatch.setattr(predictor, "_load_ml_model", lambda: None)
    result = predictor.check_url("HTTPS://[2001:db8::1]/login", fetch_live_page=False)
    assert set(result) == {"score", "reasons", "ml_status"}
    assert any("IP address" in reason for reason in result["reasons"])


def test_default_inference_never_fetches_live_pages(monkeypatch):
    monkeypatch.setattr(predictor, "_load_ml_model", lambda: None)
    def forbidden(*args, **kwargs):
        pytest.fail("Default URL analysis must not fetch a page")
    monkeypatch.setattr(predictor, "inspect_live_page", forbidden)
    predictor.check_url("https://example.com/")


def test_offline_psl_groups_multilevel_and_private_suffixes(monkeypatch):
    import requests
    def forbidden(*args, **kwargs):
        pytest.fail("PSL extraction must not access the network")
    monkeypatch.setattr(requests.Session, "request", forbidden)
    assert registered_domain("https://a.bank.co.in/x") == registered_domain("https://b.bank.co.in/y")
    assert registered_domain("https://a.blogspot.com/") == registered_domain("https://b.blogspot.com/")
    assert registered_domain("https://[::1]/") == "::1"


def test_credentials_do_not_hide_ip_hostname(monkeypatch):
    monkeypatch.setattr(predictor, "_load_ml_model", lambda: None)
    result = predictor.check_url("https://user:pass@192.168.1.1/")
    assert any("IP address" in reason for reason in result["reasons"])


def test_training_saves_backward_compatible_pipeline_and_domain_audit(tmp_path):
    rows = [(f"https://site{i}.example/path", "legitimate") for i in range(25)]
    rows += [(f"http://login{i}.test/phish", "phishing") for i in range(25)]
    data, model = tmp_path / "urls.csv", tmp_path / "model.pkl"
    pd.DataFrame(rows, columns=["url", "label"]).to_csv(data, index=False)
    artifact = train_module_b(str(data), str(model))
    loaded = joblib.load(model)
    assert hasattr(loaded["pipeline"], "predict_proba")
    assert len(loaded["pipeline"].predict_proba(["https://new.example/"])[0]) == 2
    assert artifact["evaluation"]["registered_domain_disjoint_split"]["shared_registered_domains"] == 0
    assert set(artifact["evaluation"]["models"]) == {"random_split", "registered_domain_disjoint_split"}
