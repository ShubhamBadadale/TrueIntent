from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import TransactionCheckRequest

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


@pytest.mark.parametrize('route', ['/check-transaction', '/check-combined'])
def test_phone_and_manual_paths_score_identically(route):
    phone = payload()
    manual = dict(amount=500, device_id='phone-demo', is_active_call=True)
    def post(body): return client.post(route,json={'transaction':body} if route.endswith('combined') else body)
    real = post(phone); demo = post(manual)
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
