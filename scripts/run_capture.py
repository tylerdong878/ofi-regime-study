"""CLI entry point for capturing live order book data.

Example:
    python -m scripts.run_capture --symbol BTC-USD --duration 300 --out data/btc.parquet
"""

import argparse
import asyncio

from src.ofi_study.capture import capture


def main():
    parser = argparse.ArgumentParser(
        description="Capture Coinbase L2 order book data to Parquet."
    )
    parser.add_argument("--symbol", default="BTC-USD", help="Product to capture")
    parser.add_argument("--duration", type=int, default=30, help="Seconds to capture")
    parser.add_argument("--out", default="data/btc_smoke.parquet", help="Output Parquet path")
    args = parser.parse_args()
    asyncio.run(capture(symbol=args.symbol,duration=args.duration, out_path=args.out))


if __name__ == "__main__":
    main()
