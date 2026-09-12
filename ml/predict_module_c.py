"""
Module C — Message/Scam Analyzer (text-analysis half).

MVP: rule/keyword-pattern baseline covering both behavioral signatures.
PLACEHOLDER — to be replaced/augmented by a TF-IDF + Logistic Regression
classifier once the real Module C dataset is available
(see `ml/train_module_c.py`, `data/raw/sms_spam_collection.csv`,
`data/raw/signature_examples.csv`).

Any URLs found in the message are extracted and passed to Module B's
`check_url()` and folded into the final score/reasons.
"""

import os
import re

import joblib

try:
    from ml.predict_module_b import check_url
except ImportError:  # fallback for direct script execution
    from predict_module_b import check_url

# -----------------------------------------------------------------------------
# PLACEHOLDER keyword baselines (case-insensitive substring match).
# Clearly marked as a substitute for the trained classifier.
# -----------------------------------------------------------------------------
FEAR_AUTHORITY_KEYWORDS = [
    "under investigation",
    "stay on the line",
    "stay on the call",
    "do not disconnect",
    "do not hang up",
    "digital arrest",
    "arrest warrant",
    "money laundering",
    "you are under",
    "cbi officer",
    "police officer",
    "court order",
    "legal action will be taken",
    "verify immediately or you will be arrested",
    "share your otp to verify",
    "keep this confidential from your family",
]

GREED_OPPORTUNITY_KEYWORDS = [
    "guaranteed returns",
    "limited time",
    "double your money",
    "risk-free profit",
    "risk free profit",
    "assured returns",
    "100% profit",
    "join our trading group",
    "exclusive stock tip",
    "invest now before",
    "hurry invest",
    "zero risk high return",
]

VALID_SIGNATURES = ("fear_authority", "greed_opportunity", "none")

_ML_MODEL_ARTIFACT = None


def _get_model_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, ".."))
    return os.path.join(project_root, "ml", "models", "module_c.pkl")


def _load_ml_model(model_path: str = None):
    """Load Module C ML artifact if trained, else None (rules-only mode)."""
    global _ML_MODEL_ARTIFACT
    if model_path is None:
        model_path = _get_model_path()

    if _ML_MODEL_ARTIFACT is None or _ML_MODEL_ARTIFACT.get("_path") != model_path:
        if os.path.exists(model_path):
            try:
                artifact = joblib.load(model_path)
                artifact["_path"] = model_path
                _ML_MODEL_ARTIFACT = artifact
            except Exception:
                _ML_MODEL_ARTIFACT = None
        else:
            _ML_MODEL_ARTIFACT = None
    return _ML_MODEL_ARTIFACT


def extract_urls(text: str) -> list:
    """Extract http(s):// and www. URLs from message text."""
    if not text:
        return []
    pattern = r"(https?://[^\s\"'<>]+|www\.[^\s\"'<>]+)"
    found = re.findall(pattern, text)
    # Strip trailing punctuation that is not part of the URL.
    return [u.rstrip(".,;:!?)'\"") for u in found]


def _match_keywords(text_lower: str, keywords: list) -> list:
    return [kw for kw in keywords if kw.lower() in text_lower]


def _rule_score(num_hits: int) -> float:
    """Explainable step function: 0 hits -> 0.0, 1 -> 0.55, 2 -> 0.75, 3+ -> 0.9."""
    if num_hits <= 0:
        return 0.0
    if num_hits == 1:
        return 0.55
    if num_hits == 2:
        return 0.75
    return 0.9


