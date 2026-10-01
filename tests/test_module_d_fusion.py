"""PROMPT 4 fusion-layer tests: standardized contracts, missing-is-missing,
central thresholds, no Module A fusion, determinism.

Transparent-fusion tests pin `_load_learned_model` to None so they exercise
the documented weighted risk-score path deterministically.
"""
import importlib

import pytest

d = importlib.import_module('ml.predict_module_d')
features_d = importlib.import_module('ml.features_module_d')

SAFE_B = {'score': 0.05, 'reasons': [], 'ml_status': 'rules_only (model unavailable)'}
SUSP_B = {'score': 0.9,
          'reasons': ['Host is a raw IP address (IPv4; 192.168.1.1) rather than a registered domain name'],
          'ml_status': 'rules_only (model unavailable)'}


def _message(score, text_score=None, embedded=0.0, assessed=True):
    return {
        'score': score,
        'text_score': text_score if text_score is not None else (score if assessed else None),
        'embedded_url_score': embedded,
        'signature': 'none',
        'reasons': [],
        'ml_status': 'active test' if assessed else 'unavailable (text not assessed)',
        'intent': None,
        'intent_probabilities': {},
        'rule_evidence': [],
        'heuristic_evidence': [],
        'text_assessed': assessed,
    }


BENIGN_C = _message(0.1)
SUSP_C = _message(0.85, embedded=0.9)


@pytest.fixture
def fallback(monkeypatch):
    monkeypatch.setattr(d, '_load_learned_model', lambda: None)
    return monkeypatch


# ---------------------------------------------------------- module contract ---
def test_standardized_assessed_contract_shape(fallback):
    std = d.standardize_module_result('module_b', dict(SUSP_B))
    assert std == {
        'module': 'module_b',
        'assessed': True,
        'score': 0.9,
        'confidence': None,
        'risk_level': 'Critical',
        'evidence': list(SUSP_B['reasons']),
        'model_version': SUSP_B['ml_status'],
        'abstention_reason': None,
    }


def test_standardized_unavailable_contract_shape(fallback):
    for module, reason in (('module_b', 'not_provided'), ('module_c', 'not_provided'),
                           ('module_a', 'unsupported')):
        std = d.standardize_module_result(module, None)
        assert std == {
            'module': module,
            'assessed': False,
            'score': None,
            'confidence': None,
            'risk_level': None,
            'evidence': [],
            'model_version': 'unknown',
            'abstention_reason': reason,
        }


def test_unassessed_text_never_becomes_zero_score(fallback):
    std = d.standardize_module_result(
        'module_c', _message(0.9, embedded=0.9, assessed=False))
    assert std['assessed'] is False
    assert std['score'] is None
    assert std['risk_level'] is None
    assert std['abstention_reason'] == 'model_unavailable'


def test_assessment_failed_reason_preserved(fallback):
    msg = _message(0.0, assessed=False)
    msg['ml_status'] = 'unavailable (ML inference failed; text not assessed)'
    std = d.standardize_module_result('module_c', msg)
    assert std['abstention_reason'] == 'assessment_failed'


def test_standardize_rejects_invalid_inputs(fallback):
    with pytest.raises(TypeError):
        d.standardize_module_result('module_b', True)
    for bad in (float('nan'), float('inf'), -float('inf'), 1.5, -0.1, 'high'):
        with pytest.raises((TypeError, ValueError)):
            d.standardize_module_result('module_b', bad)
    with pytest.raises(ValueError):
        d.standardize_module_result('module_b', {'reasons': []})
    with pytest.raises(ValueError):
        d.standardize_module_result('module_x', 0.5)
    mismatched = dict(d.standardize_module_result('module_b', dict(SUSP_B)))
    with pytest.raises(ValueError):
        d.standardize_module_result('module_c', mismatched)


def test_thresholds_central_and_boundaries(fallback):
    assert features_d.RISK_THRESHOLDS == {'low_max': 0.25, 'medium_max': 0.50, 'high_max': 0.75}
    assert features_d.RISK_LEVELS == ('Low', 'Medium', 'High', 'Critical')
    assert [features_d.risk_level_for(v) for v in (0.0, 0.2499, 0.25, 0.4999, 0.5, 0.7499, 0.75, 1.0)] == \
        ['Low', 'Low', 'Medium', 'Medium', 'High', 'High', 'Critical', 'Critical']
    with pytest.raises(ValueError):
        features_d.risk_level_for(float('nan'))


