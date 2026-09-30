"""Ingest observed IEEE-CIS amounts/labels; generate no telemetry or clock features."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.features_module_a import FEATURES, FEATURE_CONTRACT, SOURCE_AMOUNT_UNIT, preprocess_features

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COLUMNS = ['TransactionID', 'TransactionDT', 'TransactionAmt', 'isFraud']


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def backup(path):
    path = Path(path)
    if path.exists():
        target = path.with_name(path.stem + '.before-' + sha256(path)[:12] + '.bak' + path.suffix)
        if not target.exists():
            shutil.copy2(path, target)


def build_features(source):
    if not set(SOURCE_COLUMNS).issubset(source.columns):
        raise ValueError('Missing IEEE-CIS training columns')
    source = source.sort_values(['TransactionDT', 'TransactionID']).reset_index(drop=True)
    if source[SOURCE_COLUMNS].isna().any().any() or source.TransactionID.duplicated().any():
        raise ValueError('Missing observations or duplicate IDs')
    if not source.isFraud.isin([0, 1]).all():
        raise ValueError('Invalid labels')
    if not np.isfinite(source.TransactionDT).all() or (source.TransactionDT < 0).any():
        raise ValueError('Invalid relative source time')
    out = pd.DataFrame({
        'TransactionID': source.TransactionID,
        'TransactionDT': source.TransactionDT,  # Split/audit only; never a predictor.
        'amount': source.TransactionAmt,
        'amount_unit': SOURCE_AMOUNT_UNIT,
        'label': source.isFraud.map({0: 'legitimate', 1: 'fraud'}),
    })
    out[FEATURES] = preprocess_features(out)
    return out


def generate_module_a_data(source_path=ROOT / 'data/raw/ieee_cis/train_transaction.csv',
                           output_path=ROOT / 'data/raw/module_a_transactions.csv'):
    source_path, output_path = Path(source_path), Path(output_path)
    if not source_path.exists():
        raise FileNotFoundError(
            f'Authorized IEEE-CIS data required at {source_path}. No synthetic substitute is generated.'
        )
    out = build_features(pd.read_csv(source_path, usecols=SOURCE_COLUMNS))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    backup(output_path)
    backup(output_path.with_suffix('.metadata.json'))
    out.to_csv(output_path, index=False, lineterminator='\n')
    metadata = {
        'source': 'IEEE-CIS user-supplied train_transaction.csv',
        'source_sha256': sha256(source_path), 'data_sha256': sha256(output_path),
        'rows': len(out), 'class_counts': out.label.value_counts().to_dict(),
        'feature_contract': FEATURE_CONTRACT,
        'warning': 'Source-unit amount-only benchmark; not INR or APP coercion performance.',
    }
    output_path.with_suffix('.metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'data/raw/ieee_cis/train_transaction.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/raw/module_a_transactions.csv')
    args = parser.parse_args()
    generate_module_a_data(args.source, args.output)
