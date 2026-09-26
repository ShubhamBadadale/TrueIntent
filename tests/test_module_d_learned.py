import math
import pytest
from ml import predict_module_d as d


def test_learned_contributions_reconstruct_score():
    result = d.compute_unified_score(.2, .8, None)
    details = result['details']
    assert details['scoring_method'] == 'logistic_synthetic_policy'
    z = details['intercept'] + sum(details['module_contributions_log_odds'].values())
    assert result['score'] == round(1 / (1 + math.exp(-z)), 4)
    assert details['module_contributions_log_odds']['module_c'] == 0
    assert result['explanation'].index('link risk score') < result['explanation'].index('transaction risk score')


def test_missing_model_fallback_warns(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(d, '_get_model_path', lambda: str(tmp_path / 'missing.pkl'))
    result = d.compute_unified_score(.2, .8, None)
    assert result['score'] == round((.45 * .2 + .25 * .8) / .7, 4)
    assert 'fixed-weight fallback' in caplog.text


def test_corrupt_model_is_not_silently_ignored(tmp_path, monkeypatch):
    path = tmp_path / 'bad.pkl'; path.write_bytes(b'not a model')
    monkeypatch.setattr(d, '_get_model_path', lambda: str(path))
    with pytest.raises(Exception):
        d.compute_unified_score(.2)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_score_rejected(value):
    with pytest.raises(ValueError): d.compute_unified_score(value)


def test_no_invented_embedded_link_explanation():
    result = d.compute_unified_score(None, None, {'score': .8, 'signature': 'none', 'reasons': []})
    assert 'suspicious link embedded' not in result['explanation']


def test_incompatible_artifact_errors(tmp_path, monkeypatch):
    import joblib
    path = tmp_path / 'wrong.pkl'
    joblib.dump({'feature_cols': ['wrong']}, path)
    monkeypatch.setattr(d, '_get_model_path', lambda: str(path))
    with pytest.raises(ValueError, match='Incompatible'):
        d.compute_unified_score(.2)


def test_scenario_generation_refuses_rules_only_scores():
    from ml.generate_module_d_data import active_score
    with pytest.raises(RuntimeError): active_score({'score': .2, 'ml_status': 'rules_only'})
    assert active_score({'score': .2, 'ml_status': 'active'}) == .2
