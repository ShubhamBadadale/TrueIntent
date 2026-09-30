"""Small, shared fusion contract; unknown channels are not observed zero risk."""
import math
import pandas as pd

FEATURES = ['module_a_score', 'module_b_score', 'module_c_score',
            'a_present', 'b_present', 'c_present', 'active_call', 'call_known',
            'credential_request', 'authority_fear', 'message_transaction',
            'call_transaction', 'url_credentials', 'authority_transaction']
ABLATIONS = {'A': 'a', 'B': 'b', 'C': 'c', 'A+B': 'ab', 'A+C': 'ac',
             'B+C': 'bc', 'A+B+C': 'abc', 'A+B+C+call': 'abck'}


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
