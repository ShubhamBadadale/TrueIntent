"""Three-class real-text experiment; tiny fear support and weak greed labels."""
import json
import os
from pathlib import Path
import sys
import joblib
import sklearn
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.generate_module_c_data import LABELS, digest, validate_examples

SIGNATURE_LABELS = LABELS
SMS_PATH = 'data/raw/sms_spam_collection.csv'
SIGNATURE_PATH = 'data/raw/signature_examples.csv'


def new_pipeline():
    return Pipeline([('tfidf', TfidfVectorizer(ngram_range=(1,2), max_features=10000)),
                     ('clf', LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced'))])


def train_module_c(sms_path=SMS_PATH, signature_path=SIGNATURE_PATH, model_output_path='ml/models/module_c.pkl'):
    # Retain callable arguments, but all source assembly now belongs to the generator.
    # Never silently weak-label arbitrary spam using the predictor's keyword list.
    path = Path(signature_path)
    if not path.exists():
        print('DATASET PENDING: run ml/generate_module_c_data.py; retaining keyword fallback')
        return None
    metadata = json.loads(path.with_suffix('.metadata.json').read_text(encoding='utf-8'))
    if digest(path.read_bytes()) != metadata['data_sha256']:
        raise ValueError('Dataset/provenance hash mismatch; regenerate first')
    data = validate_examples(pd.read_csv(path))
    counts = data.signature.value_counts()
    if set(counts.index) != set(LABELS) or counts.min() < 5:
        raise ValueError('Five independent examples per class required for five-fold evaluation; never report train metrics instead')
    predictions = np.empty(len(data), dtype=object)
    fold_ids = np.full(len(data), -1)
    fold_reports = []
    # Generator collapses normalized duplicate groups to one row before this split.
    for fold, (train, test) in enumerate(StratifiedKFold(n_splits=5, shuffle=True, random_state=42).split(data.text, data.signature)):
        model = new_pipeline()
        model.fit(data.text.iloc[train], data.signature.iloc[train])
        predictions[test] = model.predict(data.text.iloc[test])
        fold_ids[test] = fold
        fold_reports.append(classification_report(data.signature.iloc[test], predictions[test], labels=list(LABELS), output_dict=True, zero_division=0))
        print(f'Fold {fold+1}/5 complete', flush=True)
    metrics = classification_report(data.signature, predictions, labels=list(LABELS), output_dict=True, zero_division=0)
    report = dict(sklearn_version=sklearn.__version__, per_class=metrics, folds=fold_reports,
                  confusion_matrix=confusion_matrix(data.signature, predictions, labels=list(LABELS)).tolist(),
                  label_order=list(LABELS), counts=counts.to_dict(),
                  evaluation='Five-fold stratified out-of-fold predictions after normalized-text deduplication; final artifact refit on all rows',
                  data_sha256=metadata['data_sha256'],
                  limitation='Fear support only five reported excerpts; greed labels weak. Cross-source style shortcuts and remaining near-duplicates possible. Not deployment accuracy.')
    for label in LABELS:
        if metrics[label]['f1-score'] >= 0.99:
            print(f'CAUTION: {label} near-perfect F1; source/style shortcuts and weak-label selection can inflate it.')
    # Every evaluation prediction above came from a held-out fold. Refit for use.
    model = new_pipeline()
    model.fit(data.text, data.signature)
    artifact = dict(pipeline=model, labels=list(model.classes_), mode='multiclass-signature',
                    metrics={'precision_macro':metrics['macro avg']['precision'],
                             'recall_macro':metrics['macro avg']['recall'], 'f1_macro':metrics['macro avg']['f1-score']},
                    evaluation=report, coverage_warning=report['limitation'])
    output=Path(model_output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        import shutil
        shutil.copy2(output, output.with_name(output.stem+'.before-'+digest(output.read_bytes())[:12]+'.pkl'))
    joblib.dump(artifact, output)
    output.with_suffix('.metrics.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    pd.DataFrame({'source_id':data.source_id,'group_id':data.group_id,'fold':fold_ids,
                  'actual':data.signature,'predicted':predictions}).to_csv(path.with_name('module_c_oof_predictions.csv'),index=False)
    print(json.dumps(metrics,indent=2))
    return artifact


if __name__ == '__main__':
    train_module_c()
