import numpy as np
import pandas as pd


def ofi_level1(df):
    """Per-snapshot Order Flow Imbalance (Cont et al. 2014), level 1.

    Returns a Series of e_n contributions, one per row. The first row is
    NaN - there's no previous snapshot to compare it against.
    """
    bid_px, bid_sz = df["bid_px_1"], df["bid_sz_1"]
    ask_px, ask_sz = df["ask_px_1"], df["ask_sz_1"]

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
