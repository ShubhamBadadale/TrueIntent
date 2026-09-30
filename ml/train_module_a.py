"""Chronological evaluation of the source-unit amount-only IEEE-CIS benchmark."""
import json
from pathlib import Path
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
import xgboost as xgb
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.generate_module_a_data import backup, generate_module_a_data, sha256
from ml.features_module_a import FEATURES, FEATURE_CONTRACT, BENCHMARK_NOTICE, preprocess_features


def chronological_split(df):
    if (len(df) < 2 or df.TransactionID.isna().any() or df.TransactionID.duplicated().any()
            or not np.isfinite(df.TransactionDT).all()):
        raise ValueError('Invalid chronological split identifiers or times')
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
    if metadata.get('feature_contract') != FEATURE_CONTRACT:
        raise ValueError('Obsolete dataset contract; regenerate from authorized IEEE-CIS source data')
    df = pd.read_csv(data_path)
    if not df.label.isin(['fraud', 'legitimate']).all():
        raise ValueError('Unknown labels')
    train, test, cutoff = chronological_split(df)
    X_train = preprocess_features(train)
    X_test = preprocess_features(test)
    y_train = (train.label == 'fraud').astype(int)
    y_test = (test.label == 'fraud').astype(int)
    parameters = dict(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42,
                      eval_metric='logloss', tree_method='hist', n_jobs=4,
                      scale_pos_weight=float((y_train == 0).sum() / y_train.sum()))
    model = xgb.XGBClassifier(**parameters)
    model.fit(X_train, y_train)
    metrics = evaluate(y_test, model.predict_proba(X_test)[:, 1] >= 0.5)
    if metrics['f1'] == 1.0:
        raise RuntimeError('Perfect F1: stop publication and investigate leakage/provenance')
    report = {'metrics': metrics, 'feature_contract': FEATURE_CONTRACT,
              'split': {'method': 'chronological 80/20; equal timestamps stay together', 'cutoff_TransactionDT': cutoff,
                        'train_rows': len(train), 'test_rows': len(test), 'train_fraud': int(y_train.sum()),
                        'test_fraud': int(y_test.sum()), 'threshold': 0.5},
              'parameters': parameters, 'provenance': metadata,
              'warning': BENCHMARK_NOTICE}
    artifact = {'model': model, 'feature_cols': FEATURES, **report}
    output = Path(model_output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    backup(output)
    backup(output.with_suffix('.metrics.json'))
    joblib.dump(artifact, output)
    output.with_suffix('.metrics.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return artifact


if __name__ == '__main__':
    train_module_a()
