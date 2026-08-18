#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import databento as db

NY = ZoneInfo("America/New_York")
DATASET = "GLBX.MDP3"
SYMBOL = "GC.v.0"
STYPE_IN = "continuous"
ALLOWED_SCHEMAS = {"trades", "tbbo"}
DEFAULT_CAP_USD = 4.03
PER_REQUEST_QUOTE_TOLERANCE_USD = 0.00020


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def bounds(date_str: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    d = pd.Timestamp(date_str)
    prev = (d - pd.Timedelta(days=1)).date()
    cur = d.date()
    return (
        pd.Timestamp(f"{prev} 17:00:00", tz=NY).tz_convert("UTC"),
        pd.Timestamp(f"{cur} 18:00:00", tz=NY).tz_convert("UTC"),
    )


def retry(fn, *args, **kwargs):
    err = None
    for k in range(7):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            err = exc
            time.sleep(min(20, 2**k))
    raise RuntimeError(f"Databento call failed after retries: {err}")


def meta_cost(client: db.Historical, schema: str, start: pd.Timestamp, end: pd.Timestamp) -> float:
    return float(
        retry(
            client.metadata.get_cost,
            dataset=DATASET,
            symbols=SYMBOL,
            stype_in=STYPE_IN,
            schema=schema,
            start=start.isoformat(),
            end=end.isoformat(),
        )
    )


def meta_count(client: db.Historical, schema: str, start: pd.Timestamp, end: pd.Timestamp) -> int:
    return int(
        retry(
            client.metadata.get_record_count,
            dataset=DATASET,
            symbols=SYMBOL,
            stype_in=STYPE_IN,
            schema=schema,
            start=start.isoformat(),
            end=end.isoformat(),
        )
    )


def gate(args: argparse.Namespace) -> None:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")
    sessions = pd.read_csv(args.sessions)
    required = {"era", "research_trading_date", "year", "quarter", "vol_band", "panel_rank_v4"}
    missing = required - set(sessions.columns)
    if missing:
        raise SystemExit(f"pilot sessions missing columns: {sorted(missing)}")
    if len(sessions) != 12 or sessions.research_trading_date.duplicated().any():
        raise SystemExit("pilot session file must contain exactly 12 unique dates")
    weekdays = pd.to_datetime(sessions.research_trading_date).dt.weekday
    if (weekdays >= 5).any():
        raise SystemExit("pilot contains weekend date; acquisition blocked")

    client = db.Historical(key)
    rows = []
    for r in sessions.itertuples():
        start, end = bounds(str(r.research_trading_date))
        for schema in ("trades", "tbbo"):
            cost = meta_cost(client, schema, start, end)
            records = meta_count(client, schema, start, end)
            rows.append(
                {
                    "era": r.era,
                    "research_trading_date": str(r.research_trading_date),
                    "year": int(r.year),
                    "quarter": int(r.quarter),
                    "vol_band": int(r.vol_band),
                    "panel_rank_v4": int(r.panel_rank_v4),
                    "schema": schema,
                    "start_utc": start.isoformat(),
                    "end_utc": end.isoformat(),
                    "quoted_cost_usd": cost,
                    "quoted_records": records,
                }
            )
    total = float(sum(x["quoted_cost_usd"] for x in rows))
    cap = float(args.cap_usd)
    if total > cap + 1e-12:
        raise SystemExit(f"HARD GATE: current quote ${total:.9f} exceeds approved cap ${cap:.2f}; no download")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    matrix = {"include": rows}
    (out / "matrix.json").write_text(json.dumps(matrix, separators=(",", ":")), encoding="utf-8")
    gate_doc = {
        "version": "COMEX_V4_PILOT12_DOWNLOAD_GATE_V1",
        "dataset": DATASET,
        "symbol": SYMBOL,
        "schemas": ["trades", "tbbo"],
        "sessions": 12,
        "requests": len(rows),
        "approved_cap_usd": cap,
        "current_pre_download_quote_usd": total,
        "remaining_margin_usd": cap - total,
        "download_performed": False,
        "rows": rows,
    }
    (out / "gate.json").write_text(json.dumps(gate_doc, indent=2), encoding="utf-8")
    print(json.dumps(gate_doc, indent=2))


def download_one(args: argparse.Namespace) -> None:
    if args.schema not in ALLOWED_SCHEMAS:
        raise SystemExit(f"schema not authorized: {args.schema}")
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)
    if start.tzinfo is None or end.tzinfo is None:
        raise SystemExit("start/end must be timezone-aware")
    expected = float(args.expected_cost)
    client = db.Historical(key)
    current = meta_cost(client, args.schema, start, end)
    tolerance = float(args.tolerance_usd)
    if current > expected + tolerance + 1e-12:
        raise SystemExit(
            f"REQUEST GATE: {args.date} {args.schema} quote rose from ${expected:.9f} "
            f"to ${current:.9f}, tolerance ${tolerance:.5f}; no download"
        )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    raw = out / f"{args.date}__{args.schema}.dbn.zst"
    if raw.exists():
        raise SystemExit(f"refusing to overwrite existing raw file: {raw}")

    # This is the only market-data request in this command.
    store = client.timeseries.get_range(
        dataset=DATASET,
        symbols=SYMBOL,
        stype_in=STYPE_IN,
        schema=args.schema,
        start=start.isoformat(),
        end=end.isoformat(),
        path=str(raw),
    )
    df = store.to_df(map_symbols=True)
    if len(df) == 0:
        raise RuntimeError("download returned zero records")

    side_missing = None
    side_counts = None
    if "side" in df.columns:
        s = df["side"].astype(str)
        miss = s.isin(["N", "None", "nan", "NaN", "", "0"])
        side_missing = int(miss.sum())
        side_counts = {str(k): int(v) for k, v in s.value_counts(dropna=False).to_dict().items()}

    qa = {
        "version": "COMEX_V4_PILOT12_RAW_FILE_V1",
        "era": args.era,
        "research_trading_date": args.date,
        "schema": args.schema,
        "dataset": DATASET,
        "symbol_request": SYMBOL,
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "gate_quote_usd": expected,
        "immediate_pre_download_quote_usd": current,
        "quote_tolerance_usd": tolerance,
        "records_downloaded": int(len(df)),
        "raw_file": raw.name,
        "raw_file_bytes": int(raw.stat().st_size),
        "sha256": sha256_file(raw),
        "instrument_ids": sorted(int(x) for x in pd.Series(df["instrument_id"]).dropna().unique()) if "instrument_id" in df.columns else [],
        "symbols": sorted(str(x) for x in pd.Series(df["symbol"]).dropna().unique()) if "symbol" in df.columns else [],
        "side_missing_records": side_missing,
        "side_counts": side_counts,
        "download_performed": True,
    }
    (out / f"{args.date}__{args.schema}.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
    print(json.dumps(qa, indent=2))


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gate")
    g.add_argument("--sessions", required=True)
    g.add_argument("--out", required=True)
    g.add_argument("--cap-usd", type=float, default=DEFAULT_CAP_USD)
    d = sub.add_parser("download-one")
    d.add_argument("--era", required=True)
    d.add_argument("--date", required=True)
    d.add_argument("--schema", required=True)
    d.add_argument("--start", required=True)
    d.add_argument("--end", required=True)
    d.add_argument("--expected-cost", required=True, type=float)
    d.add_argument("--tolerance-usd", type=float, default=PER_REQUEST_QUOTE_TOLERANCE_USD)
    d.add_argument("--out", required=True)
    return ap.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.cmd == "gate":
        gate(args)
    else:
        download_one(args)
