import os
import joblib
import pandas as pd
import numpy as np

# Global cache for model artifact
_MODEL_ARTIFACT = None

def _get_model_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, ".."))
    return os.path.join(project_root, "ml", "models", "module_a.pkl")

def load_model(model_path: str = None):
    global _MODEL_ARTIFACT
    if model_path is None:
        model_path = _get_model_path()
        
    if _MODEL_ARTIFACT is None or _MODEL_ARTIFACT.get("_path") != model_path:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Module A model artifact not found at {model_path}. Run ml/train_module_a.py first.")
        artifact = joblib.load(model_path)
        artifact["_path"] = model_path
        _MODEL_ARTIFACT = artifact
    return _MODEL_ARTIFACT

def predict_module_a(transaction_dict: dict, model_path: str = None) -> float:
    """
    Predicts fraud risk probability score for Module A (Transaction + Call Correlation).

    Parameters:
    -----------
    transaction_dict : dict
        Dictionary containing transaction telemetry fields.
        Expected keys:
        - 'amount': float
        - 'is_active_call': bool or int
        - 'transaction_velocity': int
        - 'timestamp' (optional): ISO 8601 string or int hour_of_day (0-23)
        - 'device_id' (optional): str or int is_new_device (1/0)
        - 'is_odd_hour' (optional): int/bool
        - 'is_new_device' (optional): int/bool

    Returns:
    --------
    float: Fraud risk score between 0.0 and 1.0
    """
    artifact = load_model(model_path)
    model = artifact["model"]
    device_counts = artifact.get("device_counts", {})
    
    # 1. Parse amount
    amount = float(transaction_dict.get("amount", 0.0))
    
    # 2. Parse active call
    is_active_call = 1 if bool(transaction_dict.get("is_active_call", False)) else 0
    
    # 3. Parse velocity
    velocity = int(transaction_dict.get("transaction_velocity", 1))
    
    # 4. Parse timestamp / hour_of_day / is_odd_hour
    if "is_odd_hour" in transaction_dict:
        is_odd_hour = 1 if bool(transaction_dict["is_odd_hour"]) else 0
        hour_of_day = int(transaction_dict.get("hour_of_day", 12))
    elif "timestamp" in transaction_dict and isinstance(transaction_dict["timestamp"], str):
        try:
            dt = pd.to_datetime(transaction_dict["timestamp"])
            hour_of_day = int(dt.hour)
        except Exception:
            hour_of_day = 12
        is_odd_hour = 1 if (hour_of_day < 6 or hour_of_day >= 23) else 0
    elif "hour_of_day" in transaction_dict:
        hour_of_day = int(transaction_dict["hour_of_day"])
        is_odd_hour = 1 if (hour_of_day < 6 or hour_of_day >= 23) else 0
    else:
        hour_of_day = 12
        is_odd_hour = 0
        
    # 5. Parse device_id / is_new_device
    if "is_new_device" in transaction_dict:
        is_new_device = 1 if bool(transaction_dict["is_new_device"]) else 0
    elif "device_id" in transaction_dict:
        dev_id = str(transaction_dict["device_id"])
        # New or unfamiliar device if count <= 2
        is_new_device = 1 if device_counts.get(dev_id, 0) <= 2 else 0
    else:
        is_new_device = 0

    feature_names = artifact.get("feature_cols", ['amount', 'hour_of_day', 'is_odd_hour', 'is_new_device', 'is_active_call', 'transaction_velocity'])
    input_df = pd.DataFrame([{
        'amount': amount,
        'hour_of_day': hour_of_day,
        'is_odd_hour': is_odd_hour,
        'is_new_device': is_new_device,
        'is_active_call': is_active_call,
        'transaction_velocity': velocity
    }])[feature_names]
    
    risk_score = float(model.predict_proba(input_df)[0, 1])
    return risk_score

if __name__ == "__main__":
    sample_txn = {
        "amount": 50000.0,
        "timestamp": "2026-09-12T02:30:00Z",
        "device_id": "dev_new_9999",
        "is_active_call": True,
        "transaction_velocity": 6
    }
    score = predict_module_a(sample_txn)
    print(f"Sample High Risk Prediction Score: {score:.4f}")
