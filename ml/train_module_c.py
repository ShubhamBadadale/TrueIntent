"""
Module C training: TF-IDF (word n-grams) + Logistic Regression for
behavioral-signature classification (fear_authority / greed_opportunity / none).

Data sources (see data/README.md):
  - data/raw/signature_examples.csv  (curated signature layer, primary)
  - data/raw/sms_spam_collection.csv (public SMS Spam Collection, supplements
    the "none" class with real ham messages)

If NEITHER file exists, training is skipped with a DATASET PENDING notice and
the system keeps running on the rule/keyword placeholder baseline in
`ml/predict_module_c.py`. This mirrors `ml/train_module_b.py` behavior.
"""

import os

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

SIGNATURE_LABELS = ("fear_authority", "greed_opportunity", "none")

SMS_PATH = "data/raw/sms_spam_collection.csv"
SIGNATURE_PATH = "data/raw/signature_examples.csv"


def _find_column(df: pd.DataFrame, candidates: list) -> str | None:
    cols_lower = {str(c).lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    return None


def _normalize_label(value) -> str | None:
    v = str(value).strip().lower()
    if v in ("fear_authority", "fear-authority", "fear", "authority"):
        return "fear_authority"
    if v in ("greed_opportunity", "greed-opportunity", "greed", "opportunity"):
        return "greed_opportunity"
    if v in ("none", "ham", "legit", "legitimate", "0", "clean"):
        return "none"
    if v in ("spam", "scam", "phishing", "1", "bad", "fraud"):
        # Binary spam without signature info -> cannot map to a
        # behavioral signature; caller decides (weak-label or skip).
        return "__spam_unmapped__"
    return None


def _load_signature_examples(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    text_col = _find_column(df, ["text", "message", "sms", "content", "v2"])
    label_col = _find_column(df, ["signature", "label", "class", "v1", "category"])
    if text_col is None or label_col is None:
        raise ValueError(
            f"Dataset at {path} must contain a text column "
            f"(one of text/message/sms/content) and a label column "
            f"(one of signature/label/class). Found: {list(df.columns)}"
        )
    out = pd.DataFrame({"text": df[text_col].astype(str), "raw_label": df[label_col]})
    out["signature"] = out["raw_label"].apply(_normalize_label)
    out = out[out["signature"].isin(SIGNATURE_LABELS)].reset_index(drop=True)
    return out[["text", "signature"]]


def _load_sms_ham_as_none(path: str, max_samples: int | None = 500) -> pd.DataFrame:
    """Load ham/legitimate rows from the SMS Spam Collection as 'none' examples."""
    df = pd.read_csv(path)
    text_col = _find_column(df, ["message", "text", "sms", "content", "v2"])
    label_col = _find_column(df, ["label", "class", "category", "v1"])
    if text_col is None or label_col is None:
        raise ValueError(
            f"Dataset at {path} must contain a text and a label column. "
            f"Found: {list(df.columns)}"
        )
    labels = df[label_col].apply(_normalize_label)
    ham = df[labels == "none"].copy()
    if max_samples is not None and len(ham) > max_samples:
        ham = ham.sample(n=max_samples, random_state=42)
    return pd.DataFrame({"text": ham[text_col].astype(str), "signature": "none"})


def _weak_label_sms_spam(path: str) -> pd.DataFrame:
    """Fallback: weak-label spam rows with the placeholder keyword lists."""
    # Local import avoids a hard dependency at module import time.
    from ml.predict_module_c import (
        FEAR_AUTHORITY_KEYWORDS,
        GREED_OPPORTUNITY_KEYWORDS,
    )

    df = pd.read_csv(path)
    text_col = _find_column(df, ["message", "text", "sms", "content", "v2"])
    label_col = _find_column(df, ["label", "class", "category", "v1"])
    if text_col is None or label_col is None:
        raise ValueError(
            f"Dataset at {path} must contain a text and a label column. "
            f"Found: {list(df.columns)}"
        )
    rows = []
    for _, row in df.iterrows():
        text = str(row[text_col])
        norm = _normalize_label(row[label_col])
        if norm == "none":
            rows.append((text, "none"))
        elif norm == "__spam_unmapped__":
            low = text.lower()
            fear = sum(1 for kw in FEAR_AUTHORITY_KEYWORDS if kw.lower() in low)
            greed = sum(1 for kw in GREED_OPPORTUNITY_KEYWORDS if kw.lower() in low)
            if fear == 0 and greed == 0:
                continue  # skip ambiguous spam without signature evidence
            rows.append((text, "fear_authority" if fear >= greed else "greed_opportunity"))
    return pd.DataFrame(rows, columns=["text", "signature"])


def train_module_c(
    sms_path: str = SMS_PATH,
    signature_path: str = SIGNATURE_PATH,
    model_output_path: str = "ml/models/module_c.pkl",
):
    """
    Train the Module C signature classifier.

    Returns the saved artifact dict, or None when no dataset is available.
    """
    has_sig = os.path.exists(signature_path)
    has_sms = os.path.exists(sms_path)
    if not has_sig and not has_sms:
        print("=" * 75)
        print(f"[Train Module C] DATASET PENDING: '{signature_path}' not found")
        print(f"[Train Module C] DATASET PENDING: '{sms_path}' not found.")
        print("System is running on the RULE/KEYWORD PLACEHOLDER baseline.")
        print("Once the dataset files are placed in data/raw/, re-run this script.")
        print("=" * 75)
        return None

    frames: list = []
    if has_sig:
        print(f"[Train Module C] Loading curated signatures from {signature_path}...")
        frames.append(_load_signature_examples(signature_path))
    if has_sms:
        if has_sig:
            print(f"[Train Module C] Supplementing 'none' class from {sms_path}...")
            frames.append(_load_sms_ham_as_none(sms_path))
        else:
            print(f"[Train Module C] No curated file; weak-labeling {sms_path}...")
            frames.append(_weak_label_sms_spam(sms_path))

    import pandas as _pd

    df = _pd.concat(frames, ignore_index=True)
    df["text"] = df["text"].astype(str)
    df = df[df["text"].str.strip().str.len() > 0].reset_index(drop=True)
    df = df[df["signature"].isin(SIGNATURE_LABELS)].reset_index(drop=True)

    if len(df) < 6 or df["signature"].nunique() < 2:
        print("[Train Module C] Not enough labeled samples to train "
              f"({len(df)} rows, classes={sorted(df['signature'].unique())}). "
              "Staying on placeholder baseline.")
        return None

    X = df["text"]
    y = df["signature"].values

    # Small curated sets (40-60 rows) may not support stratified splits.
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=42, stratify=y
        )
    except ValueError as e:
        print(f"[Train Module C] Stratified split failed ({e}); "
              "training on full data and reporting train metrics.")
        X_train, y_train = X, y
        X_test, y_test = X, y

    print(f"[Train Module C] Training TF-IDF + Logistic Regression on {len(X_train)} samples...")
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=10000)),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    precision = precision_score(y_test, y_pred, average="macro", zero_division=0)
    recall = recall_score(y_test, y_pred, average="macro", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)

    print("\n" + "=" * 50)
    print("MODULE C — TF-IDF + LOGISTIC REGRESSION EVALUATION (macro avg)")
    print("=" * 50)
    print(f"Samples (train/test):   {len(X_train)} / {len(X_test)}")
    print(f"Classes:                {sorted(set(y))}")
    print(f"Precision (macro):      {precision:.4f}")
    print(f"Recall (macro):         {recall:.4f}")
    print(f"F1 Score (macro):       {f1:.4f}")
    print("=" * 50 + "\n")

    artifact = {
        "pipeline": pipeline,
        "labels": sorted(set(y)),
        "mode": "multiclass-signature",
        "metrics": {
            "precision_macro": float(precision),
            "recall_macro": float(recall),
            "f1_macro": float(f1),
        },
    }

    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    joblib.dump(artifact, model_output_path)
    print(f"[Train Module C] Model artifact successfully saved to {model_output_path}")
    return artifact


if __name__ == "__main__":
    train_module_c()
