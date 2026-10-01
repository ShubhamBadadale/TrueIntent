"""PROMPT 3 hardening tests for Modules A, B and C.

Scientific-honesty guards: no synthetic call/device/velocity features, no live
fetching, no fabricated ML probabilities.
"""
import importlib

import joblib
import numpy as np
import pandas as pd
import pytest

mod_a = importlib.import_module('ml.predict_module_a')
mod_b = importlib.import_module('ml.predict_module_b')
mod_c = importlib.import_module('ml.predict_module_c')
from ml.features_module_a import (
    ARTIFACT_VERSION, DATASET_ID, EXPECTED_UNITS, FEATURE_CONTRACT,
    FEATURE_ORDER, FEATURES, MODEL_VERSION, PREPROCESSING_VERSION,
    SOURCE_AMOUNT_UNIT, ModuleAIncompatibleError, ModuleAUnavailableError,
    preprocess_features, transaction_features, validate_artifact,
)
from ml.features_module_b import (
    describe_hostname, describe_port, hostname, is_idn_host,
    is_private_or_internal, is_shortener_host, lookalike_indicators,
    nested_redirect_target, parse_url, shannon_entropy, subdomain_count,
    suspicious_encoded_chars, suspicious_path_query,
)
from ml.predict_module_b import check_url
from ml.predict_module_c import analyze_message, extract_heuristic_evidence
from ml.features_module_c import HEURISTIC_CATEGORIES, HEURISTIC_DEFINITIONS

BASE = dict(amount=5.25, amount_unit=SOURCE_AMOUNT_UNIT)


def test_contract_has_all_required_fields():
    for key in ('artifact_version', 'model_version', 'features', 'feature_order',
                'dataset_id', 'preprocessing_version', 'amount_unit',
                'expected_units', 'scope'):
        assert key in FEATURE_CONTRACT, f'missing contract field {key}'
    assert FEATURE_CONTRACT['artifact_version'] == ARTIFACT_VERSION
    assert FEATURE_CONTRACT['model_version'] == MODEL_VERSION
    assert FEATURE_CONTRACT['features'] == FEATURES == ['amount']
    assert FEATURE_CONTRACT['feature_order'] == FEATURE_ORDER == ['amount']
    assert FEATURE_CONTRACT['dataset_id'] == DATASET_ID
    assert FEATURE_CONTRACT['preprocessing_version'] == PREPROCESSING_VERSION
    assert FEATURE_CONTRACT['expected_units'] == EXPECTED_UNITS
    assert EXPECTED_UNITS['amount'] == SOURCE_AMOUNT_UNIT


def test_trained_artifact_records_library_versions(benchmark_file):
    artifact = joblib.load(str(benchmark_file))
    assert artifact['feature_contract'] == FEATURE_CONTRACT
    assert artifact['artifact_version'] == ARTIFACT_VERSION
    assert artifact['model_version'] == MODEL_VERSION
    assert artifact['feature_order'] == ['amount']
    libs = artifact.get('model_library_versions', {})
    assert 'xgboost' in libs and 'sklearn' in libs


def test_incompatible_is_distinct_but_compatible():
    assert issubclass(ModuleAIncompatibleError, ModuleAUnavailableError)
    assert ModuleAIncompatibleError is not ModuleAUnavailableError


@pytest.mark.parametrize('amount', [
    float('nan'), float('inf'), -float('inf'), -1, -0.01, True, False,
    '5.25', None, object(), 1e100, float(np.finfo(np.float32).max) * 2,
])
def test_rejects_invalid_amounts(amount):
    with pytest.raises(ValueError):
        transaction_features(dict(BASE, amount=amount))


@pytest.mark.parametrize('unit', [None, 'INR', 'USD', '', 'inr', 'ieee_cis'])
def test_wrong_units_rejected_before_model_loading(unit):
    payload = dict(BASE)
    if unit is None:
        del payload['amount_unit']
    else:
        payload['amount_unit'] = unit
    with pytest.raises(ValueError):
        mod_a.predict_module_a(payload, 'does-not-exist.pkl')


