#!/usr/bin/env python3
"""Read Sierra Chart .scid files directly and normalize 1-tick GC records.

This avoids a manual text export. The binary layout follows Sierra Chart's
published Intraday Data File Format (header 56 bytes, record 40 bytes).

For a single-trade record:
- Close = trade price
- High = ask at trade time
- Low = bid at trade time
- BidVolume > 0 => sell aggressor
- AskVolume > 0 => buy aggressor
"""
from __future__ import annotations

import argparse
import csv
import gzip
import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import IO

HEADER = struct.Struct("<4sIIHHI36s")  # 56 bytes
RECORD = struct.Struct("<qffffIIII")    # 40 bytes
EPOCH = datetime(1899, 12, 30, tzinfo=timezone.utc)
FIELDS = [
    "ts_utc", "contract", "trade_price", "trade_size",
    "bid_price", "ask_price", "bid_volume", "ask_volume",
    "aggressor", "source"
]


def _open_out(path: Path) -> IO[str]:
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "wt", encoding="utf-8", newline="")
    return path.open("w", encoding="utf-8", newline="")


def dt_iso(us_since_epoch: int) -> str:
    return (EPOCH + timedelta(microseconds=us_since_epoch)).isoformat().replace("+00:00", "Z")


def side(bid_vol: int, ask_vol: int) -> str:
    if ask_vol > 0 and bid_vol == 0:
        return "BUY"
    if bid_vol > 0 and ask_vol == 0:
        return "SELL"
    return "UNKNOWN"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="Sierra .scid file")
    ap.add_argument("--contract", help="Exact GC contract; defaults to input filename stem")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--allow-aggregated", action="store_true", help="Allow records with NumTrades != 1 (not recommended)")
    args = ap.parse_args()

    contract = args.contract or args.input.stem
    args.output.parent.mkdir(parents=True, exist_ok=True)
    stats = {"rows": 0, "buy": 0, "sell": 0, "unknown": 0, "aggregated": 0}
    first_ts = last_ts = None

    with args.input.open("rb") as f:
        raw = f.read(HEADER.size)
        if len(raw) != HEADER.size:
            raise SystemExit("SCID file too short for header")
        magic, header_size, record_size, version, _unused1, _utc_start, _reserve = HEADER.unpack(raw)
        if magic != b"SCID":
            raise SystemExit(f"Not a Sierra SCID file: magic={magic!r}")
        if header_size != HEADER.size:
            raise SystemExit(f"Unsupported SCID header size {header_size}; expected {HEADER.size}")
        if record_size != RECORD.size:
            raise SystemExit(f"Unsupported SCID record size {record_size}; expected {RECORD.size}")
        if version != 1:
            raise SystemExit(f"Unsupported SCID version {version}")

        with _open_out(args.output) as out:
            writer = csv.DictWriter(out, fieldnames=FIELDS)
            writer.writeheader()
            rec_no = 0
            while True:
                buf = f.read(RECORD.size)
                if not buf:
                    break
                if len(buf) != RECORD.size:
                    raise SystemExit(f"Truncated SCID record at #{rec_no + 1}")
                rec_no += 1
                dt_us, opn, high, low, close, ntrades, total_vol, bid_vol, ask_vol = RECORD.unpack(buf)

                if ntrades != 1:
                    stats["aggregated"] += 1
                    if not args.allow_aggregated:
                        raise SystemExit(
                            f"Record #{rec_no} has NumTrades={ntrades}; canonical research requires Sierra Intraday Data Storage Time Unit = 1 Tick."
                        )
                ts = dt_iso(dt_us)
                first_ts = first_ts or ts
                last_ts = ts
                ag = side(bid_vol, ask_vol)
                stats["rows"] += 1
                stats[ag.lower()] += 1
                writer.writerow({
                    "ts_utc": ts,
                    "contract": contract,
                    "trade_price": close,
                    "trade_size": total_vol,
                    "bid_price": low if ntrades == 1 else "",
                    "ask_price": high if ntrades == 1 else "",
                    "bid_volume": bid_vol,
                    "ask_volume": ask_vol,
                    "aggressor": ag,
                    "source": "SIERRA_CHART_SCID",
                })

    print({
        "input": str(args.input), "output": str(args.output), "contract": contract,
        "first_ts": first_ts, "last_ts": last_ts, **stats,
    })


if __name__ == "__main__":
    main()
