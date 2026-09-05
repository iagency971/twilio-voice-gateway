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
AMENDMENT = Path("us100-zero-data/PROTOCOL_OR_FAMILY_V1_2_PARTIAL_2025_OOS_AMENDMENT.md")
SOURCE_REPO = "CodyOutcast/Academic-Paper-Data-Source"
SOURCE_COMMIT = "50052606c16d71850755e6dbdda02d43b4399c2b"
EXPECTED_DEV_BLOB_SHA = "d0b6fc1789d876a677eeeb0f3e0027ad1554179c"
POINT = 0.1
YEAR = 2025
EXPECTED_START = pd.Timestamp("2025-01-02 01:00:00")
EXPECTED_END = pd.Timestamp("2025-04-30 23:59:00")


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


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
    pf = pos / neg if neg > 0 else (1e99 if pos > 0 else None)
    cur = longest = 0
    for v in a:
        if v < 0:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    return {
        "n": int(len(a)), "mean": float(a.mean()), "sum": float(a.sum()),
        "pf": float(pf) if pf is not None else None,
        "win_rate": float((a > 0).mean()),
        "max_dd": float(dd.max(initial=0.0)), "losing_streak": int(longest),
    }


def load_data() -> tuple[pd.DataFrame, dict]:
    url = (f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/"
           "OHLC-USTEC-M1-2025.csv")
    p = Path("/tmp/OHLC-USTEC-M1-2025.csv")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    p.write_bytes(r.content)
    d = pd.read_csv(p, sep=";")
    d.columns = [str(c).strip().lower() for c in d.columns]
    d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    for c in ["open", "high", "low", "close", "volume", "spread"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["time", "open", "high", "low", "close", "spread"]).copy()
    d = d.sort_values("time").reset_index(drop=True)
    d["spread_px"] = d.spread * POINT
    d["date"] = d.time.dt.date
    d["minute"] = d.time.dt.hour * 60 + d.time.dt.minute
    dup = int(d.duplicated("time").sum())
    bad_ohlc = int(((d.low > d.high) | (d.open < d.low) | (d.open > d.high) |
                    (d.close < d.low) | (d.close > d.high)).sum())
    bad_spread = int(((~np.isfinite(d.spread)) | (d.spread < 0)).sum())
    sc = d[(d.minute >= dev.OR_START_MIN) & (d.minute < dev.SIGNAL_CUTOFF_MIN)].groupby("date").size()
    candidate_sessions = int((sc >= 120).sum())
    qa = {
        "rows": int(len(d)), "first": str(d.time.min()), "last": str(d.time.max()),
        "duplicates": dup, "ohlc_violations": bad_ohlc, "bad_spread": bad_spread,
        "candidate_sessions": candidate_sessions,
        "median_recorded_spread_points": float(d.spread.median()),
        "median_spread_price": float(d.spread_px.median()),
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
    }
    qa["pass"] = bool(
        dup == 0 and bad_ohlc == 0 and bad_spread == 0 and
        d.time.min() == EXPECTED_START and d.time.max() == EXPECTED_END and
        candidate_sessions >= 80
    )
    return d, qa


def run_scenario(d: pd.DataFrame, spread_mult: float):
    trades = []
    sessions = 0
    for _, g in d.groupby("date", sort=True):
        g = g.reset_index(drop=True)
        if dev.session_is_candidate(g, 30):
            sessions += 1
        t = dev.simulate_day(g, YEAR, "ORB", 30, 2.0, spread_mult)
        if t is not None:
            trades.append(t)
    return trades, sessions


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not UNLOCK.exists() or not AMENDMENT.exists():
        raise RuntimeError("frozen OOS authorization/amendment missing")
    unlock = json.loads(UNLOCK.read_text())
    if unlock.get("selected") != {"family": "ORB", "range_min": 30, "rr": 2.0}:
        raise RuntimeError("frozen selection mismatch")
    got_blob = git_blob_sha(Path("us100-zero-data/run_or_family_dev_v1.py").read_bytes())
    if got_blob != EXPECTED_DEV_BLOB_SHA or got_blob != unlock.get("dev_runner_git_blob_sha"):
        raise RuntimeError(f"DEV runner changed: {got_blob}")

    d, qa = load_data()
    if not qa["pass"]:
        result = {"status": "OR_FAMILY_V1_2_JAN_APR_2025_DATA_QA_FAIL", "data_qa": qa}
        (OUT / "OOS_JAN_APR_2025_RESULT.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        return

    pt, sessions = run_scenario(d, 1.0)
    st, s_sessions = run_scenario(d, 2.0)
    if sessions != s_sessions:
        raise RuntimeError("session denominator changed under spread stress")
    p = stats([t.r for t in pt]); s = stats([t.r for t in st])
    p["sessions"] = sessions; p["frequency"] = len(pt) / sessions if sessions else 0.0
    s["sessions"] = s_sessions; s["frequency"] = len(st) / s_sessions if s_sessions else 0.0

    months = {}
    for m in (1, 2, 3, 4):
        months[f"2025-{m:02d}"] = stats([t.r for t in pt if pd.Timestamp(t.date).month == m])
    positive_months = sum(v["sum"] > 0 for v in months.values())

    a = np.asarray([t.r for t in pt], dtype=float)
    remove_n = max(1, int(np.ceil(len(a) * 0.10))) if len(a) else 0
    remaining = np.sort(a)[:-remove_n] if len(a) > remove_n else np.array([], dtype=float)
    remove_best_mean = float(remaining.mean()) if len(remaining) else None

    gate = {
        "n_ge_30": p["n"] >= 30,
        "frequency_ge_0_40": p["frequency"] >= 0.40,
        "primary_expectancy_ge_0_05": p["mean"] is not None and p["mean"] >= 0.05,
        "primary_pf_ge_1_15": p["pf"] is not None and p["pf"] >= 1.15,
        "primary_max_dd_le_12R": p["max_dd"] is not None and p["max_dd"] <= 12.0,
        "positive_months_ge_3_of_4": positive_months >= 3,
        "stress_expectancy_gt_0": s["mean"] is not None and s["mean"] > 0,
        "stress_pf_ge_1_05": s["pf"] is not None and s["pf"] >= 1.05,
        "remove_best_10pct_mean_ge_0": remove_best_mean is not None and remove_best_mean >= 0,
    }
    passed = all(gate.values())
    status = ("OR_FAMILY_V1_JAN_APR_2025_OOS_PASS_REQUIRES_FTMO_FEED_PARITY"
              if passed else "OR_FAMILY_V1_JAN_APR_2025_OOS_NO_GO")
    result = {
        "status": status,
        "classification": "SEALED_JAN_APR_2025_SINGLE_VARIANT_OOS",
        "source_repo": SOURCE_REPO, "source_commit": SOURCE_COMMIT,
        "selected": {"family": "ORB", "range_min": 30, "rr": 2.0},
        "dev_runner_git_blob_sha": got_blob,
        "data_qa": qa, "PRIMARY": p, "STRESS": s,
        "monthly_primary": months, "positive_months": int(positive_months),
        "remove_best_10pct": {"removed_n": remove_n, "remaining_mean": remove_best_mean},
        "gate": gate, "pass": passed,
        "no_other_2025_variant_opened": True,
    }
    (OUT / "OOS_JAN_APR_2025_RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    pd.DataFrame([{**t.__dict__, "scenario": "PRIMARY"} for t in pt] +
                 [{**t.__dict__, "scenario": "STRESS"} for t in st]).to_csv(
                     OUT / "OOS_JAN_APR_2025_TRADES.csv", index=False)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
