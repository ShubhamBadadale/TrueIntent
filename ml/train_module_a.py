import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
import xgboost as xgb

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.generate_module_a_data import generate_synthetic_data


def preprocess_features(df: pd.DataFrame, device_counts: dict = None):
    """
    Transforms raw telemetry data into model features.
    
    Features engineered:
    - hour_of_day: int (0-23)
    - is_odd_hour: int (1 if hour < 6 or >= 23 else 0)
    - is_new_device: int (1 if device historical count <= 2 else 0)
    - amount: float
    - is_active_call: int (1/0)
    - transaction_velocity: int
    """
    df = df.copy()
    
    # Parse timestamp
    if 'timestamp' in df.columns:
        parsed_dt = pd.to_datetime(df['timestamp'], errors='coerce')
        df['hour_of_day'] = parsed_dt.dt.hour.fillna(12).astype(int)
        df['is_odd_hour'] = ((df['hour_of_day'] < 6) | (df['hour_of_day'] >= 23)).astype(int)
    else:
        if 'hour_of_day' not in df.columns:
            df['hour_of_day'] = 12
        df['is_odd_hour'] = ((df['hour_of_day'] < 6) | (df['hour_of_day'] >= 23)).astype(int)
        
    # Process device_id
    if device_counts is None:
        if 'device_id' in df.columns:
            device_counts = df['device_id'].value_counts().to_dict()
        else:
            device_counts = {}
            
    if 'is_new_device' not in df.columns:
        if 'device_id' in df.columns:
            df['is_new_device'] = df['device_id'].apply(lambda d: 1 if device_counts.get(d, 0) <= 2 else 0)
        else:
            df['is_new_device'] = 0

    # Ensure numeric types
    df['is_active_call'] = df['is_active_call'].astype(int)
    df['amount'] = df['amount'].astype(float)
    df['transaction_velocity'] = df['transaction_velocity'].astype(int)
    
    feature_cols = ['amount', 'hour_of_day', 'is_odd_hour', 'is_new_device', 'is_active_call', 'transaction_velocity']
    return df[feature_cols], device_counts

def train_module_a(data_path: str = "data/raw/module_a_transactions.csv", model_output_path: str = "ml/models/module_a.pkl"):
    """
    Trains XGBoost binary classifier for Module A risk engine and exports artifact.
    """
    if not os.path.exists(data_path):
        print(f"[Train Module A] Dataset not found at {data_path}. Generating synthetic dataset...")
        generate_synthetic_data(output_path=data_path)
        
    print(f"[Train Module A] Loading dataset from {data_path}...")
    raw_df = pd.read_csv(data_path)
    
    # Target encoding
    y = raw_df['label'].apply(lambda l: 1 if str(l).lower() == 'fraud' else 0).values
    
    # Feature extraction
    X, device_counts = preprocess_features(raw_df)
    
    # Train / Test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    
    print(f"[Train Module A] Training XGBoost classifier on {len(X_train)} train samples, evaluating on {len(X_test)} test samples...")
    
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
        eval_metric='logloss'
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    
    print("\n" + "="*50)
    print("MODULE A — XGBOOST TEST SET EVALUATION METRICS")
    print("="*50)
    print(f"Precision:            {precision:.4f}")
    print(f"Recall:               {recall:.4f}")
    print(f"F1 Score:             {f1:.4f}")
    print(f"False Positive Rate:  {fpr:.4f}")
    print("="*50 + "\n")
    
    # Package artifact
    artifact = {
        "model": model,
        "feature_cols": ['amount', 'hour_of_day', 'is_odd_hour', 'is_new_device', 'is_active_call', 'transaction_velocity'],
        "device_counts": device_counts,
        "metrics": {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "fpr": float(fpr)
        }
    }
    
    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    joblib.dump(artifact, model_output_path)
    print(f"[Train Module A] Model artifact successfully saved to {model_output_path}")
    return artifact

if __name__ == "__main__":
    train_module_a()
