import importlib
import joblib
import pytest

pytest.importorskip("fastapi", reason="fastapi required for API tests")
pytest.importorskip("httpx", reason="httpx required for TestClient")

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)
BASE = dict(amount=500, amount_unit='ieee_cis_source')


@pytest.mark.parametrize('payload', [{'amount': 500}, {'amount': 500, 'amount_unit': 'INR'}])
def test_api_rejects_real_or_unspecified_currency(payload):
    response = client.post('/check-transaction', json=payload)
    assert response.status_code == 422
    assert 'INR' in response.json()['detail']


@pytest.mark.parametrize('amount', [True, -1, 'Infinity', 'NaN', 1e100])
def test_api_rejects_invalid_amount(amount):
    assert client.post('/check-transaction', json=dict(BASE, amount=amount)).status_code == 422


def test_api_accepts_source_zero_and_does_not_require_device(benchmark_model):
    assert client.post('/check-transaction', json=dict(BASE, amount=0)).status_code == 200


@pytest.mark.parametrize('legacy', [False, True])
def test_missing_and_legacy_artifacts_are_unavailable(tmp_path, monkeypatch, legacy):
    path = tmp_path / 'module_a.pkl'
    if legacy:
        joblib.dump({'feature_cols': ['amount', 'hour_of_day'], 'model': object()}, path)
    predictor = importlib.import_module('ml.predict_module_a')
    monkeypatch.setattr(predictor, '_get_model_path', lambda: str(path))
    response = client.post('/check-transaction', json=BASE)
    assert response.status_code == 503
    assert 'score' not in response.json()


@pytest.mark.parametrize('unit', ['INR', 'ieee_cis_source'])
def test_transaction_fusion_is_disabled_without_silently_skipping_it(unit):
    response = client.post('/check-combined', json={
        'transaction': dict(BASE, amount_unit=unit), 'text': 'Lunch tomorrow?',
    })
    assert response.status_code == 422
    assert 'fusion is disabled' in response.json()['detail']


def test_api_timestamps_and_device_ids_cannot_change_score(benchmark_model):
    scores = []
    for timestamp, device in [('2026-01-01T00:00:00Z', 'known'),
                              ('2026-01-01T05:30:00+05:30', 'unknown')]:
        response = client.post('/check-transaction', json=dict(BASE, timestamp=timestamp, device_id=device))
        assert response.status_code == 200
        scores.append(response.json()['score'])
    assert scores[0] == scores[1]
