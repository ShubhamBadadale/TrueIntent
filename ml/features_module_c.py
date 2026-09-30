"""Shared, Unicode-preserving text features and explicit intent definitions."""
import re
import unicodedata
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

INTENTS = ('benign', 'urgency_pressure', 'authority_fear', 'digital_arrest',
           'investment_scam', 'kyc_upi_scam', 'impersonation',
           'courier_customs_scam', 'credential_theft', 'other_fraud')
# Compatibility psychology labels are separate from the more specific intent.
LEGACY_MAP = {'benign': 'none', 'urgency_pressure': 'fear_authority',
              'authority_fear': 'fear_authority', 'digital_arrest': 'fear_authority',
              'investment_scam': 'greed_opportunity', 'kyc_upi_scam': 'none',
              'impersonation': 'fear_authority', 'courier_customs_scam': 'fear_authority',
              'credential_theft': 'none', 'other_fraud': 'greed_opportunity'}


def normalize_text(text):
    text = unicodedata.normalize('NFKC', str(text)).casefold()
    text = re.sub('[\u200b\u200c\u200d\ufeff]', '', text)
    text = re.sub(r'https?://\S+|www\.\S+', ' urltoken ', text)
    text = re.sub(r'\b[\w.+-]+@[\w.-]+\.[a-z]+\b', ' emailtoken ', text)
    return re.sub(r'\s+', ' ', text).strip()


def word_tokens(text):
    # Whitespace/punctuation tokenization keeps Devanagari vowel marks with letters.
    return re.findall(r'[^\s.,!?;:()\[\]{}<>/\\"\u201c\u201d]+', text)


def make_intent_pipeline(kind='word_char'):
    if kind == 'baseline':
        # Exact old word-vectorizer configuration for a fair same-data comparison.
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=10000)
    elif kind == 'word_char':
        vectorizer = FeatureUnion([
            ('word', TfidfVectorizer(preprocessor=normalize_text, tokenizer=word_tokens,
                                    token_pattern=None, lowercase=False,
                                    ngram_range=(1, 2), max_features=10000, sublinear_tf=True)),
            ('char', TfidfVectorizer(preprocessor=normalize_text, lowercase=False,
                                    analyzer='char_wb', ngram_range=(3, 5),
                                    max_features=15000, sublinear_tf=True)),
        ], transformer_weights={'word': 1.0, 'char': 1.0})
    else:
        raise ValueError('Unknown text feature configuration')
    return Pipeline([('tfidf', vectorizer), ('clf', LogisticRegression(
        max_iter=1000, random_state=42, class_weight='balanced'))])
