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

def test_predict_module_a_relative_risk():
    low_risk_txn = {
        "amount": 500.0,
        "timestamp": "2026-09-12T14:00:00Z",
        "device_id": "dev_0001",
        "is_active_call": False,
        "transaction_velocity": 1
    }
    
    high_risk_txn = {
        "amount": 80000.0,
        "timestamp": "2026-09-12T02:30:00Z",
        "device_id": "dev_new_9999",
        "is_active_call": True,
        "transaction_velocity": 7
    }
    
    low_score = predict_module_a(low_risk_txn)
    high_score = predict_module_a(high_risk_txn)
    
    assert 0.0 <= low_score <= 1.0
    assert 0.0 <= high_score <= 1.0
    assert high_score > low_score, f"Expected high risk score ({high_score}) to be greater than low risk score ({low_score})"
