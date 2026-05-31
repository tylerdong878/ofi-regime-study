"""Sanity check for volatility regime classification.

Run from the project root with: python -m tests.test_regime
"""

import pandas as pd

from src.ofi_study.regime import classify_regime


def test_high_low_split():
    vol = pd.Series([1.0, 3.0, 2.0, 5.0, 0.5])
    regime = classify_regime(vol)
    # expanding-median thresholds: 1, 2, 2, 2.5, 2
    assert list(regime) == ["low", "high", "low", "high", "low"]


def test_classification_is_casusal():
    vol = pd.Series([1.0, 3.0, 2.0, 5.0, 0.5, 4.0])
    full = classify_regime(vol)
    prefix = classify_regime(vol.iloc[:4])
    # first 4 labels must be identical whether or not later data exists
    assert list(full.iloc[:4]) == list(prefix)


if __name__ == "__main__":
    test_high_low_split()
    test_classification_is_casusal()
    print("All regime tests passed")
