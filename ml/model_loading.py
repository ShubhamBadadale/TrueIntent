"""Cache only trusted local artifacts; detect replacement and deletion."""
import os
import joblib


def load_artifact(path, cached=None):
    try:
        path = os.path.abspath(path)
        stat = os.stat(path)
        stamp = (path, stat.st_mtime_ns, stat.st_size)
        if cached is not None and cached.get('_stamp') == stamp:
            return cached
        artifact = joblib.load(path)
        if not isinstance(artifact, dict):
            return None
        pipeline = artifact.get('pipeline')
        if not callable(getattr(pipeline, 'predict_proba', None)) or not hasattr(pipeline, 'classes_'):
            return None
        return dict(artifact, _path=path, _stamp=stamp)
    except Exception:
        # Consumers explicitly report unavailable models or rules-only fallback.
        return None