def test_missing_artifact_is_unavailable_not_incompatible(tmp_path):
    with pytest.raises(ModuleAUnavailableError) as exc:
        mod_a.load_model(str(tmp_path / 'nope.pkl'))
    assert 'missing' in str(exc.value).lower()


def test_obsolete_contract_is_incompatible(benchmark_file, tmp_path):
    artifact = joblib.load(str(benchmark_file))
    old = dict(artifact)
    old['feature_contract'] = dict(old['feature_contract'])
    old['feature_contract']['artifact_version'] = 2
    path = tmp_path / 'old.pkl'
    joblib.dump(old, path)
    with pytest.raises(ModuleAIncompatibleError):
        mod_a.load_model(str(path))


def test_legacy_six_feature_model_rejected(tmp_path):
    joblib.dump({'model': object(), 'feature_cols': ['amount', 'hour_of_day'],
                 'feature_contract': FEATURE_CONTRACT}, tmp_path / 'legacy.pkl')
    with pytest.raises(ModuleAIncompatibleError):
        mod_a.load_model(str(tmp_path / 'legacy.pkl'))


def test_malformed_artifacts_rejected(tmp_path):
    bad = tmp_path / 'bad.pkl'
    bad.write_bytes(b'not a pickle')
    with pytest.raises(ModuleAUnavailableError):
        mod_a.load_model(str(bad))
    joblib.dump({'feature_cols': ['amount']}, tmp_path / 'nocon.pkl')
    with pytest.raises(ModuleAIncompatibleError):
        mod_a.load_model(str(tmp_path / 'nocon.pkl'))
    with pytest.raises(ModuleAIncompatibleError):
        validate_artifact(['not', 'a', 'dict'])


def test_no_synthetic_features_accepted(benchmark_model):
    for extra in ('is_active_call', 'transaction_velocity', 'hour_of_day',
                  'is_new_device', 'device_id', 'timestamp'):
        payload = dict(BASE, **{extra: 1})
        assert list(transaction_features(payload).columns) == ['amount']
        assert mod_a.predict_module_a(payload) == pytest.approx(
            mod_a.predict_module_a(BASE))


# ---------------------------------------------------------------- Module B ---

@pytest.fixture
def _rules_only(monkeypatch):
    monkeypatch.setattr(mod_b, '_load_ml_model', lambda: None)
    # mod_c shells out to Module B for embedded URLs; keep that offline too.
    monkeypatch.setattr(mod_c, 'check_url',
                        lambda url, fetch_live_page=False: mod_b.check_url(
                            url, fetch_live_page=False))
    return monkeypatch


def _res(url):
    return check_url(url, fetch_live_page=False)


def test_safe_url_stays_clean(_rules_only):
    res = _res('https://www.google.com/search?q=test')
    assert res['score'] < 0.3
    assert res['reasons'] == []


def test_ipv4_and_ipv6_flagged(_rules_only):
    for url in ('http://192.0.2.1/login', 'https://[2001:db8::1]/login'):
        res = _res(url)
        assert any('IP address' in r for r in res['reasons']), url
        assert res['score'] >= 0.4, url


def test_idn_punycode_flagged(_rules_only):
    res = _res('https://xn--bcher-kva.example/login')
    assert is_idn_host('https://xn--bcher-kva.example/login')
    assert any('punycode' in r.lower() for r in res['reasons'])
    assert res['score'] > 0


def test_shortener_flagged(_rules_only):
    res = _res('http://t.co/abc123')
    assert is_shortener_host('http://t.co/abc123')
    assert any('shortener' in r.lower() for r in res['reasons'])


def test_unusual_port_flagged(_rules_only):
    info = describe_port('https://example.com:8443/login')
    assert info['unusual'] and info['port'] == 8443
    res = _res('https://example.com:8443/login')
    assert any('port' in r.lower() for r in res['reasons'])
    assert _res('https://example.com:443/a')['score'] < 0.5


def test_excessive_subdomains_flagged(_rules_only):
    url = 'https://a.b.c.d.e.example.com/login'
    assert subdomain_count(url) >= 4
    assert any('subdomain' in r.lower() for r in _res(url)['reasons'])


