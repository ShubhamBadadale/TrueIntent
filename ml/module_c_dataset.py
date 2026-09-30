"""Provenance-aware intent assembly; translations never form independent groups."""
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from ml.features_module_c import INTENTS, normalize_text
from ml.generate_module_c_data import digest, validate_examples

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / 'data/module_c_intent_seeds.json'


def grouping_text(text):
    text = re.sub(r'\d+', ' numbertoken ', normalize_text(text))
    return re.sub(r'[^\w\s\u0900-\u097f]', ' ', text).strip()


def assemble_intents(signature_path, seed_path=SEEDS):
    path = Path(signature_path)
    metadata = json.loads(path.with_suffix('.metadata.json').read_text(encoding='utf-8'))
    if digest(path.read_bytes()) != metadata['data_sha256']:
        raise ValueError('Dataset/provenance hash mismatch')
    legacy = validate_examples(pd.read_csv(path))
    rows = []
    for row in legacy.itertuples():
        label = {'none': 'benign', 'greed_opportunity': 'other_fraud',
                 'fear_authority': 'authority_fear'}[row.signature]
        rows.append(dict(text=row.text, intent=label,
                         provenance='manually_curated' if row.signature == 'fear_authority' else 'real_public',
                         origin='public', language='en' if row.signature == 'fear_authority' else 'source_english_dominant',
                         source_id=row.source_id, source_url=row.source_url,
                         label_basis=row.label_basis, seed_id=row.source_id))
    seeds = json.loads(Path(seed_path).read_text(encoding='utf-8'))
    for seed in seeds['seeds']:
        if seed['intent'] not in INTENTS:
            raise ValueError('Unknown seed intent')
        for language in ('en', 'hinglish', 'hi'):
            if language not in seed:
                continue
            rows.append(dict(text=seed[language], intent=seed['intent'],
                             provenance='synthetic' if language == 'en' else 'augmented',
                             origin='synthetic', language=language,
                             source_id=f"seed:{seed['id']}:{language}", source_url='data/module_c_intent_seeds.json',
                             label_basis='AI-authored illustration; no independent human annotation; translation retains synthetic origin',
                             seed_id=f"seed:{seed['id']}"))
    data = pd.DataFrame(rows)
    if data.source_id.duplicated().any() or data.text.str.strip().eq('').any():
        raise ValueError('Duplicate source IDs or empty text')
    normalized = data.text.map(grouping_text)
    if data.assign(key=normalized).groupby('key').intent.nunique().gt(1).any():
        raise ValueError('Conflicting labels for normalized text')

    # Connected components join explicit lineage, exact templates and near duplicates.
    parent = list(range(len(data)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def join(a, b):
        a, b = root(a), root(b)
        parent[max(a, b)] = min(a, b)
    for values in (data.seed_id, normalized):
        first = {}
        for i, value in enumerate(values):
            if value in first:
                join(i, first[value])
            else:
                first[value] = i
    # This all-text representation only constructs leakage groups. Model vectorizers
    # are always fitted on training folds, independently of this grouping vectorizer.
    vectors = TfidfVectorizer(analyzer='word', ngram_range=(1, 2),
                             max_features=20000).fit_transform(normalized)
    neighbors = NearestNeighbors(metric='cosine', algorithm='brute', radius=.1).fit(vectors)
    edges = 0
    for start in range(0, len(data), 256):
        found = neighbors.radius_neighbors(vectors[start:start + 256], return_distance=False)
        for offset, matches in enumerate(found):
            i = start + offset
            for j in matches:
                if j > i:
                    join(i, int(j))
                    edges += 1
    data['group_id'] = [f'component:{root(i)}' for i in range(len(data))]
    # A translation bundle contributes one seed's total weight; it is not extra
    # independent evidence. Public examples remain unit weight.
    family_sizes = data.groupby('seed_id').source_id.transform('count')
    data['sample_weight'] = np.where(data.origin.eq('synthetic'), 1 / family_sizes, 1.0)
    return data, dict(legacy_data_sha256=metadata['data_sha256'],
                     source_hashes=metadata.get('source_hashes', {}), emails_included=metadata.get('emails_included'),
                     seed_sha256=digest(Path(seed_path).read_bytes()),
                     provenance_counts=data.provenance.value_counts().to_dict(),
                     origin_counts=data.origin.value_counts().to_dict(),
                     language_counts=data.language.value_counts().to_dict(),
                     label_counts=data.intent.value_counts().to_dict(),
                     independent_groups=int(data.group_id.nunique()), near_duplicate_edges=edges,
                     grouping='Connected components: explicit seed lineage, normalized number/contact templates, word-TFIDF cosine >=0.90; approximate, not exhaustive semantic similarity')
