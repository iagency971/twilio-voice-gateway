#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import databento as db

EXT_REPO = "https://github.com/s-k-28/nq-es-trader-5k-payout.git"
EXT_SHA = "d472d6b442764c2adafbba4bbeb96881c100e3e0"
TZ = "America/New_York"
OUTDIR = Path("mnq-databento/results/cme_validation_v1")
WORK = Path("/tmp/mnq_databento_cme_v1")

REQUEST = {
    "dataset": "GLBX.MDP3",
    "symbols": ["NQ.v.0"],
    "schema": "ohlcv-1m",
    "stype_in": "continuous",
    "start": "2026-06-01T00:00:00Z",
    "end": "2026-08-20T17:40:00Z",
}
MAX_AUTHORIZED_COST_USD = 0.50
EVAL_START = pd.Timestamp("2026-08-03 00:00:00")
EVAL_END = pd.Timestamp("2026-08-19 23:59:59")
HALF_SPLIT = pd.Timestamp("2026-08-12 00:00:00")
EXPECTED_AUG_DATES = [d.date() for d in pd.bdate_range("2026-08-03", "2026-08-19")]


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
        raise RuntimeError(f"Cannot locate Databento event timestamp column: {list(df.columns)}")

    out = pd.DataFrame()
    dt = pd.to_datetime(df[dt_col], errors="coerce")
    if getattr(dt.dt, "tz", None) is not None:
        dt = dt.dt.tz_convert(TZ).dt.tz_localize(None)
    out["datetime"] = dt
    for c in ["open", "high", "low", "close", "volume"]:
        actual = cols.get(c)
        if actual is None:
            raise RuntimeError(f"Missing Databento OHLCV column {c}: {list(df.columns)}")
        out[c] = pd.to_numeric(df[actual], errors="coerce")
    out = out.dropna(subset=["datetime", "open", "high", "low", "close"])
    out = out.sort_values("datetime").reset_index(drop=True)
    return out


def data_qa(d: pd.DataFrame, estimated_cost: float) -> dict:
    dup = int(d.duplicated("datetime").sum())
    bad_ohlc = int(((d.low > d.high) | (d.open < d.low) | (d.open > d.high) |
                    (d.close < d.low) | (d.close > d.high)).sum())
    t = d.datetime.dt.time
    rth = d[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())].copy()
    rth["date"] = rth.datetime.dt.date
    counts = rth.groupby("date").size()
    aug_counts = counts[counts.index.isin(EXPECTED_AUG_DATES)]
    missing_aug = [str(x) for x in EXPECTED_AUG_DATES if x not in set(aug_counts.index)]

    prices = d[["open", "high", "low", "close"]].to_numpy(dtype=float)
    plausible = bool(np.isfinite(prices).all() and np.nanmin(prices) > 10000 and np.nanmax(prices) < 50000)

    delta_min = d.datetime.diff().dt.total_seconds().div(60)
    close_jump = d.close.diff().abs()
    isolated_intraday_jumps = d[(delta_min <= 2.0) & (close_jump > 250.0)][["datetime", "close"]]

    qa = {
        "request": REQUEST,
        "estimated_cost_usd": estimated_cost,
        "rows": int(len(d)),
        "min_datetime_et": str(d.datetime.min()),
        "max_datetime_et": str(d.datetime.max()),
        "duplicate_timestamps": dup,
        "ohlc_consistency_violations": bad_ohlc,
        "expected_aug_rth_dates": len(EXPECTED_AUG_DATES),
        "observed_aug_rth_dates": int(len(aug_counts)),
        "missing_aug_rth_dates": missing_aug,
        "median_aug_rth_bars": float(aug_counts.median()) if len(aug_counts) else None,
        "min_aug_rth_bars": int(aug_counts.min()) if len(aug_counts) else None,
        "price_min": float(np.nanmin(prices)) if len(prices) else None,
        "price_max": float(np.nanmax(prices)) if len(prices) else None,
        "plausible_nq_scale": plausible,
        "isolated_intraday_jump_gt250pt_count": int(len(isolated_intraday_jumps)),
        "isolated_intraday_jump_samples": [
            {"datetime": str(r.datetime), "close": float(r.close)}
            for r in isolated_intraday_jumps.head(10).itertuples()
        ],
    }
    qa["pass"] = bool(
        len(d) > 0 and dup == 0 and bad_ohlc == 0 and not missing_aug and
        qa["median_aug_rth_bars"] is not None and qa["median_aug_rth_bars"] >= 380 and
        plausible and len(isolated_intraday_jumps) == 0
    )
    return qa


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

    t = cme.datetime.dt.time
    rth = cme[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())].copy()
    rth["datetime"] = rth.datetime.dt.normalize()
    cur = rth.groupby("datetime", as_index=False).agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum"))
    combined = pd.concat([hist, cur], ignore_index=True).sort_values("datetime")
    combined = combined.drop_duplicates("datetime", keep="last")
    path = ext / "data" / "databento_combined_daily.csv"
    combined.to_csv(path, index=False)
    return path


