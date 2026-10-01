"""Small, shared fusion contract; unknown channels are not observed zero risk."""
import math
import pandas as pd

FEATURES = ['module_a_score', 'module_b_score', 'module_c_score',
            'a_present', 'b_present', 'c_present', 'active_call', 'call_known',
            'credential_request', 'authority_fear', 'message_transaction',
            'call_transaction', 'url_credentials', 'authority_transaction']
ABLATIONS = {'A': 'a', 'B': 'b', 'C': 'c', 'A+B': 'ab', 'A+C': 'ac',
             'B+C': 'bc', 'A+B+C': 'abc', 'A+B+C+call': 'abck'}

# ---------------------------------------------------------------------------
# Central fusion contract (single source of truth — no magic values elsewhere).
#
# Module D fuses Module B (URL) and Module C (message) evidence. Module A is
# an amount-only IEEE-CIS benchmark and is NOT a fusion input; its weight is
# reserved here so a future *validated* Module A can plug in without
# renumbering the contract (see MODULE_A_FUSION_ENABLED in predict_module_d).
# ---------------------------------------------------------------------------
FUSION_VERSION = '3.0.0'

SUPPORTED_MODULES = ('module_a', 'module_b', 'module_c')
ACTIVE_MODULES = ('module_b', 'module_c')

RISK_LEVELS = ('Low', 'Medium', 'High', 'Critical')

# Overall risk score -> risk level. Mirrored read-only in frontend api.js;
# change both together or not at all.
RISK_THRESHOLDS = {
    'low_max': 0.25,     # score < 0.25 -> Low
    'medium_max': 0.50,  # score < 0.50 -> Medium
    'high_max': 0.75,    # score < 0.75 -> High; >= 0.75 -> Critical
}

# Transparent fallback weights (renormalized over assessed modules only).
# Missing/unavailable modules contribute nothing and are listed, never zeroed.
MODULE_WEIGHTS = {
    'module_a': 0.45,  # reserved for a future validated Module A
    'module_b': 0.25,  # URL safety (narrowest; often already folded into C)
    'module_c': 0.30,  # message analysis (text score only; URL folded once)
}

# An assessed module at/above this counts as "risky" for explanations.
RISKY_MODULE_SCORE = 0.40

ABSTENTION_REASONS = (
    'not_provided',      # no input was submitted for this module
    'model_unavailable', # model/artifact missing so nothing was assessed
    'assessment_failed', # inference raised; nothing was assessed
    'not_assessed',      # analysis ran but explicitly did not assess (e.g. Module C text)
    'unsupported',       # module exists but is not a fusion input (Module A benchmark)
)

LIMITATIONS = (
    'The overall score is an uncalibrated risk score, not a calibrated fraud probability.',
    'URL analysis is offline only; destinations are never fetched.',
    'Message assessment has limited real-language coverage; calm or novel phrasing may be missed.',
    'Only submitted evidence is analyzed; encrypted channels cannot be observed.',
    'A missing module stays missing: partial results reflect only the evidence that ran.',
)

RECOMMENDED_ACTIONS = {
    'Low': ('No strong risk signals in the evidence provided. Proceed with normal '
            'caution and verify important details independently.'),
    'Medium': ('Some risk signals. Pause before acting: verify the sender and any '
               'link through an independent channel; do not share codes or pay under pressure.'),
    'High': ('Strong risk signals. Do not send money, share OTPs/passwords, or install '
             'apps at their request. Verify independently or stop.'),
    'Critical': ('Very strong risk signals. Stop: do not transfer funds or share OTPs, '
                 'passwords, or remote access. Consider reporting the incident.'),
}

#: Concrete per-level safety steps for mobile clients (same source as
#: RECOMMENDED_ACTIONS, rendered as a checklist instead of prose).
SAFETY_ACTIONS = {
    'Low': (
        'Proceed with normal caution.',
        'Verify important details independently before acting.',
    ),
    'Medium': (
        'Pause before acting.',
        'Verify the sender and any link through an independent channel.',
        'Do not share OTPs, passwords, or payments under pressure.',
    ),
    'High': (
        'Do not send money or share OTPs/passwords.',
        'Do not install apps at their request.',
        'Verify independently or stop engaging.',
    ),
    'Critical': (
        'Stop: do not transfer funds or share codes/passwords.',
        'Do not grant remote or screen access.',
        'Consider reporting the incident to your bank or cyber helpline.',
    ),
}


def risk_level_for(score_value) -> str:
    """Map a finite 0-1 overall risk score to a risk level (central thresholds)."""
    number = float(score_value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError('Fusion risk scores must be finite and between zero and one')
    if number < RISK_THRESHOLDS['low_max']:
        return 'Low'
    if number < RISK_THRESHOLDS['medium_max']:
        return 'Medium'
    if number < RISK_THRESHOLDS['high_max']:
        return 'High'
    return 'Critical'


def recommend_action(risk_level: str, *, partial: bool = False) -> str:
    """User-facing next step for a risk level, noting partial evidence."""
    action = RECOMMENDED_ACTIONS[risk_level]
    if partial:
        action += (' Only partial evidence was available, so treat this as a lower '
                   'bound on risk and seek the missing evidence where possible.')
    return action


def score(value):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError('A score cannot be boolean')
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError('Fusion scores must be finite and between zero and one')
    return number


def feature_row(a=None, b=None, c=None, active_call=None, credential_request=0., authority_fear=0.):
    a, b, c = score(a), score(b), score(c)
    if a is None and b is None and c is None:
        raise ValueError('At least one scored channel is required; call status alone is insufficient')
    if active_call is not None and not isinstance(active_call, bool):
        raise ValueError('active_call must be boolean or unknown (None)')
    credential = score(credential_request) if c is not None else 0.
    authority = score(authority_fear) if c is not None else 0.
    av, bv, cv = a or 0., b or 0., c or 0.
    return dict(zip(FEATURES, [av, bv, cv, int(a is not None), int(b is not None), int(c is not None),
        int(active_call is True), int(active_call is not None), credential, authority,
        av * cv, av * int(active_call is True), bv * credential, av * authority]))


def frame_for(data, channels):
    return pd.DataFrame([feature_row(
        r.module_a_score if 'a' in channels else None,
        r.module_b_score if 'b' in channels else None,
        r.module_c_score if 'c' in channels else None,
        bool(r.active_call) if 'k' in channels else None,
        r.credential_request, r.authority_fear) for r in data.itertuples()], columns=FEATURES)


def rule_score(row):
    # Explicit demo policy: strongest observation plus bounded corroboration.
    # Shared C/B URL evidence is separated before this function is called.
    strongest = max(row['module_a_score'], row['module_b_score'], row['module_c_score'])
    interaction = max(row['message_transaction'], row['call_transaction'],
                      row['url_credentials'], row['authority_transaction'])
    return min(1., .7 * strongest + .3 * interaction)
