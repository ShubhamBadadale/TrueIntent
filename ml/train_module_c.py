"""Ten-intent real-text experiment; weak labelling and thin real-language support.

The previous three-signature trainer (`train_legacy_module_c`) is gone: the
10-class intent pipeline in `ml/evaluate_module_c.py` supersedes it and shares the
same feature contract, so keeping both duplicated assembly logic. `new_pipeline`
remains as the exact legacy word-TF-IDF configuration used for measured
baseline-vs-candidate comparisons and by tests.
"""
import sys
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
SIGNATURE_PATH = ROOT / 'data/raw/signature_examples.csv'


def new_pipeline():
    return Pipeline([('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=10000)),
                     ('clf', LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced'))])


def train_module_c(signature_path=SIGNATURE_PATH, model_output_path=ROOT / 'ml/models/module_c.pkl'):
    if not Path(signature_path).exists():
        print('DATASET PENDING: run ml/generate_module_c_data.py after source approval')
        return None
    from ml.evaluate_module_c import train_intents
    return train_intents(signature_path, model_output_path)


if __name__ == '__main__':
    train_module_c()