def run_external(ext: Path, cme_csv: Path, daily_csv: Path) -> pd.DataFrame:
    out_csv = OUTDIR.resolve() / "external_trades.csv"
    cmd = [sys.executable, "run_multi.py", "--nq", str(cme_csv.resolve()),
           "--nq-daily", str(daily_csv.resolve()), "--csv", str(out_csv)]
    p = subprocess.run(cmd, cwd=ext, text=True, capture_output=True, timeout=1800)
    (OUTDIR / "external_stdout.txt").write_text(p.stdout)
    (OUTDIR / "external_stderr.txt").write_text(p.stderr)
    if p.returncode != 0:
        raise RuntimeError(f"External run failed rc={p.returncode}: {p.stderr[-3000:]}")
    return pd.read_csv(out_csv)


def rescore(df: pd.DataFrame, extra_points: float) -> np.ndarray:
    risk_points = pd.to_numeric(df.risk_ticks, errors="coerce").to_numpy(dtype=float) * 0.25
    total_r = pd.to_numeric(df.total_r, errors="coerce").to_numpy(dtype=float)
    if np.any(risk_points <= 0) or np.any(~np.isfinite(risk_points)):
        raise RuntimeError("Invalid risk_points in external trade ledger")
    return total_r - extra_points / risk_points


def grouped(df: pd.DataFrame, value_col: str, group_col: str) -> dict:
    return {str(k): stats(g[value_col].to_numpy()) for k, g in df.groupby(group_col)}


