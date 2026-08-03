import numpy as np
import pandas as pd

from scipy.optimize import minimize
from scipy.stats import chi2


def load_event_times(path):
    """Load trade timestamps and return seconds elapsed from the first trade.

    Simultaneous fills (one market order sweeping several resting orders)
    share a time stamp; we collapse them to a single arrival, since a sweep
    is one trading decision. Duplicate times also make the Hawkes likelinhood
    degenerate (zero gaps never decay).
    """
    df = pd.read_parquet(path)
    t = pd.to_datetime(df["time"]).sort_values()
    secs = (t - t.iloc[0]).dt.total_seconds().to_numpy()
    return np.unique(secs)


def neg_log_likelihood(params, times, T):
    """Negative log-likelihood of a univariate Hawkes process (exp kernel).

    lambda(t) = mu + sum_{t_j < t} alpha * exp(-beta * (t - t_j))
    Returns -LL so we can *minimize* it. `T` is the observation horizon.
    """
    mu, alpha, beta = params
    if mu <= 0 or alpha < 0 or beta <= 0:
        return 1e10

    # sum of log intensity at each event time, via the O(n) recursion
    ll = np.log(mu)         # first event: no prior events, lambda = mu
    A = 0.0
    for i in range(1, len(times)):
        A = np.exp(-beta * (times[i] - times[i - 1])) * (1.0 + A)
        ll += np.log(mu + alpha * A)

    # the integral (compensator) term
    compensator = mu * T + (alpha / beta) * np.sum(1.0 - np.exp(-beta * (T - times)))
    ll -= compensator

    return -ll


def fit(times, T=None):
    """Fit a Hawkes process by maximum likelihood; returns params + branching ratio."""
    if T is None:
        T = float(times[-1])
    rate = len(times) / T
    bounds = [(1e-9, None), (0.0, None), (1e-9, None)]
    starts = [
        [rate * 0.5, 1.0, 2.0],
        [rate * 0.25, 0.4, 0.6],
        [rate * 0.75, 2.0, 5.0],
        [rate * 0.1, 0.1, 0.2],
    ]

    best = None
    for x0 in starts:
        res = minimize(neg_log_likelihood, np.array(x0), args=(times, T),
                       method="L-BFGS-B", bounds=bounds)
        if best is None or res.fun < best.fun:
            best = res

    mu, alpha, beta = res.x
    return {
        "mu": mu,
        "alpha": alpha,
        "beta": beta,
        "branching_ratio": alpha / beta,
        "log_likelihood": -res.fun,
        "converged": bool(res.success),
    }


def poisson_log_likelihood(times, T = None):
    """Log-likelihood of a homogeneous Poisson process (the no clustering null).

    This is the alpha=0 special case of Hawkes: constant rate, no self-excitation.
    """
    if T is None:
        T = float(times[-1])
    n = len(times)
    lam = n / T
    return n * np.log(lam) - lam * T


def compare_to_poisson(times, T=None):
    """Likelihood-ratio test: does self-excitation explain the data better?"""

    if T is None:
        T = float(times[-1])
    hawkes = fit(times, T)
    ll_poisson = poisson_log_likelihood(times, T)
    lr = 2.0 * (hawkes["log_likelihood"] - ll_poisson)
    p = chi2.sf(lr, df=2)
    return {
        "hawkes_log_likelihood": hawkes["log_likelihood"],
        "poisson_log_likelihood": ll_poisson,
        "lr_statistic": lr,
        "p_value": p,
        "branching_ratio": hawkes["branching_ratio"],
    }
