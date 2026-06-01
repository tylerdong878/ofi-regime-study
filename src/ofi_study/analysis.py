import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.ofi_study.ofi import ofi_level1
from src.ofi_study.regime import realized_vol, classify_regime


def load(path):
    """Load a captured Parquet file, indexed and sorted by event time."""
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.set_index("timestamp").sort_index()


def build_features(df, bucket="1s", horizon=5, vol_window=300):
    """Aggregate raw snapshots into a per-bucket modeling frame.
    
    Returns columns: ofi (summed per bucket), mid, ret, fwd_ret, vol, regime.
    """
    df = df.copy()
    df["ofi"] = ofi_level1(df)
    df["mid"] = (df["bid_px_1"] + df["ask_px_1"]) / 2.0

    ofi = df["ofi"].resample(bucket).sum()
    mid = df["mid"].resample(bucket).last().ffill()

    frame = pd.DataFrame({"ofi": ofi, "mid": mid})
    log_mid = np.log(frame["mid"])
    frame["ret"] = log_mid.diff()
    frame["fwd_ret"] = log_mid.shift(-horizon) - log_mid
    frame["vol"] = realized_vol(frame["ret"], vol_window)
    frame["regime"] = classify_regime(frame["vol"])
    return frame.dropna(subset=["ofi", "fwd_ret", "regime"])


def regress(frame, hac_lags=5):
    """OLS of forward return on OFI with Newey-West (HAC) standard errors."""
    X = sm.add_constant(frame["ofi"])
    y = frame["fwd_ret"]
    model = sm.OLS(y, X)
    return model.fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})


def directional_accuracy(frame):
    """Share of seconds where sign(ofi) matches sign(fwd_ret), vs a baseline."""
    pred = np.sign(frame["ofi"])
    actual = np.sign(frame["fwd_ret"])
    mask = (pred != 0) & (actual != 0)
    accuracy = (pred[mask] == actual[mask]).mean()
    baseline = actual[mask].value_counts(normalize=True).max()
    return accuracy, baseline
