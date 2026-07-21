"""Sanity checks for the Cont et al. OFI computation.

Run from the project root with: python -m tests.test_ofi
"""

import numpy as np
import pandas as pd

from src.ofi_study.ofi import ofi_level1, ofi_multi_level


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


def test_multi_level_sums_across_levels():
    # level 1: bid 5->8 (+3), ask 3->2 (+1) => OFI_1 = +4
    # level 2: bid 4->6 (+2), ask 7->7 ( 0) => OFI_2 = +2
    # multi-level over 2 levels => +6
    df = pd.DataFrame({
        "bid_px_1": [100.0, 100.0], "bid_sz_1": [5.0, 8.0],
        "ask_px_1": [101.0, 101.0], "ask_sz_1": [3.0, 2.0],
        "bid_px_2": [99.0, 99.0],   "bid_sz_2": [4.0, 6.0],
        "ask_px_2": [102.0, 102.0], "ask_sz_2": [7.0, 7.0],
    })
    ofi = ofi_multi_level(df, levels=2)
    assert  np.isnan(ofi.iloc[0])
    assert ofi.iloc[1] == 6.0


if __name__ == "__main__":
    test_unchanged_prices()
    test_bid_price_improves()
    test_multi_level_sums_across_levels()
    print("All OFI tests passed")
