"""
Module D — Unified Risk Scoring & Explanation Layer (central fusion layer).

Fuses Module B (URL safety) and Module C (message analysis) evidence into one
deterministic, explainable verdict. Module A is an amount-only IEEE-CIS
benchmark and is NOT a fusion input (see MODULE_A_FUSION_ENABLED).

Design notes
------------
* Every module result is first normalized with :func:`standardize_module_result`
  into ``{module, assessed, score, confidence, risk_level, evidence,
  model_version, abstention_reason}``. Unavailable modules keep
  ``score=None`` — missing information is never scored as zero.
* The overall result is an uncalibrated **risk score** (never called a fraud
  probability) with a risk level, analyzed/contributing/unavailable module
  lists, evidence, warnings, fusion version, limitations and a recommended
  action. Legacy keys (``tier``, ``explanation``, ``details``) are preserved.
* Scoring is deterministic for identical inputs: a transparent weighted
  average (renormalized over assessed modules) when no learned artifact is
  present, otherwise the versioned interaction policy. No randomness, no
  clock, no network.
* Skipped modules are ALWAYS reported — never implied to have run. No
  assessed module raises ValueError instead of returning a false verdict.
* SHAP: Module C (only when an ML artifact exists AND the caller passes the
  analyzed `text`) uses exact linear-SHAP token attribution. Everything
  degrades gracefully to rule/keyword reasons when SHAP is unavailable.
"""

import os
import re
import sys
import logging
import math
import joblib
import numpy as np
import pandas as pd

