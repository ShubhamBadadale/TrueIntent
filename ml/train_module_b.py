import os
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
try:
    from ml.generate_module_b_data import validate_urls
except ModuleNotFoundError:
    from generate_module_b_data import validate_urls

def train_module_b(data_path: str = "data/raw/module_b_urls.csv", model_output_path: str = "ml/models/module_b.pkl"):
    """
    Trains lightweight TF-IDF char n-gram + Logistic Regression classifier for Module B URL safety.
    """
    if not os.path.exists(data_path):
        print("="*75)
        print(f"[Train Module B] DATASET PENDING: '{data_path}' not found.")
        print("System is running in RULES-ONLY mode.")
        print("Once the dataset is placed at data/raw/module_b_urls.csv, re-run this script.")
        print("="*75)
        return None

    print(f"[Train Module B] Loading URL dataset from {data_path}...")
    df = pd.read_csv(data_path)
    
    if "url" not in df.columns or "label" not in df.columns:
        raise ValueError(f"Dataset at {data_path} must contain 'url' and 'label' columns.")
        
    # Preserve explicitly supported historical labels, but reject unknowns.
    df["label"] = df["label"].astype("string").str.strip().str.lower().replace({
        "bad": "phishing", "scam": "phishing", "1": "phishing",
        "0": "legitimate",
    })
    df = validate_urls(df)
    X = df["url"]
    y = df["label"].map({"phishing": 1, "legitimate": 0}).values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    print(f"[Train Module B] Training TF-IDF + Logistic Regression on {len(X_train)} samples...")
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(analyzer="char", ngram_range=(3, 5), max_features=10000)),
        ("clf", LogisticRegression(max_iter=1000, random_state=42))
    ])

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    print("\n" + "="*50)
    print("MODULE B — TF-IDF + LOGISTIC REGRESSION EVALUATION METRICS")
    print("="*50)
    print(f"Precision:            {precision:.4f}")
    print(f"Recall:               {recall:.4f}")
    print(f"F1 Score:             {f1:.4f}")
    print(f"False Positive Rate:  {fpr:.4f}")
    print("="*50 + "\n")
    if f1 >= 0.99:
        print("WARNING: Suspiciously near-perfect F1. Audit leakage and data provenance; not real-world performance.")
    print("Historical random URL holdout only; related hosts/campaigns may span splits.")

    train_hosts = {urlsplit(url).hostname for url in X_train}
    test_hosts = {urlsplit(url).hostname for url in X_test}
    data_sha256 = hashlib.sha256(Path(data_path).read_bytes()).hexdigest()

    artifact = {
        "pipeline": pipeline,
        "metrics": {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "fpr": float(fpr),
            "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]]
        },
        "evaluation": {
            "split": "stratified random URL holdout", "seed": 42, "test_size": 0.20,
            "train_rows": len(X_train), "test_rows": len(X_test),
            "shared_hostnames": len(train_hosts & test_hosts),
            "test_rows_with_train_hostname": sum(urlsplit(u).hostname in train_hosts for u in X_test),
            "data_sha256": data_sha256,
            "scope": "Classifier only; not the 50/50 rules blend or current real-world performance.",
        },
    }

    os.makedirs(os.path.dirname(model_output_path) or ".", exist_ok=True)
    joblib.dump(artifact, model_output_path)
    Path(model_output_path).with_suffix(".metrics.json").write_text(
        json.dumps({key: value for key, value in artifact.items() if key != "pipeline"}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[Train Module B] Model artifact successfully saved to {model_output_path}")
    return artifact

if __name__ == "__main__":
    train_module_b()
