#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("yahoo_v1_base", HERE / "run_v1.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

# V1.1 pre-outcome QA date amendment only.
base.QA_START = pd.Timestamp("2026-07-28 09:30:00")
base.QA_END = pd.Timestamp("2026-07-31 15:59:59")


def bridged_source_qa(yahoo: pd.DataFrame, outdir: Path) -> dict:
    get = base.load_getdata()
    y = yahoo[(yahoo.datetime >= base.QA_START) & (yahoo.datetime <= base.QA_END)].copy()
    g = get[(get.datetime >= base.QA_START) & (get.datetime <= base.QA_END)].copy()

    yt = y.datetime.dt.time
    gt = g.datetime.dt.time
    lo, hi = pd.Timestamp("09:30").time(), pd.Timestamp("15:59").time()
    y = y[(yt >= lo) & (yt <= hi)]
    g = g[(gt >= lo) & (gt <= hi)]

    m = y.merge(g, on="datetime", suffixes=("_yahoo", "_get"))
    for c in ["open", "high", "low", "close"]:
        m[f"{c}_abs_diff"] = (m[f"{c}_yahoo"] - m[f"{c}_get"]).abs()
    m["max_ohlc_abs_diff"] = m[[f"{c}_abs_diff" for c in ["open", "high", "low", "close"]]].max(axis=1)

    overlap_days = int(m.datetime.dt.normalize().nunique()) if len(m) else 0
    qa = {
        "mode": "bridged_recent_price_parity_v1_1",
        "yahoo_getdata_overlap_days": overlap_days,
        "yahoo_getdata_overlap_minute_bars": int(len(m)),
        "median_abs_close_diff": float(m.close_abs_diff.median()) if len(m) else None,
        "pct_close_within_1pt": float((m.close_abs_diff <= 1.0).mean()) if len(m) else None,
        "median_max_ohlc_abs_diff": float(m.max_ohlc_abs_diff.median()) if len(m) else None,
        "pct_max_ohlc_within_2pt": float((m.max_ohlc_abs_diff <= 2.0).mean()) if len(m) else None,
        "bridge_prior_true_mnq_evidence": {
            "overlap_days": 39,
            "median_abs_entry_diff": 0.25,
            "median_abs_exit_diff": 0.25,
            "pct_entries_within_1pt": 0.9743589743589743,
            "pct_exits_within_1pt": 0.9230769230769231,
            "pct_exits_within_2pt": 0.9743589743589743,
            "direction_agreement": 0.9743589743589743,
            "known_anomaly": "2026-06-16",
        },
    }
    qa["pass"] = bool(
        qa["yahoo_getdata_overlap_days"] >= 4 and
        qa["yahoo_getdata_overlap_minute_bars"] >= 1200 and
        qa["median_abs_close_diff"] is not None and qa["median_abs_close_diff"] <= 0.50 and
        qa["pct_close_within_1pt"] is not None and qa["pct_close_within_1pt"] >= 0.95 and
        qa["median_max_ohlc_abs_diff"] is not None and qa["median_max_ohlc_abs_diff"] <= 0.50 and
        qa["pct_max_ohlc_within_2pt"] is not None and qa["pct_max_ohlc_within_2pt"] >= 0.95
    )
    (outdir / "source_qa_v1_1.json").write_text(json.dumps(qa, indent=2, allow_nan=False))
    if len(m):
        m.to_csv(outdir / "yahoo_getdata_parity_v1_1.csv", index=False)
    return qa


def absolute_run_external(ext: Path, yahoo_csv: Path, daily_csv: Path, outdir: Path) -> pd.DataFrame:
    out_csv = (outdir / "external_trades.csv").resolve()
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "run_multi.py", "--nq", str(yahoo_csv), "--nq-daily", str(daily_csv), "--csv", str(out_csv)]
    p = subprocess.run(cmd, cwd=ext, text=True, capture_output=True, timeout=1200)
    (outdir / "external_stdout.txt").write_text(p.stdout)
    (outdir / "external_stderr.txt").write_text(p.stderr)
    if p.returncode != 0:
        raise RuntimeError(f"External run failed rc={p.returncode}: {p.stderr[-2500:]}")
    return pd.read_csv(out_csv)


base.source_qa = bridged_source_qa
base.run_external = absolute_run_external

base.main()

# Reporting-only annotation; no economic values are modified.
result_path = Path("mnq-12model-yahoo/results/v1/RESULT.json")
if result_path.exists():
    obj = json.loads(result_path.read_text())
    obj["protocol_version"] = "V1.1_PREOUTCOME_QA_AMENDMENT"
    obj["source_qa_interpretation"] = "Bridged Yahoo->GetData Jul28-31 plus prior GetData->true-MNQ audit through Jul27; screening only, not licensed CME validation."
    notes = obj.get("notes", [])
    notes = [n for n in notes if "true MNQ ledger" not in n]
    notes.append("Yahoo source is bridged-parity gated under AMENDMENT_V1_1_PREOUTCOME.md; no direct Yahoo/true-MNQ date overlap was available.")
    obj["notes"] = notes
    result_path.write_text(json.dumps(obj, indent=2, allow_nan=False))
    print(json.dumps(obj, indent=2, allow_nan=False))
