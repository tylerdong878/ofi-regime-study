import numpy as np
import pandas as pd


def realized_vol(returns, window):
    """Trailing realized volatility: rolling std of returns over `window`.

    Uses only a trailing window of past observations, so it is causal.
    """
    return returns.rolling(window).std()


def classify_regime(vol):
    """Label each point 'high' or 'low' volatility, with no lookahead.

    The threshold at time t is the expanding median of volatility seen up
    to and including t. Because it never uses future data, the label at t
    could have been computed live, in real time.
    """
    threshold = vol.expanding().median()
    regime = pd.Series(np.where(vol > threshold, "high", "low"), index=vol.index)
    regime[vol.isna()] = None
    return regime
