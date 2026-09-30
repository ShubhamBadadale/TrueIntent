"""
Module D — Unified Risk Scoring & Explanation Layer (core differentiator).

Combines Module A (transaction+call), Module B (URL safety) and Module C
(message/screenshot analysis) into one explainable verdict:

    compute_unified_score(module_a_result, module_b_result, module_c_result)
        -> {tier, score, explanation, details}

Design notes
------------
* Transaction-context fusion is disabled after Module A's source-unit benchmark
  correction. Numeric scores remain supported for policy experiments; the A SHAP
  helper is available only for offline benchmark explanation.
* Version 2 uses availability flags and score/tactic/call interactions. C text
  and URL evidence are separated when metadata is available. Old three-score
  artifacts remain readable. Models learn synthetic policy labels. Fixed weighted sum
  ONLY when the artifact is missing (warning logged), renormalized over modules
  that actually ran. Original fallback weights are A=.45, B=.25, C=.30.
* SHAP: Module A uses shap.TreeExplainer on the XGBoost model; Module C (only
  when an ML artifact exists AND the caller passes the analyzed `text`) uses
  exact linear-SHAP token attribution (coef x TF-IDF vs. a zero baseline —
  mathematically equal to SHAP values for a linear model). Everything
  degrades gracefully to rule/keyword reasons when SHAP is unavailable.
* Skipped modules (None) are ALWAYS reported as skipped — never implied to
  have run. All-None raises ValueError instead of returning a false verdict.
"""

import os
import re
import logging
import math
import joblib
import numpy as np
import pandas as pd

_LOGGER = logging.getLogger(__name__)
_D_CACHE = None

def _get_model_path():
    return os.path.join(os.path.dirname(__file__), "models", "module_d.pkl")

def _load_learned_model():
    global _D_CACHE
    path = _get_model_path()
    if not os.path.exists(path):
        _LOGGER.warning("Module D learned model missing; using fixed-weight fallback: %s", path)
        return None
    stamp = (path, os.stat(path).st_mtime_ns, os.stat(path).st_size)
    if _D_CACHE is None or _D_CACHE[0] != stamp:
        artifact = joblib.load(path)  # Corruption/incompatibility must NOT silently fall back.
        if artifact.get('format_version') == 2:
            from ml.features_module_d import FEATURES
            model = artifact.get('model')
            if (artifact.get('feature_cols') != FEATURES or model is None
                    or list(model.classes_) != [0, 1] or model.coef_.shape != (1, len(FEATURES))
                    or not np.isfinite(model.coef_).all() or not np.isfinite(model.intercept_).all()):
                raise ValueError('Incompatible Module D interaction artifact')
            _D_CACHE = (stamp, artifact)
            return artifact
        expected = ["module_a_score", "module_b_score", "module_c_score"]
        if artifact.get("feature_cols") != expected or list(artifact["model"].classes_) != [0, 1]:
            raise ValueError("Incompatible Module D model artifact")
        if (not np.isfinite(artifact["model"].coef_).all()
                or not np.isfinite(artifact["model"].intercept_).all()
                or artifact["model"].coef_.shape != (1, 3)):
            raise ValueError("Non-finite Module D coefficients")
        _D_CACHE = (stamp, artifact)
    return _D_CACHE[1]

# -----------------------------------------------------------------------------
# NAMED WEIGHT CONSTANTS (documented, tunable — not a black box)
# -----------------------------------------------------------------------------
WEIGHT_MODULE_A = 0.45  # transaction + active-call correlation (core thesis)
WEIGHT_MODULE_C = 0.30  # message psychology / behavioral signature
WEIGHT_MODULE_B = 0.25  # URL safety (narrowest; often already folded into C)

# -----------------------------------------------------------------------------
# NAMED TIER THRESHOLDS (unified score -> tier)
# -----------------------------------------------------------------------------
TIER_LOW_MAX = 0.25
TIER_MEDIUM_MAX = 0.50
TIER_HIGH_MAX = 0.75  # >= this -> Critical

VALID_TIERS = ("Low", "Medium", "High", "Critical")

