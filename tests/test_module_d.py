"""Fusion mechanics and exclusion of the unsupported transaction path."""
import pytest
from ml import predict_module_d as d


@pytest.fixture(autouse=True)
def explicit_fallback(monkeypatch):
    monkeypatch.setattr(d, '_load_learned_model', lambda: None)


@pytest.mark.parametrize('transaction', [
    {'amount': 500, 'device_id': 'known'},
    {'amount': 500, 'amount_unit': 'ieee_cis_source'},
])
def test_transaction_context_cannot_enter_obsolete_fusion(transaction):
    with pytest.raises(ValueError, match='fusion is disabled'):
        d.compute_unified_score({'score': .2, 'transaction': transaction}, .8, .9)


def test_high_url_and_message_scores_retain_explanations():
    result = d.compute_unified_score(None,
        {'score': .9, 'reasons': ['Potential typosquatting / brand spoofing']},
        {'score': .9, 'signature': 'fear_authority', 'reasons': []})
    assert result['tier'] == 'Critical'
    assert 'brand' in result['explanation']
    assert 'authority' in result['explanation']
    assert 'Module A (no transaction submitted)' in result['explanation']


def test_skipped_modules_reported_honestly():
    result = d.compute_unified_score(None, {'score': .1, 'reasons': []}, None)
    contributing = result['explanation'].split('Modules contributing:')[1].split('Modules skipped:')[0]
    assert 'Module B' in contributing
    assert 'Module A' not in contributing and 'Module C' not in contributing
    assert result['tier'] == 'Low'


def test_no_modules_raises_instead_of_false_verdict():
    with pytest.raises(ValueError):
        d.compute_unified_score(None, None, None)


def test_accepts_plain_float_scores_for_policy_experiments():
    result = d.compute_unified_score(.9, .8, .85)
    assert result['tier'] == 'Critical'
    assert result['explanation']
