import importlib
import joblib
import numpy as np
import pandas as pd
import pytest

from ml.features_module_a import (
    FEATURES, FEATURE_CONTRACT, SOURCE_AMOUNT_UNIT, ModuleAUnavailableError,
    preprocess_features, transaction_features,
)
from ml.predict_module_a import predict_module_a, load_model
from ml.predict_module_d import _build_module_a_features, _describe_module_a_feature, _shap_factors_module_a

BASE = dict(amount=5.25, amount_unit=SOURCE_AMOUNT_UNIT)


def test_training_inference_and_explanation_share_features(benchmark_model):
    frame = pd.DataFrame([dict(BASE, timestamp='2026-01-01T00:00:00Z', device_id='unknown')])
    pd.testing.assert_frame_equal(preprocess_features(frame), transaction_features(frame.iloc[0].to_dict()))
    assert _build_module_a_features(frame.iloc[0].to_dict(), benchmark_model) == {'amount': 5.25}
    assert benchmark_model['feature_cols'] == FEATURES == ['amount']
    expected = benchmark_model['model'].predict_proba(preprocess_features(frame))[0, 1]
    assert predict_module_a(frame.iloc[0].to_dict()) == pytest.approx(expected)


@pytest.mark.parametrize('metadata', [
    {'timestamp': '2026-01-01T00:00:00Z'},
    {'timestamp': '2026-01-01T05:30:00+05:30'},
    {'timestamp': '2026-01-01T23:00:00'},
    {'device_id': 'known', 'is_new_device': False},
    {'device_id': 'never-seen', 'is_new_device': True},
    {'is_active_call': True, 'transaction_velocity': 100, 'is_odd_hour': 1, 'hour_of_day': 2},
])
def test_unsupported_metadata_cannot_change_prediction(benchmark_model, metadata):
    assert predict_module_a(dict(BASE, **metadata)) == predict_module_a(BASE)
    assert list(transaction_features(dict(BASE, **metadata)).columns) == ['amount']


@pytest.mark.parametrize('unit', [None, 'INR', 'USD', ''])
def test_missing_or_currency_units_rejected_before_model_loading(unit):
    payload = dict(BASE)
    if unit is None:
        del payload['amount_unit']
    else:
        payload['amount_unit'] = unit
    with pytest.raises(ValueError):
        predict_module_a(payload, 'does-not-exist.pkl')


@pytest.mark.parametrize('amount', [float('nan'), float('inf'), -float('inf'), -1, True, 1e100])
def test_invalid_amounts_rejected(amount):
    with pytest.raises(ValueError):
        transaction_features(dict(BASE, amount=amount))


def test_zero_is_consistent_with_source_contract(benchmark_model):
    assert np.isfinite(predict_module_a(dict(BASE, amount=0)))


def test_roundtrip_and_missing_corrupt_legacy_artifacts(benchmark_file, tmp_path):
    assert load_model(str(benchmark_file))['feature_contract'] == FEATURE_CONTRACT
    path = tmp_path / 'model.pkl'
    with pytest.raises(ModuleAUnavailableError, match='missing'):
        load_model(str(path))
    path.write_bytes(b'bad pickle')
    with pytest.raises(ModuleAUnavailableError):
        load_model(str(path))
    joblib.dump({'model': object(), 'feature_cols': ['amount', 'hour_of_day'], 'device_counts': {}}, path)
    with pytest.raises(ModuleAUnavailableError, match='obsolete'):
        load_model(str(path))


def test_artifact_replacement_invalidates_cache(benchmark_file, tmp_path):
    path = tmp_path / 'model.pkl'
    path.write_bytes(benchmark_file.read_bytes())
    load_model(str(path))
    joblib.dump({'feature_cols': ['amount']}, path)
    with pytest.raises(ModuleAUnavailableError):
        load_model(str(path))


def test_explanations_never_invent_removed_features(monkeypatch):
    for name in ['is_active_call', 'is_new_device', 'transaction_velocity', 'hour_of_day', 'is_odd_hour']:
        assert _describe_module_a_feature(name, 1) is None
    assert 'source units' in _describe_module_a_feature('amount', 5)
    predictor = importlib.import_module('ml.predict_module_a')
    def unavailable():
        raise ModuleAUnavailableError('test missing artifact')
    monkeypatch.setattr(predictor, 'load_model', unavailable)
    factors, method = _shap_factors_module_a({'score': .9, 'transaction': dict(BASE, is_active_call=True)})
    assert factors == []
    assert method == 'attribution_unavailable'
