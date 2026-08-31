import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.ofi_study.ofi import ofi_multi_level, ofi_at_level
from src.ofi_study.regime import realized_vol, classify_regime


def load(path):
    """Load a captured Parquet file, indexed and sorted by event time."""
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.set_index("timestamp").sort_index()


def build_features(df, bucket="1s", horizon=5, vol_window=300, ofi_levels=5):
    """Aggregate raw snapshots into a per-bucket modeling frame.

    Returns columns: ofi (summed per bucket), mid, ret, fwd_ret, vol, regime.
    """
    df = df.copy()
    df["ofi"] = ofi_multi_level(df, ofi_levels)
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


def build_features_by_level(df, bucket="1s", horizon=5, vol_window=300, levels=5):
    """Like build_features, but keeps each level's OFI as its own column (ofi_1..ofi_N)."""
    df = df.copy()

    frame = pd.DataFrame()
    for m in range(1, levels + 1):
        frame[f"ofi_{m}"] = ofi_at_level(df, m).resample(bucket).sum()

    frame["mid"] = ((df["bid_px_1"] + df["ask_px_1"]) / 2.0).resample(bucket).last().ffill()
    log_mid = np.log(frame["mid"])
    frame["ret"] = log_mid.diff()
    frame["fwd_ret"] = log_mid.shift(-horizon) - log_mid
    frame["vol"] = realized_vol(frame["ret"], vol_window)
    frame["regime"] = classify_regime(frame["vol"])

    ofi_cols = [f"ofi_{m}" for m in range(1, levels + 1)]
    return frame.dropna(subset=ofi_cols + ["fwd_ret", "regime"])


def regress(frame, hac_lags=5):
    """OLS of forward return on OFI with Newey-West (HAC) standard errors."""
    X = sm.add_constant(frame["ofi"])
    y = frame["fwd_ret"]
    model = sm.OLS(y, X)
    return model.fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})


def regress_multi(frame, ofi_cols, hac_lags=5):
    """Multivariate OLS of forward return on several OFI columns, HAC errors."""
    X = sm.add_constant(frame[ofi_cols])
    y = frame["fwd_ret"]
    return sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})


def directional_accuracy(frame):
    """Share of seconds where sign(ofi) matches sign(fwd_ret), vs a baseline."""
    pred = np.sign(frame["ofi"])
    actual = np.sign(frame["fwd_ret"])
    mask = (pred != 0) & (actual != 0)
    accuracy = (pred[mask] == actual[mask]).mean()
    baseline = actual[mask].value_counts(normalize=True).max()
    return accuracy, baseline


def load_bucketed(path, bucket="1s", levels=1):
    """Load one capture file, reduced to per-bucket OFI and mid price.

    Reducing each file before concatenating keeps memory bounded: a 57k-row
    file collapses to ~3.6k rows.
    """
    cols = ["timestamp"] + [f"{s}_{i}" for i in range(1, levels + 1)
                            for s in ("bid_px", "bid_sz", "ask_px", "ask_sz")]
    df = pd.read_parquet(path, columns=cols)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()

    ofi = ofi_multi_level(df, levels).resample(bucket).sum()
    mid = ((df["bid_px_1"] + df["ask_px_1"]) / 2.0).resample(bucket).last()
    return pd.DataFrame({"ofi": ofi, "mid": mid})


def build_features_many(paths, bucket="1s", horizon=5, vol_window=300, levels=1):
    """Build the modeling frame from many capture files."""
    frame = pd.concat([load_bucketed(p, bucket, levels) for p in sorted(paths)])
    frame = frame.sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    frame["mid"] = frame["mid"].ffill()

    log_mid = np.log(frame["mid"])
    frame["ret"] = log_mid.diff()
    frame["fwd_ret"] = log_mid.shift(-horizon) - log_mid
    frame["vol"] = realized_vol(frame["ret"], vol_window)
    frame["regime"] = classify_regime(frame["vol"])
    return frame.dropna(subset=["ofi", "fwd_ret", "regime"])
