#!/usr/bin/env python3
"""Aggregate vendor-neutral GC ticks to causal 1-minute features.

Input columns are those emitted by ingest_sierra_gc.py (or a Databento adapter
using the same canonical schema).
"""
from __future__ import annotations

import argparse
import csv
import gzip
from datetime import datetime
from pathlib import Path
from typing import IO

FIELDS = [
    "minute_utc", "contract", "open", "high", "low", "close",
    "volume", "bid_volume", "ask_volume", "delta", "trade_count", "vwap",
    "buy_trade_count", "sell_trade_count", "unknown_trade_count", "source"
]


def _open(path: Path, mode: str) -> IO[str]:
    if path.suffix.lower() == ".gz":
        return gzip.open(path, mode + "t", encoding="utf-8", newline="")
    return path.open(mode, encoding="utf-8", newline="")


def minute_key(ts: str) -> str:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    dt = dt.replace(second=0, microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def new_bucket(row):
    p = float(row["trade_price"])
    size = float(row["trade_size"])
    bid = float(row["bid_volume"])
    ask = float(row["ask_volume"])
    ag = row["aggressor"]
    return {
        "minute_utc": minute_key(row["ts_utc"]),
        "contract": row["contract"],
        "open": p, "high": p, "low": p, "close": p,
        "volume": size, "bid_volume": bid, "ask_volume": ask,
        "delta": ask - bid, "trade_count": 1,
        "pv": p * size,
        "buy_trade_count": int(ag == "BUY"),
        "sell_trade_count": int(ag == "SELL"),
        "unknown_trade_count": int(ag == "UNKNOWN"),
        "source": row["source"],
    }


def add(b, row):
    p = float(row["trade_price"])
    size = float(row["trade_size"])
    bid = float(row["bid_volume"])
    ask = float(row["ask_volume"])
    b["high"] = max(b["high"], p)
    b["low"] = min(b["low"], p)
    b["close"] = p
    b["volume"] += size
    b["bid_volume"] += bid
    b["ask_volume"] += ask
    b["delta"] += ask - bid
    b["trade_count"] += 1
    b["pv"] += p * size
    ag = row["aggressor"]
    b["buy_trade_count"] += int(ag == "BUY")
    b["sell_trade_count"] += int(ag == "SELL")
    b["unknown_trade_count"] += int(ag == "UNKNOWN")


def emit(writer, b):
    if b is None:
        return
    out = {k: b[k] for k in FIELDS if k != "vwap"}
    out["vwap"] = b["pv"] / b["volume"] if b["volume"] > 0 else b["close"]
    writer.writerow(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with _open(args.input, "r") as src, _open(args.output, "w") as dst:
        reader = csv.DictReader(src)
        writer = csv.DictWriter(dst, fieldnames=FIELDS)
        writer.writeheader()
        bucket = None
        last_ts = None
        rows = minutes = 0
        for row in reader:
            rows += 1
            ts = row["ts_utc"]
            if last_ts is not None and ts < last_ts:
                raise ValueError(f"Input is not time ordered: {ts} < {last_ts}")
            last_ts = ts
            key = (minute_key(ts), row["contract"], row["source"])
            if bucket is None:
                bucket = new_bucket(row)
                current = key
            elif key != current:
                emit(writer, bucket)
                minutes += 1
                bucket = new_bucket(row)
                current = key
            else:
                add(bucket, row)
        if bucket is not None:
            emit(writer, bucket)
            minutes += 1

    print({"tick_rows": rows, "minute_rows": minutes, "output": str(args.output)})


if __name__ == "__main__":
    main()
