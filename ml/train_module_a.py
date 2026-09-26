"""Chronological evaluation and paired synthetic-telemetry ablation."""
import json
from pathlib import Path
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
import xgboost as xgb
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.generate_module_a_data import FEATURES, SYNTHETIC, backup, generate_module_a_data, sha256


def preprocess_features(df: pd.DataFrame, device_counts: dict = None):
    missing = set(FEATURES) - set(df.columns)
    if missing:
        raise ValueError(f'Missing features {sorted(missing)}; regenerate Module A data')
    features = df[FEATURES].apply(pd.to_numeric, errors='raise')
    if not np.isfinite(features.to_numpy()).all():
        raise ValueError('Non-finite features')
    for name in ['is_odd_hour', *SYNTHETIC]:
        if not features[name].isin([0, 1]).all():
            raise ValueError(f'{name} must be binary')
    return features, {} if device_counts is None else device_counts


def chronological_split(df):
    ordered = df.sort_values(['TransactionDT', 'TransactionID']).reset_index(drop=True)
    cutoff = ordered.TransactionDT.iloc[int(len(ordered) * 0.8)]
    train = ordered[ordered.TransactionDT < cutoff]
    test = ordered[ordered.TransactionDT >= cutoff]
    if train.empty or test.empty or train.label.nunique() != 2 or test.label.nunique() != 2:
        raise ValueError('Chronological train and holdout must each contain both classes')
    return train, test, int(cutoff)


def evaluate(y, predicted):
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    return {'precision': float(precision_score(y, predicted, zero_division=0)),
            'recall': float(recall_score(y, predicted, zero_division=0)),
            'f1': float(f1_score(y, predicted, zero_division=0)),
            'fpr': float(fp / (fp + tn)),
            'confusion_matrix': [[int(tn), int(fp)], [int(fn), int(tp)]]}


def train_module_a(data_path: str = 'data/raw/module_a_transactions.csv', model_output_path: str = 'ml/models/module_a.pkl'):
    data_path = Path(data_path)
    if not data_path.exists():
        generate_module_a_data(output_path=data_path)
    metadata = json.loads(data_path.with_suffix('.metadata.json').read_text(encoding='utf-8'))
    if metadata['data_sha256'] != sha256(data_path):
        raise ValueError('Dataset hash differs from provenance; regenerate before training')
    df = pd.read_csv(data_path)
    if not df.label.isin(['fraud', 'legitimate']).all():
        raise ValueError('Unknown labels')
    train, test, cutoff = chronological_split(df)
    X_train, _ = preprocess_features(train)
    X_test, _ = preprocess_features(test)
    y_train = (train.label == 'fraud').astype(int)
    y_test = (test.label == 'fraud').astype(int)
    parameters = dict(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42,
                      eval_metric='logloss', tree_method='hist', n_jobs=4,
                      scale_pos_weight=float((y_train == 0).sum() / y_train.sum()))
    results = {}
    for name, columns in [('with_telemetry', FEATURES),
                          ('without_telemetry', [c for c in FEATURES if c not in SYNTHETIC])]:
        model = xgb.XGBClassifier(**parameters)
        model.fit(X_train[columns], y_train)
        results[name] = evaluate(y_test, model.predict_proba(X_test[columns])[:, 1] >= 0.5)
        if results[name]['f1'] == 1.0:
            raise RuntimeError('Perfect F1: stop publication and investigate leakage/provenance')
        if name == 'with_telemetry':
            full_model = model
    report = {'metrics': results['with_telemetry'], 'ablation': results,
              'recall_delta': results['with_telemetry']['recall'] - results['without_telemetry']['recall'],
              'split': {'method': 'chronological 80/20; equal timestamps stay together', 'cutoff_TransactionDT': cutoff,
                        'train_rows': len(train), 'test_rows': len(test), 'train_fraud': int(y_train.sum()),
                        'test_fraud': int(y_test.sum()), 'threshold': 0.5},
              'parameters': parameters, 'provenance': metadata,
              'warning': 'Do not present these metrics as real-world performance. Telemetry is generated conditional on labels in both splits.'}
    artifact = {'model': full_model, 'feature_cols': FEATURES, 'device_counts': {}, **report}
    output = Path(model_output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    backup(output)
    joblib.dump(artifact, output)
    output.with_suffix('.metrics.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return artifact


if __name__ == '__main__':
    train_module_a()