# ------------------------------------------------------------------ fusion ----
def _keys(result):
    for key in ('score', 'risk_level', 'tier', 'explanation', 'analyzed_modules',
                'contributing_modules', 'unavailable_modules', 'evidence',
                'warnings', 'fusion_version', 'limitations',
                'recommended_action', 'details', 'modules'):
        assert key in result, f'missing combined key {key}'


def test_url_only(fallback):
    result = d.compute_unified_score(None, dict(SUSP_B), None)
    _keys(result)
    assert result['score'] == pytest.approx(0.9)  # unavailable C never drags to 0
    assert result['risk_level'] == result['tier'] == 'Critical'
    assert result['analyzed_modules'] == ['module_b']
    assert result['contributing_modules'] == ['module_b']
    assert sorted(result['unavailable_modules']) == ['module_a', 'module_c']
    assert result['modules']['module_b']['assessed'] is True
    assert result['modules']['module_c'] == {
        'module': 'module_c', 'assessed': False, 'score': None,
        'confidence': None, 'risk_level': None, 'evidence': [],
        'model_version': 'unknown', 'abstention_reason': 'not_provided',
    }
    assert any(e['module'] == 'module_b' for e in result['evidence'])
    assert result['fusion_version'] == features_d.FUSION_VERSION
    assert result['limitations'] and result['recommended_action']
    assert 'fraud probability' not in result['explanation'].lower()


def test_message_only(fallback):
    result = d.compute_unified_score(None, None, _message(0.2))
    assert result['score'] == pytest.approx(0.2)
    assert result['risk_level'] == 'Low'
    assert result['analyzed_modules'] == ['module_c']
    assert sorted(result['unavailable_modules']) == ['module_a', 'module_b']


def test_url_and_message_weighted(fallback):
    result = d.compute_unified_score(None, dict(SUSP_B), _message(0.1))
    assert result['score'] == pytest.approx(round((0.25 * 0.9 + 0.30 * 0.1) / 0.55, 4))
    assert result['analyzed_modules'] == ['module_b', 'module_c']
    assert result['unavailable_modules'] == ['module_a']
    assert {e['module'] for e in result['evidence']} == {'module_b'}


def test_module_b_unavailable_matches_message_only(fallback):
    unavailable_b = {'module': 'module_b', 'assessed': False, 'score': None,
                     'confidence': None, 'risk_level': None, 'evidence': [],
                     'model_version': 'unknown', 'abstention_reason': 'model_unavailable'}
    assert d.compute_unified_score(None, unavailable_b, _message(0.2))['score'] == \
        pytest.approx(d.compute_unified_score(None, None, _message(0.2))['score'])


def test_module_c_unavailable_matches_url_only(fallback):
    assert d.compute_unified_score(None, dict(SUSP_B), None)['score'] == \
        pytest.approx(d.compute_unified_score(
            None, dict(SUSP_B),
            _message(0.9, embedded=0.9, assessed=False))['score'])
    partial = d.compute_unified_score(None, dict(SUSP_B), _message(0.9, assessed=False))
    assert 'module_c' in partial['unavailable_modules']
    assert any('Partial analysis' in w for w in partial['warnings'])


def test_both_unavailable_raises(fallback):
    with pytest.raises(ValueError):
        d.compute_unified_score(None, None, None)
    with pytest.raises(ValueError):
        d.compute_unified_score(None, None, _message(0.0, assessed=False))


@pytest.mark.parametrize(('b_score', 'c_score', 'level'), [
    (0.05, 0.10, 'Low'), (0.9, 0.10, 'Medium'), (0.05, 0.85, 'Medium'), (0.9, 0.85, 'Critical'),
])
def test_suspicious_combinations_ordered(fallback, b_score, c_score, level):
    result = d.compute_unified_score(
        None, {'score': b_score, 'reasons': [], 'ml_status': 'x'}, _message(c_score))
    assert result['risk_level'] == level


