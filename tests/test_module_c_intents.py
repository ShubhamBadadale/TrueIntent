"""Contract/leakage tests; authored fixtures never imply real-data accuracy."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import StratifiedGroupKFold

from ml.features_module_c import normalize_text, word_tokens, INTENTS
from ml.generate_module_c_data import digest, group_key
from ml.module_c_dataset import assemble_intents
from ml.evaluate_module_c import supported_rules
from ml import predict_module_c as predictor
from ml.ocr_module_c import has_enough_text


def test_hindi_marks_negation_and_unicode_are_preserved():
    text = '  अपना पासवर्ड किसी को मत देना।  '
    assert 'पासवर्ड' in word_tokens(normalize_text(text))
    assert 'मत' in word_tokens(normalize_text(text))
    assert normalize_text('Do NOT share\u200b your OTP') == 'do not share your otp'
    assert has_enough_text(text)


def test_translation_and_number_variants_cannot_cross_folds(tmp_path):
    rows = []
    for i, (text, label) in enumerate([
        ('Lunch is at the library today', 'none'),
        ('A beneficiary can claim the large estate', 'greed_opportunity'),
        ('The police demand money to cancel charges', 'fear_authority'),
        ('Win 100 call https://one.example', 'greed_opportunity'),
        ('Win 500 call https://two.example', 'greed_opportunity'),
    ]):
        rows.append(dict(text=text, signature=label, source_url='unit-test',
                         source_id=f'fixture:{i}', source_kind='test', label_basis='test', group_id=group_key(text)))
    path = tmp_path / 'source.csv'
    pd.DataFrame(rows).to_csv(path, index=False)
    path.with_suffix('.metadata.json').write_text(json.dumps({'data_sha256': digest(path.read_bytes())}))
    data, meta = assemble_intents(path)
    assert meta['provenance_counts']['synthetic'] == 54
    assert meta['provenance_counts']['augmented'] == 63
    assert data.groupby('seed_id').group_id.nunique().max() == 1
    authored = data[data.origin.eq('synthetic')]
    assert np.allclose(authored.groupby('seed_id').sample_weight.sum(), 1)
    for train, test in StratifiedGroupKFold(2, shuffle=True, random_state=42).split(data.text, data.intent, data.group_id):
        assert not set(data.iloc[train].group_id) & set(data.iloc[test].group_id)
        assert not set(data.iloc[train].seed_id) & set(data.iloc[test].seed_id)


def test_duplicate_translations_do_not_make_rule_support():
    data = pd.DataFrame([dict(text='digital arrest', intent='digital_arrest', group_id='one')] * 3)
    assert supported_rules(data) == []


def test_ml_prediction_and_rule_evidence_are_separate(monkeypatch):
    class IntentModel:
        classes_ = np.asarray(INTENTS)
        def predict_proba(self, texts):
            return np.asarray([[.91, .01, .01, .01, .01, .01, .01, .01, .01, .01]])
    class Psychology:
        def predict(self, texts):
            return ['none']
    monkeypatch.setattr(predictor, '_load_ml_model', lambda: dict(mode='intent-v2', intent_pipeline=IntentModel(),
                        pipeline=Psychology(), evidence_rules=[dict(phrase='digital arrest', intent='digital_arrest')]))
    result = predictor.analyze_message('This is an advisory about digital arrest')
    assert result['intent'] == 'benign'
    assert result['score'] == pytest.approx(.09)
    assert result['signature'] == 'none'
    assert result['rule_evidence'][0]['affects_score'] is False
    assert result['text_assessed']


def test_api_preserves_intent_and_abstention_fields(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import main, services
    monkeypatch.setattr(services, 'analyze_text', lambda *args, **kwargs: dict(
        score=.6, signature='none', reasons=['ML intent prediction'], ml_status='active test',
        intent='credential_theft', intent_probabilities={'credential_theft': .6},
        rule_evidence=[], text_assessed=True))
    response = TestClient(main.app).post('/check-message', data={'text': 'fixture'})
    assert response.status_code == 200
    assert response.json()['intent'] == 'credential_theft'
    assert response.json()['text_assessed'] is True


def test_api_cannot_present_missing_text_model_as_low_risk(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import main, services
    monkeypatch.setattr(services, 'analyze_text', lambda *args, **kwargs: dict(
        score=0, signature='none', reasons=[], ml_status='unavailable', text_assessed=False))
    client = TestClient(main.app)
    assert client.post('/check-message', data={'text': 'test'}).status_code == 503
    assert client.post('/check-combined', json={'text': 'test'}).status_code == 503
