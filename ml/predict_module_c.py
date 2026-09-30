"""
Module C — Message/Scam Analyzer (text-analysis half).

Lightweight intent classifier with explicit real/curated/synthetic provenance.
Keyword overrides are disabled; any retained rules are labeled evidence only.
Missing models explicitly abstain from text assessment.

Any URLs found in the message are extracted and passed to Module B's
`check_url()` and folded into the final score/reasons.
"""

import os
import re

try:
    from ml.model_loading import load_artifact
except ImportError:
    from model_loading import load_artifact

try:
    from ml.predict_module_b import check_url
except ImportError:  # fallback for direct script execution
    from predict_module_b import check_url

# -----------------------------------------------------------------------------
# Historical keyword candidates, retained for measured ablations only.
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
    """Load Module C artifact if trained, else None (text assessment unavailable)."""
    global _ML_MODEL_ARTIFACT
    if model_path is None:
        model_path = _get_model_path()

    _ML_MODEL_ARTIFACT = load_artifact(model_path, _ML_MODEL_ARTIFACT)
    return _ML_MODEL_ARTIFACT


def extract_urls(text: str) -> list:
    """Extract http(s):// and www. URLs from message text."""
    if not text:
        return []
    pattern = r"(https?://[^\s\"'<>]+|www\.[^\s\"'<>]+)"
    found = re.findall(pattern, text, flags=re.IGNORECASE)
    # Strip trailing punctuation that is not part of the URL.
    return list(dict.fromkeys(u.rstrip(".,;:!?)'\"") for u in found))


def analyze_message(text: str, fetch_live_page: bool = False) -> dict:
    """Separate ML intent predictions, keyword evidence and embedded URL evidence."""
    import numpy as np
    from ml.features_module_c import normalize_text, INTENTS
    text = '' if text is None else str(text).strip()
    artifact = _load_ml_model()
    result = dict(score=0.0, signature='none', reasons=[],
                  ml_status='not_run (empty text)' if not text else 'unavailable (text not assessed)',
                  intent=None, intent_probabilities={}, rule_evidence=[], text_assessed=False)
    if not text:
        result['reasons'] = ['Empty message text provided']
        return result
    if artifact is not None:
        try:
            is_v2 = artifact.get('mode') == 'intent-v2'
            model = artifact['intent_pipeline'] if is_v2 else artifact['pipeline']
            classes = list(model.classes_)
            expected = set(INTENTS) if is_v2 else set(VALID_SIGNATURES)
            if set(classes) != expected:
                raise ValueError('Unsupported intent contract')
            probabilities = np.asarray(model.predict_proba([text])[0], dtype=float)
            if not np.isfinite(probabilities).all() or np.any(probabilities < 0) or not np.isclose(probabilities.sum(), 1):
                raise ValueError('Invalid probability output')
            top = str(classes[int(probabilities.argmax())])
            benign = 'benign' if is_v2 else 'none'
            result['score'] = round(1 - float(probabilities[classes.index(benign)]), 4)
            signature = str(artifact['pipeline'].predict([text])[0]) if is_v2 else top
            result['signature'] = signature if signature in VALID_SIGNATURES else 'none'
            if is_v2:
                result['intent'] = top
                result['intent_probabilities'] = dict(zip(classes, probabilities.tolist()))
            result['text_assessed'] = True
            result['ml_status'] = 'active (experimental intent model; limited real-language coverage)' if is_v2 else 'active (legacy three-class model)'
            result['reasons'].append(f"ML {'intent' if is_v2 else 'signature'} prediction: '{top}' (not a verified finding of fraud)")
            if is_v2:
                result['reasons'].append('Expanded intent and Hindi/Hinglish coverage relies on authored examples; real-world recall is unvalidated.')
            for rule in artifact.get('evidence_rules', []):
                if rule['phrase'] in normalize_text(text):
                    result['rule_evidence'].append(dict(source='keyword_rule', phrase=rule['phrase'],
                                                       intent=rule['intent'], affects_score=False))
                    result['reasons'].append(f"Rule evidence only: '{rule['phrase']}' (does not override ML)")
        except Exception:
            result.update(score=0.0, signature='none', intent=None, intent_probabilities={}, text_assessed=False,
                          ml_status='unavailable (ML inference failed; text not assessed)')
    if not result['text_assessed']:
        result['reasons'].append('Text could not be assessed. A zero text score does not mean this message is safe.')
    result['text_score'] = result['score'] if result['text_assessed'] else None
    result['embedded_url_score'] = 0.0
    for url in extract_urls(text):
        try:
            url_result = check_url(url, fetch_live_page=fetch_live_page)
            score = float(url_result['score'])
            if not np.isfinite(score) or not 0 <= score <= 1:
                continue
            result['score'] = round(max(result['score'], score), 4)
            result['embedded_url_score'] = max(result['embedded_url_score'], score)
            if score >= .4:
                result['reasons'].append(f"Embedded URL '{url}' flagged by Module B (score {score:.2f})")
                result['reasons'].extend(f'URL evidence: {reason}' for reason in url_result.get('reasons', []))
        except Exception:
            continue
    return result


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
