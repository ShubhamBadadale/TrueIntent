"""IEEE-CIS real amounts/labels, historical proxies, simulated call/device flags."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('module_a_priors.json')
FEATURES = ['amount', 'hour_of_day', 'is_odd_hour', 'is_new_device', 'is_active_call', 'transaction_velocity']
SYNTHETIC = ['is_new_device', 'is_active_call']
SOURCE_COLUMNS = ['TransactionID', 'TransactionDT', 'TransactionAmt', 'isFraud', 'card1', 'card2', 'addr1']


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


def build_features(source, config):
    if not set(SOURCE_COLUMNS).issubset(source.columns):
        raise ValueError('Missing IEEE-CIS training columns')
    source = source.sort_values(['TransactionDT', 'TransactionID']).reset_index(drop=True)
    if source[SOURCE_COLUMNS[:4]].isna().any().any() or source.TransactionID.duplicated().any():
        raise ValueError('Missing observations or duplicate IDs')
    if not source.isFraud.isin([0, 1]).all() or (source.TransactionAmt < 0).any():
        raise ValueError('Invalid labels or amounts')
    if not np.isfinite(source[['TransactionDT', 'TransactionAmt']].to_numpy()).all():
        raise ValueError('Non-finite time or amount')
    flip = config['telemetry_flip_probability']
    if not 0 <= flip <= 1:
        raise ValueError('Invalid flip probability')
    out = pd.DataFrame({'TransactionID': source.TransactionID, 'TransactionDT': source.TransactionDT,
                        'amount': source.TransactionAmt,
                        'hour_of_day': ((source.TransactionDT // 3600) % 24).astype(int),
                        'label': source.isFraud.map({0: 'legitimate', 1: 'fraud'})})
    out['is_odd_hour'] = ((out.hour_of_day < 6) | (out.hour_of_day >= 23)).astype(int)
    velocity = np.zeros(len(source), dtype=np.int64)
    times = source.TransactionDT.to_numpy()
    complete = source[['card1', 'card2', 'addr1']].notna().all(axis=1)
    for positions in source[complete].groupby(['card1', 'card2', 'addr1'], sort=False).groups.values():
        idx = np.asarray(positions)
        t = times[idx]
        # [t-3600, t): exclude current, simultaneous and future transactions.
        velocity[idx] = np.searchsorted(t, t, side='left') - np.searchsorted(t, t - 3600, side='left')
    out['transaction_velocity'] = velocity
    rng = np.random.default_rng(config['seed'])
    audit = {}
    for name in SYNTHETIC:
        priors = config[name]
        if not all(0 <= priors[label] <= 1 for label in ('fraud', 'legitimate')):
            raise ValueError('Invalid prior')
        probabilities = np.where(source.isFraud == 1, priors['fraud'], priors['legitimate'])
        original = rng.random(len(out)) < probabilities
        flipped = rng.random(len(out)) < flip
        out[name] = np.logical_xor(original, flipped).astype(int)
        audit[name] = {'flip_fraction': float(flipped.mean()),
                       'positive_fraction_by_label': out.groupby('label')[name].mean().to_dict()}
    return out, {'telemetry': audit, 'incomplete_history_keys': int((~complete).sum())}


def generate_module_a_data(source_path=ROOT / 'data/raw/ieee_cis/train_transaction.csv',
                           output_path=ROOT / 'data/raw/module_a_transactions.csv', config_path=CONFIG):
    source_path, output_path = Path(source_path), Path(output_path)
    config = json.loads(Path(config_path).read_text(encoding='utf-8-sig'))
    source = pd.read_csv(source_path, usecols=SOURCE_COLUMNS)
    out, audit = build_features(source, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    backup(output_path)
    out.to_csv(output_path, index=False, lineterminator='\n')
    metadata = {'source': 'IEEE-CIS user-supplied train_transaction.csv',
                'source_sha256': sha256(source_path), 'data_sha256': sha256(output_path),
                'rows': len(out), 'class_counts': out.label.value_counts().to_dict(),
                'features': FEATURES, 'synthetic_features': SYNTHETIC, 'config': config, **audit,
                'warning': 'Do not present these metrics as real-world performance.'}
    output_path.with_suffix('.metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(metadata, indent=2))
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'data/raw/ieee_cis/train_transaction.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/raw/module_a_transactions.csv')
    parser.add_argument('--config', type=Path, default=CONFIG)
    args = parser.parse_args()
    generate_module_a_data(args.source, args.output, args.config)
