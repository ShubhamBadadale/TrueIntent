"""Train and audit lightweight Module B URL classifiers."""
import hashlib
import json
import os
from pathlib import Path
import time
import sys
import platform

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.features_module_b import URLFeatures, URLText, near_duplicate_key, registered_domain, hostname
from ml.generate_module_b_data import validate_urls


def make_pipeline(kind):
    tfidf = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), max_features=10000)
    clf = LogisticRegression(max_iter=1000, random_state=42)
    if kind == "tfidf":
        return Pipeline([("text", URLText()), ("features", tfidf), ("clf", clf)])
    if kind == "engineered":
        return Pipeline([("features", URLFeatures()), ("scale", StandardScaler()), ("clf", clf)])
    if kind == "combined":
        features = FeatureUnion([
            ("text", Pipeline([("text", URLText()), ("tfidf", tfidf)])),
            ("engineered", Pipeline([("features", URLFeatures()), ("scale", StandardScaler())])),
        ])
        return Pipeline([("features", features), ("clf", clf)])
    raise ValueError(kind)


def measure(pipeline, x_train, y_train, x_test, y_test, benchmark=False):
    pipeline.fit(x_train, y_train)
    started = time.perf_counter()
    probabilities = pipeline.predict_proba(x_test)[:, list(pipeline.classes_).index(1)]
    elapsed = (time.perf_counter() - started) * 1000
    pred = (probabilities >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred, labels=[0, 1]).ravel()
    timings = []
    if benchmark:
        pipeline.predict_proba([x_test.iloc[0]])  # Warm the loaded model only.
        for url in x_test.iloc[:min(200, len(x_test))]:
            started = time.perf_counter()
            pipeline.predict_proba([url])
            timings.append((time.perf_counter() - started) * 1000)
    metrics = {
        "precision": float(precision_score(y_test, pred, zero_division=0)),
        "recall": float(recall_score(y_test, pred, zero_division=0)),
        "f1": float(f1_score(y_test, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "pr_auc": float(average_precision_score(y_test, probabilities)),
        "latency_ms_per_url": float(elapsed / len(x_test)),
        "batch_latency_ms": float(elapsed),
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "fpr": float(fp / (fp + tn)),
    }
    if timings:
        metrics["single_url_latency_ms_median"] = float(np.median(timings))
        metrics["single_url_latency_ms_p95"] = float(np.percentile(timings, 95))
    return metrics, pipeline


def audit_splits(df, random_train, random_test, group_train, group_test, casefold_duplicates):
    hosts = df.url.map(hostname)
    domains = df.url.map(registered_domain)
    keys = df.url.map(near_duplicate_key)
    def stats(train, test):
        train_hosts, test_hosts = set(hosts.iloc[train]), set(hosts.iloc[test])
        train_domains, test_domains = set(domains.iloc[train]), set(domains.iloc[test])
        train_keys, test_keys = set(keys.iloc[train]), set(keys.iloc[test])
        return {"train_rows": len(train), "test_rows": len(test),
                "shared_hostnames": len(train_hosts & test_hosts),
                "test_rows_with_train_hostname": int(hosts.iloc[test].isin(train_hosts).sum()),
                "shared_registered_domains": len(train_domains & test_domains),
                "test_rows_with_train_registered_domain": int(domains.iloc[test].isin(train_domains).sum()),
                "shared_near_duplicate_templates": len(train_keys & test_keys),
                "test_rows_with_train_near_duplicate_template": int(keys.iloc[test].isin(train_keys).sum())}
    return {"dataset_audit": {
        "rows_after_casefold_exact_dedup": len(df),
        "casefold_duplicate_urls_present_in_training_csv": int(casefold_duplicates),
        "rows_in_within_hostname_near_duplicate_groups": int(keys.duplicated(keep=False).sum()),
        "near_duplicate_definition": "same hostname, decoded/lowercased digit-collapsed path, same sorted query keys; conservative template heuristic"},
        "random_split": stats(random_train, random_test),
        "registered_domain_disjoint_split": stats(group_train, group_test)}


def train_module_b(data_path="data/raw/module_b_urls.csv", model_output_path="ml/models/module_b.pkl"):
    if not os.path.exists(data_path):
        print(f"[Train Module B] DATASET PENDING: '{data_path}' not found.")
        return None
    df = pd.read_csv(data_path)
    if not {"url", "label"}.issubset(df.columns):
        raise ValueError(f"Dataset at {data_path} must contain 'url' and 'label' columns.")
    casefold_duplicates = int(df.url.astype("string").str.strip().str.lower().duplicated().sum())
    df.label = df.label.astype("string").str.strip().str.lower().replace({"bad": "phishing", "scam": "phishing", "1": "phishing", "0": "legitimate"})
    df = validate_urls(df)
    x = df.url.reset_index(drop=True)
    y = df.label.map({"legitimate": 0, "phishing": 1}).to_numpy()

    positions = np.arange(len(df))
    random_train, random_test = train_test_split(positions, test_size=0.2, random_state=42, stratify=y)
    groups = x.map(registered_domain).to_numpy()
    candidates = []
    for tr, te in GroupShuffleSplit(n_splits=100, test_size=0.2, random_state=42).split(positions, y, groups):
        if len(np.unique(y[tr])) == 2 and len(np.unique(y[te])) == 2:
            candidates.append((tr, te))
    if not candidates:
        raise ValueError("Cannot form a two-class registered-domain-disjoint holdout")
    group_train, group_test = min(candidates, key=lambda pair: abs(len(pair[1]) / len(df) - .2) + abs(y[pair[1]].mean() - y.mean()))

    # Pick the model family using grouped validation folds from the outer training set.
    validation_scores = {kind: [] for kind in ("tfidf", "engineered", "combined")}
    outer_domains = groups[group_train]
    for tr_local, va_local in StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=43).split(group_train, y[group_train], outer_domains):
        tr, va = group_train[tr_local], group_train[va_local]
        for kind in validation_scores:
            result, _ = measure(make_pipeline(kind), x.iloc[tr], y[tr], x.iloc[va], y[va])
            validation_scores[kind].append(result["f1"])
    baseline_cv = float(np.mean(validation_scores["tfidf"]))
    best_candidate = max(validation_scores, key=lambda k: float(np.mean(validation_scores[k])))
    # Prefer the lean baseline unless a feature model adds a useful validated gain.
    selected = best_candidate if float(np.mean(validation_scores[best_candidate])) >= baseline_cv + 0.01 else "tfidf"

    reports = {"random_split": {}, "registered_domain_disjoint_split": {}}
    for split_name, tr, te in (("random_split", random_train, random_test), ("registered_domain_disjoint_split", group_train, group_test)):
        for kind in ("tfidf", "engineered", "combined"):
            reports[split_name][kind], _ = measure(make_pipeline(kind), x.iloc[tr], y[tr], x.iloc[te], y[te], benchmark=True)

    # Production artifact trains on all approved labeled data; API remains the same.
    final_model = make_pipeline(selected).fit(x, y)
    audit = audit_splits(df, random_train, random_test, group_train, group_test, casefold_duplicates)
    metadata_path = Path(data_path).with_suffix(".metadata.json")
    if metadata_path.exists():
        audit["dataset_audit"]["source_duplicates_removed_by_ingestion"] = json.loads(metadata_path.read_text(encoding="utf-8")).get("duplicates_removed")
    data_sha256 = hashlib.sha256(Path(data_path).read_bytes()).hexdigest()
    evaluation = {
        "models": reports,
        "model_selection": {"method": "mean F1 on 5-fold StratifiedGroupKFold over registered domains within outer domain-training partition",
                            "validation_f1_mean": {k: float(np.mean(v)) for k, v in validation_scores.items()},
                            "validation_f1_folds": validation_scores,
                            "minimum_f1_gain_to_replace_baseline": 0.01,
                            "policy_note": "Conservative engineering policy, not a statistical significance test or preregistered experiment.",
                            "selected": selected},
        "splits": {"random": {"seed": 42, "test_size": .2},
                   "registered_domain_disjoint": {"method": "GroupShuffleSplit; selected near 20% with prevalence near full data", "seed": 42, "test_size_target": .2}},
        **audit,
        "data_sha256": data_sha256,
        "threshold": 0.5,
        "pr_auc_definition": "average precision (not trapezoidal PR integration)",
        "latency_method": "Loaded classifier including preprocessing, no URL feature cache or network; batch ms/rows plus first 200 heldout URLs scored individually; excludes API and rules.",
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "final_artifact_fit": "All validated rows, after model-family selection; reported holdout metrics refer to separate evaluation fits, not this full-data refit.",
        "scope": "Classifier only, not the existing 50/50 rule blend. Offline dataset labels are a May 2020 snapshot and do not represent current live URLs.",
    }
    artifact = {"pipeline": final_model, "model_type": selected,
                "metrics": reports["registered_domain_disjoint_split"][selected],
                "evaluation": evaluation, "preprocessing_version": 2}
    os.makedirs(os.path.dirname(model_output_path) or ".", exist_ok=True)
    joblib.dump(artifact, model_output_path)
    Path(model_output_path).with_suffix(".metrics.json").write_text(json.dumps({k: v for k, v in artifact.items() if k != "pipeline"}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selected_model": selected, "evaluation": evaluation}, indent=2))
    return artifact


if __name__ == "__main__":
    train_module_b()
