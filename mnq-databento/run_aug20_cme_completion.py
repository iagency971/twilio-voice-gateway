#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import databento as db
import numpy as np
import pandas as pd

EXT_REPO = "https://github.com/s-k-28/nq-es-trader-5k-payout.git"
EXT_SHA = "d472d6b442764c2adafbba4bbeb96881c100e3e0"
TZ = "America/New_York"
TARGET_DATE = pd.Timestamp("2026-08-20")
OUTDIR = Path("mnq-databento/results/aug20_cme_completion")
ARCHIVE = Path("mnq-databento/results/cme_validation_v1/databento_nq_1m.csv.gz")
WORK = Path("/tmp/mnq_aug20_cme_completion")
REQUEST = {
    "dataset": "GLBX.MDP3",
    "symbols": ["NQ.v.0"],
    "schema": "ohlcv-1m",
    "stype_in": "continuous",
    "start": "2026-08-20T17:40:00Z",  # 13:40 ET
    "end": "2026-08-20T20:00:00Z",    # exclusive; 16:00 ET
}
MAX_AUTHORIZED_COST_USD = 0.001


def dump(obj, name: str) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / name).write_text(json.dumps(obj, indent=2, allow_nan=False, default=str))


def pf(vals: np.ndarray):
    pos = vals[vals > 0].sum()
    neg = -vals[vals < 0].sum()
    if neg > 0:
        return float(pos / neg)
    return 1e99 if pos > 0 else None


def stats(vals) -> dict:
    a = np.asarray(vals, dtype=float)
    if len(a) == 0:
        return {"n": 0, "mean": None, "sum": 0.0, "pf": None,
                "win_rate": None, "max_dd": None, "losing_streak": None}
    eq = np.cumsum(a)
    peaks = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(peaks - eq, 0.0)
    cur = longest = 0
    for v in a:
        if v < 0:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    return {
        "n": int(len(a)),
        "mean": float(a.mean()),
        "sum": float(a.sum()),
        "pf": pf(a),
        "win_rate": float((a > 0).mean()),
        "max_dd": float(dd.max(initial=0.0)),
        "losing_streak": int(longest),
    }


def normalize_db_frame(store) -> pd.DataFrame:
    df = store.to_df(tz=TZ).reset_index()
    cols = {str(c).lower(): c for c in df.columns}
    dt_col = None
    for candidate in ("ts_event", "timestamp", "datetime", "index"):
        if candidate in cols:
            dt_col = cols[candidate]
            break
    if dt_col is None:
        for c in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[c]):
                dt_col = c
                break
    if dt_col is None:
        raise RuntimeError(f"Cannot locate timestamp column: {list(df.columns)}")
    dt = pd.to_datetime(df[dt_col], errors="coerce")
    if getattr(dt.dt, "tz", None) is not None:
        dt = dt.dt.tz_convert(TZ).dt.tz_localize(None)
    out = pd.DataFrame({"datetime": dt})
    for c in ["open", "high", "low", "close", "volume"]:
        actual = cols.get(c)
        if actual is None:
            raise RuntimeError(f"Missing Databento OHLCV column {c}")
        out[c] = pd.to_numeric(df[actual], errors="coerce")
    return (out.dropna(subset=["datetime", "open", "high", "low", "close"])
               .sort_values("datetime").drop_duplicates("datetime", keep="last")
               .reset_index(drop=True))


def ensure_external() -> Path:
    ext = WORK / "external"
    if not ext.exists():
        subprocess.run(["git", "clone", "--quiet", EXT_REPO, str(ext)], check=True)
    subprocess.run(["git", "checkout", "--quiet", EXT_SHA], cwd=ext, check=True)
    got = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ext, text=True).strip()
    if got != EXT_SHA:
        raise RuntimeError(f"External commit mismatch: {got}")
    return ext


