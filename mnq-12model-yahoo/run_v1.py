#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf

EXT_REPO = "https://github.com/s-k-28/nq-es-trader-5k-payout.git"
EXT_SHA = "d472d6b442764c2adafbba4bbeb96881c100e3e0"
TICKER = "NQ=F"
TZ = "America/New_York"
GET_URL = "https://raw.githubusercontent.com/getdata-finance/nq-1m-ohlcv-stocks-historical-data/main/NQ_1m.csv"
GET_SHA = "232fbc18375e6475dbe3b99e6e1504da69c58a962aa7a358b14f4e2b61cf229d"
TRUE_LOG_URL = "https://raw.githubusercontent.com/dng-nguyn/mnq-intraday-momentum-backtest/main/results/trade_log.csv"
EVAL_START = pd.Timestamp("2026-08-03 00:00:00")
EVAL_END = pd.Timestamp("2026-08-20 23:59:59")
QA_START = pd.Timestamp("2026-07-22 09:30:00")
QA_END = pd.Timestamp("2026-07-27 15:59:59")


def _pf(a: np.ndarray):
    pos = a[a > 0].sum()
    neg = -a[a < 0].sum()
    if neg > 0:
        return float(pos / neg)
    return 1e99 if pos > 0 else None


def _stats(vals):
    a = np.asarray(vals, dtype=float)
    if len(a) == 0:
        return {"n": 0, "mean": None, "sum": 0.0, "pf": None, "win_rate": None,
                "max_dd": None, "losing_streak": None}
    eq = np.cumsum(a)
    peak = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(peak - eq, 0.0)
    cur = ls = 0
    for v in a:
        if v < 0:
            cur += 1
            ls = max(ls, cur)
        else:
            cur = 0
    return {"n": int(len(a)), "mean": float(a.mean()), "sum": float(a.sum()),
            "pf": _pf(a), "win_rate": float((a > 0).mean()),
            "max_dd": float(dd.max(initial=0.0)), "losing_streak": int(ls)}


def _normalize_yf_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])
    f = frame.copy()
    if isinstance(f.columns, pd.MultiIndex):
        # yfinance may return either (Price,Ticker) or (Ticker,Price); select the price level.
        price_names = {"Open", "High", "Low", "Close", "Volume"}
        if set(map(str, f.columns.get_level_values(0))) & price_names:
            f.columns = f.columns.get_level_values(0)
        elif set(map(str, f.columns.get_level_values(-1))) & price_names:
            f.columns = f.columns.get_level_values(-1)
        else:
            raise RuntimeError(f"Unexpected yfinance MultiIndex columns: {f.columns}")
    idx = pd.DatetimeIndex(f.index)
    if idx.tz is None:
        idx = idx.tz_localize(TZ)
    else:
        idx = idx.tz_convert(TZ)
    out = pd.DataFrame({
        "datetime": idx.tz_localize(None),
        "open": pd.to_numeric(f["Open"], errors="coerce").to_numpy(),
        "high": pd.to_numeric(f["High"], errors="coerce").to_numpy(),
        "low": pd.to_numeric(f["Low"], errors="coerce").to_numpy(),
        "close": pd.to_numeric(f["Close"], errors="coerce").to_numpy(),
        "volume": pd.to_numeric(f["Volume"], errors="coerce").fillna(0).to_numpy(),
    })
    return out.dropna(subset=["datetime", "open", "high", "low", "close"])


def download_yahoo(outdir: Path) -> pd.DataFrame:
    # Small chunks avoid Yahoo's fine-interval range restrictions. All requested dates are recent.
    chunks = [
        ("2026-07-21", "2026-07-28"),
        ("2026-07-28", "2026-08-04"),
        ("2026-08-04", "2026-08-11"),
        ("2026-08-11", "2026-08-18"),
        ("2026-08-18", "2026-08-21"),
    ]
    frames = []
    qa_chunks = []
    for start, end in chunks:
        raw = yf.download(TICKER, start=start, end=end, interval="1m", prepost=True,
                          auto_adjust=False, progress=False, threads=False, timeout=30)
        f = _normalize_yf_frame(raw)
        qa_chunks.append({"start": start, "end": end, "rows": int(len(f)),
                          "min": str(f.datetime.min()) if len(f) else None,
                          "max": str(f.datetime.max()) if len(f) else None})
        if len(f):
            frames.append(f)
    if not frames:
        raise RuntimeError("Yahoo returned no NQ=F 1-minute data")
    d = pd.concat(frames, ignore_index=True).sort_values("datetime").drop_duplicates("datetime", keep="last")
    d = d[(d.datetime >= pd.Timestamp("2026-07-21")) & (d.datetime <= EVAL_END)].copy()
    if d.empty:
        raise RuntimeError("Yahoo data empty after date filter")
    d.to_csv(outdir / "yahoo_nq_1m.csv", index=False)
    (outdir / "yahoo_download_qa.json").write_text(json.dumps({
        "ticker": TICKER, "chunks": qa_chunks, "rows": int(len(d)),
        "min": str(d.datetime.min()), "max": str(d.datetime.max()),
        "unique_dates": int(d.datetime.dt.normalize().nunique())
    }, indent=2))
    return d


