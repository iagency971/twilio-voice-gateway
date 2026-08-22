#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import requests

SOURCE_REPO = "CodyOutcast/Academic-Paper-Data-Source"
SOURCE_COMMIT = "50052606c16d71850755e6dbdda02d43b4399c2b"
YEARS = (2021, 2022, 2023, 2024, 2025)
SERVER_TO_NY_HOURS = 7
SPREAD_POINT_PRICE = 0.1
MODEL_TICK_SIZE = 0.25
OUT = Path("us100-zero-data/results/native_12model_port_v5")
RAW = OUT / "external_trades_raw.csv"
CACHE = Path("/tmp/us100_native12_v5_2_rescore")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(obj, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, indent=2, allow_nan=False, default=str))


def download(year: int) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"OHLC-USTEC-M1-{year}.csv"
    if p.exists() and p.stat().st_size > 1000:
        return p
    url = (f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/"
           f"OHLC-USTEC-M1-{year}.csv")
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    p.write_bytes(r.content)
    return p


def load_spreads(year: int) -> tuple[pd.DataFrame, dict]:
    p = download(year)
    d = pd.read_csv(p, sep=";", low_memory=False)
    d.columns = [str(c).strip().lower() for c in d.columns]
    for c in ["time", "spread"]:
        if c not in d.columns:
            raise RuntimeError(f"{year}: missing {c}")
    d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    d["spread"] = pd.to_numeric(d["spread"], errors="coerce")
    d = d.dropna(subset=["time", "spread"]).copy()
    d = d.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    d["datetime"] = d["time"] - pd.Timedelta(hours=SERVER_TO_NY_HOURS)
    d["spread_price"] = d["spread"] * SPREAD_POINT_PRICE
    d["date"] = d["datetime"].dt.date
    bad = int(((~np.isfinite(d.spread_price)) | (d.spread_price < 0)).sum())
    qa = {
        "year": year,
        "rows": int(len(d)),
        "bad_spread": bad,
        "median_spread_price": float(d.spread_price.median()) if len(d) else None,
        "source_sha256": sha256_file(p),
        "pass": bool(len(d) > 100000 and bad == 0),
    }
    return d[["datetime", "date", "spread_price"]], qa


def complete_rth_days(d: pd.DataFrame) -> set:
    t = d.datetime.dt.time
    r = d[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())].copy()
    counts = r.groupby("date").size()
    return set(counts[counts >= 380].index)


def pf(vals: np.ndarray):
    a = np.asarray(vals, dtype=float)
    pos = a[a > 0].sum()
    neg = -a[a < 0].sum()
    if neg > 0:
        return float(pos / neg)
    if pos > 0:
        return 1e99
    return None


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


def challenge_plan(expectancy: float, trades_per_day: float, max_dd: float, worst_daily_r: float) -> dict:
    if not (expectancy > 0 and trades_per_day > 0 and max_dd > 0):
        return {"safe": None, "aggressive": None}
    levels = {
        "safe": min(0.005, 0.08 / (2.0 * max_dd)),
        "aggressive": min(0.005, 0.08 / (1.5 * max_dd)),
    }
    out = {}
    for name, risk in levels.items():
        daily_loss = abs(min(0.0, worst_daily_r)) * risk
        admissible = daily_loss < 0.04
        expected_daily = expectancy * trades_per_day * risk
        out[name] = {
            "risk_pct_per_trade": float(risk),
            "risk_dollars_on_10k": float(risk * 10000.0),
            "observed_worst_daily_loss_pct": float(daily_loss),
            "admissible_daily_limit_buffer": bool(admissible),
            "expected_daily_return_pct": float(expected_daily),
            "step1_days_theoretical": float(0.10 / expected_daily) if admissible and expected_daily > 0 else None,
            "step2_days_theoretical": float(0.05 / expected_daily) if admissible and expected_daily > 0 else None,
            "total_2step_days_theoretical": float(0.15 / expected_daily) if admissible and expected_daily > 0 else None,
        }
    return out


