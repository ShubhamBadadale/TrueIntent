from datetime import datetime, timezone, timedelta

import pytest

pytest.importorskip("fastapi", reason="fastapi required for API tests")
pytest.importorskip("httpx", reason="httpx required for TestClient")

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas import TransactionCheckRequest

client = TestClient(app)

def payload(age=0):
    return dict(amount=500, device_id='phone-demo', is_active_call=False,
        call_telemetry=dict(device_id='phone-demo', is_active_call=True,
            timestamp=(datetime.now(timezone.utc)-timedelta(seconds=age)).isoformat()))


def test_telemetry_overrides_manual_and_preserves_contract():
    normalized = TransactionCheckRequest(**payload()).to_module_a_payload()
    assert normalized['is_active_call'] is True
    assert 'call_telemetry' not in normalized
    assert TransactionCheckRequest(amount=500, device_id='manual').to_module_a_payload()['is_active_call'] is False


def test_phone_and_manual_paths_are_not_interpreted_as_benchmark_units():
    phone = payload()
    manual = dict(amount=500, device_id='phone-demo', is_active_call=True)
    def post(body): return client.post('/check-transaction', json=body)
    real = post(phone); demo = post(manual)
    assert real.status_code == demo.status_code == 422
    assert 'INR' in real.json()['detail']


def test_call_report_does_not_change_benchmark_score(benchmark_model):
    phone = dict(payload(), amount_unit='ieee_cis_source')
    manual = dict(amount=500, amount_unit='ieee_cis_source')
    real = client.post('/check-transaction', json=phone)
    demo = client.post('/check-transaction', json=manual)
    assert real.status_code == demo.status_code == 200
    assert real.json()['score'] == demo.json()['score']


@pytest.mark.parametrize('age', [121, -31])
def test_stale_future_telemetry_rejected(age):
    assert client.post('/check-transaction',json=payload(age)).status_code == 422


def test_mismatched_device_and_naive_timestamp_rejected():
    p = payload(); p['call_telemetry']['device_id'] = 'other'
    assert client.post('/check-transaction',json=p).status_code == 422
    p = payload(); p['call_telemetry']['timestamp'] = '2026-09-26T12:00:00'
    assert client.post('/check-transaction',json=p).status_code == 422