def build_daily_context(ext: Path, cme: pd.DataFrame) -> Path:
    hist = pd.read_csv(ext / "data" / "NQ_daily.csv")
    hist.columns = [str(c).strip().lower().replace(" ", "_") for c in hist.columns]
    date_col = "datetime" if "datetime" in hist.columns else ("date" if "date" in hist.columns else hist.columns[0])
    hist["datetime"] = pd.to_datetime(hist[date_col], errors="coerce").dt.normalize()
    for c in ["open", "high", "low", "close", "volume"]:
        hist[c] = pd.to_numeric(hist[c], errors="coerce")
    hist = hist.dropna(subset=["datetime", "open", "high", "low", "close"])
    hist = hist[["datetime", "open", "high", "low", "close", "volume"]]

    tt = cme.datetime.dt.time
    rth = cme[(tt >= pd.Timestamp("09:30").time()) & (tt < pd.Timestamp("16:00").time())].copy()
    rth["datetime"] = rth.datetime.dt.normalize()
    cur = rth.groupby("datetime", as_index=False).agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum"))
    both = pd.concat([hist, cur], ignore_index=True).sort_values("datetime")
    both = both.drop_duplicates("datetime", keep="last")
    path = ext / "data" / "databento_aug20_complete_daily.csv"
    both.to_csv(path, index=False)
    return path


def run_external(ext: Path, cme: pd.DataFrame, daily: Path) -> pd.DataFrame:
    inp = ext / "data" / "databento_aug20_complete_1m.csv"
    cme.to_csv(inp, index=False)
    outcsv = OUTDIR.resolve() / "external_trades_all.csv"
    cmd = [sys.executable, "run_multi.py", "--nq", str(inp.resolve()),
           "--nq-daily", str(daily.resolve()), "--csv", str(outcsv)]
    p = subprocess.run(cmd, cwd=ext, text=True, capture_output=True, timeout=1800)
    (OUTDIR / "external_stdout.txt").write_text(p.stdout)
    (OUTDIR / "external_stderr.txt").write_text(p.stderr)
    if p.returncode != 0:
        raise RuntimeError(f"External run failed rc={p.returncode}: {p.stderr[-3000:]}")
    return pd.read_csv(outcsv)