def main() -> None:
    if not RAW.exists():
        raise RuntimeError(f"Frozen raw ledger missing: {RAW}")
    raw_sha = sha256_file(RAW)
    tr = pd.read_csv(RAW)
    for c in ["entry_time", "exit_time"]:
        tr[c] = pd.to_datetime(tr[c], errors="coerce")
    tr["risk_ticks"] = pd.to_numeric(tr["risk_ticks"], errors="coerce")
    tr["total_r"] = pd.to_numeric(tr["total_r"], errors="coerce")
    tr = tr.dropna(subset=["entry_time", "exit_time", "risk_ticks", "total_r"]).copy()
    tr = tr.sort_values("entry_time").reset_index(drop=True)
    tr["risk_points"] = tr.risk_ticks * MODEL_TICK_SIZE
    if len(tr) == 0 or (tr.risk_points <= 0).any():
        raise RuntimeError("Invalid frozen raw ledger")

    frames = []
    qa = {}
    complete_days = set()
    for y in YEARS:
        d, q = load_spreads(y)
        frames.append(d)
        qa[str(y)] = q
        complete_days |= complete_rth_days(d)
    if not all(q["pass"] for q in qa.values()):
        dump({"status": "V5_2_SPREAD_DATA_QA_FAIL", "data_qa": qa,
              "frozen_raw_ledger_sha256": raw_sha}, "RESULT.json")
        return

    sp = pd.concat(frames, ignore_index=True).sort_values("datetime").drop_duplicates("datetime", keep="last")
    exact = dict(zip(sp.datetime.astype("int64"), sp.spread_price.astype(float)))
    medians = sp.groupby("date").spread_price.median().to_dict()

    costs = []
    fallback_flags = []
    required_times = []
    for row in tr.itertuples(index=False):
        required = pd.Timestamp(row.entry_time) if str(row.direction).lower() == "long" else pd.Timestamp(row.exit_time)
        required_times.append(required)
        key = required.value
        if key in exact:
            costs.append(float(exact[key]))
            fallback_flags.append(False)
        else:
            d = required.date()
            if d not in medians or not np.isfinite(medians[d]):
                raise RuntimeError(f"No same-date median spread for {required}")
            costs.append(float(medians[d]))
            fallback_flags.append(True)

    tr["spread_required_time"] = required_times
    tr["spread_cost_points"] = np.asarray(costs, dtype=float)
    tr["spread_fallback_same_day_median"] = fallback_flags
    tr["primary_r"] = tr.total_r - tr.spread_cost_points / tr.risk_points
    tr["stress_r"] = tr.total_r - 2.0 * tr.spread_cost_points / tr.risk_points
    tr["date"] = tr.entry_time.dt.date
    tr["year"] = tr.entry_time.dt.year
    tr["month"] = tr.entry_time.dt.to_period("M").astype(str)
    tr.to_csv(OUT / "TRADES_RESCORED.csv", index=False)

    primary = stats(tr.primary_r.to_numpy())
    stress = stats(tr.stress_r.to_numpy())
    trades_per_day = float(len(tr) / len(complete_days)) if complete_days else 0.0

    by_year = {}
    for y in YEARS:
        z = tr[tr.year == y]
        by_year[str(y)] = {"primary": stats(z.primary_r), "stress": stats(z.stress_r)}
    by_month = {str(m): {"primary": stats(z.primary_r), "stress": stats(z.stress_r)}
                for m, z in tr.groupby("month", sort=True)}
    by_model = {str(m): {"primary": stats(z.primary_r), "stress": stats(z.stress_r),
                          "share_of_trades": float(len(z) / len(tr))}
                for m, z in tr.groupby("model", sort=True)}

    daily = tr.groupby("date", sort=True).agg(primary_r=("primary_r", "sum"),
                                                stress_r=("stress_r", "sum"),
                                                n=("primary_r", "size")).reset_index()
    daily.to_csv(OUT / "DAILY.csv", index=False)
    worst_daily_r = float(daily.primary_r.min())
    best_daily_r = float(daily.primary_r.max())

    n_remove = int(math.ceil(len(tr) * 0.10))
    ordered = tr.sort_values("primary_r", ascending=False)
    removed = ordered.iloc[:n_remove]
    remaining = ordered.iloc[n_remove:]
    concentration = {
        "removed_n": n_remove,
        "removed_sum_r": float(removed.primary_r.sum()),
        "remaining_n": int(len(remaining)),
        "remaining_expectancy": float(remaining.primary_r.mean()),
        "top10_share_of_total_r": float(removed.primary_r.sum() / tr.primary_r.sum()) if tr.primary_r.sum() != 0 else None,
    }
    half = len(tr) // 2
    halves = {"first": stats(tr.iloc[:half].primary_r), "second": stats(tr.iloc[half:].primary_r)}
    full_years_positive = sum(1 for y in (2021, 2022, 2023, 2024) if by_year[str(y)]["primary"]["sum"] > 0)
    plan = challenge_plan(primary["mean"], trades_per_day, primary["max_dd"], worst_daily_r)
    speed_ok = any(v is not None and v["admissible_daily_limit_buffer"] and
                   v["step1_days_theoretical"] is not None and v["step1_days_theoretical"] <= 45 and
                   v["total_2step_days_theoretical"] is not None and v["total_2step_days_theoretical"] <= 70
                   for v in plan.values())

    gate = {
        "n_ge_1000": primary["n"] >= 1000,
        "trades_per_day_ge_2": trades_per_day >= 2.0,
        "primary_expectancy_ge_0_08": primary["mean"] >= 0.08,
        "primary_pf_ge_1_20": primary["pf"] is not None and primary["pf"] >= 1.20,
        "primary_max_dd_le_18R": primary["max_dd"] <= 18.0,
        "full_years_positive_ge_3": full_years_positive >= 3,
        "stress_expectancy_gt_0": stress["mean"] > 0,
        "stress_pf_ge_1_10": stress["pf"] is not None and stress["pf"] >= 1.10,
        "remove_best_10pct_expectancy_ge_0": concentration["remaining_expectancy"] >= 0,
        "challenge_speed_gate": bool(speed_ok),
    }
    passed = all(gate.values())
    result = {
        "status": "V5_PROMISING_FOR_FTMO_NATIVE_FORWARD" if passed else "NATIVE_12MODEL_PORT_V5_NO_GO",
        "classification": "V5_2_ZERO_PAID_DATA_RESCORE_FROM_FROZEN_RAW_LEDGER",
        "source_repo": SOURCE_REPO,
        "source_commit": SOURCE_COMMIT,
        "external_commit": "d472d6b442764c2adafbba4bbeb96881c100e3e0",
        "frozen_raw_ledger_sha256": raw_sha,
        "raw_trade_count": int(len(tr)),
        "spread_fallback": {
            "rule": "exact required minute else same-NY-calendar-date median",
            "fallback_trade_count": int(np.sum(fallback_flags)),
            "fallback_fraction": float(np.mean(fallback_flags)),
        },
        "data_qa": qa,
        "candidate_complete_rth_days": int(len(complete_days)),
        "trades_per_day": trades_per_day,
        "PRIMARY": primary,
        "STRESS": stress,
        "full_years_2021_2024_positive": int(full_years_positive),
        "by_year": by_year,
        "by_month": by_month,
        "by_model": by_model,
        "worst_daily_r": worst_daily_r,
        "best_daily_r": best_daily_r,
        "remove_best_10pct": concentration,
        "halves": halves,
        "challenge_plan_10k": plan,
        "gate": gate,
        "pass": bool(passed),
        "notes": [
            "No external 12-model rerun was performed in V5.2.",
            "No strategy parameter or raw trade outcome was changed by the spread fallback amendment.",
            "Live architecture requires only the native US100.cash broker/FTMO feed and zero paid external market data."
        ],
    }
    dump(result, "RESULT.json")
    print(json.dumps(result, indent=2, allow_nan=False, default=str))


if __name__ == "__main__":
    main()
