import os
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix

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
        
    X = df["url"].astype(str)
    y = df["label"].apply(lambda l: 1 if str(l).lower() in ["phishing", "bad", "1", "scam"] else 0).values

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

    artifact = {
        "pipeline": pipeline,
        "metrics": {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "fpr": float(fpr)
        }
    }

    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    joblib.dump(artifact, model_output_path)
    print(f"[Train Module B] Model artifact successfully saved to {model_output_path}")
    return artifact

if __name__ == "__main__":
    train_module_b()
