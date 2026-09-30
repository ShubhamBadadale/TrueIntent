"""Strict serving boundary for the amount-only IEEE-CIS research benchmark."""
import os
import joblib
import numpy as np

from ml.features_module_a import (
    ModuleAUnavailableError, transaction_features, validate_artifact,
)

_MODEL_ARTIFACT = None


def _get_model_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'module_a.pkl')


def load_model(model_path: str = None):
    global _MODEL_ARTIFACT
    path = os.path.abspath(model_path or _get_model_path())
    try:
        stat = os.stat(path)
    except FileNotFoundError as exc:
        raise ModuleAUnavailableError(
            'Module A benchmark artifact is missing. Retraining requires authorized '
            'IEEE-CIS data; no transaction verdict is available.'
        ) from exc
    stamp = (path, stat.st_mtime_ns, stat.st_size)
    if _MODEL_ARTIFACT is None or _MODEL_ARTIFACT.get('_stamp') != stamp:
        try:
            artifact = joblib.load(path)
            validate_artifact(artifact)
        except ModuleAUnavailableError:
            raise
        except Exception as exc:
            raise ModuleAUnavailableError('Module A artifact could not be loaded.') from exc
        artifact['_stamp'] = stamp
        _MODEL_ARTIFACT = artifact
    return _MODEL_ARTIFACT


def predict_module_a(transaction_dict: dict, model_path: str = None) -> float:
    # Validate semantics before loading: missing artifacts must not hide INR misuse.
    features = transaction_features(transaction_dict)
    artifact = load_model(model_path)
    score = float(artifact['model'].predict_proba(features)[0, 1])
    if not np.isfinite(score) or not 0 <= score <= 1:
        raise ModuleAUnavailableError('Module A returned an invalid benchmark score.')
    return score
