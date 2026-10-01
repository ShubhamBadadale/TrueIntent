"""Shared amount-only IEEE-CIS benchmark contract; not an INR transfer model."""
import numpy as np
import pandas as pd

FEATURES = ['amount']
FEATURE_ORDER = ['amount']
ARTIFACT_VERSION = 3
MODEL_VERSION = 'amount-only-xgb-v3'
PREPROCESSING_VERSION = 3
DATASET_ID = 'ieee_cis_train_transaction_source_units'
SOURCE_AMOUNT_UNIT = 'ieee_cis_source'
EXPECTED_UNITS = {'amount': SOURCE_AMOUNT_UNIT, 'amount_unit': SOURCE_AMOUNT_UNIT}
FEATURE_CONTRACT = {
    'artifact_version': ARTIFACT_VERSION,
    'model_version': MODEL_VERSION,
    'features': FEATURES,
    'feature_order': FEATURE_ORDER,
    'dataset_id': DATASET_ID,
    'preprocessing_version': PREPROCESSING_VERSION,
    'amount_unit': SOURCE_AMOUNT_UNIT,
    'expected_units': EXPECTED_UNITS,
    'scope': 'ieee_cis_amount_only_benchmark',
}
# Backwards-compatible alias: historic code referenced contract['version'].
FEATURE_CONTRACT['version'] = ARTIFACT_VERSION
BENCHMARK_NOTICE = (
    'IEEE-CIS amount-only benchmark in original source units. This is not an INR '
    'transfer assessment or a calibrated fraud probability. Time, device, call '
    'state and transfer count are not used.'
)


class ModuleAUnavailableError(RuntimeError):
    """Missing or unreadable artifact; never substitute a safe score."""


class ModuleAIncompatibleError(ModuleAUnavailableError):
    """Obsolete, malformed or feature-incompatible artifact."""


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
    raw = frame['amount']
    if raw.map(lambda value: isinstance(value, (bool, np.bool_))).any():
        raise ValueError('amount must be numeric, not boolean.')
    # Boolean-as-number and wrong-type guard: only real numeric scalars pass.
    # Numeric strings are rejected even when parseable, so '5.25' cannot
    # masquerade as a benchmark amount.
    for value in raw:
        if isinstance(value, str):
            raise ValueError('amount must be numeric, not a string.')
        if value is None:
            raise ValueError('amount must be numeric, not missing.')
        if not isinstance(value, (int, float, np.integer, np.floating)):
            raise ValueError('amount must be numeric, not boolean or object.')
    values = pd.to_numeric(raw, errors='raise').astype('float64')
    if (not np.isfinite(values).all() or (values < 0).any()
            or (values > np.finfo(np.float32).max).any()):
        raise ValueError('amount must be finite, nonnegative and representable by the model.')
    return pd.DataFrame({'amount': values}, index=frame.index)[FEATURES]


def transaction_features(transaction: dict) -> pd.DataFrame:
    return preprocess_features(pd.DataFrame([transaction]))


def validate_artifact(artifact: dict) -> None:
    """Reject obsolete, malformed or feature-incompatible artifacts.

    Raises ModuleAIncompatibleError (a ModuleAUnavailableError subclass, so
    legacy ``except ModuleAUnavailableError`` guards keep working) with a
    message naming the contract field that failed.
    """
    if not isinstance(artifact, dict):
        raise ModuleAIncompatibleError('Module A artifact is malformed: expected a dict.')
    contract = artifact.get('feature_contract')
    if not isinstance(contract, dict):
        raise ModuleAIncompatibleError(
            'Module A artifact is obsolete or malformed: missing feature_contract.'
        )
    for key in ('artifact_version', 'model_version', 'features', 'feature_order',
                'dataset_id', 'preprocessing_version', 'amount_unit',
                'expected_units', 'scope'):
        if contract.get(key) != FEATURE_CONTRACT.get(key):
            raise ModuleAIncompatibleError(
                f'Module A artifact is obsolete or incompatible: contract field {key!r} '
                f'mismatch (expected {FEATURE_CONTRACT.get(key)!r}). Retrain the amount-only '
                'benchmark with authorized IEEE-CIS data; legacy six-feature models are disabled.'
            )
    if artifact.get('feature_cols') != FEATURES:
        raise ModuleAIncompatibleError(
            'Module A artifact is incompatible: feature_cols does not match '
            f'feature_order {FEATURE_ORDER}.'
        )
    model = artifact.get('model')
    if (getattr(model, 'n_features_in_', None) != len(FEATURES)
            or list(getattr(model, 'classes_', [])) != [0, 1]):
        raise ModuleAIncompatibleError('Module A model does not match its feature contract.')