# A module scoring at/above this counts as "risky" (headline factor + wording).
RISKY_MODULE_SCORE = 0.40

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
    if score < TIER_LOW_MAX:
        return "Low"
    if score < TIER_MEDIUM_MAX:
        return "Medium"
    if score < TIER_HIGH_MAX:
        return "High"
    return "Critical"


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
        try:
            from predict_module_a import load_model
        except ImportError:
            return [], "module_a_loader_unavailable"
    try:
        artifact = load_model()
        model = artifact["model"]
        values = _build_module_a_features(transaction, artifact)
        feature_names = list(values.keys())
        import pandas as pd

        X = pd.DataFrame([values])[feature_names]
        import shap

        explainer = shap.TreeExplainer(model)
        sv = explainer.shap_values(X)
        import numpy as np

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
    if "raw ip address" in r:
        return "link uses a raw IP address instead of a registered domain"
    if "typosquatting" in r or "spoofing" in r:
        return "link mimics a known brand domain"
    if "form" in r and ("login" in r or "credential" in r):
        return "destination page contains a login/credential form"
    if "high-risk top-level" in r:
        return "link uses a high-risk domain ending"
    if "redirect" in r:
        return "link redirects to a different site"
    if "insecure protocol" in r or "https" in r:
        return "link does not use an encrypted HTTPS connection"
    if "long" in r:
        return "unusually long link"
    if "'@'" in r or "hex-encoded" in r or "hyphen" in r:
        return "link contains obfuscation characters"
    short = reason.strip()
    return short if len(short) <= 90 else short[:87] + "..."


def _url_reason_severity(reason: str) -> int:
    """Lower = more incriminating (headline-worthy)."""
    r = reason.lower()
    if "raw ip address" in r or "typosquatting" in r or "spoofing" in r:
        return 0
    if "login" in r or "credential" in r or "redirect" in r:
        return 1
    if "high-risk top-level" in r or "'@'" in r or "hex-encoded" in r or "hyphen" in r:
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
        try:
            from ml.predict_module_c import _load_ml_model
        except ImportError:
            from predict_module_c import _load_ml_model
        artifact = _load_ml_model()
        if artifact is None:
            return [], "no_ml_artifact"
        pipeline = artifact["pipeline"]
        tfidf = pipeline.named_steps["tfidf"]
        clf = pipeline.named_steps["clf"]
        classes = [str(c) for c in clf.classes_]
        target = signature if signature in classes else max(classes)
        row = tfidf.transform([text])
        import numpy as np

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
# Unified scoring
# -----------------------------------------------------------------------------
def compute_unified_score(module_a_result=None, module_b_result=None,
                           module_c_result=None, *, active_call=None) -> dict:
    """
    Combine per-module risk scores into one tier + plain-language explanation.

    Parameters accept None (module skipped), a score float, or the module's
    result dict. Transaction-context dictionaries are refused: Module A's new
    benchmark must not feed the old transaction policy. Module C dictionaries
    may include analyzed "text" for token attribution.

    Returns {tier, score, explanation, details}. Raises ValueError if no
    module ran, TypeError/ValueError on malformed inputs.
    """
    if isinstance(module_a_result, dict) and (isinstance(module_a_result.get("transaction"), dict)
                                             or module_a_result.get('analysis_scope') == 'ieee_cis_amount_only_benchmark'):
        raise ValueError(
            "Transaction fusion is disabled: Module A is a source-unit benchmark, "
            "incompatible with the existing combined policy."
        )
    score_a = _extract_score(module_a_result)
    score_b = _extract_score(module_b_result)
    score_c = _extract_score(module_c_result)

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
        return _interaction_result(artifact, module_a_result, module_b_result, module_c_result, active_call)
    names = ["module_a", "module_b", "module_c"]
    supplied = [score_a, score_b, score_c]
    contributions = {}
    if artifact is None:
        total_w = sum(w for _, _, w in contribs)
        unified = round(min(1.0, sum(s * w for _, s, w in contribs) / total_w), 4)
        weights = dict(module_a=WEIGHT_MODULE_A, module_b=WEIGHT_MODULE_B, module_c=WEIGHT_MODULE_C)
        fusion_method = "fixed_weights_missing_model"
        intercept = None
        ranked_contribs = contribs
    else:
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
                f"Flagged as {tier} risk (unified score {unified:.2f})."
            )
    else:
        if headline:
            parts.append(
                f"Assessed as {tier} risk (unified score {unified:.2f}): "
                + "; ".join(headline) + "."
            )
        else:
            parts.append(
                f"Assessed as {tier} risk (unified score {unified:.2f}): "
                "no strong risk signals from the modules that ran."
            )
    parts.append("Modules contributing: " + ", ".join(ran) + ".")
    parts.append(
        "Modules skipped: " + (", ".join(skipped) + "." if skipped else "none.")
    )
    explanation = " ".join(parts)

    return {
        "tier": tier,
        "score": unified,
        "explanation": explanation,
        "details": {
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
        },
    }


def _interaction_result(artifact, a_result, b_result, c_result, active_call):
    from ml.features_module_d import FEATURES, feature_row, score
    def read(value):
        return score(value['score'] if isinstance(value, dict) else value)
    a, b, c = read(a_result), read(b_result), read(c_result)
    credential, authority = 0., 0.
    evidence_note = 'C text-only evidence unavailable; legacy combined C score may include a URL.'
    if isinstance(c_result, dict):
        if c_result.get('text_assessed') is False:
            raise ValueError('Module C text was not assessed')
        probabilities = c_result.get('intent_probabilities') or {}
        if 'text_score' in c_result:
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
