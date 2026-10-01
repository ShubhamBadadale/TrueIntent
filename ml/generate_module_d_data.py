"""Synthetic joint scenarios for Module D; labels are an explicit invented policy.

The pre-correction generator that paired real Module A/B/C outputs is gone. It
could not run against the amount-only Module A benchmark (`validate_artifact`
rejects any artifact that is not the v2 contract) and its `combined_label` policy
did not distinguish an absent channel from a zero score. `generate_module_d_data`
now delegates to the interaction-policy simulation in `ml/evaluate_module_d.py`,
which models availability explicitly.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

POLICY = ('combined_label=1 iff at least one PRESENT component has a positive source label; '
          'independently paired components are synthetic scenarios, not linked incidents.')


def active_score(result):
    """Do not silently build learned fusion data from rules-only fallback scores."""
    if not result.get('ml_status', '').startswith('active'):
        raise RuntimeError('Module D data requires active trained base classifiers')
    return result['score']


def generate_module_d_data():
    """Current explicit simulation; never silently reinterpret Module A benchmark outputs."""
    from ml.evaluate_module_d import generate_scenarios
    return generate_scenarios(ROOT / 'data/raw/module_d_interaction_scenarios.csv')


if __name__ == '__main__':
    generate_module_d_data()