def test_mixed_and_both_suspicious_above_benign(fallback):
    benign = d.compute_unified_score(
        None, {'score': 0.05, 'reasons': [], 'ml_status': 'x'}, _message(0.10))['score']
    mixed_url = d.compute_unified_score(None, dict(SUSP_B), _message(0.10))['score']
    mixed_text = d.compute_unified_score(
        None, {'score': 0.05, 'reasons': [], 'ml_status': 'x'}, _message(0.85))['score']
    both = d.compute_unified_score(None, dict(SUSP_B), _message(0.85))['score']
    assert mixed_url > benign and mixed_text > benign
    assert both > mixed_url and both > mixed_text
    assert d.compute_unified_score(None, dict(SUSP_B), _message(0.85))['risk_level'] == 'Critical'


def test_url_evidence_counted_once(fallback):
    # Same embedded URL whether or not it is also submitted standalone.
    c_only = d.compute_unified_score(None, None, _message(0.1, embedded=0.9))
    both = d.compute_unified_score(None, dict(SUSP_B), _message(0.1, embedded=0.9))
    assert both['score'] == pytest.approx(c_only['score'])
    assert any('counted once' in w for w in both['warnings'])


def test_invalid_inputs_rejected(fallback):
    with pytest.raises(TypeError):
        d.compute_unified_score(None, True, None)
    for bad in (float('nan'), float('inf'), {'reasons': []}, [0.5]):
        with pytest.raises((TypeError, ValueError)):
            d.compute_unified_score(None, bad, None)
    with pytest.raises(ValueError):
        d.compute_unified_score(None, dict(SUSP_B), None, active_call='yes')
    with pytest.raises(ValueError):
        d.compute_unified_score(None, dict(SUSP_B), None, active_call=1)


@pytest.mark.parametrize('a_input', [
    {'amount': 500, 'device_id': 'known'},
    {'score': 0.8, 'analysis_scope': 'ieee_cis_amount_only_benchmark'},
    {'module': 'module_a', 'assessed': True, 'score': 0.8, 'confidence': None,
     'risk_level': 'Critical', 'evidence': [], 'model_version': 'x',
     'abstention_reason': None},
    {'score': 0.8, 'transaction': {'amount': 1}},
])
def test_unsupported_module_a_fusion_refused(fallback, a_input):
    with pytest.raises(ValueError, match='fusion is disabled'):
        d.compute_unified_score(a_input, dict(SUSP_B), None)


def test_deterministic_for_identical_inputs(fallback):
    msg = _message(0.4, embedded=0.2)
    msg['heuristic_evidence'] = [{'signal': 's', 'category': 'urgency',
                                  'description': 'd', 'severity': 'medium',
                                  'matched': 'hurry', 'affects_score': False}]
    args = (None, dict(SUSP_B), dict(msg))
    first = d.compute_unified_score(*args, active_call=True)
    second = d.compute_unified_score(*args, active_call=True)
    assert first == second
    assert d.fuse_modules(dict(SUSP_B), _message(0.4)) == \
        d.compute_unified_score(None, dict(SUSP_B), _message(0.4))


def test_output_is_risk_score_not_fraud_probability(fallback):
    result = d.compute_unified_score(None, dict(SUSP_B), SUSP_C)
    blob = (result['explanation'] + ' ' + result['recommended_action'] + ' '
            + ' '.join(result['warnings'])).lower()
    assert 'fraud probability' not in blob
    assert 'risk score' in blob


def test_combined_api_surfaces_fusion_contract():
    pytest.importorskip('fastapi', reason='fastapi required for API tests')
    from pathlib import Path
    from fastapi.testclient import TestClient
    root = Path(__file__).resolve().parents[1]
    if not (root / 'ml/models/module_c.pkl').exists():
        pytest.skip('Train Module C to run model-backed API tests')
    from backend.app.main import app
    client = TestClient(app)
    body = client.post('/check-combined', json={
        'url': 'https://www.google.com/',
        'text': 'Hey, are we still meeting for lunch tomorrow?',
    })
    assert body.status_code == 200, body.text
    data = body.json()
    assert data['risk_level'] == data['tier'] == 'Low'
    assert data['analyzed_modules'] == ['module_b', 'module_c']
    assert 'module_a' in data['unavailable_modules']
    assert data['fusion_version'] == features_d.FUSION_VERSION
    assert data['limitations'] and data['recommended_action'] and data['warnings']
    assert isinstance(data['evidence'], list)
    v1 = client.post('/api/v1/analyze/combined', json={
        'url': 'https://www.google.com/',
        'text': 'Hey, are we still meeting for lunch tomorrow?',
    })
    assert v1.status_code == 200, v1.text
    assert v1.json()['data']['risk_level'] == 'Low'
