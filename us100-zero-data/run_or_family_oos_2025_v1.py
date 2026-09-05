#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import run_or_family_dev_v1 as dev

OUT = Path("us100-zero-data/results/or_family_v1")
UNLOCK = Path("us100-zero-data/OOS_UNLOCK.json")
SOURCE_REPO = "CodyOutcast/Academic-Paper-Data-Source"
SOURCE_COMMIT = "50052606c16d71850755e6dbdda02d43b4399c2b"
YEAR = 2025
POINT = 0.1
EXPECTED_DEV_BLOB_SHA = "d0b6fc1789d876a677eeeb0f3e0027ad1554179c"


def git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def stats(vals) -> dict:
    a = np.asarray(list(vals), dtype=float)
    if len(a) == 0:
        return {"n": 0, "mean": None, "sum": 0.0, "pf": None,
                "win_rate": None, "max_dd": None, "losing_streak": None}
    eq = np.cumsum(a)
    peaks = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(peaks - eq, 0.0)
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    pf = (pos / neg) if neg > 0 else (1e99 if pos > 0 else None)
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
        "pf": float(pf) if pf is not None else None,
        "win_rate": float((a > 0).mean()),
        "max_dd": float(dd.max(initial=0.0)),
        "losing_streak": int(longest),
    }


def load_2025() -> tuple[pd.DataFrame, dict]:
    url = (f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/"
           f"OHLC-USTEC-M1-{YEAR}.csv")
    p = Path("/tmp/OHLC-USTEC-M1-2025.csv")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    p.write_bytes(r.content)
    d = pd.read_csv(p, sep=";")
    d.columns = [str(c).strip().lower() for c in d.columns]
    expected = ["time", "open", "high", "low", "close", "volume", "spread"]
    missing = [c for c in expected if c not in d.columns]
    if missing:
        raise RuntimeError(f"missing columns {missing}")
    d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    for c in ["open", "high", "low", "close", "volume", "spread"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["time", "open", "high", "low", "close", "spread"]).copy()
    d = d.sort_values("time").reset_index(drop=True)
    dup = int(d.duplicated("time").sum())
    bad_ohlc = int(((d.low > d.high) | (d.open < d.low) | (d.open > d.high) |
                    (d.close < d.low) | (d.close > d.high)).sum())
    bad_spread = int(((~np.isfinite(d.spread)) | (d.spread < 0)).sum())
    d["spread_px"] = d["spread"] * POINT
    d["date"] = d["time"].dt.date
    d["minute"] = d["time"].dt.hour * 60 + d["time"].dt.minute
    session_counts = d[(d.minute >= dev.OR_START_MIN) & (d.minute < dev.SIGNAL_CUTOFF_MIN)].groupby("date").size()
    candidate_sessions = int((session_counts >= 120).sum())
    qa = {
        "year": YEAR,
        "rows": int(len(d)),
        "first": str(d.time.min()),
        "last": str(d.time.max()),
        "duplicates": dup,
        "ohlc_violations": bad_ohlc,
        "bad_spread": bad_spread,
        "candidate_sessions": candidate_sessions,
        "median_recorded_spread_points": float(d.spread.median()),
        "median_spread_price": float(d.spread_px.median()),
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        "pass": bool(dup == 0 and bad_ohlc == 0 and bad_spread == 0 and candidate_sessions >= 200),
    }
    return d, qa


