"""Sanity checks for the Cont et al. OFI computation.

Run from the project root with: python -m tests.test_ofi
"""

import numpy as np
import pandas as pd

from src.ofi_study.ofi import ofi_level1


def test_unchanged_prices():
    # bid 100 x5 -> x8 (demand up: +3); ask 101 x3 -> x2 (supply down: +1) => +4
    df = pd.DataFrame({
        "bid_px_1": [100.0, 100.0],
        "bid_sz_1": [5.0, 8.0],
        "ask_px_1": [101.0, 101.0],
        "ask_sz_1": [3.0, 2.0],
    })
    ofi = ofi_level1(df)
    assert np.isnan(ofi.iloc[0])    # first row has no predecessor
    assert ofi.iloc[1] == 4.0


def test_bid_price_improves():
    # bid price climbs 100 -> 101 (size 4): whole new queue counts => +4
    # ask unchanged 102 x2 -> x2 => 0
    df = pd.DataFrame({
        "bid_px_1": [100.0, 101.0],
        "bid_sz_1": [5.0, 4.0],
        "ask_px_1": [102.0, 102.0],
        "ask_sz_1": [2.0, 2.0],
    })
    ofi = ofi_level1(df)
    assert ofi.iloc[1] == 4.0


if __name__ == "__main__":
    test_unchanged_prices()
    test_bid_price_improves()
    print("All OFI tests passed")
