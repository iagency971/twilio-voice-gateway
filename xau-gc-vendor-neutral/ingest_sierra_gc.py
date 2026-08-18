#!/usr/bin/env python3
"""Normalize Sierra Chart GC intraday exports into a vendor-neutral tick stream.

Expected Sierra export header (names may contain spaces):
Date,Time,Open,High,Low,Last,Volume,NumberOfTrades,BidVolume,AskVolume

For Sierra 1-tick records, Last is the actual trade price. BidVolume is volume
executed at bid or lower (sell aggressor), AskVolume at ask or higher (buy aggressor).

Output is gzip CSV by default and is deliberately simple/streaming so multi-year
exports do not need to fit in RAM.
"""
from __future__ import annotations

import argparse
import csv
import gzip
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Dict, Iterable

OUT_FIELDS = [
    "ts_utc",
    "contract",
    "trade_price",
    "trade_size",
    "bid_volume",
    "ask_volume",
    "aggressor",
    "source",
]


def _open_text(path: Path, mode: str) -> IO[str]:
    if path.suffix.lower() == ".gz":
        return gzip.open(path, mode + "t", encoding="utf-8", newline="")
    return path.open(mode, encoding="utf-8-sig", newline="")


def _norm_key(k: str) -> str:
    return "".join(ch for ch in k.lower() if ch.isalnum())


def _canon_row(raw: Dict[str, str]) -> Dict[str, str]:
    return {_norm_key(k): (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}


def _pick(r: Dict[str, str], *names: str, default: str = "") -> str:
    for name in names:
        key = _norm_key(name)
        if key in r and r[key] != "":
            return r[key]
    return default


def parse_ts(date_s: str, time_s: str) -> str:
    # Sierra intraday text export timestamps are UTC according to Sierra docs.
    fmts = ("%Y/%m/%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S")
    value = f"{date_s} {time_s}"
    for fmt in fmts:
        try:
            dt = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        except ValueError:
            pass
    raise ValueError(f"Unsupported Sierra timestamp: {value!r}")


def as_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def aggressor(bid_volume: float, ask_volume: float) -> str:
    if ask_volume > 0 and bid_volume == 0:
        return "BUY"
    if bid_volume > 0 and ask_volume == 0:
        return "SELL"
    return "UNKNOWN"


def iter_ticks(reader: Iterable[Dict[str, str]], contract: str):
    for line_no, raw in enumerate(reader, start=2):
        r = _canon_row(raw)
        try:
            ts = parse_ts(_pick(r, "Date"), _pick(r, "Time"))
            last = as_float(_pick(r, "Last", "Close"))
            volume = as_float(_pick(r, "Volume"))
            bid_vol = as_float(_pick(r, "BidVolume", "Bid Volume"))
            ask_vol = as_float(_pick(r, "AskVolume", "Ask Volume"))
            num_trades = int(as_float(_pick(r, "NumberOfTrades", "Number of Trades", default="1"), 1.0))
        except Exception as exc:
            raise ValueError(f"Bad Sierra row at line {line_no}: {exc}") from exc

        # Canonical tick research requires one-trade records. Do not silently
        # pretend aggregated records are ticks.
        if num_trades != 1:
            raise ValueError(
                f"Line {line_no}: NumberOfTrades={num_trades}. Export/load Sierra data at 1-tick granularity before normalization."
            )
        if last <= 0 or volume < 0:
            raise ValueError(f"Line {line_no}: invalid trade price/volume")

        yield {
            "ts_utc": ts,
            "contract": contract,
            "trade_price": f"{last:.10f}".rstrip("0").rstrip("."),
            "trade_size": f"{volume:.10f}".rstrip("0").rstrip("."),
            "bid_volume": f"{bid_vol:.10f}".rstrip("0").rstrip("."),
            "ask_volume": f"{ask_vol:.10f}".rstrip("0").rstrip("."),
            "aggressor": aggressor(bid_vol, ask_vol),
            "source": "SIERRA_CHART",
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="Sierra intraday text/CSV export (.txt/.csv/.gz)")
    ap.add_argument("--contract", required=True, help="Exact GC contract, e.g. GCZ25")
    ap.add_argument("--output", type=Path, required=True, help="Normalized .csv or .csv.gz")
    args = ap.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    buy = sell = unknown = 0
    first_ts = last_ts = None

    with _open_text(args.input, "r") as src, _open_text(args.output, "w") as dst:
        reader = csv.DictReader(src)
        if not reader.fieldnames:
            raise SystemExit("Input has no header")
        writer = csv.DictWriter(dst, fieldnames=OUT_FIELDS)
        writer.writeheader()
        for row in iter_ticks(reader, args.contract):
            writer.writerow(row)
            count += 1
            first_ts = first_ts or row["ts_utc"]
            last_ts = row["ts_utc"]
            if row["aggressor"] == "BUY":
                buy += 1
            elif row["aggressor"] == "SELL":
                sell += 1
            else:
                unknown += 1

    print({
        "rows": count,
        "contract": args.contract,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "buy_rows": buy,
        "sell_rows": sell,
        "unknown_rows": unknown,
        "output": str(args.output),
    })


if __name__ == "__main__":
    main()
