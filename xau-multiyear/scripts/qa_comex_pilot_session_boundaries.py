#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import databento as db

NY = ZoneInfo("America/New_York")


def load(path: Path) -> pd.DataFrame:
    x = db.DBNStore.from_file(path).to_df(map_symbols=True).reset_index(drop=False)
    x["ts_event"] = pd.to_datetime(x["ts_event"], utc=True)
    return x.sort_values("ts_event").reset_index(drop=True)


def qa_one(date: str, path: Path) -> dict:
    x = load(path)
    ts = x.ts_event
    local = ts.dt.tz_convert(NY)
    gaps = ts.diff().dt.total_seconds().div(60)
    gap_rows = []
    for i in gaps[gaps >= 15].index:
        a = ts.iloc[i - 1]
        b = ts.iloc[i]
        mid = a + (b - a) / 2
        gap_rows.append(
            {
                "gap_start_utc": a.isoformat(),
                "gap_end_utc": b.isoformat(),
                "gap_start_ny": a.tz_convert(NY).isoformat(),
                "gap_end_ny": b.tz_convert(NY).isoformat(),
                "gap_mid_hour_ny": float(mid.tz_convert(NY).hour + mid.tz_convert(NY).minute / 60),
                "gap_minutes": float((b - a).total_seconds() / 60),
            }
        )
    maintenance_candidates = [g for g in gap_rows if 16.0 <= g["gap_mid_hour_ny"] <= 19.5]
    best = max(maintenance_candidates, key=lambda z: z["gap_minutes"]) if maintenance_candidates else None
    in_17_18 = (local.dt.hour == 17)
    inst = sorted(int(v) for v in pd.Series(x.get("instrument_id", pd.Series(dtype=float))).dropna().unique())
    seq = pd.to_numeric(x.get("sequence", pd.Series(dtype=float)), errors="coerce")
    seq_back = int((seq.diff() < 0).sum()) if len(seq) else 0
    return {
        "research_trading_date": date,
        "records": int(len(x)),
        "first_trade_utc": ts.min().isoformat() if len(ts) else None,
        "last_trade_utc": ts.max().isoformat() if len(ts) else None,
        "first_trade_ny": local.min().isoformat() if len(local) else None,
        "last_trade_ny": local.max().isoformat() if len(local) else None,
        "instrument_ids": inst,
        "instrument_count": len(inst),
        "sequence_backward_steps": seq_back,
        "trades_during_17xx_ny": int(in_17_18.sum()),
        "gaps_ge_15m": int(len(gap_rows)),
        "maintenance_gap_candidate": best,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-root", required=True)
    ap.add_argument("--sessions", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root = Path(args.raw_root)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sessions = pd.read_csv(args.sessions)
    rows = []
    for r in sessions.itertuples():
        files = list(root.rglob(f"{r.research_trading_date}__trades.dbn.zst"))
        if len(files) != 1:
            raise SystemExit(f"expected exactly one paid trades file for {r.research_trading_date}, got {len(files)}")
        z = qa_one(str(r.research_trading_date), files[0])
        z["era"] = str(r.era)
        z["year"] = int(r.year)
        rows.append(z)
    frame = pd.DataFrame(rows)
    flat = frame.copy()
    flat["instrument_ids"] = flat.instrument_ids.map(json.dumps)
    flat["maintenance_gap_candidate"] = flat.maintenance_gap_candidate.map(json.dumps)
    flat.to_csv(out / "pilot_session_boundary_qa.csv", index=False)
    maint = [r["maintenance_gap_candidate"] for r in rows if r["maintenance_gap_candidate"]]
    result = {
        "version": "COMEX_PILOT_SESSION_BOUNDARY_QA_V1",
        "market_data_download_performed": False,
        "source": "existing paid 12-session trades artifact",
        "sessions": len(rows),
        "sessions_with_multiple_instruments": int(sum(r["instrument_count"] > 1 for r in rows)),
        "sessions_with_17xx_ny_trades": int(sum(r["trades_during_17xx_ny"] > 0 for r in rows)),
        "total_17xx_ny_trades": int(sum(r["trades_during_17xx_ny"] for r in rows)),
        "sessions_with_maintenance_gap_candidate": int(len(maint)),
        "maintenance_gap_minutes_min": min((g["gap_minutes"] for g in maint), default=None),
        "maintenance_gap_minutes_median": float(pd.Series([g["gap_minutes"] for g in maint]).median()) if maint else None,
        "maintenance_gap_minutes_max": max((g["gap_minutes"] for g in maint), default=None),
        "sequence_backward_steps_total": int(sum(r["sequence_backward_steps"] for r in rows)),
        "note": "This QA does not infer trade direction or strategy outcomes. It only checks raw paid pilot files for session-boundary and mapping behavior.",
    }
    (out / "pilot_session_boundary_qa.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
