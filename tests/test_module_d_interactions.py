"""Fusion mechanics and policy isolation; no real-world accuracy assertions."""
import math
import joblib
import pytest
from sklearn.linear_model import LogisticRegression
from ml.features_module_d import FEATURES, feature_row, frame_for, ABLATIONS
from ml.evaluate_module_d import generate_scenarios
from ml import predict_module_d as d


@pytest.fixture
def interaction_model(tmp_path, monkeypatch):
    data = generate_scenarios()
    model = LogisticRegression(max_iter=1000).fit(frame_for(data, 'abck'), data.combined_label)
    path = tmp_path / 'fixture.pkl'
    joblib.dump(dict(model=model, feature_cols=FEATURES, format_version=2), path)
    monkeypatch.setattr(d, '_get_model_path', lambda: str(path))
    return model


def test_missing_is_distinct_from_zero_and_unknown_call():
    missing = feature_row(b=.2)
    zero = feature_row(a=0., b=.2, active_call=False)
    assert missing['module_a_score'] == zero['module_a_score'] == 0
    assert missing['a_present'] == 0 and zero['a_present'] == 1
    assert missing['call_known'] == 0 and zero['call_known'] == 1
    with pytest.raises(ValueError):
        feature_row(active_call=True)


def test_cross_channel_interactions_are_gated_by_presence():
    row = feature_row(.8, .7, .6, True, .9, .5)
    assert row['message_transaction'] == pytest.approx(.48)
    assert row['call_transaction'] == .8
    assert row['url_credentials'] == pytest.approx(.63)
    assert row['authority_transaction'] == .4
    missing_c = feature_row(.8, .7, None, None, .9, .5)
    assert missing_c['url_credentials'] == missing_c['authority_transaction'] == 0


def test_feature_contributions_reconstruct_score(interaction_model):
    result = d.compute_unified_score(.7, .4, .6, active_call=True)
    detail = result['details']
    z = detail['intercept'] + sum(detail['feature_contributions_log_odds'].values())
    assert result['score'] == round(1 / (1 + math.exp(-z)), 4)
    assert detail['availability'] == dict(module_a=True, module_b=True, module_c=True)


def test_embedded_url_is_not_a_second_message_signal(interaction_model):
    message = dict(score=.9, text_score=.1, embedded_url_score=.9, text_assessed=True,
                   intent_probabilities={'credential_theft': .02, 'authority_fear': .03})
    result = d.compute_unified_score(None, .9, message)
    scores = result['details']['module_scores']
    assert scores == dict(module_a=None, module_b=.9, module_c=.1)
    assert result['details']['feature_values']['url_credentials'] == pytest.approx(.018)


def test_module_a_benchmark_contract_is_refused(interaction_model):
    with pytest.raises(ValueError, match='fusion is disabled'):
        d.compute_unified_score({'score': .8, 'analysis_scope': 'ieee_cis_amount_only_benchmark'}, .7)


def test_synthetic_split_and_fixed_ablation_labels():
    data = generate_scenarios()
    assert data.family_id.is_unique
    assert set(data.provenance) == {'synthetic_policy'}
    for channels in ABLATIONS.values():
        features = frame_for(data, channels)
        assert len(features) == len(data)
        assert 'combined_label' not in features
        if 'c' not in channels:
            assert features.credential_request.eq(0).all()
    assert not data.combined_label.eq(data.legacy_or_label).all()


def test_combined_api_accepts_call_but_not_call_only():
    from backend.app.schemas import CombinedRequest
    assert CombinedRequest(text='hello', active_call=True).active_call is True
    assert CombinedRequest(text='hello').active_call is None
    with pytest.raises(ValueError):
        CombinedRequest(active_call=True)
    with pytest.raises(ValueError):
        CombinedRequest(text='hello', active_call='false')
