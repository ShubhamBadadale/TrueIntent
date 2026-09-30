"""Portable test fixtures. Invented rows stay in pytest's temporary directory."""
import importlib
import json
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'backend'))


@pytest.fixture(scope='session')
def benchmark_file(tmp_path_factory):
    from ml.features_module_a import FEATURE_CONTRACT, SOURCE_AMOUNT_UNIT
    from ml.generate_module_a_data import sha256
    from ml.train_module_a import train_module_a
    directory = tmp_path_factory.mktemp('module_a_unit_fixture')
    path = directory / 'unit_fixture.csv'
    # Unit-test mechanics only; these labels/metrics are not evaluation evidence.
    pd.DataFrame({
        'TransactionID': range(40), 'TransactionDT': range(40),
        'amount': [float(i % 7) for i in range(40)],
        'amount_unit': SOURCE_AMOUNT_UNIT,
        'label': ['legitimate', 'fraud'] * 20,
    }).to_csv(path, index=False)
    path.with_suffix('.metadata.json').write_text(json.dumps({
        'data_sha256': sha256(path), 'feature_contract': FEATURE_CONTRACT,
        'source': 'Invented unit-test fixture, never production data',
    }), encoding='utf-8')
    model_path = directory / 'unit_fixture.pkl'
    train_module_a(str(path), str(model_path))
    return model_path


@pytest.fixture
def benchmark_model(benchmark_file, monkeypatch):
    predictor = importlib.import_module('ml.predict_module_a')
    monkeypatch.setattr(predictor, '_MODEL_ARTIFACT', None)
    monkeypatch.setattr(predictor, '_get_model_path', lambda: str(benchmark_file))
    return predictor.load_model()
