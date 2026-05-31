import asyncio
import json
import time
from pathlib import Path

import pandas as pd
import websockets

from src.ofi_study.orderbook import OrderBook

WS_URL = "wss://ws-feed.exchange.coinbase.com"


def record_row(book, ts, levels=5):
    """Flatten the top `levels` of the book into one flat row dict."""
    bids, asks = book.top_n(levels)
    row = {"timestamp": ts, "recv_ns": time.time_ns()}
    for i in range(levels):
        bid_px, bid_sz = bids[i] if i < len(bids) else (None, None)
        ask_px, ask_sz = asks[i] if i < len(asks) else (None, None)
        row[f"bid_px_{i + 1}"] = bid_px
        row[f"bid_sz_{i + 1}"] = bid_sz
        row[f"ask_px_{i + 1}"] = ask_px
        row[f"ask_sz_{i + 1}"] = ask_sz
    return row


async def capture(symbol="BTC-USD", duration=30, out_path="data/btc_smoke.parquet", levels=5):
    """Stream the live book for `duration` seconds, saving top-`levels` snapshots."""
    book = OrderBook()
    rows = []
    subscribe = {
        "type": "subscribe",
        "product_ids": [symbol],
        "channels": ["level2_batch"],
    }
    start = time.monotonic()
    async with websockets.connect(WS_URL, max_size=None) as ws:
        await ws.send(json.dumps(subscribe))
        async for raw in ws:
            msg = json.loads(raw)
            if msg["type"] == "snapshot":
                book.apply_snapshot(msg["bids"], msg["asks"])
            elif msg["type"] == "l2update":
                book.apply_update(msg["changes"])
                rows.append(record_row(book, msg["time"], levels))
            if time.monotonic() - start >= duration:
                break
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_parquet(out_path)
    print(f"captured {len(df)} rows over ~{duration}s -> {out_path}")