def analyze_message(text: str, fetch_live_page: bool = False) -> dict:
    """
    Analyze a message for scam intent.

    Returns:
    --------
    dict: {
        "score": float (0.0 safe to 1.0 scam),
        "signature": "fear_authority" | "greed_opportunity" | "none",
        "reasons": list[str],
        "ml_status": str,
    }
    """
    if text is None:
        text = ""
    if not isinstance(text, str):
        text = str(text)

    text_stripped = text.strip()
    if not text_stripped:
        return {
            "score": 0.0,
            "signature": "none",
            "reasons": ["Empty message text provided"],
            "ml_status": "rules_only (placeholder baseline; Module C dataset pending)",
        }

    text_lower = text_stripped.lower()

    fear_hits = _match_keywords(text_lower, FEAR_AUTHORITY_KEYWORDS)
    greed_hits = _match_keywords(text_lower, GREED_OPPORTUNITY_KEYWORDS)

    # Signature: higher hit count wins; ties with both > 0 go to fear_authority
    # (deterministic, documented); zero hits -> "none".
    if len(fear_hits) == 0 and len(greed_hits) == 0:
        rule_signature = "none"
        rule_score = 0.0
    elif len(fear_hits) >= len(greed_hits):
        rule_signature = "fear_authority"
        rule_score = _rule_score(len(fear_hits))
    else:
        rule_signature = "greed_opportunity"
        rule_score = _rule_score(len(greed_hits))

    reasons: list = []
    for kw in fear_hits:
        reasons.append(f"Matched fear/authority pattern: '{kw}'")
    for kw in greed_hits:
        reasons.append(f"Matched greed/opportunity pattern: '{kw}'")

    # --- ML combination (if a trained artifact exists) ---
    artifact = _load_ml_model()
    if artifact is not None:
        try:
            pipeline = artifact["pipeline"]
            proba = pipeline.predict_proba([text_stripped])[0]
            classes = list(pipeline.classes_)
            prob_map = {str(c): float(p) for c, p in zip(classes, proba)}
            p_none = prob_map.get("none", 0.0)
            ml_score = round(1.0 - p_none, 4)
            # ML signature = highest-probability non-none class (fallback: argmax).
            scam_classes = [c for c in classes if str(c) != "none"]
            if scam_classes:
                ml_signature = str(max(scam_classes, key=lambda c: prob_map.get(str(c), 0.0)))
                if prob_map.get(ml_signature, 0.0) < 0.5:
                    ml_signature = str(classes[int(proba.argmax())])
            else:
                ml_signature = str(classes[int(proba.argmax())])
            if ml_signature not in VALID_SIGNATURES:
                ml_signature = "none"

            if rule_signature != "none":
                signature = rule_signature  # keep explainable rule vote
                text_score = round(min(1.0, 0.50 * rule_score + 0.50 * ml_score), 4)
            else:
                signature = ml_signature
                text_score = round(ml_score, 4)
            ml_status = "combined (rules + ML classifier)"
        except Exception:
            signature = rule_signature
            text_score = round(rule_score, 4)
            ml_status = "rules_only (ML inference failed)"
    else:
        signature = rule_signature
        text_score = round(rule_score, 4)
        ml_status = "rules_only (placeholder baseline; Module C dataset pending)"

    # --- URL folding via Module B ---
    urls = extract_urls(text_stripped)
    url_max = 0.0
    for url in urls:
        try:
            url_res = check_url(url, fetch_live_page=fetch_live_page)
        except Exception:
            continue
        try:
            u_score = float(url_res.get("score", 0.0))
        except (TypeError, ValueError):
            u_score = 0.0
        url_max = max(url_max, u_score)
        u_reasons = url_res.get("reasons", []) or []
        if u_score >= 0.4:
            reasons.append(f"Embedded URL '{url}' flagged by Module B (score {u_score:.2f})")
            for r in u_reasons:
                reasons.append(f"  URL evidence: {r}")
        elif u_reasons:
            reasons.append(f"Embedded URL '{url}' checked (score {u_score:.2f})")

    final_score = round(min(1.0, max(text_score, url_max)), 4)

    return {
        "score": final_score,
        "signature": signature,
        "reasons": reasons,
        "ml_status": ml_status,
    }


if __name__ == "__main__":
    demos = [
        "You are under investigation for money laundering. Stay on the line and do not disconnect.",
        "Limited time offer! Guaranteed returns, double your money with our exclusive stock tip.",
        "Hey, are we still meeting for lunch tomorrow?",
        "Please review this doc https://www.google.com/ and let me know.",
        "Urgent KYC update needed http://192.168.1.1/verify-account do not disconnect.",
    ]
    for d in demos:
        print(f"TEXT: {d}\n -> {analyze_message(d)}\n")