def test_suspicious_encodings_flagged(_rules_only):
    assert suspicious_encoded_chars('https://example.com/%00admin')
    assert suspicious_encoded_chars('https://example.com/%252e')
    res = _res('https://example.com/%00admin')
    assert any('encoded' in r.lower() for r in res['reasons'])


def test_malformed_hostnames_flagged(_rules_only):
    for url in ('https://bad_host.example/login', 'https://-bad.example/login'):
        audit = describe_hostname(url)
        assert audit['malformed'], url
        assert any('malformed' in r.lower() for r in _res(url)['reasons'])


def test_suspicious_path_query_flagged(_rules_only):
    assert suspicious_path_query('https://example.com/login/verify?account=1')
    res = _res('https://example.com/login/verify?account=1')
    assert any('path/query' in r.lower() for r in res['reasons'])


def test_extreme_length_and_entropy(_rules_only):
    long_url = 'https://example.com/' + 'a' * 220
    res = _res(long_url)
    assert any('extremely long' in r.lower() for r in res['reasons'])
    assert res['score'] >= 0.2
    assert shannon_entropy('https://example.com/' + 'x7K9qZ2mN4vLp8sWb0' * 8) > 4.0


def test_nested_redirect_flagged(_rules_only):
    url = 'https://example.com/go?redirect=https://evil.example/login'
    assert nested_redirect_target(url)
    assert any('redirect' in r.lower() for r in _res(url)['reasons'])


def test_private_and_localhost_flagged(_rules_only):
    for url in ('http://127.0.0.1/admin', 'http://10.0.0.5/x',
                'http://192.168.1.1/x', 'http://localhost/admin'):
        assert is_private_or_internal(hostname(url)), url
        assert any('private/internal' in r.lower() or 'localhost' in r.lower()
                   for r in _res(url)['reasons']), url


def test_lookalike_indicators(_rules_only):
    assert lookalike_indicators('https://paypa1-login.example/')
    res = _res('http://hdfcbaank-login.xyz/update-kyc')
    assert any('typosquatting' in r.lower() or 'spoofing' in r.lower()
               for r in res['reasons'])


def test_no_server_side_fetching(_rules_only, monkeypatch):
    # Default offline path never touches the (disabled) live-fetch stub.
    def forbidden(*a, **k):
        raise AssertionError('default URL analysis must not fetch a page')
    monkeypatch.setattr(mod_b, 'inspect_live_page', forbidden)
    _res('https://example.com/')
    monkeypatch.undo()
    # Explicit opt-in still performs no I/O: the stub is offline by contract.
    import socket
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    res = check_url('https://example.com/', fetch_live_page=True)
    assert any('disabled' in r.lower() or 'offline' in r.lower()
               for r in res['reasons'])


def test_centralized_parsing_shared(_rules_only):
    assert parse_url('HTTPS://example.com:443/p').scheme == 'https'
    with pytest.raises(ValueError):
        parse_url('ftp://example.com/file')
    # A hostname with spaces is handled as malformed evidence, never a crash.
    res = _res('https://bad host.example/login')
    assert isinstance(res['score'], float)
    assert any('malformed' in r.lower() for r in res['reasons'])


# ---------------------------------------------------------------- Module C ---

@pytest.fixture
def _no_model(monkeypatch):
    monkeypatch.setattr(mod_c, '_load_ml_model', lambda: None)
    monkeypatch.setattr(mod_c, 'check_url',
                        lambda url, fetch_live_page=False: mod_b.check_url(
                            url, fetch_live_page=False))
    return monkeypatch


def _msg(text):
    return analyze_message(text, fetch_live_page=False)


