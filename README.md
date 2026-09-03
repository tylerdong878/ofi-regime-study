# Order Flow Imbalance & Price Impact: A Regime-Based Microstructure Study

Quantitative research into whether **order flow imbalance (OFI)** predicts short-term price movement in crypto markets - and whether that relationship changes between **high- and low-volatility regimes**. Based on Cont, Kukanov & Stoikov (2014).

> **Status:** Complete. Python research pipeline, C++ ingestion layer, multi-level OFI,
> Hawkes-process modeling, and a 20-day continuous EC2 capture are all done.

## Research question

Does order flow imbalance predict short-term price movement, and does that relationship vary significantly between high- and low-volatility regimes?

## Findings

On **20.5 days** of continuously captured Coinbase BTC-USD L2 data
(~28M book snapshots -> 1.77M one-second observations):

- **OFI significantly predicts forward returns**, robust across **1-30 second** horizons.
- **Predictive power is concentrated in low-volatility regimes** - R² is 4-8x higher at
   every horizon (full-sample HAC t = 18.7 vs 2.9), and low-vol is stronger on 13 of 17 days
   (two of the four exceptions are effectively ties).
- **Direction vs. magnitude:** the directional edge over a naive baseline is nearly
  identical across regimes (~10pp at 1s, ~5pp at 5s, ~2pp at 30s). OFI calls the sign
  equally well in both regimes, but explains far more return *variance* in calm markets.
- The signal **decays monotonically with horizon**, consistent with order-flow
  information being incorporated into price quickly.

An earlier 2-hour sample suggested this same regime effect; a 16-hour sample appeared to
reverse it. Only the full 20-day dataset resolved the question - short windows were unreliable in both directions.

Order arrivals are also strongly **self-exciting**: a fitted Hawkes process gives a
branching ratio of **0.75** (~75% of trades triggered by prior trades), decisively
rejecting a Poisson null (LR = 202).

*Limitations: one asset (BTC-USD), level-1 OFI, in-sample.*

## Architecture

```
Coinbase L2 WebSocket   (live)
        |
        v
C++ ingestion           (cpp/) - book reconstruction, Arrow -> Parquet
        |                        runs 24/7 on EC2 under systemd
        v
Parquet tick data       (data/)
        |
        v
Python research         (ofi.py, regime.py, analysis.py, hawkes.py, notebook)
```

- **`src/ofi_study/orderbook.py`** - reconstructs the L2 book from snapshot + deltas.
- **`src/ofi_study/capture.py`** - async WebSocket capture -> top-5 snapshots to Parquet.
- **`src/ofi_study/ofi.py`** - Cont et al. order flow imbalance.
- **`src/ofi_study/regime.py`** - causal (no-lookahead) volatility regime classification.
- **`src/ofi_study/analysis.py`** - feature build, OLS with HAC errors, directional accuracy.
- **`notebooks/01_first_results.ipynb`** - results and charts.
- **`src/ofi_study/hawkes.py`** - Hawkes process fitting (MLE, branching ratio).
- **`notebooks/02_robustness.ipynb`** - 20-day robustness analysis.

## How to run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# capture live data (e.g. 30 minutes of BTC-USD)
python -m scripts.run_capture --symbol BTC-USD --duration 1800 --out data/btc.parquet

# run the tests
python -m tests.test_orderbook && python -m tests.test_ofi && python -m tests.test_regime

# then open notebooks/01_first_results.ipynb and notebooks/02_robustness.ipynb
```

## C++ ingestion layer

The ingestion layer (order book reconstruction + live capture) is implemented in C++ for low-latency processing. It connects to Coinbase over a TLS WebSocket, reconstructs the L2 book with `std::map`, and writes **Parquet** tick data that the Python research layer reads unchanged (via Apache Arrow).

```bash
sudo dnf install libarrow-devel parquet-libs-devel # one-time deps
cmake -S cpp -B cpp/build
cmake --build cpp/build
./cpp/build/ingest         # runs until Ctrl+C, rotating hourly -> data/btc_<epoch>.parquet
./cpp/build/test_orderbook # order book unit tests
```

Measured on live BTC-USD (30-second sample): per-update processing latency
p50 ~0.4 ms, p99 ~2.5 ms (incl. Parquet serialization); throughput is feed-limited at ~16 batched updates/sec.

The collector runs continuously under `systemd` on an AWS EC2 instance, rotating Parquet
files hourly and flushing gracefully on SIGTERM; 20 days of BTC-USD data were captured
this way and pulled down with `rsync` for research.

## Roadmap

- [x] C++ rewrite of the ingestion layer + latency benchmarks
- [x] C++ writes Parquet (Apache Arrow), read by the Python layer
- [x] Continuous multi-day capture (EC2 + systemd)
- [x] Multi-level OFI (levels 1-5) - tested; level-1 dominant, deeper levels add nothing
- [x] Hawkes process for order-arrival clustering

## Future work

Multi-asset replication (ETH, SOL) and formal out-of-sample validation - the current
result rests on a single asset, in-sample.

## Reference

Cont, R., Kukanov, A., & Stoikov, S. (2014). *The Price Impact of Order Book Events.* Journal of Financial Econometrics.
