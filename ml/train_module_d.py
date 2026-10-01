"""Interaction-policy logistic fusion model plus its ablations."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.evaluate_module_d import evaluate


def train_module_d():
    """Reproduce the explicit interaction-policy simulation and all ablations."""
    return evaluate()


if __name__ == '__main__':
    train_module_d()