def rescore(df: pd.DataFrame, extra_points: float) -> np.ndarray:
    risk_points = pd.to_numeric(df.risk_ticks, errors="coerce").to_numpy(dtype=float) * 0.25
    total_r = pd.to_numeric(df.total_r, errors="coerce").to_numpy(dtype=float)
    if np.any(risk_points <= 0) or np.any(~np.isfinite(risk_points)):
        raise RuntimeError("Invalid risk_points")
    return total_r - extra_points / risk_points


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    if not ARCHIVE.exists():
        raise RuntimeError(f"Archived CME file missing: {ARCHIVE}")
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("DATABENTO_API_KEY missing")

    client = db.Historical(key)
    cost = float(client.metadata.get_cost(**REQUEST))
    dump({"status": "PRE_DOWNLOAD_COST_CHECK", "request": REQUEST,
          "estimated_cost_usd": cost, "max_authorized_cost_usd": MAX_AUTHORIZED_COST_USD,
          "authorized": cost <= MAX_AUTHORIZED_COST_USD, "data_downloaded": False},
         "pre_download_cost_check.json")
    if cost > MAX_AUTHORIZED_COST_USD:
        dump({"status": "ABORT_COST_EXCEEDS_AUTHORIZATION", "estimated_cost_usd": cost}, "RESULT.json")
        return

    # The only paid request in this diagnostic: the missing Aug20 tail.
    tail_store = client.timeseries.get_range(**REQUEST)
    tail = normalize_db_frame(tail_store)
    tail.to_csv(OUTDIR / "aug20_missing_tail.csv.gz", index=False, compression="gzip")

    archived = pd.read_csv(ARCHIVE, compression="gzip")
    archived["datetime"] = pd.to_datetime(archived["datetime"], errors="coerce")
    for c in ["open", "high", "low", "close", "volume"]:
        archived[c] = pd.to_numeric(archived[c], errors="coerce")
    archived = archived.dropna(subset=["datetime", "open", "high", "low", "close"])
    combined = (pd.concat([archived, tail], ignore_index=True)
                  .sort_values("datetime")
                  .drop_duplicates("datetime", keep="last")
                  .reset_index(drop=True))

    tt = combined.datetime.dt.time
    aug20_rth = combined[(combined.datetime.dt.normalize() == TARGET_DATE) &
                         (tt >= pd.Timestamp("09:30").time()) &
                         (tt < pd.Timestamp("16:00").time())].copy()
    qa = {
        "status": "AUG20_CME_DATA_COMPLETION_QA",
        "estimated_incremental_cost_usd": cost,
        "tail_rows": int(len(tail)),
        "tail_min_datetime_et": str(tail.datetime.min()) if len(tail) else None,
        "tail_max_datetime_et": str(tail.datetime.max()) if len(tail) else None,
        "aug20_rth_rows_after_merge": int(len(aug20_rth)),
        "aug20_rth_first": str(aug20_rth.datetime.min()) if len(aug20_rth) else None,
        "aug20_rth_last": str(aug20_rth.datetime.max()) if len(aug20_rth) else None,
        "duplicates_after_merge": int(combined.duplicated("datetime").sum()),
        "ohlc_violations_aug20": int(((aug20_rth.low > aug20_rth.high) |
                                      (aug20_rth.open < aug20_rth.low) |
                                      (aug20_rth.open > aug20_rth.high) |
                                      (aug20_rth.close < aug20_rth.low) |
                                      (aug20_rth.close > aug20_rth.high)).sum()),
    }
    qa["pass"] = bool(len(tail) == 140 and len(aug20_rth) == 390 and
                      qa["duplicates_after_merge"] == 0 and qa["ohlc_violations_aug20"] == 0)
    dump(qa, "data_qa.json")
    if not qa["pass"]:
        dump({"status": "AUG20_CME_COMPLETION_QA_FAIL_NO_ECONOMIC_INTERPRETATION", "data_qa": qa}, "RESULT.json")
        return

    ext = ensure_external()
    daily = build_daily_context(ext, combined)
    trades = run_external(ext, combined, daily)
    trades["entry_time"] = pd.to_datetime(trades.entry_time, errors="coerce")
    trades = trades.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)
    day = trades[trades.entry_time.dt.normalize() == TARGET_DATE].copy().reset_index(drop=True)
    if day.empty:
        raise RuntimeError("Pinned engine generated no Aug20 trades on complete CME data")

    day["primary_r"] = rescore(day, 1.0)
    day["stress_r"] = rescore(day, 2.0)
    day.to_csv(OUTDIR / "aug20_trades_rescored.csv", index=False)

    result = {
        "status": "CME_AUG20_DIAGNOSTIC_REMEASUREMENT_COMPLETE",
        "classification": "POST_CONFIRMATORY_DIAGNOSTIC_ONLY_DOES_NOT_CHANGE_AUG3_19_NO_GO",
        "external_repo": EXT_REPO,
        "external_commit": EXT_SHA,
        "official_data": "Databento GLBX.MDP3 NQ.v.0 ohlcv-1m",
        "incremental_request": REQUEST,
        "incremental_cost_usd": cost,
        "data_qa": qa,
        "PRIMARY": stats(day.primary_r.to_numpy()),
        "STRESS": stats(day.stress_r.to_numpy()),
        "trades": day[["entry_time", "exit_time", "direction", "model", "tag", "reason",
                       "risk_ticks", "total_r", "primary_r", "stress_r"]].to_dict("records"),
        "notes": [
            "Aug20 was already observed on Yahoo before this CME completion, so this is diagnostic remeasurement, not new forward evidence.",
            "No model, direction, threshold, stop, target, time window, or weighting was changed.",
            "The prior CME Aug3-Aug19 confirmatory NO_GO remains unchanged."
        ]
    }
    dump(result, "RESULT.json")
    print(json.dumps(result, indent=2, allow_nan=False, default=str))


if __name__ == "__main__":
    main()
