import numpy as np
import pandas as pd


def ofi_at_level(df, level):
    """Per-snapshot OFI (Cont et al. 2014) at a single book level (1-5).

    Returns a Series of e_n contributions; The first row is NaN (no
    previous snapshot to compare against).
    """
    bid_px, bid_sz = df[f"bid_px_{level}"], df[f"bid_sz_{level}"]
    ask_px, ask_sz = df[f"ask_px_{level}"], df[f"ask_sz_{level}"]

    prev_bid_px, prev_bid_sz = bid_px.shift(1), bid_sz.shift(1)
    prev_ask_px, prev_ask_sz = ask_px.shift(1), ask_sz.shift(1)

    bid_term = (
        np.where(bid_px >= prev_bid_px, bid_sz, 0.0)
        - np.where(bid_px <= prev_bid_px, prev_bid_sz, 0.0)
    )
    ask_term = (
        np.where(ask_px <= prev_ask_px, ask_sz, 0.0)
        - np.where(ask_px >= prev_ask_px, prev_ask_sz, 0.0)
    )

    ofi = pd.Series(bid_term - ask_term, index=df.index)
    ofi.iloc[0] = np.nan
    return ofi


def ofi_level1(df):
    """Level-1 OFI (kept for backward compatibility)."""
    return ofi_at_level(df, 1)


def ofi_multi_level(df, levels=5):
    """Multi-level OFI: sum of per-leel OFI accross levels 1..`levels`."""
    total = ofi_at_level(df, 1)
    for level in range(2, levels + 1):
        total = total + ofi_at_level(df, level)
    return total
