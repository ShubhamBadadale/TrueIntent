"""Offline classifier integration and data validation; never fetch listed URLs."""
from pathlib import Path

import joblib
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split

from ml import predict_module_b as predictor
from ml.generate_module_b_data import generate_module_b_data, validate_urls
from ml.train_module_b import train_module_b


@pytest.fixture(scope="module")
def real_artifact():
    path = Path(__file__).resolve().parents[1] / "ml/models/module_b.pkl"
    if not path.exists():
        pytest.skip("Run generate_module_b_data.py and train_module_b.py for real-data integration tests")
    artifact = joblib.load(path)
    assert artifact["evaluation"]["data_sha256"] == "588f85c75146706a255e8001738b75323443cd062a3c19896df24a999428374f"
    return artifact


@pytest.mark.parametrize("url,label", [
    # Fixed illustrative examples from the seed-42 holdout, labeled in May 2020.
    ("http://crackedtool.com/b/login.php?l=_JeHFUq_VJOXK0QWHtoGYDw1774256418&fid.13InboxLight.aspxn.1774256418&fid.125289964252813InboxLight99642_Product-userid&userid=", 1),
    ("http://iwanarif.lecturer.pens.ac.id/2.%20network%20protocols.pdf", 0),
])
def test_real_classifier_and_blend(real_artifact, monkeypatch, url, label):
    pipeline = real_artifact["pipeline"]
    probability = pipeline.predict_proba([url])[0, list(pipeline.classes_).index(1)]
    assert probability > 0.8 if label else probability < 0.2
    monkeypatch.setattr(predictor, "_load_ml_model", lambda: None)
    rules = predictor.check_url(url, fetch_live_page=False)
    monkeypatch.setattr(predictor, "_load_ml_model", lambda: real_artifact)
    result = predictor.check_url(url, fetch_live_page=False)
    assert result["ml_status"] == "active"
    assert result["score"] == round(0.5 * rules["score"] + 0.5 * probability, 4)
    assert result["score"] > 0.6 if label else result["score"] < 0.3
    assert result["reasons"] == rules["reasons"]


def test_real_split_has_no_duplicate_text_leakage(real_artifact):
    path = Path(__file__).resolve().parents[1] / "data/raw/module_b_urls.csv"
    if not path.exists():
        pytest.skip("Raw dataset needed to verify split membership")
    frame = pd.read_csv(path)
    train, test = train_test_split(frame, test_size=0.2, random_state=42, stratify=frame.label)
    assert not set(train.url.str.lower()) & set(test.url.str.lower())
    assert len(test) == real_artifact["evaluation"]["test_rows"]


def test_inference_failure_retains_rules(monkeypatch):
    monkeypatch.setattr(predictor, "_load_ml_model", lambda: {"pipeline": object()})
    result = predictor.check_url("http://192.168.1.1/verify-account", False)
    assert result["ml_status"] == "rules_only (ML inference failed)"
    assert result["score"] == pytest.approx(0.6)


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
    assert artifact["evaluation"]["test_rows"] == 8
    monkeypatch.setattr(predictor, "_ML_MODEL_ARTIFACT", None)
    monkeypatch.setattr(predictor, "_get_model_path", lambda: str(model))
    assert predictor.check_url("https://library99.example/books", False)["ml_status"] == "active"
