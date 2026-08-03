"""Capture individual trade timestamps (Coinbase matches channel) for Hawkes fitting.

Run: python -m scripts.capture_trades --duration 300
"""
import argparse
import asyncio
import json
import time
from pathlib import Path

import pandas as pd
import websockets

WS_URL = "wss://ws-feed.exchange.coinbase.com"


async def capture_trades(symbol, duration, out_path):
    sub = {"type": "subscribe", "product_ids": [symbol], "channels": ["matches"]}
    times = []
    start = time.monotonic()
    async with websockets.connect(WS_URL, max_size=None) as ws:
        await ws.send(json.dumps(sub))
        async for raw in ws:
            msg = json.loads(raw)
            if msg.get("type") == "match":
                times.append(msg["time"])
            if time.monotonic() - start >= duration:
                break
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame({"time": times})
    df.to_parquet(out_path)
    print(f"captured {len(df)} trades over ~{duration}s -> {out_path}")


def main():
    p = argparse.ArgumentParser(description="Capture Coinbase trades for Hawkes.")
    p.add_argument("--symbol", default="BTC-USD")
    p.add_argument("--duration", type=int, default=300)
    p.add_argument("--out", default="data/trades.parquet")
    args = p.parse_args()
    asyncio.run(capture_trades(args.symbol, args.duration, args.out))


if __name__ == "__main__":
    main()
