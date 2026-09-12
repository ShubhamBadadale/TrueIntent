"""
Module D — Unified Risk Scoring & Explanation Layer (core differentiator).

Combines Module A (transaction+call), Module B (URL safety) and Module C
(message/screenshot analysis) into one explainable verdict:

    compute_unified_score(module_a_result, module_b_result, module_c_result)
        -> {tier, score, explanation, details}

Design notes
------------
* Weighted sum with named constants below (renormalized over the modules
  that actually ran, so a single-module check still spans the full 0-1 range).
  Rationale: Module A carries the highest weight because transaction+call
  correlation is the project's core thesis signal; Module C next (psychological
  manipulation language); Module B lowest (narrowest signal, and often already
  folded into Module C via URL folding).
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
        return max(0.0, min(1.0, float(result)))
    if isinstance(result, dict):
        if "score" not in result:
            raise ValueError(f"Module result dict must contain a 'score' key: {result}")
        return max(0.0, min(1.0, float(result["score"])))
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
    """Mirror of predict_module_a's feature engineering (kept in sync by test)."""
    import pandas as pd

    device_counts = artifact.get("device_counts", {})
    amount = float(transaction.get("amount", 0.0))
    is_active_call = 1 if bool(transaction.get("is_active_call", False)) else 0
    velocity = int(transaction.get("transaction_velocity", 1))

    if "is_odd_hour" in transaction:
        is_odd_hour = 1 if bool(transaction["is_odd_hour"]) else 0
        hour_of_day = int(transaction.get("hour_of_day", 12))
    elif "timestamp" in transaction and isinstance(transaction["timestamp"], str):
        try:
            hour_of_day = int(pd.to_datetime(transaction["timestamp"]).hour)
        except Exception:
            hour_of_day = 12
        is_odd_hour = 1 if (hour_of_day < 6 or hour_of_day >= 23) else 0
    elif "hour_of_day" in transaction:
        hour_of_day = int(transaction["hour_of_day"])
        is_odd_hour = 1 if (hour_of_day < 6 or hour_of_day >= 23) else 0
    else:
        hour_of_day = 12
        is_odd_hour = 0

    if "is_new_device" in transaction:
        is_new_device = 1 if bool(transaction["is_new_device"]) else 0
    elif "device_id" in transaction:
        dev_id = str(transaction["device_id"])
        is_new_device = 1 if device_counts.get(dev_id, 0) <= 2 else 0
    else:
        is_new_device = 0

    feature_names = artifact.get(
        "feature_cols",
        ["amount", "hour_of_day", "is_odd_hour", "is_new_device",
         "is_active_call", "transaction_velocity"],
    )
    row = {
        "amount": amount,
        "hour_of_day": hour_of_day,
        "is_odd_hour": is_odd_hour,
        "is_new_device": is_new_device,
        "is_active_call": is_active_call,
        "transaction_velocity": velocity,
    }
    values = {k: row[k] for k in feature_names}
    return values


def _describe_module_a_feature(name: str, value) -> str | None:
    """Value-aware plain-language template per feature. None if not statable."""
    if name == "is_active_call":
        return "active call detected during transfer" if int(value) == 1 else None
    if name == "amount":
        try:
            return f"unusually large transfer amount (\u20b9{float(value):,.0f})"
        except (TypeError, ValueError):
            return "unusually large transfer amount"
    if name == "transaction_velocity":
        return f"rapid burst of {int(value)} transfers in the last hour"
    if name == "is_new_device":
        return "transfer from a new or unrecognised device" if int(value) == 1 else None
    if name == "is_odd_hour":
        return "transfer at an unusual late-night hour" if int(value) == 1 else None
    if name == "hour_of_day":
        return f"transfer at an unusual hour ({int(value)}:00)"
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
        # Graceful fallback: value-aware heuristics (honestly labeled).
        try:
            values = _build_module_a_features(transaction, {"device_counts": {}})
        except Exception:
            return [], "heuristic_failed"
        factors = []
        for name in ("is_active_call", "transaction_velocity", "amount",
                     "is_new_device", "is_odd_hour"):
            phrase = _describe_module_a_feature(name, values.get(name))
            if phrase and phrase not in factors:
                # Only state binary flags when active; amount/velocity only
                # when notably elevated (avoid stating benign values as risk).
                if name == "amount" and float(values.get("amount", 0)) < 15000:
                    continue
                if name == "transaction_velocity" and int(values.get("transaction_velocity", 1)) < 3:
                    continue
                factors.append(phrase)
            if len(factors) >= 2:
                break
        return factors, "heuristic_fallback"


