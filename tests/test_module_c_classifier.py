"""Offline data validation and classifier-path tests; no performance claim from fixtures."""
import json
from pathlib import Path
import joblib
import pandas as pd
import pytest
from ml import predict_module_c as predictor
from ml.generate_module_c_data import group_key, validate_examples, email_bodies
from ml.train_module_c import new_pipeline


def test_grouping_collapses_contact_and_number_variants():
    assert group_key('Win 100 call https://a.example') == group_key('Win 500 call https://b.example')


def test_unknown_signature_is_rejected():
    frame=pd.DataFrame([dict(text='test',signature='unknown',source_url='source',source_id='1',source_kind='test',label_basis='test',group_id='a')])
    with pytest.raises(ValueError):
        validate_examples(frame)


def test_email_parser_omits_headers():
    payload=b'From sender date\nFrom: private@example.com\nSubject: header token\nContent-Type: text/plain\n\nBody example.\n'
    assert list(email_bodies(payload)) == [(1,'Body example.')]


def test_cited_fear_set_is_small_and_has_no_duplicate_sources():
    path=Path(__file__).resolve().parents[1]/'data/module_c_fear_sources.json'
    rows=json.loads(path.read_text())
    assert len(rows)==5
    assert len({r['source_url'] for r in rows})==5
    assert all(r['text'] and r['label_basis'] for r in rows)


def test_real_model_metadata_and_inference(monkeypatch):
    path=Path(__file__).resolve().parents[1]/'ml/models/module_c.pkl'
    if not path.exists():
        pytest.skip('Generate and train Module C to run real-data integration')
    artifact=joblib.load(path)
    assert set(artifact['pipeline'].classes_) == {'fear_authority','greed_opportunity','none'}
    if artifact.get('mode') == 'intent-v2':
        assert artifact['evaluation']['provenance']['provenance_counts']['manually_curated'] == 5
    monkeypatch.setattr(predictor,'_load_ml_model',lambda:artifact)
    result=predictor.analyze_message('Hey, are we still meeting for lunch tomorrow?',False)
    assert result['ml_status'].startswith('active')
    assert result['signature']=='none'
    assert result['score']<0.3


def test_classifier_can_classify_without_keyword_hits(monkeypatch):
    # Invented unit-test fixtures only; never used in the production dataset/model.
    texts=['police custody investigation']*5+['inheritance beneficiary fortune']*5+['lunch tomorrow friends']*5
    labels=['fear_authority']*5+['greed_opportunity']*5+['none']*5
    pipeline=new_pipeline().fit(texts,labels)
    monkeypatch.setattr(predictor,'_load_ml_model',lambda:{'pipeline':pipeline})
    result=predictor.analyze_message('inheritance beneficiary fortune',False)
    assert result['signature']=='greed_opportunity'
    assert result['ml_status'].startswith('active')
    assert result['score']>0.5


def test_broken_model_does_not_masquerade_as_keyword_prediction(monkeypatch):
    monkeypatch.setattr(predictor,'_load_ml_model',lambda:{'pipeline':object()})
    result=predictor.analyze_message('You are under investigation. Stay on the line.',False)
    assert result['signature']=='none'
    assert result['text_assessed'] is False
    assert 'inference failed' in result['ml_status']
