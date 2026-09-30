"""Shared amount-only IEEE-CIS benchmark contract; not an INR transfer model."""
import numpy as np
import pandas as pd

FEATURES = ['amount']
SOURCE_AMOUNT_UNIT = 'ieee_cis_source'
FEATURE_CONTRACT = {
    'version': 2,
    'features': FEATURES,
    'amount_unit': SOURCE_AMOUNT_UNIT,
    'scope': 'ieee_cis_amount_only_benchmark',
}
BENCHMARK_NOTICE = (
    'IEEE-CIS amount-only benchmark in original source units. This is not an INR '
    'transfer assessment or a calibrated fraud probability. Time, device, call '
    'state and transfer count are not used.'
)


class ModuleAUnavailableError(RuntimeError):
    """Missing, obsolete or incompatible artifact; never substitute a safe score."""


def preprocess_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Sole transformation for training, inference and explanations.

    Units must be explicit. No currency conversion, clock-hour extraction,
    device-history lookup or synthetic telemetry is performed.
    """
    if not {'amount', 'amount_unit'}.issubset(frame.columns) or frame.empty:
        raise ValueError('Module A requires amount and an explicit amount_unit.')
    if not frame['amount_unit'].eq(SOURCE_AMOUNT_UNIT).all():
        raise ValueError(
            'Module A cannot assess INR or unspecified currency amounts. '
            'Only original IEEE-CIS source-unit benchmark amounts are supported.'
        )
    if frame['amount'].map(lambda value: isinstance(value, (bool, np.bool_))).any():
        raise ValueError('amount must be numeric, not boolean.')
    values = pd.to_numeric(frame['amount'], errors='raise').astype('float64')
    if (not np.isfinite(values).all() or (values < 0).any()
            or (values > np.finfo(np.float32).max).any()):
        raise ValueError('amount must be finite, nonnegative and representable by the model.')
    return pd.DataFrame({'amount': values}, index=frame.index)[FEATURES]


def transaction_features(transaction: dict) -> pd.DataFrame:
    return preprocess_features(pd.DataFrame([transaction]))


def validate_artifact(artifact: dict) -> None:
    if (not isinstance(artifact, dict)
            or artifact.get('feature_contract') != FEATURE_CONTRACT
            or artifact.get('feature_cols') != FEATURES):
        raise ModuleAUnavailableError(
            'Module A artifact is obsolete or incompatible. Retrain the amount-only '
            'benchmark with authorized IEEE-CIS data; legacy six-feature models are disabled.'
        )
    model = artifact.get('model')
    if (getattr(model, 'n_features_in_', None) != len(FEATURES)
            or list(getattr(model, 'classes_', [])) != [0, 1]):
        raise ModuleAUnavailableError('Module A model does not match its feature contract.')