# -----------------------------------------------------------------------------
# Module B: shorten rule reasons -> plain-language factors
# -----------------------------------------------------------------------------
def _shorten_url_reason(reason: str) -> str:
    r = reason.lower()
    if "raw ip address" in r:
        return "link uses a raw IP address instead of a registered domain"
    if "typosquatting" in r or "spoofing" in r:
        return "link mimics a known brand domain"
    if "login" in r or "credential" in r:
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
    elif float(module_c_result.get("score", 0.0)) >= RISKY_MODULE_SCORE:
        # Risky without a behavioral signature (e.g. via embedded-URL folding).
        factors.append("suspicious link embedded in the message")
    return factors, method


# -----------------------------------------------------------------------------
# Unified scoring
# -----------------------------------------------------------------------------
def compute_unified_score(module_a_result=None, module_b_result=None,
                           module_c_result=None) -> dict:
    """
    Combine per-module risk scores into one tier + plain-language explanation.

    Parameters accept None (module skipped), a score float, or the module's
    result dict (optionally carrying context: Module A dict may include the
    raw "transaction" dict for SHAP; Module C dict may include the analyzed
    "text" for token attribution).

    Returns {tier, score, explanation, details}. Raises ValueError if no
    module ran, TypeError/ValueError on malformed inputs.
    """
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

    total_w = sum(w for _, _, w in contribs)
    unified = round(min(1.0, sum(s * w for _, s, w in contribs) / total_w), 4)
    tier = _tier_for(unified)

    # --- headline factors: one per risky contributing module, max 3 ---
    shap_methods: dict = {}
    factor_groups: list = []  # (module_weight, [factors])
    for label, s, w in contribs:
        if s < RISKY_MODULE_SCORE:
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
            "weights": {"module_a": WEIGHT_MODULE_A, "module_b": WEIGHT_MODULE_B,
                        "module_c": WEIGHT_MODULE_C},
            "renormalized_over": ran,
            "module_scores": {
                "module_a": score_a, "module_b": score_b, "module_c": score_c,
            },
            "shap_methods": shap_methods,
        },
    }


if __name__ == "__main__":
    low = compute_unified_score(
        {"score": 0.01, "transaction": {
            "amount": 500.0, "timestamp": "2026-09-12T14:00:00Z",
            "device_id": "dev_0001", "is_active_call": False,
            "transaction_velocity": 1}},
        {"score": 0.0, "reasons": []},
        {"score": 0.0, "signature": "none", "reasons": [],
         "text": "Hey, lunch tomorrow?"},
    )
    print(low["tier"], low["score"])
    print(low["explanation"], "\n")
    high = compute_unified_score(
        {"score": 0.99, "transaction": {
            "amount": 80000.0, "timestamp": "2026-09-12T02:30:00Z",
            "device_id": "dev_new_9999", "is_active_call": True,
            "transaction_velocity": 7}},
        {"score": 0.75, "reasons": [
            "Host is a raw IP address (1.2.3.4) rather than a registered domain name",
            "Potential typosquatting / brand spoofing targeting 'hdfc'"]},
        {"score": 0.9, "signature": "fear_authority",
         "reasons": ["Matched fear/authority pattern: 'under investigation'"],
         "text": "You are under investigation. Stay on the line."},
    )
    print(high["tier"], high["score"])
    print(high["explanation"])
