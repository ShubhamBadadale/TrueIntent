import json
import pandas as pd
import pytest
from ml.features_module_a import FEATURES, FEATURE_CONTRACT, preprocess_features
from ml.generate_module_a_data import build_features, generate_module_a_data, sha256
from ml.train_module_a import chronological_split, train_module_a


def sample():
    return pd.DataFrame({
        'TransactionID': range(10), 'TransactionDT': [1,2,3,4,5,6,7,8,8,9],
        'TransactionAmt': [10.] * 10, 'isFraud': [0, 1] * 5,
    })


def test_only_observed_amount_enters_model():
    out = build_features(sample())
    assert list(out.columns) == ['TransactionID', 'TransactionDT', 'amount', 'amount_unit', 'label']
    assert out.amount.tolist() == sample().TransactionAmt.tolist()
    assert list(preprocess_features(out).columns) == FEATURES == ['amount']


def test_features_do_not_depend_on_labels_time_or_telemetry():
    original = sample()
    changed = original.copy()
    changed['isFraud'] = 1 - changed.isFraud
    changed['TransactionDT'] += 123456
    changed['is_active_call'] = True
    changed['device_id'] = 'unknown'
    pd.testing.assert_frame_equal(
        preprocess_features(build_features(original)), preprocess_features(build_features(changed))
    )


def test_chronological_boundary_never_splits_equal_times():
    frame = build_features(sample())
    train, test, cutoff = chronological_split(frame)
    assert train.TransactionDT.max() < test.TransactionDT.min()
    assert cutoff == 8
    assert len(train) + len(test) == len(frame)


def test_ingestion_records_unit_contract_and_source_hash(tmp_path):
    source = tmp_path / 'source.csv'
    sample().to_csv(source, index=False)
    output = tmp_path / 'amounts.csv'
    generate_module_a_data(source, output)
    meta = json.loads(output.with_suffix('.metadata.json').read_text())
    assert meta['feature_contract'] == FEATURE_CONTRACT
    assert meta['source_sha256'] == sha256(source)
    assert meta['data_sha256'] == sha256(output)


def test_no_data_means_no_synthetic_substitute(tmp_path):
    output = tmp_path / 'amounts.csv'
    with pytest.raises(FileNotFoundError, match='No synthetic substitute'):
        generate_module_a_data(tmp_path / 'missing.csv', output)
    assert not output.exists()


def test_legacy_dataset_contract_rejected(tmp_path):
    path = tmp_path / 'old.csv'
    build_features(sample()).to_csv(path, index=False)
    path.with_suffix('.metadata.json').write_text(json.dumps({'data_sha256': sha256(path)}))
    with pytest.raises(ValueError, match='Obsolete dataset'):
        train_module_a(str(path), str(tmp_path / 'model.pkl'))


def test_tampered_dataset_rejected(tmp_path):
    path = tmp_path / 'changed.csv'
    build_features(sample()).to_csv(path, index=False)
    path.with_suffix('.metadata.json').write_text(json.dumps({
        'data_sha256': 'wrong', 'feature_contract': FEATURE_CONTRACT,
    }))
    with pytest.raises(ValueError, match='hash differs'):
        train_module_a(str(path), str(tmp_path / 'model.pkl'))
