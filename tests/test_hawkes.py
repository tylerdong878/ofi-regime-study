"""Sanity checks for the Hawkes process module.

Run from the project root with: python -m tests.test_hawkes
"""

import numpy as np

from src.ofi_study.hawkes import neg_log_likelihood, poisson_log_likelihood


def test_poisson_log_likelihood():
    # 10 events over 5 seconds -> rate 2/sec; LL = n*log(lam) - lam*T
    times = np.linspace(0.5, 5.0, 10)
    expected = 10 * np.log(10 / 5.0) - (10 / 5.0) * 5.0
    assert abs(poisson_log_likelihood(times, T=5.0) - expected) < 1e-9


def test_hawkes_reduces_to_poisson_when_alpha_zero():
    # alpha = 0 means no self-excitation, so Hawkes LL must equal Poisson LL
    times = np.linspace(0.5, 5.0, 10)
    lam = 10 / 5.0
    hawkes_ll = -neg_log_likelihood([lam, 0.0, 1.0], times, 5.0)
    assert abs(hawkes_ll - poisson_log_likelihood(times, T=5.0)) < 1e-9


def test_invalid_params_are_penalized():
    times = np.linspace(0.5, 5.0, 10)
    assert neg_log_likelihood([-1.0, 0.5, 1.0], times, 5.0) >= 1e10
    assert neg_log_likelihood([1.0, -0.5, 1.0], times, 5.0) >= 1e10


if __name__ == "__main__":
    test_poisson_log_likelihood()
    test_hawkes_reduces_to_poisson_when_alpha_zero()
    test_invalid_params_are_penalized()
    print("All Hawkes tests passed")
