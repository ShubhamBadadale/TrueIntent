import json
import numpy as np
import pandas as pd
import pytest
from ml.generate_module_a_data import build_features, CONFIG, FEATURES
from ml.train_module_a import chronological_split


def sample():
    return pd.DataFrame({'TransactionID': range(8), 'TransactionDT': [0, 100, 100, 3600, 3601, 7200, 7300, 7400],
                         'TransactionAmt': [10.] * 8, 'isFraud': [0, 1] * 4,
                         'card1': [1] * 8, 'card2': [2] * 8, 'addr1': [3] * 8})


def test_velocity_excludes_simultaneous_future_and_other_accounts():
    source = sample()
    source.loc[6, 'card1'] = 99
    source.loc[7, 'addr1'] = np.nan
    out, _ = build_features(source, json.loads(CONFIG.read_text()))
    assert out.transaction_velocity.tolist() == [0, 1, 1, 3, 3, 2, 0, 0]
    assert out.amount.tolist() == source.TransactionAmt.tolist()
    assert out.label.tolist() == ['legitimate', 'fraud'] * 4


def test_only_telemetry_depends_on_labels_and_seed():
    config = json.loads(CONFIG.read_text())
    a, _ = build_features(sample(), config)
    b, _ = build_features(sample(), config)
    pd.testing.assert_frame_equal(a, b)
    changed = sample()
    changed['isFraud'] = 1 - changed.isFraud
    c, _ = build_features(changed, config)
    real = ['amount', 'hour_of_day', 'is_odd_hour', 'transaction_velocity']
    pd.testing.assert_frame_equal(a[real], c[real])
    assert set(FEATURES).issubset(a.columns)


def test_noise_flips_features_not_targets():
    config = json.loads(CONFIG.read_text())
    config['telemetry_flip_probability'] = 0
    a, _ = build_features(sample(), config)
    config['telemetry_flip_probability'] = 1
    b, _ = build_features(sample(), config)
    for name in ['is_active_call', 'is_new_device']:
        assert (a[name] == 1 - b[name]).all()
    assert a.label.equals(b.label)


def test_chronological_boundary_never_splits_equal_times():
    frame = pd.DataFrame({'TransactionID': range(10), 'TransactionDT': [1,2,3,4,5,6,7,8,8,9],
                          'label': ['fraud', 'legitimate'] * 5})
    train, test, cutoff = chronological_split(frame)
    assert train.TransactionDT.max() < test.TransactionDT.min()
    assert cutoff == 8
    assert len(train) + len(test) == len(frame)
