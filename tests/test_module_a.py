import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from ml.predict_module_a import predict_module_a


def test_model_artifact_exists():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    model_path = os.path.join(root, "ml", "models", "module_a.pkl")
    assert os.path.exists(model_path), "Model artifact ml/models/module_a.pkl does not exist."

def test_predict_module_a_returns_float_in_range():
    sample_transaction = {
        "amount": 45000.0,
        "timestamp": "2026-09-12T03:15:00Z",
        "device_id": "dev_new_1234",
        "is_active_call": True,
        "transaction_velocity": 4
    }
    
    score = predict_module_a(sample_transaction)
    
    assert isinstance(score, float), f"Expected float return type, got {type(score)}"
    assert 0.0 <= score <= 1.0, f"Expected risk score between 0 and 1, got {score}"

def test_predict_module_a_matches_six_feature_model():
    # The old amount-monotonic demo was a property of the synthetic generator,
    # not a valid invariant for observed IEEE-CIS fraud.
    import pandas as pd
    from ml.predict_module_a import load_model
    from ml.generate_module_a_data import FEATURES
    artifact = load_model()
    assert artifact['feature_cols'] == FEATURES
    transaction = dict(amount=500.0, hour_of_day=14, is_new_device=0,
                       is_active_call=False, transaction_velocity=1)
    row = pd.DataFrame([dict(amount=500.0, hour_of_day=14, is_odd_hour=0,
                            is_new_device=0, is_active_call=0, transaction_velocity=1)])[FEATURES]
    expected = float(artifact['model'].predict_proba(row)[0, 1])
    assert predict_module_a(transaction) == pytest.approx(expected)
