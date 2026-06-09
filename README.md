# Order Flow Imbalance & Price Impact: A Regime-Based Microstructure Study

Quantitative research into whether **order flow imbalance (OFI)** predicts short-term price movement in crypto markets - and whether that relationship changes between **high- and low-volatility regimes**. Based on Cont, Kukanov & Stoikov (2014).

> **Status:** Phase 1 (Python end-to-end) complete. C++ ingestion rewrite, multi-level
> OFI, and Hawkes-process modeling are planned

## Research question

Does order flow imbalance predict short-term price movement, and does that relationship vary significantly between high- and low-volatility regimes?

## Preliminary finding

On ~2 hours of Coinbase BTC-USD L2 data (1-second buckets, 5-second forward returns):

- OFI **positively predicts** 5-second forward returns (HAC t = 4.2 overall).
- The signal is **stronger and significant in low-volatility regimes** (t = 5.8; beats a naive directional baseline by ~7 points) but **insignificant in high-volatility regimes** (t = 1.9, p = 0.05; no directional edge).

This is consistent with OFI being informative in orderly markets but drowned out by news/large trades when volatility is high. *(Preliminary: one 2-hour window, one asset.)*

## Architecture

```
Coinbase L2 WebSocket (live)
        |
        v
Order book reconstruct  (orderbook.py + capture.py)
        |
        v
Parquet tick data       (data/)
        |
        v
Python research         (ofi.py, regime.py, analysis.py, notebook)
```

- **`src/ofi_study/orderbook.py`** - reconstructs the L2 book from snapshot + deltas.
- **`src/ofi_study/capture.py`** - async WebSocket capture -> top-5 snapshots to Parquet.
- **`src/ofi_study/ofi.py`** - Cont et al. order flow imbalance.
- **`src/ofi_study/regime.py`** - causal (no-lookahead) volatility regime classification.
- **`src/ofi_study/analysis.py`** - feature build, OLS with HAC errors, directional accuracy.
- **`notebooks/01_first_results.ipynb`** - results and charts.

## How to run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# capture live data (e.g. 30 minutes of BTC-USD)
python -m scripts.run_capture --symbol BTC-USD --duration 1800 --out data/btc.parquet

# run the tests
python -m tests.test_orderbook && python -m tests.test_ofi && python -m tests.test_regime

# then open notebooks/01_first_results.ipynb
```

## Roadmap

- [ ] Multi-day, multi-asset capture (BTC, ETH, SOL)
- [ ] Multi-level OFI (levels 1-5)
- [ ] Hawkes process for order-arrival clustering
- [ ] C++ rewrite of the ingestion layer + latency benchmarks
- [ ] Blog post writeup

## Reference

Cont, R., Kukanov, A., & Stoikov, S. (2014). *The Price Impact of Order Book Events.* Journal of Financial Econometrics.