def remove_best_mean(vals: np.ndarray, pct: float) -> tuple[float | None, int]:
    a = np.asarray(vals, dtype=float)
    if len(a) == 0:
        return None, 0
    n = max(1, int(np.ceil(len(a) * pct)))
    keep = np.sort(a)[:-n] if n < len(a) else np.array([], dtype=float)
    return (float(keep.mean()) if len(keep) else None), n


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("DATABENTO_API_KEY missing")
    client = db.Historical(key)

    estimated_cost = float(client.metadata.get_cost(**REQUEST))
    dump({
        "status": "PRE_DOWNLOAD_COST_CHECK",
        "estimated_cost_usd": estimated_cost,
        "max_authorized_cost_usd": MAX_AUTHORIZED_COST_USD,
        "request": REQUEST,
        "authorized": estimated_cost <= MAX_AUTHORIZED_COST_USD,
        "data_downloaded": False,
    }, "pre_download_cost_check.json")
    if estimated_cost > MAX_AUTHORIZED_COST_USD:
        dump({"status": "ABORT_COST_EXCEEDS_AUTHORIZATION", "estimated_cost_usd": estimated_cost}, "RESULT.json")
        return

    store = client.timeseries.get_range(**REQUEST)
    cme = normalize_db_frame(store)
    cme.to_csv(OUTDIR / "databento_nq_1m.csv.gz", index=False, compression="gzip")

    qa = data_qa(cme, estimated_cost)
    dump(qa, "data_qa.json")
    if not qa["pass"]:
        dump({
            "status": "CME_DATA_QA_FAIL_NO_ECONOMIC_INTERPRETATION",
            "external_commit": EXT_SHA,
            "data_qa": qa,
        }, "RESULT.json")
        return

    ext = ensure_external()
    cme_csv = ext / "data" / "databento_nq_1m.csv"
    cme.to_csv(cme_csv, index=False)
    daily_csv = build_daily_context(ext, cme)
    trades = run_external(ext, cme_csv, daily_csv)
    trades["entry_time"] = pd.to_datetime(trades.entry_time, errors="coerce")
    trades = trades.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)

    # All Jun-Jul trades are retained only as diagnostics. Confirmatory economics are Aug3-Aug19.
    ev = trades[(trades.entry_time >= EVAL_START) & (trades.entry_time <= EVAL_END)].copy().reset_index(drop=True)
    if ev.empty:
        raise RuntimeError("Pinned engine generated no confirmatory August trades")

    ev["primary_r"] = rescore(ev, 1.0)
    ev["stress_r"] = rescore(ev, 2.0)
    ev["half"] = np.where(ev.entry_time < HALF_SPLIT, "Aug03_11", "Aug12_19")
    ev["date"] = ev.entry_time.dt.date.astype(str)
    ev.to_csv(OUTDIR / "august_trades_rescored.csv", index=False)

    # Diagnostic Jun-Jul official CME, never allowed to rescue August.
    diag = trades[(trades.entry_time >= pd.Timestamp("2026-06-01")) &
                  (trades.entry_time < pd.Timestamp("2026-08-01"))].copy().reset_index(drop=True)
    if len(diag):
        diag["primary_r"] = rescore(diag, 1.0)
        diag["stress_r"] = rescore(diag, 2.0)
        diag["month"] = diag.entry_time.dt.to_period("M").astype(str)
        diag.to_csv(OUTDIR / "jun_jul_trades_diagnostic.csv", index=False)

    prim = stats(ev.primary_r.to_numpy())
    stress_s = stats(ev.stress_r.to_numpy())
    rb10, rb_n = remove_best_mean(ev.primary_r.to_numpy(), 0.10)

    observed_aug_days = qa["observed_aug_rth_dates"]
    tpd = float(len(ev) / observed_aug_days) if observed_aug_days else 0.0
    halves = grouped(ev, "primary_r", "half")

    gates = {
        "data_qa_pass": bool(qa["pass"]),
        "n_ge_25": len(ev) >= 25,
        "trades_per_day_ge_1_5": tpd >= 1.5,
        "primary_mean_ge_0_10R": prim["mean"] is not None and prim["mean"] >= 0.10,
        "primary_pf_ge_1_25": prim["pf"] is not None and prim["pf"] >= 1.25,
        "aug03_11_positive": halves.get("Aug03_11", {}).get("sum", 0.0) > 0,
        "aug12_19_positive": halves.get("Aug12_19", {}).get("sum", 0.0) > 0,
        "primary_max_dd_le_7R": prim["max_dd"] is not None and prim["max_dd"] <= 7.0,
        "remove_best_10pct_mean_nonnegative": rb10 is not None and rb10 >= 0.0,
        "stress_mean_positive": stress_s["mean"] is not None and stress_s["mean"] > 0.0,
        "stress_pf_ge_1_10": stress_s["pf"] is not None and stress_s["pf"] >= 1.10,
    }
    verdict = "CME_AUGUST_CONFIRMATORY_PASS_FOR_PROPFIRM_SIMULATION" if all(gates.values()) else "CME_AUGUST_CONFIRMATORY_NO_GO"

    result = {
        "status": verdict,
        "external_repo": EXT_REPO,
        "external_commit": EXT_SHA,
        "databento_request": REQUEST,
        "estimated_cost_usd": estimated_cost,
        "data_qa": qa,
        "evaluation_start": str(EVAL_START),
        "evaluation_end": str(EVAL_END),
        "observed_august_rth_days": observed_aug_days,
        "trades_per_day": tpd,
        "scenarios": {
            "PRIMARY": {
                "full": prim,
                "by_half": halves,
                "by_model": grouped(ev, "primary_r", "model"),
                "by_direction": grouped(ev, "primary_r", "direction"),
                "remove_best_10pct_mean": rb10,
                "removed_best_n": rb_n,
            },
            "STRESS": {
                "full": stress_s,
                "by_half": grouped(ev, "stress_r", "half"),
                "by_model": grouped(ev, "stress_r", "model"),
                "by_direction": grouped(ev, "stress_r", "direction"),
            },
        },
        "jun_jul_diagnostic_only": {
            "n": int(len(diag)),
            "PRIMARY": stats(diag.primary_r.to_numpy()) if len(diag) else stats([]),
            "STRESS": stats(diag.stress_r.to_numpy()) if len(diag) else stats([]),
            "by_month_primary": grouped(diag, "primary_r", "month") if len(diag) else {},
        },
        "gates": gates,
        "notes": [
            "Official Databento CME NQ.v.0 OHLCV-1m is authoritative for this verdict.",
            "Pinned May-31 external trade logic is executed unchanged.",
            "Only deterministic additional friction is subtracted after trade-path generation.",
            "Jun-Jul official CME is diagnostic only and cannot rescue a failed August gate.",
            "No post-outcome model/direction/date rescue is permitted.",
        ],
    }
    dump(result, "RESULT.json")
    print(json.dumps(result, indent=2, allow_nan=False, default=str))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        dump({
            "status": "CME_VALIDATION_INVALID_ABORT",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }, "RESULT.json")
        raise