def run_scenario(d: pd.DataFrame, family: str, L: int, rr: float, spread_mult: float):
    trades = []
    sessions = 0
    for _, g in d.groupby("date", sort=True):
        g = g.reset_index(drop=True)
        if dev.session_is_candidate(g, L):
            sessions += 1
        t = dev.simulate_day(g, YEAR, family, L, rr, spread_mult)
        if t is not None:
            trades.append(t)
    return trades, sessions


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not UNLOCK.exists():
        raise RuntimeError("OOS unlock missing")
    unlock = json.loads(UNLOCK.read_text())
    if unlock.get("status") != "OOS_2025_UNLOCK_FROZEN":
        raise RuntimeError("OOS unlock status invalid")
    if unlock.get("source_commit") != SOURCE_COMMIT:
        raise RuntimeError("source commit mismatch")
    dev_code = Path("us100-zero-data/run_or_family_dev_v1.py").read_bytes()
    got_blob = git_blob_sha(dev_code)
    if got_blob != EXPECTED_DEV_BLOB_SHA or got_blob != unlock.get("dev_runner_git_blob_sha"):
        raise RuntimeError(f"DEV code blob mismatch: {got_blob}")

    sel = unlock["selected"]
    family = str(sel["family"])
    L = int(sel["range_min"])
    rr = float(sel["rr"])
    if (family, L, rr) != ("ORB", 30, 2.0):
        raise RuntimeError("unexpected frozen selection")

    d, qa = load_2025()
    if not qa["pass"]:
        result = {"status": "OR_FAMILY_V1_OOS_DATA_QA_FAIL", "data_qa": qa}
        (OUT / "OOS_2025_RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        print(json.dumps(result, indent=2, allow_nan=False))
        return

    p_trades, sessions = run_scenario(d, family, L, rr, 1.0)
    s_trades, s_sessions = run_scenario(d, family, L, rr, 2.0)
    if sessions != s_sessions:
        raise RuntimeError("session denominator changed under stress")

    p = stats([t.r for t in p_trades])
    s = stats([t.r for t in s_trades])
    p["sessions"] = sessions
    p["frequency"] = len(p_trades) / sessions if sessions else 0.0
    s["sessions"] = s_sessions
    s["frequency"] = len(s_trades) / s_sessions if s_sessions else 0.0

    months = {}
    for m in range(1, 13):
        vals = [t.r for t in p_trades if pd.Timestamp(t.date).month == m]
        months[f"2025-{m:02d}"] = stats(vals)
    positive_months = sum(1 for x in months.values() if x["sum"] > 0)

    a = np.asarray([t.r for t in p_trades], dtype=float)
    remove_n = max(1, int(np.ceil(len(a) * 0.10))) if len(a) else 0
    if len(a) > remove_n:
        keep = np.sort(a)[:-remove_n]
        remove_best_mean = float(keep.mean())
    else:
        remove_best_mean = None

    gate = {
        "n_ge_80": p["n"] >= 80,
        "frequency_ge_0_40": p["frequency"] >= 0.40,
        "primary_expectancy_ge_0_05": p["mean"] is not None and p["mean"] >= 0.05,
        "primary_pf_ge_1_15": p["pf"] is not None and p["pf"] >= 1.15,
        "primary_max_dd_le_12R": p["max_dd"] is not None and p["max_dd"] <= 12.0,
        "positive_months_ge_7": positive_months >= 7,
        "stress_expectancy_gt_0": s["mean"] is not None and s["mean"] > 0,
        "stress_pf_ge_1_05": s["pf"] is not None and s["pf"] >= 1.05,
        "remove_best_10pct_mean_ge_0": remove_best_mean is not None and remove_best_mean >= 0,
    }
    passed = all(gate.values())
    status = ("OR_FAMILY_V1_OOS_PASS_REQUIRES_FTMO_FEED_PARITY" if passed
              else "OR_FAMILY_V1_OOS_NO_GO")
    result = {
        "status": status,
        "classification": "SEALED_2025_SINGLE_VARIANT_OOS",
        "source_repo": SOURCE_REPO,
        "source_commit": SOURCE_COMMIT,
        "dev_runner_git_blob_sha": got_blob,
        "selected": sel,
        "data_qa": qa,
        "PRIMARY": p,
        "STRESS": s,
        "monthly_primary": months,
        "positive_months": positive_months,
        "remove_best_10pct": {"removed_n": remove_n, "remaining_mean": remove_best_mean},
        "gate": gate,
        "pass": passed,
        "no_other_2025_variant_opened": True,
    }
    (OUT / "OOS_2025_RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    pd.DataFrame([{**t.__dict__, "scenario": "PRIMARY"} for t in p_trades] +
                 [{**t.__dict__, "scenario": "STRESS"} for t in s_trades]).to_csv(
                     OUT / "OOS_2025_TRADES.csv", index=False)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