_ROOT = str(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ml.features_module_d import (
    ABSTENTION_REASONS,
    ACTIVE_MODULES,
    FEATURES as _FEATURES_D,
    FUSION_VERSION,
    LIMITATIONS,
    MODULE_WEIGHTS,
    RISK_LEVELS,
    RISK_THRESHOLDS,
    RISKY_MODULE_SCORE,
    SUPPORTED_MODULES,
    feature_row,
    recommend_action,
    risk_level_for,
    score as _score_d,
)

_LOGGER = logging.getLogger(__name__)
_D_CACHE = None


class ModuleDUnavailableError(ValueError):
    """The learned artifact exists but cannot be trusted: it is corrupt,
    unreadable, or incompatible with the current feature contract.

    A ``ValueError`` subclass so existing guards keep working; the serving
    layer maps it to 503 rather than falling back silently or 500ing.
    """


def _get_model_path():
    return os.path.join(os.path.dirname(__file__), "models", "module_d.pkl")


def _load_learned_model():
    global _D_CACHE
    path = _get_model_path()
    if not os.path.exists(path):
        _LOGGER.warning("Module D learned model missing; using fixed-weight fallback: %s", path)
        return None
    stat = os.stat(path)
    stamp = (path, stat.st_mtime_ns, stat.st_size)
    if _D_CACHE is not None and _D_CACHE[0] == stamp:
        return _D_CACHE[1]
    try:
        artifact = joblib.load(path)  # Corruption/incompatibility must NOT silently fall back.
    except Exception as exc:
        raise ModuleDUnavailableError(
            'Incompatible or unreadable Module D model artifact.'
        ) from exc
    if not isinstance(artifact, dict):
        raise ModuleDUnavailableError('Incompatible Module D model artifact.')
    if artifact.get('format_version') == 2:
        FEATURES = _FEATURES_D
        model = artifact.get('model')
        if (artifact.get('feature_cols') != FEATURES or model is None
                or list(model.classes_) != [0, 1] or model.coef_.shape != (1, len(FEATURES))
                or not np.isfinite(model.coef_).all() or not np.isfinite(model.intercept_).all()):
            raise ModuleDUnavailableError('Incompatible Module D interaction artifact')
        _D_CACHE = (stamp, artifact)
        return artifact
    expected = ["module_a_score", "module_b_score", "module_c_score"]
    model = artifact.get('model')
    if (artifact.get("feature_cols") != expected or model is None
            or list(model.classes_) != [0, 1]):
        raise ModuleDUnavailableError("Incompatible Module D model artifact")
    if (not np.isfinite(model.coef_).all()
            or not np.isfinite(model.intercept_).all()
            or model.coef_.shape != (1, 3)):
        raise ModuleDUnavailableError("Non-finite Module D coefficients")
    _D_CACHE = (stamp, artifact)
    return _D_CACHE[1]

# -----------------------------------------------------------------------------
# Central fusion constants (imported — the values live in features_module_d).
# Aliases below exist so existing imports keep working.
# -----------------------------------------------------------------------------
WEIGHT_MODULE_A = MODULE_WEIGHTS['module_a']  # reserved; not a fusion input
WEIGHT_MODULE_C = MODULE_WEIGHTS['module_c']  # message analysis (text score)
WEIGHT_MODULE_B = MODULE_WEIGHTS['module_b']  # URL safety

# -----------------------------------------------------------------------------
# Risk-level thresholds live in features_module_d.RISK_THRESHOLDS. Aliases kept.
# -----------------------------------------------------------------------------
TIER_LOW_MAX = RISK_THRESHOLDS['low_max']
TIER_MEDIUM_MAX = RISK_THRESHOLDS['medium_max']
TIER_HIGH_MAX = RISK_THRESHOLDS['high_max']  # >= this -> Critical

VALID_TIERS = RISK_LEVELS

# Set True only by a future validated Module A integration. While False, any
# assessment-like Module A input is refused (never silently fused).
MODULE_A_FUSION_ENABLED = False

#: Refusal raised for any Module A fusion attempt (transaction context,
#: benchmark scope, or standardized module_a assessment).
MODULE_A_FUSION_MESSAGE = (
    "Transaction fusion is disabled: Module A is a source-unit benchmark, "
    "incompatible with the existing combined policy."
)

# A module scoring at/above RISKY_MODULE_SCORE counts as "risky" for headlines.

_SIGNATURE_PHRASES = {
    "fear_authority": "message contains urgency and authority-impersonation language",
    "greed_opportunity": "message contains too-good-to-be-true investment-return language",
}


# -----------------------------------------------------------------------------
# Input normalization
# -----------------------------------------------------------------------------
def _extract_score(result) -> float | None:
    """None -> module skipped. float/int/dict-with-'score' -> clamped float."""
    if result is None:
        return None
    if isinstance(result, bool):
        raise TypeError("Module result must be a score float or dict, not bool.")
    if isinstance(result, (int, float)):
        value = float(result)
        if not math.isfinite(value):
            raise ValueError("Module score must be finite")
        return max(0.0, min(1.0, value))
    if isinstance(result, dict):
        if "score" not in result:
            raise ValueError(f"Module result dict must contain a 'score' key: {result}")
        return _extract_score(result["score"])
    raise TypeError(
        "Module result must be None, a score float, or a dict with a "
        f"'score' key — got {type(result).__name__}."
    )


def _tier_for(score: float) -> str:
    """Legacy alias of the central risk-level mapping (kept for compatibility)."""
    return risk_level_for(score)


def _refuse_module_a_input(result) -> None:
    """Raise for any assessment-like Module A input (never silently fuse)."""
    raise ValueError(MODULE_A_FUSION_MESSAGE)


def _is_standardized_module_dict(result) -> bool:
    return (
        isinstance(result, dict)
        and result.get('module') in SUPPORTED_MODULES
        and 'assessed' in result
    )


def _validate_finite_score(value, *, what: str = 'Module score') -> float:
    if isinstance(value, bool):
        raise TypeError(f'{what} must be a score float or dict, not bool.')
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{what} must be finite and between zero and one') from None
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError(f'{what} must be finite and between zero and one')
    return number


def _unassessed(module_name: str, reason: str) -> dict:
    if reason not in ABSTENTION_REASONS:
        raise ValueError(f'Unknown abstention reason: {reason!r}')
    return {
        'module': module_name,
        'assessed': False,
        'score': None,
        'confidence': None,
        'risk_level': None,
        'evidence': [],
        'model_version': 'unknown',
        'abstention_reason': reason,
    }


def _assessed(module_name: str, score_value, evidence, model_version) -> dict:
    number = _validate_finite_score(score_value, what=f'{module_name} score')
    return {
        'module': module_name,
        'assessed': True,
        'score': round(number, 4),
        'confidence': None,  # explicitly uncalibrated; never a fraud probability
        'risk_level': risk_level_for(number),
        'evidence': [str(item) for item in (evidence or []) if str(item).strip()],
        'model_version': str(model_version or 'unknown'),
        'abstention_reason': None,
    }


def standardize_module_result(module_name: str, result) -> dict:
    """Normalize any module output to the standard module-result contract.

    Returns ``{module, assessed, score, confidence, risk_level, evidence,
    model_version, abstention_reason}``. ``score`` is ``None`` (never zero)
    whenever ``assessed`` is ``False``. Raises ``TypeError``/``ValueError``
    on invalid inputs. Module A assessment-like inputs are refused: the
    benchmark is not a fusion input until a validated integration enables it.
    """
    if module_name not in SUPPORTED_MODULES:
        raise ValueError(
            f'Unknown module {module_name!r}; expected one of {list(SUPPORTED_MODULES)}.'
        )
    if result is None:
        reason = 'unsupported' if module_name == 'module_a' else 'not_provided'
        return _unassessed(module_name, reason)
    if isinstance(result, bool):
        raise TypeError(f'Module result must be a score float or dict, not bool.')
    if isinstance(result, (int, float)):
        if module_name == 'module_a' and not MODULE_A_FUSION_ENABLED:
            # Legacy bare-number policy experiments only; no validated model.
            number = _validate_finite_score(result, what='module_a score')
            return _assessed(module_name, number, [], 'policy_experiment')
        if module_name == 'module_a':
            _refuse_module_a_input(result)
        return _assessed(module_name, result, [], 'numeric_score')
    if _is_standardized_module_dict(result):
        if result.get('module') != module_name:
            raise ValueError(
                f"Module mismatch: expected {module_name!r}, got {result.get('module')!r}."
            )
        if result.get('assessed'):
            if module_name == 'module_a' and not MODULE_A_FUSION_ENABLED:
                _refuse_module_a_input(result)
            return _assessed(module_name, result.get('score'),
                             result.get('evidence', []),
                             result.get('model_version'))
        reason = result.get('abstention_reason') or (
            'unsupported' if module_name == 'module_a' else 'not_provided')
        if reason not in ABSTENTION_REASONS:
            raise ValueError(f'Unknown abstention reason: {reason!r}')
        return _unassessed(module_name, reason)
    if not isinstance(result, dict):
        raise TypeError(
            'Module result must be None, a score float, or a dict with a '
            f"'score' key — got {type(result).__name__}."
        )
    if module_name == 'module_a':
        # Transaction contexts, benchmark scopes and any other Module A dict
        # are incompatible with fusion; bare numbers above stay available for
        # legacy policy experiments only.
        _refuse_module_a_input(result)
    if module_name == 'module_b':
        return _standardize_url_result(result)
    return _standardize_message_result(result)


def _standardize_url_result(result: dict) -> dict:
    if 'score' not in result:
        raise ValueError(f"Module result dict must contain a 'score' key: {result}")
    number = _validate_finite_score(result['score'], what='module_b score')
    reasons = result.get('reasons', []) or []
    if not isinstance(reasons, list):
        raise ValueError('Module B reasons must be a list of strings')
    model_version = result.get('model_version') or result.get('ml_status') or 'unknown'
    return _assessed('module_b', number, [str(r) for r in reasons], model_version)


def _standardize_message_result(result: dict) -> dict:
    if result.get('text_assessed') is False:
        status = str(result.get('ml_status', ''))
        reason = 'assessment_failed' if 'inference failed' in status else 'model_unavailable'
        out = _unassessed('module_c', reason)
        out['model_version'] = str(result.get('model_version') or status or 'unknown')
        return out
    if 'score' not in result:
        raise ValueError(f"Module result dict must contain a 'score' key: {result}")
    # Text score only: an embedded-URL fold must never masquerade as text risk.
    # The URL component is fused once via Module B / embedded_url_score.
    if result.get('text_score') is not None:
        number = _validate_finite_score(result['text_score'], what='module_c score')
    else:
        number = _validate_finite_score(result['score'], what='module_c score')
    return _assessed('module_c', number, _message_evidence(result),
                     result.get('model_version') or result.get('ml_status') or 'unknown')


def _message_evidence(result: dict) -> list:
    """Deterministic, deduplicated Module C evidence (heuristics + rules)."""
    findings = []
    for item in result.get('heuristic_evidence', []) or []:
        if not isinstance(item, dict):
            continue
        category = item.get('category', 'signal')
        matched = str(item.get('matched', '')).strip()[:120]
        if matched and matched not in [f.rsplit(': ', 1)[-1] for f in findings]:
            findings.append(f'Heuristic [{category}]: {matched}')
    for item in result.get('rule_evidence', []) or []:
        if isinstance(item, dict) and item.get('phrase'):
            findings.append(f"Rule evidence: {item['phrase']}")
    embedded = result.get('embedded_url_score')
    try:
        embedded_value = float(embedded) if embedded is not None else 0.0
    except (TypeError, ValueError):
        embedded_value = 0.0
    if embedded_value >= 0.4:
        findings.append(f'Embedded URL risk score {embedded_value:.2f}')
    # Deduplicate while preserving first-seen order (deterministic).
    return list(dict.fromkeys(findings))


# -----------------------------------------------------------------------------
# Module A: SHAP on XGBoost features -> plain-language factors
# -----------------------------------------------------------------------------
def _build_module_a_features(transaction: dict, artifact: dict):
    """Use the exact training/serving transform for offline benchmark explanations."""
    from ml.features_module_a import transaction_features, validate_artifact
    validate_artifact(artifact)
    return transaction_features(transaction).iloc[0].to_dict()


def _describe_module_a_feature(name: str, value) -> str | None:
    if name == "amount":
        return f"benchmark amount ({float(value):,.2f} IEEE-CIS source units)"
    return None


def _shap_factors_module_a(module_a_result) -> tuple[list, str]:
    """Top SHAP contributors for Module A -> (factors, method note)."""
    transaction = None
    if isinstance(module_a_result, dict):
        transaction = module_a_result.get("transaction")
    if not isinstance(transaction, dict):
        return [], "no_transaction_context"
    try:
        from ml.predict_module_a import load_model
    except ImportError:
        return [], "module_a_loader_unavailable"
    try:
        artifact = load_model()
        model = artifact["model"]
        values = _build_module_a_features(transaction, artifact)
        feature_names = list(values.keys())
        import shap

        explainer = shap.TreeExplainer(model)
        sv = explainer.shap_values(pd.DataFrame([values])[feature_names])
        row = np.asarray(sv).reshape(-1)
        ranked = sorted(
            zip(feature_names, row, [values[f] for f in feature_names]),
            key=lambda t: float(t[1]),
            reverse=True,
        )
        factors = []
        for name, shap_val, feat_val in ranked:
            if float(shap_val) <= 0:
                continue  # only factors pushing TOWARD fraud
            phrase = _describe_module_a_feature(name, feat_val)
            if phrase and phrase not in factors:
                factors.append(phrase)
            if len(factors) >= 2:
                break
        return factors, "shap_tree_explainer"
    except Exception:
        # Failed attribution must not invent call/device/nighttime risk factors.
        return [], "attribution_unavailable"


# -----------------------------------------------------------------------------
# Module B: shorten rule reasons -> plain-language factors
# -----------------------------------------------------------------------------
def _shorten_url_reason(reason: str) -> str:
    r = reason.lower()
    if "raw ip" in r and "address" in r:
        return "link uses a raw IP address instead of a registered domain"
    if "localhost/private/internal" in r or "private/internal" in r:
        return "link targets a localhost/private/internal address"
    if "typosquatting" in r or "spoofing" in r:
        return "link mimics a known brand domain"
    if "look-alike" in r or "look-alike" in r:
        return "link shows look-alike domain indicators"
    if "shortener" in r:
        return "link hides its destination behind a URL shortener"
    if "punycode" in r or "internationalized" in r:
        return "link uses an internationalized (punycode) hostname"
    if "malformed hostname" in r:
        return "link hostname is malformed"
    if "unusual port" in r:
        return "link uses an unusual port"
    if "excessive subdomains" in r:
        return "link buries its domain under excessive subdomains"
    if "form" in r and ("login" in r or "credential" in r):
        return "destination page contains a login/credential form"
    if "high-risk top-level" in r:
        return "link uses a high-risk domain ending"
    if "redirect" in r:
        return "link redirects to a different site"
    if "suspicious path/query" in r or "suspicious encoded" in r:
        return "link path/query contains phishing patterns"
    if "entropy" in r:
        return "link looks randomly generated (high entropy)"
    if "insecure protocol" in r or "https" in r:
        return "link does not use an encrypted HTTPS connection"
    if "extremely long" in r:
        return "extremely long, likely obfuscated link"
    if "long" in r:
        return "unusually long link"
    if "'@'" in r or "hex-encoded" in r or "hyphen" in r:
        return "link contains obfuscation characters"
    short = reason.strip()
    return short if len(short) <= 90 else short[:87] + "..."


def _url_reason_severity(reason: str) -> int:
    """Lower = more incriminating (headline-worthy)."""
    r = reason.lower()
    if "raw ip" in r or "typosquatting" in r or "spoofing" in r:
        return 0
    if "localhost/private" in r or "private/internal" in r or "malformed hostname" in r or "shortener" in r:
        return 0
    if "login" in r or "credential" in r or "redirect" in r or "punycode" in r or "look-alike" in r:
        return 1
    if "high-risk top-level" in r or "'@'" in r or "hex-encoded" in r or "hyphen" in r or "unusual port" in r or "subdomains" in r or "entropy" in r or "suspicious" in r:
        return 2
    return 3


def _factors_module_b(module_b_result) -> list:
    if not isinstance(module_b_result, dict):
        return []
    reasons = [r for r in (module_b_result.get("reasons", []) or []) if isinstance(r, str)]
    reasons.sort(key=_url_reason_severity)  # most incriminating first (stable)
    factors = []
    for r in reasons:
        short = _shorten_url_reason(r)
        if short not in factors:
            factors.append(short)
        if len(factors) >= 2:
            break
    return factors


# -----------------------------------------------------------------------------
# Module C: signature phrase + (if ML) exact linear-SHAP token attribution
# -----------------------------------------------------------------------------
def _shap_tokens_module_c(text: str, signature: str, top_k: int = 3) -> tuple[list, str]:
    """Exact linear-SHAP (coef x TF-IDF) top tokens. ([tokens], method note)."""
    try:
        from ml.predict_module_c import _load_ml_model
        artifact = _load_ml_model()
        if artifact is None:
            return [], "no_ml_artifact"
        pipeline = artifact["pipeline"]
        tfidf = pipeline.named_steps["tfidf"]
        clf = pipeline.named_steps["clf"]
        classes = [str(c) for c in clf.classes_]
        target = signature if signature in classes else max(classes)
        row = tfidf.transform([text])
        coefs = np.asarray(clf.coef_[classes.index(target)]).ravel()
        contrib = row.multiply(coefs).tocoo()
        scored = sorted(zip(contrib.col, contrib.data), key=lambda t: float(t[1]), reverse=True)
        names = tfidf.get_feature_names_out()
        tokens = [str(names[c]) for c, v in scored if float(v) > 0][:top_k]
        # Drop sub-word char n-gram noise for word analyzers only; char
        # analyzers keep n-grams as-is (still informative for URLs).
        return tokens, "linear_shap_tokens"
    except Exception:
        return [], "token_attribution_failed"


def _factors_module_c(module_c_result) -> tuple[list, str]:
    if not isinstance(module_c_result, dict):
        return [], "no_module_c_detail"
    signature = str(module_c_result.get("signature", "none"))
    reasons = module_c_result.get("reasons", []) or []
    text = module_c_result.get("text")
    factors: list = []
    method = "keyword_reasons"
    if signature in _SIGNATURE_PHRASES:
        factors.append(_SIGNATURE_PHRASES[signature])
        if isinstance(text, str) and text.strip():
            tokens, method = _shap_tokens_module_c(text, signature)
            if tokens:
                quoted = ", ".join(f"'{t}'" for t in tokens)
                factors.append(f"most indicative wording: {quoted}")
        else:
            # Fall back to the matched keyword evidence already in reasons.
            quoted = []
            for r in reasons:
                m = re.search(r"pattern: '([^']+)'", str(r))
                if m and m.group(1) not in quoted:
                    quoted.append(m.group(1))
                if len(quoted) >= 3:
                    break
            if quoted:
                factors.append("matched phrases: " + ", ".join(f"'{q}'" for q in quoted))
    elif any("flagged by Module B" in str(reason) for reason in reasons):
        # Risky without a behavioral signature (e.g. via embedded-URL folding).
        factors.append("suspicious link embedded in the message")
    return factors, method


# -----------------------------------------------------------------------------
# Unified scoring (central TrueIntent fusion layer)
# -----------------------------------------------------------------------------
def _validate_active_call(active_call):
    if active_call is not None and not isinstance(active_call, bool):
        raise ValueError('active_call must be boolean or unknown (None)')
    return active_call


def _embedded_url_score(module_c_result) -> float:
    """Embedded Module B evidence inside a Module C dict (0 when absent)."""
    if not isinstance(module_c_result, dict):
        return 0.0
    try:
        value = float(module_c_result.get('embedded_url_score') or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value) or not 0 <= value <= 1:
        return 0.0
    return value


def compute_unified_score(module_a_result=None, module_b_result=None,
                           module_c_result=None, *, active_call=None) -> dict:
    """
    Fuse Module B (URL) and Module C (message) evidence into one verdict.

    Parameters accept None (module skipped), a score float, a legacy module
    result dict, or a standardized module-result dict. Module C dictionaries
    may include analyzed "text" for token attribution. Any assessment-like
    Module A input (transaction context, benchmark scope, standardized
    ``module_a`` assessment) is refused: Module A is a source-unit benchmark,
    incompatible with fusion. Bare-number Module A inputs remain available
    for legacy policy experiments only.

    Returns the overall risk score with risk level, analyzed / contributing /
    unavailable modules, evidence, warnings, fusion version, limitations and
    a recommended action (plus legacy ``tier``/``explanation``/``details``
    keys). Raises ValueError if no module ran, TypeError/ValueError on
    malformed inputs. Deterministic for identical inputs.
    """
    _validate_active_call(active_call)
    std_a = standardize_module_result('module_a', module_a_result)
    std_b = standardize_module_result('module_b', module_b_result)
    std_c = standardize_module_result('module_c', module_c_result)

    score_a = std_a['score']
    score_b = std_b['score']
    # Text score only: shared URL evidence is fused once via Module B below.
    score_c = std_c['score']
    embedded = _embedded_url_score(module_c_result)

    contribs = []
    if score_a is not None:
        contribs.append(("Module A (transaction\u2013call)", score_a, WEIGHT_MODULE_A))
    if score_b is not None:
        contribs.append(("Module B (URL safety)", score_b, WEIGHT_MODULE_B))
    if score_c is not None:
        sig = None
        if isinstance(module_c_result, dict):
            sig = module_c_result.get("signature")
        label = "Module C (message analysis" + (f", signature={sig})" if sig else ")")
        contribs.append((label, score_c, WEIGHT_MODULE_C))

    if not contribs:
        raise ValueError(
            "No module results provided — at least one of module_a_result, "
            "module_b_result, module_c_result is required. Refusing to "
            "return a verdict with no evidence."
        )

    artifact = _load_learned_model()
    if artifact is not None and artifact.get('format_version') == 2:
        legacy = _interaction_result(artifact, module_a_result, module_b_result, module_c_result, active_call)
        return _finalize_result(
            unified=legacy['score'], explanation=legacy['explanation'],
            details=legacy['details'], std_a=std_a, std_b=std_b, std_c=std_c,
            active_call=active_call, embedded=_embedded_url_score(module_c_result),
            method_note='learned interaction policy',
            learned=True,
        )
    names = ["module_a", "module_b", "module_c"]
    # URL evidence counted once: an embedded Module B finding inside the message
    # joins (never adds to) the standalone URL score via max.
    b_effective = score_b
    if embedded > 0 and (b_effective is None or embedded > b_effective):
        b_effective = embedded
    fused = {'module_a': score_a, 'module_b': b_effective, 'module_c': score_c}
    contributions = {}
    total_w = sum(
        WEIGHT_MODULE_A if name == 'module_a'
        else WEIGHT_MODULE_B if name == 'module_b'
        else WEIGHT_MODULE_C
        for name, value in (('module_a', score_a), ('module_b', b_effective), ('module_c', score_c))
        if value is not None
    )
    unified = round(min(1.0, sum(
        fused[name] * (WEIGHT_MODULE_A if name == 'module_a'
                       else WEIGHT_MODULE_B if name == 'module_b'
                       else WEIGHT_MODULE_C)
        for name in names if fused[name] is not None
    ) / total_w), 4)
    weights = dict(module_a=WEIGHT_MODULE_A, module_b=WEIGHT_MODULE_B, module_c=WEIGHT_MODULE_C)
    fusion_method = "fixed_weights_missing_model"
    intercept = None
    ranked_contribs = contribs
    if artifact is not None:
        # Legacy three-score learned artifact (research/test fixtures only).
        supplied = [score_a, score_b, score_c]
        model = artifact["model"]
        values = [0.0 if v is None else v for v in supplied]
        frame = pd.DataFrame([values], columns=artifact["feature_cols"])
        unified = round(float(model.predict_proba(frame)[0, 1]), 4)
        weights = dict(zip(names, map(float, model.coef_[0])))
        intercept = float(model.intercept_[0])
        # Exact linear SHAP for a point background of all-zero scores, in log-odds.
        # Missing modules equal that reference and receive zero contribution.
        contributions = {name: weights[name] * value for name, value in zip(names, values)}
        fusion_method = "logistic_synthetic_policy"
        present_names = [name for name, value in zip(names, supplied) if value is not None]
        ranked_contribs = [(label, score, contributions[name])
                          for (label, score, _), name in zip(contribs, present_names)]
    tier = _tier_for(unified)

    # --- headline factors: one per risky contributing module, max 3 ---
    shap_methods: dict = {}
    factor_groups: list = []  # (module_weight, [factors])
    for label, s, w in ranked_contribs:
        if (artifact is None and s < RISKY_MODULE_SCORE) or (artifact is not None and w <= 0):
            continue
        if label.startswith("Module A"):
            f, m = _shap_factors_module_a(module_a_result)
            shap_methods["module_a"] = m
            if not f:
                f = [f"transaction risk score {s:.2f}"]
            factor_groups.append((w, f))
        elif label.startswith("Module B"):
            f = _factors_module_b(module_b_result)
            if not f:
                f = [f"link risk score {s:.2f}"]
            factor_groups.append((w, f))
        else:
            f, m = _factors_module_c(module_c_result)
            shap_methods["module_c"] = m
            if not f:
                f = [f"message risk score {s:.2f}"]
            factor_groups.append((w, f))

    factor_groups.sort(key=lambda t: t[0], reverse=True)
    # Round-robin across modules so every risky contributing module is
    # represented in the headline (rather than one module crowding out the
    # others), capped at 3 factors total.
    headline: list = []
    max_depth = max([len(f) for _, f in factor_groups] or [0])
    for i in range(max_depth):
        for _, f in factor_groups:
            if i < len(f) and f[i] not in headline:
                headline.append(f[i])
            if len(headline) >= 3:
                break
        if len(headline) >= 3:
            break

    # --- explanation (always names contributing vs skipped modules) ---
    ran = [label for label, _, _ in contribs]
    skipped = []
    if score_a is None:
        skipped.append("Module A (no transaction submitted)")
    if score_b is None:
        skipped.append("Module B (no URL submitted)")
    if score_c is None:
        skipped.append("Module C (no message submitted)")

    parts = []
    if tier in ("High", "Critical"):
        if headline:
            parts.append(
                f"Flagged as {tier} risk because: " + "; ".join(headline) + "."
            )
        else:
            parts.append(
                f"Flagged as {tier} risk (unified risk score {unified:.2f})."
            )
    else:
        if headline:
            parts.append(
                f"Assessed as {tier} risk (unified risk score {unified:.2f}): "
                + "; ".join(headline) + "."
            )
        else:
            parts.append(
                f"Assessed as {tier} risk (unified risk score {unified:.2f}): "
                "no strong risk signals from the modules that ran."
            )
    parts.append("Modules contributing: " + ", ".join(ran) + ".")
    parts.append(
        "Modules skipped: " + (", ".join(skipped) + "." if skipped else "none.")
    )
    explanation = " ".join(parts)

    details = {
        "weights": weights,
        "weight_semantics": "logistic coefficients (not normalized shares)" if artifact is not None else "fixed weights",
        "scoring_method": fusion_method,
        "intercept": intercept,
        "module_contributions_log_odds": contributions,
        "fusion_shap_method": "linear_zero_reference_log_odds" if artifact is not None else "not_applicable",
        "model_caveat": "Synthetic joint labels; not calibrated real-world fraud probability" if artifact is not None else "Learned model file missing",
        "renormalized_over": ran if artifact is None else [],
        "module_scores": {
            "module_a": score_a, "module_b": score_b, "module_c": score_c,
        },
        "shap_methods": shap_methods,
        "fusion_version": FUSION_VERSION,
        "risk_level": tier,
    }
    return _finalize_result(
        unified=unified, explanation=explanation, details=details,
        std_a=std_a, std_b=std_b, std_c=std_c, active_call=active_call,
        embedded=embedded, method_note=fusion_method, learned=artifact is not None,
    )


def _build_evidence(std_b: dict, std_c: dict) -> list:
    """Deterministic fused evidence: Module B findings then Module C findings."""
    evidence = []
    if std_b.get('assessed'):
        for finding in std_b.get('evidence', []):
            evidence.append({'module': 'module_b', 'finding': str(finding)})
    if std_c.get('assessed'):
        for finding in std_c.get('evidence', []):
            evidence.append({'module': 'module_c', 'finding': str(finding)})
    return evidence


def _build_warnings(std_a: dict, std_b: dict, std_c: dict, *,
                    active_call, embedded: float, learned: bool) -> list:
    warnings = []
    missing = [m['module'] for m in (std_b, std_c) if not m.get('assessed')]
    if missing:
        warnings.append(
            'Partial analysis: '
            + ', '.join(missing)
            + ' did not provide an assessment; the overall risk score reflects only '
            + 'the evidence that ran and is a lower bound on risk.'
        )
    warnings.append(
        'Module A is a source-unit benchmark and is not fused; '
        'submit URL and/or message evidence for combined analysis.'
    )
    if embedded > 0:
        warnings.append(
            'URL evidence shared between the message and the URL channel '
            'was counted once (maximum).'
        )
    if active_call is True:
        warnings.append(
            'An active call was user-reported during this analysis; '
            'call status is unverified and does not change the risk score.'
        )
    if learned:
        warnings.append(
            'Learned synthetic-policy fusion used; the overall score is an '
            'uncalibrated risk score, not a calibrated fraud probability.'
        )
    else:
        warnings.append(
            'Transparent weighted risk-score fusion used (renormalized over '
            'assessed modules); the overall score is uncalibrated.'
        )
    return warnings


def _finalize_result(*, unified: float, explanation: str, details: dict,
                     std_a: dict, std_b: dict, std_c: dict,
                     active_call, embedded: float, method_note: str,
                     learned: bool) -> dict:
    """Attach the standard fusion contract to any scoring path's output."""
    tier = risk_level_for(unified)
    standards = {'module_a': std_a, 'module_b': std_b, 'module_c': std_c}
    analyzed = [name for name, std in standards.items() if std.get('assessed')]
    contributing = list(analyzed)  # every assessed module feeds the weights
    unavailable = [name for name, std in standards.items() if not std.get('assessed')]
    details = dict(details)
    details['fusion_version'] = FUSION_VERSION
    details['risk_level'] = tier
    details['scoring_note'] = method_note
    partial = any(not standards[m].get('assessed') for m in ('module_b', 'module_c'))
    warnings = _build_warnings(std_a, std_b, std_c, active_call=active_call,
                               embedded=embedded, learned=learned)
    return {
        'tier': tier,  # legacy alias of risk_level (kept for compatibility)
        'risk_level': tier,
        'score': unified,  # overall uncalibrated risk score, never a fraud probability
        'explanation': explanation,
        'analyzed_modules': analyzed,
        'contributing_modules': contributing,
        'unavailable_modules': unavailable,
        'evidence': _build_evidence(std_b, std_c),
        'warnings': warnings,
        'fusion_version': FUSION_VERSION,
        'limitations': list(LIMITATIONS),
        'recommended_action': recommend_action(tier, partial=partial),
        'details': details,
        'modules': standards,
    }


def fuse_modules(module_b_result=None, module_c_result=None,
                 module_a_result=None, *, active_call=None) -> dict:
    """Named fusion entry point: fuse Module B/C evidence (Module A refused).

    Argument order puts the supported channels first; see
    :func:`compute_unified_score` for semantics.
    """
    return compute_unified_score(module_a_result, module_b_result,
                                 module_c_result, active_call=active_call)


def _interaction_result(artifact, a_result, b_result, c_result, active_call):
    FEATURES = _FEATURES_D
    def read(value):
        return _score_d(value['score'] if isinstance(value, dict) else value)
    a, b, c = read(a_result), read(b_result), read(c_result)
    credential, authority = 0., 0.
    evidence_note = 'C text-only evidence unavailable; legacy combined C score may include a URL.'
    if isinstance(c_result, dict):
        if c_result.get('text_assessed') is False:
            # Unassessed text stays missing (never fused as zero or as message
            # evidence); an embedded URL finding still counts once via Module B.
            c = None
            evidence_note = ('Module C text was not assessed; fused from URL evidence only. '
                             'URL evidence counted once using max.')
        probabilities = c_result.get('intent_probabilities') or {}
        if c_result.get('text_assessed') is not False and 'text_score' in c_result:
            c = c_result['text_score']
            evidence_note = 'C text and embedded URL scores separated; URL evidence counted once using max.'
        elif 'benign' in probabilities:
            c = 1 - float(probabilities['benign'])
            evidence_note = 'C text score reconstructed from P(benign); legacy URL decomposition may be incomplete.'
        embedded = c_result.get('embedded_url_score')
        if embedded is not None and float(embedded) > 0:
            b = max(b or 0., float(embedded))
        credential = c_result.get('credential_request', probabilities.get('credential_theft', 0.))
        authority = c_result.get('authority_fear', min(1., probabilities.get('authority_fear', 0.) + probabilities.get('digital_arrest', 0.)))
    row = feature_row(a, b, c, active_call, credential, authority)
    frame = pd.DataFrame([row], columns=FEATURES)
    model = artifact['model']
    unified = round(float(model.predict_proba(frame)[0, 1]), 4)
    contributions = {name: float(coef) * row[name] for name, coef in zip(FEATURES, model.coef_[0])}
    descriptions = {
        'module_a_score': f'transaction risk score {a or 0:.2f}',
        'module_b_score': f'link risk score {b or 0:.2f}',
        'module_c_score': f'message text risk score {c or 0:.2f}',
        'message_transaction': 'suspicious message and unusual transaction',
        'call_transaction': 'reported active call and unusual transaction',
        'url_credentials': 'URL risk combined with a model-indicated credential request',
        'authority_transaction': 'model-indicated authority/fear language and unusual transaction',
    }
    factors = [descriptions[name] for name in sorted(descriptions, key=lambda n: contributions[n], reverse=True)
               if contributions[name] > 0 and row[name] > .1][:3]
    supplied = [a, b, c]
    ran = [f'Module {name.upper()}' for name, value in zip('abc', supplied) if value is not None]
    skipped = [f'Module {name.upper()} (no {kind} submitted)' for name, kind, value
               in zip('abc', ('transaction', 'URL', 'message'), supplied) if value is None]
    tier = _tier_for(unified)
    explanation = (f'{tier} synthetic-policy risk index ({unified:.2f}). '
                   + ('Factors: ' + '; '.join(factors) + '. ' if factors else '')
                   + 'Modules contributing: ' + ', '.join(ran) + '. Modules skipped: '
                   + (', '.join(skipped) if skipped else 'none') + '. '
                   + 'This index is not a calibrated real-world fraud probability.')
    return dict(tier=tier, score=unified, explanation=explanation, details=dict(
        scoring_method='logistic_interactions_synthetic_policy',
        model_caveat='Synthetic labels and detector scores; no real incident validation. Module A remains benchmark-only.',
        module_scores=dict(module_a=a, module_b=b, module_c=c),
        availability={name: value is not None for name, value in zip(('module_a', 'module_b', 'module_c'), supplied)},
        active_call=active_call, call_status_source='user-reported' if active_call is not None else 'unknown',
        feature_values=row, feature_contributions_log_odds=contributions,
        intercept=float(model.intercept_[0]), fusion_shap_method='linear_zero_reference_log_odds',
        contribution_caveat='Exact coefficient products for engineered features; interactions are not independent causal effects.',
        channel_evidence_note=evidence_note,
        weights=dict(zip(FEATURES, map(float, model.coef_[0]))),
        weight_semantics='logistic coefficients, not normalized importance shares',
    ))


if __name__ == "__main__":
    print(compute_unified_score(None, {"score": 0.6, "reasons": []}, None))