def load_getdata() -> pd.DataFrame:
    rr = requests.get(GET_URL, timeout=180); rr.raise_for_status()
    if hashlib.sha256(rr.content).hexdigest() != GET_SHA:
        raise RuntimeError("GetData reference snapshot changed")
    d = pd.read_csv(io.BytesIO(rr.content))
    d["datetime"] = pd.to_datetime(d["datetime"], utc=True, errors="coerce")
    for c in ["open", "high", "low", "close", "volume"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["datetime", "open", "high", "low", "close"])
    d["datetime"] = d["datetime"].dt.tz_convert(TZ).dt.tz_localize(None)
    return d[["datetime", "open", "high", "low", "close", "volume"]].sort_values("datetime").drop_duplicates("datetime")


def source_qa(yahoo: pd.DataFrame, outdir: Path) -> dict:
    get = load_getdata()
    y = yahoo[(yahoo.datetime >= QA_START) & (yahoo.datetime <= QA_END)].copy()
    g = get[(get.datetime >= QA_START) & (get.datetime <= QA_END)].copy()
    # RTH only for full-minute parity.
    yt = y.datetime.dt.time
    gt = g.datetime.dt.time
    y = y[(yt >= pd.Timestamp("09:30").time()) & (yt <= pd.Timestamp("15:59").time())]
    g = g[(gt >= pd.Timestamp("09:30").time()) & (gt <= pd.Timestamp("15:59").time())]
    m = y.merge(g, on="datetime", suffixes=("_yahoo", "_get"))
    m["close_abs_diff"] = (m.close_yahoo - m.close_get).abs()
    overlap_days = int(m.datetime.dt.normalize().nunique()) if len(m) else 0

    rr = requests.get(TRUE_LOG_URL, timeout=180); rr.raise_for_status()
    t = pd.read_csv(io.BytesIO(rr.content))
    t["date"] = pd.to_datetime(t["date"], errors="coerce").dt.normalize()
    t = t[(t.variant == "eta_r1") & (pd.to_numeric(t.k, errors="coerce") == 300)]
    t = t[(t.date >= QA_START.normalize()) & (t.date <= QA_END.normalize())]
    true_rows = []
    for _, r in t.iterrows():
        day = pd.Timestamp(r.date)
        yd = yahoo[yahoo.datetime.dt.normalize().eq(day)]
        e = yd[(yd.datetime.dt.hour == 15) & (yd.datetime.dt.minute == 30)]
        x = yd[(yd.datetime.dt.hour == 15) & (yd.datetime.dt.minute == 59)]
        if len(e) == 1 and len(x) == 1:
            true_rows.append({
                "date": str(day.date()),
                "entry_abs_diff": abs(float(e.iloc[0].open) - float(r.entry_price)),
                "exit_abs_diff": abs(float(x.iloc[0].close) - float(r.exit_price)),
            })
    tr = pd.DataFrame(true_rows)
    qa = {
        "yahoo_getdata_overlap_days": overlap_days,
        "yahoo_getdata_overlap_minute_bars": int(len(m)),
        "median_abs_close_diff": float(m.close_abs_diff.median()) if len(m) else None,
        "pct_close_within_1pt": float((m.close_abs_diff <= 1.0).mean()) if len(m) else None,
        "true_mnq_overlap_days": int(len(tr)),
        "median_true_entry_abs_diff": float(tr.entry_abs_diff.median()) if len(tr) else None,
        "median_true_exit_abs_diff": float(tr.exit_abs_diff.median()) if len(tr) else None,
    }
    qa["pass"] = bool(
        qa["yahoo_getdata_overlap_days"] >= 3 and
        qa["yahoo_getdata_overlap_minute_bars"] >= 900 and
        qa["median_abs_close_diff"] is not None and qa["median_abs_close_diff"] <= 0.50 and
        qa["pct_close_within_1pt"] is not None and qa["pct_close_within_1pt"] >= 0.95 and
        qa["true_mnq_overlap_days"] >= 3 and
        qa["median_true_entry_abs_diff"] is not None and qa["median_true_entry_abs_diff"] <= 1.0 and
        qa["median_true_exit_abs_diff"] is not None and qa["median_true_exit_abs_diff"] <= 1.0
    )
    (outdir / "source_qa.json").write_text(json.dumps(qa, indent=2, allow_nan=False))
    if len(m): m.to_csv(outdir / "yahoo_getdata_parity.csv", index=False)
    if len(tr): tr.to_csv(outdir / "yahoo_true_mnq_parity.csv", index=False)
    return qa