def test_all_categories_reachable(_no_model):
    probes = {
        'urgency': 'Act now, limited time, hurry before it expires',
        'threats': 'An arrest warrant will issue and legal action follows',
        'fear': 'You are under investigation for money laundering, stay on the line',
        'authority_impersonation': 'This is a CBI police officer with a court order',
        'investment_scam': 'Guaranteed returns, double your money, join our trading group',
        'guaranteed_rewards': 'Congratulations, you have won the lottery prize',
        'credential_request': 'Share your password and login details to verify your account',
        'otp_request': 'Share the OTP verification code now',
        'payment_request': 'Send money via UPI payment immediately',
        'remote_access_request': 'Install AnyDesk and enable remote access for screen sharing',
        'account_suspension': 'Your account will be suspended and blocked',
        'kyc_update_scam': 'Complete KYC update and submit documents for verification',
        'suspicious_links': 'See https://suspicious.example/login now',
    }
    covered = set()
    for category, probe in probes.items():
        findings = extract_heuristic_evidence(probe)
        assert findings, f'no heuristic for {category}'
        covered.update(f['category'] for f in findings)
    for category in HEURISTIC_CATEGORIES:
        assert category in covered, f'category {category} unreachable'


def test_heuristic_schema(_no_model):
    findings = extract_heuristic_evidence(
        'Urgent: share your OTP now or your account will be suspended. '
        'See https://evil.example/verify')
    assert findings
    for item in findings:
        assert set(item) >= {'signal', 'category', 'description',
                             'severity', 'matched', 'affects_score'}
        assert item['category'] in HEURISTIC_CATEGORIES
        assert item['severity'] in ('low', 'medium', 'high')
        assert isinstance(item['matched'], str) and 0 < len(item['matched']) <= 120
        assert item['affects_score'] is False
        assert len(item['matched']) < 200


def test_missing_model_fabricates_nothing(_no_model):
    res = _msg('Share your OTP immediately, your account will be suspended.')
    assert res['text_assessed'] is False
    assert res['intent'] is None
    assert res['intent_probabilities'] == {}
    assert res['text_score'] is None
    assert res['score'] == pytest.approx(0.0)
    assert 'unavailable' in res['ml_status'] or 'not assessed' in res['ml_status']
    assert len(res['heuristic_evidence']) >= 2
    assert all(h['affects_score'] is False for h in res['heuristic_evidence'])


def test_url_only_score_without_model(_no_model):
    res = _msg('Update KYC here: http://192.168.1.1/verify-account thanks')
    assert res['text_assessed'] is False
    assert res['score'] >= 0.4
    assert any('URL' in r for r in res['reasons'])


def test_no_duplicate_signals_inflate_severity(_no_model):
    findings = extract_heuristic_evidence('urgent urgent urgent act now right now hurry hurry')
    signals = [f['signal'] for f in findings]
    assert len(signals) == len(set(signals))
    assert signals.count('urgency_keywords') == 1


def test_clean_message_has_no_heuristics(_no_model):
    res = _msg('Hey, are we still meeting for lunch tomorrow? Let me know!')
    assert res['heuristic_evidence'] == []
    assert res['score'] < 0.3


def test_empty_message_shape(_no_model):
    res = _msg('   ')
    assert res['signature'] == 'none'
    assert res['heuristic_evidence'] == []
    assert isinstance(res['score'], float)


def test_ml_and_heuristics_stay_separate(monkeypatch):
    from ml.features_module_c import INTENTS

    class IntentModel:
        classes_ = np.asarray(INTENTS)

        def predict_proba(self, texts):
            probs = np.full((len(texts), len(INTENTS)), 0.01)
            probs[:, 0] = 0.91
            return probs

    class Psychology:
        def predict(self, texts):
            return ['none']

    monkeypatch.setattr(mod_c, '_load_ml_model', lambda: dict(
        mode='intent-v2', intent_pipeline=IntentModel(),
        pipeline=Psychology(), evidence_rules=[]))
    # Keep embedded-URL folding deterministic: rules-only, no ML blend.
    monkeypatch.setattr(mod_b, '_load_ml_model', lambda: None)
    res = mod_c.analyze_message('Share your OTP now at https://example.com/x')
    assert res['text_assessed'] is True
    assert res['intent'] == 'benign'
    assert res['score'] == pytest.approx(0.09)
    assert res['intent_probabilities']['benign'] == pytest.approx(0.91)
    assert res['heuristic_evidence']
    assert all(h['affects_score'] is False for h in res['heuristic_evidence'])