def ensure_external(work: Path) -> Path:
    ext = work / "external"
    if not ext.exists():
        subprocess.run(["git", "clone", "--quiet", EXT_REPO, str(ext)], check=True)
    subprocess.run(["git", "checkout", "--quiet", EXT_SHA], cwd=ext, check=True)
    got = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ext, text=True).strip()
    if got != EXT_SHA:
        raise RuntimeError(f"External commit mismatch: {got}")
    return ext


def build_daily_context(ext: Path, yahoo: pd.DataFrame) -> Path:
    hist = pd.read_csv(ext / "data" / "NQ_daily.csv")
    hist.columns = [str(c).strip().lower().replace(" ", "_") for c in hist.columns]
    date_col = "datetime" if "datetime" in hist.columns else ("date" if "date" in hist.columns else hist.columns[0])
    hist["datetime"] = pd.to_datetime(hist[date_col], errors="coerce").dt.normalize()
    for c in ["open", "high", "low", "close", "volume"]:
        hist[c] = pd.to_numeric(hist[c], errors="coerce")
    hist = hist.dropna(subset=["datetime", "open", "high", "low", "close"])[["datetime", "open", "high", "low", "close", "volume"]]

    t = yahoo.datetime.dt.time
    rth = yahoo[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())].copy()
    rth["date"] = rth.datetime.dt.normalize()
    cur = rth.groupby("date", as_index=False).agg(open=("open", "first"), high=("high", "max"),
                                                  low=("low", "min"), close=("close", "last"), volume=("volume", "sum"))
    cur = cur.rename(columns={"date": "datetime"})
    combined = pd.concat([hist, cur], ignore_index=True).sort_values("datetime").drop_duplicates("datetime", keep="last")
    path = ext / "data" / "yahoo_combined_daily.csv"
    combined.to_csv(path, index=False)
    return path


def run_external(ext: Path, yahoo_csv: Path, daily_csv: Path, outdir: Path) -> pd.DataFrame:
    out_csv = outdir / "external_trades.csv"
    cmd = [sys.executable, "run_multi.py", "--nq", str(yahoo_csv), "--nq-daily", str(daily_csv), "--csv", str(out_csv)]
    p = subprocess.run(cmd, cwd=ext, text=True, capture_output=True, timeout=1200)
    (outdir / "external_stdout.txt").write_text(p.stdout)
    (outdir / "external_stderr.txt").write_text(p.stderr)
    if p.returncode != 0:
        raise RuntimeError(f"External run failed rc={p.returncode}: {p.stderr[-2500:]}")
    return pd.read_csv(out_csv)


def rescore(df: pd.DataFrame, extra_points: float) -> np.ndarray:
    risk_points = pd.to_numeric(df.risk_ticks, errors="coerce") * 0.25
    return pd.to_numeric(df.total_r, errors="coerce").to_numpy() - extra_points / risk_points.to_numpy()


def group_stats(df: pd.DataFrame, col: str, key: str):
    return {str(k): _stats(g[col].to_numpy()) for k, g in df.groupby(key)} if len(df) else {}


def main():
    outdir = Path("mnq-12model-yahoo/results/v1"); outdir.mkdir(parents=True, exist_ok=True)
    try:
        work = Path("/tmp/mnq12yahoo"); work.mkdir(parents=True, exist_ok=True)
        yahoo = download_yahoo(outdir)
        qa = source_qa(yahoo, outdir)
        ext = ensure_external(work)
        yahoo_csv = ext / "data" / "yahoo_nq_recent.csv"
        yahoo.to_csv(yahoo_csv, index=False)
        daily_csv = build_daily_context(ext, yahoo)
        trades = run_external(ext, yahoo_csv, daily_csv, outdir)
        trades["entry_time"] = pd.to_datetime(trades.entry_time, errors="coerce")
        ev = trades[(trades.entry_time >= EVAL_START) & (trades.entry_time <= EVAL_END)].copy().sort_values("entry_time").reset_index(drop=True)
        # Observed August RTH days from Yahoo, not just days with trades.
        tt = yahoo.datetime.dt.time
        rth = yahoo[(yahoo.datetime >= EVAL_START) & (yahoo.datetime <= EVAL_END) &
                    (tt >= pd.Timestamp("09:30").time()) & (tt < pd.Timestamp("16:00").time())]
        observed_days = int(rth.datetime.dt.normalize().nunique())
        if ev.empty:
            raise RuntimeError("External engine generated no August trades")
        ev["primary_r"] = rescore(ev, 1.0)
        ev["stress_r"] = rescore(ev, 2.0)
        ev["half"] = np.where(ev.entry_time < pd.Timestamp("2026-08-12"), "Aug03_11", "Aug12_20")
        ev.to_csv(outdir / "trades_rescored.csv", index=False)

        result = {"status": "", "external_commit": EXT_SHA, "data_qa": qa,
                  "evaluation_start": str(EVAL_START), "evaluation_end": str(EVAL_END),
                  "observed_august_rth_days": observed_days, "scenarios": {}, "gates": {}}
        for sc, col in [("PRIMARY", "primary_r"), ("STRESS", "stress_r")]:
            vals = ev[col].to_numpy()
            cut = max(1, int(np.ceil(len(vals) * 0.10)))
            rem = np.sort(vals)[:-cut] if len(vals) > cut else np.array([])
            result["scenarios"][sc] = {
                "full": _stats(vals),
                "by_half": group_stats(ev, col, "half"),
                "by_model": group_stats(ev, col, "model"),
                "by_direction": group_stats(ev, col, "direction"),
                "remove_best_10pct_mean": float(rem.mean()) if len(rem) else None,
                "removed_best_n": cut,
            }

        p = result["scenarios"]["PRIMARY"]["full"]
        s = result["scenarios"]["STRESS"]["full"]
        halves = result["scenarios"]["PRIMARY"]["by_half"]
        rem = result["scenarios"]["PRIMARY"]["remove_best_10pct_mean"]
        tpd = p["n"] / max(observed_days, 1)
        gates = {
            "data_qa_pass": bool(qa.get("pass")),
            "n_ge_25": p["n"] >= 25,
            "trades_per_day_ge_1_5": tpd >= 1.5,
            "primary_mean_ge_0_10R": p["mean"] is not None and p["mean"] >= 0.10,
            "primary_pf_ge_1_25": p["pf"] is not None and p["pf"] >= 1.25,
            "aug03_11_positive": halves.get("Aug03_11", {}).get("sum", 0) > 0,
            "aug12_20_positive": halves.get("Aug12_20", {}).get("sum", 0) > 0,
            "primary_max_dd_le_7R": p["max_dd"] is not None and p["max_dd"] <= 7.0,
            "remove_best_10pct_mean_nonnegative": rem is not None and rem >= 0,
            "stress_mean_positive": s["mean"] is not None and s["mean"] > 0,
            "stress_pf_ge_1_10": s["pf"] is not None and s["pf"] >= 1.10,
        }
        result["trades_per_day"] = tpd
        result["gates"] = gates
        if not qa.get("pass"):
            result["status"] = "MNQ_12MODEL_YAHOO_V1_DATA_QA_FAIL_NO_ECONOMIC_INTERPRETATION"
        elif all(gates.values()):
            result["status"] = "MNQ_12MODEL_YAHOO_V1_FORWARD_PASS_JUSTIFIES_LICENSED_CME_VALIDATION"
        else:
            result["status"] = "MNQ_12MODEL_YAHOO_V1_FORWARD_NO_GO"
        result["notes"] = [
            "August 3-20 outcomes were not used to modify the pinned May-31 ensemble before this run.",
            "Yahoo is independently parity-gated against late-July GetData and true MNQ ledger before economic interpretation.",
            "External trade logic is unchanged; only additional friction is subtracted after the fact.",
            "No post-outcome model/direction/date rescue is permitted on August results."
        ]
        (outdir / "RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        print(json.dumps(result, indent=2, allow_nan=False))
    except Exception as e:
        obj = {"status": "MNQ_12MODEL_YAHOO_V1_INVALID_ABORT", "error": repr(e)}
        (outdir / "RESULT.json").write_text(json.dumps(obj, indent=2))
        print(json.dumps(obj, indent=2)); raise

if __name__ == "__main__":
    main()
