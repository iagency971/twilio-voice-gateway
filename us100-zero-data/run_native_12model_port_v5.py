#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

SOURCE_REPO = "CodyOutcast/Academic-Paper-Data-Source"
SOURCE_COMMIT = "50052606c16d71850755e6dbdda02d43b4399c2b"
SOURCE_YEARS = (2021, 2022, 2023, 2024, 2025)
EXT_REPO = "https://github.com/s-k-28/nq-es-trader-5k-payout.git"
EXT_COMMIT = "d472d6b442764c2adafbba4bbeb96881c100e3e0"
SERVER_TO_NY_HOURS = 7
SPREAD_POINT_PRICE = 0.1
MODEL_TICK_SIZE = 0.25
OUT = Path("us100-zero-data/results/native_12model_port_v5")
CACHE = Path("/tmp/us100_native_12model_v5")
EXT = CACHE / "external"


def dump(obj, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, indent=2, allow_nan=False, default=str))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def url_for(year: int) -> str:
    return (
        f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/"
        f"OHLC-USTEC-M1-{year}.csv"
    )


def download_year(year: int) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"OHLC-USTEC-M1-{year}.csv"
    if p.exists() and p.stat().st_size > 1000:
        return p
    r = requests.get(url_for(year), timeout=180)
    r.raise_for_status()
    p.write_bytes(r.content)
    return p


def load_year(year: int) -> tuple[pd.DataFrame, dict]:
    p = download_year(year)
    d = pd.read_csv(p, sep=";")
    d.columns = [str(c).strip().lower() for c in d.columns]
    need = ["time", "open", "high", "low", "close", "volume", "spread"]
    missing = [c for c in need if c not in d.columns]
    if missing:
        raise RuntimeError(f"{year}: missing columns {missing}")
    d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    for c in ["open", "high", "low", "close", "volume", "spread"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["time", "open", "high", "low", "close", "spread"]).copy()
    d = d.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    d["datetime"] = d["time"] - pd.Timedelta(hours=SERVER_TO_NY_HOURS)
    d["spread_price"] = d["spread"] * SPREAD_POINT_PRICE
    d["source_year"] = year

    bad_ohlc = int(((d.low > d.high) | (d.open < d.low) | (d.open > d.high) |
                    (d.close < d.low) | (d.close > d.high)).sum())
    bad_spread = int(((~np.isfinite(d.spread_price)) | (d.spread_price < 0)).sum())
    dup = int(d.duplicated("datetime").sum())
    qa = {
        "year": year,
        "rows": int(len(d)),
        "source_first_server": str(d.time.min()) if len(d) else None,
        "source_last_server": str(d.time.max()) if len(d) else None,
        "ny_first": str(d.datetime.min()) if len(d) else None,
        "ny_last": str(d.datetime.max()) if len(d) else None,
        "duplicates": dup,
        "ohlc_violations": bad_ohlc,
        "bad_spread": bad_spread,
        "median_spread_price": float(d.spread_price.median()) if len(d) else None,
        "sha256": sha256_file(p),
        "pass": bool(len(d) > 100000 and dup == 0 and bad_ohlc == 0 and bad_spread == 0),
    }
    return d, qa


def ensure_external() -> Path:
    if not EXT.exists():
        subprocess.run(["git", "clone", "--quiet", EXT_REPO, str(EXT)], check=True)
    subprocess.run(["git", "checkout", "--quiet", EXT_COMMIT], cwd=EXT, check=True)
    got = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=EXT, text=True).strip()
    if got != EXT_COMMIT:
        raise RuntimeError(f"external commit mismatch {got}")
    return EXT


def pf(vals: np.ndarray):
    vals = np.asarray(vals, dtype=float)
    pos = vals[vals > 0].sum()
    neg = -vals[vals < 0].sum()
    if neg > 0:
        return float(pos / neg)
    if pos > 0:
        return 1e99
    return None


def stats(vals) -> dict:
    a = np.asarray(vals, dtype=float)
    if len(a) == 0:
        return {"n": 0, "mean": None, "sum": 0.0, "pf": None, "win_rate": None,
                "max_dd": None, "losing_streak": None}
    eq = np.cumsum(a)
    peak = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(peak - eq, 0.0)
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


def complete_rth_days(d: pd.DataFrame) -> set:
    t = d.datetime.dt.time
    r = d[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())].copy()
    r["date"] = r.datetime.dt.date
    counts = r.groupby("date").size()
    return set(counts[counts >= 380].index)


def nearest_spread_map(allbars: pd.DataFrame):
    # Exact minute lookup is expected. Dictionaries keep the rescore simple and deterministic.
    return dict(zip(allbars.datetime.astype("int64"), allbars.spread_price.astype(float)))


def lookup_spread(spread_map: dict, ts: pd.Timestamp) -> float:
    key = pd.Timestamp(ts).value
    if key in spread_map:
        return float(spread_map[key])
    # Conservative same-or-prior minute fallback, never future for entry-side use.
    for k in range(1, 6):
        kk = (pd.Timestamp(ts) - pd.Timedelta(minutes=k)).value
        if kk in spread_map:
            return float(spread_map[kk])
    raise RuntimeError(f"No spread near {ts}")


def challenge_plan(expectancy: float, trades_per_day: float, max_dd: float, worst_daily_r: float) -> dict:
    if not (expectancy > 0 and trades_per_day > 0 and max_dd > 0):
        return {"safe": None, "aggressive": None}

    levels = {
        "safe": min(0.005, 0.08 / (2.0 * max_dd)),
        "aggressive": min(0.005, 0.08 / (1.5 * max_dd)),
    }
    out = {}
    for name, risk in levels.items():
        implied_worst_daily = abs(min(0.0, worst_daily_r)) * risk
        admissible = implied_worst_daily < 0.04
        daily = expectancy * trades_per_day * risk
        out[name] = {
            "risk_pct_per_trade": float(risk),
            "risk_dollars_on_10k": float(risk * 10000),
            "observed_worst_daily_loss_pct": float(implied_worst_daily),
            "daily_expectancy_pct": float(daily),
            "admissible_daily_limit_buffer": bool(admissible),
            "step1_days_theoretical": float(0.10 / daily) if admissible and daily > 0 else None,
            "step2_days_theoretical": float(0.05 / daily) if admissible and daily > 0 else None,
            "total_2step_days_theoretical": float(0.15 / daily) if admissible and daily > 0 else None,
        }
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frames = []
    qa = {}
    complete_days = set()
    for y in SOURCE_YEARS:
        d, q = load_year(y)
        frames.append(d)
        qa[str(y)] = q
        complete_days |= complete_rth_days(d)
    if not all(q["pass"] for q in qa.values()):
        dump({"status": "NATIVE_12MODEL_V5_DATA_QA_FAIL", "data_qa": qa}, "RESULT.json")
        return

    allbars = pd.concat(frames, ignore_index=True).sort_values("datetime")
    # Cross-file duplicates can occur only at boundaries; fail rather than silently blend them.
    cross_dup = int(allbars.duplicated("datetime").sum())
    if cross_dup:
        dump({"status": "NATIVE_12MODEL_V5_CROSS_YEAR_DUPLICATE_FAIL", "duplicates": cross_dup,
              "data_qa": qa}, "RESULT.json")
        return

    ext = ensure_external()
    inp = CACHE / "USTEC_NY_WALLCLOCK_2021_2025.csv"
    allbars[["datetime", "open", "high", "low", "close", "volume"]].to_csv(inp, index=False)
    trades_path = OUT.resolve() / "external_trades_raw.csv"
    cmd = [sys.executable, "run_multi.py", "--nq", str(inp.resolve()), "--csv", str(trades_path)]
    p = subprocess.run(cmd, cwd=ext, text=True, capture_output=True, timeout=3600)
    (OUT / "external_stdout.txt").write_text(p.stdout)
    (OUT / "external_stderr.txt").write_text(p.stderr)
    if p.returncode != 0:
        dump({"status": "NATIVE_12MODEL_V5_EXTERNAL_ENGINE_FAIL", "returncode": p.returncode,
              "stderr_tail": p.stderr[-5000:], "data_qa": qa}, "RESULT.json")
        return

    tr = pd.read_csv(trades_path)
    for c in ["entry_time", "exit_time"]:
        tr[c] = pd.to_datetime(tr[c], errors="coerce")
    tr = tr.dropna(subset=["entry_time", "exit_time", "risk_ticks", "total_r"]).copy()
    tr = tr.sort_values("entry_time").reset_index(drop=True)
    tr["risk_points"] = pd.to_numeric(tr.risk_ticks, errors="coerce") * MODEL_TICK_SIZE
    if (tr.risk_points <= 0).any():
        raise RuntimeError("nonpositive risk_points")

    spread_map = nearest_spread_map(allbars)
    spread_costs = []
    for row in tr.itertuples(index=False):
        if str(row.direction).lower() == "long":
            s = lookup_spread(spread_map, row.entry_time)
        else:
            s = lookup_spread(spread_map, row.exit_time)
        spread_costs.append(s)
    tr["spread_cost_points"] = np.asarray(spread_costs, dtype=float)
    tr["primary_r"] = pd.to_numeric(tr.total_r, errors="coerce") - tr.spread_cost_points / tr.risk_points
    tr["stress_r"] = pd.to_numeric(tr.total_r, errors="coerce") - 2.0 * tr.spread_cost_points / tr.risk_points
    tr["date"] = tr.entry_time.dt.date
    tr["year"] = tr.entry_time.dt.year
    tr["month"] = tr.entry_time.dt.to_period("M").astype(str)
    tr.to_csv(OUT / "TRADES_RESCORED.csv", index=False)

    primary = stats(tr.primary_r.to_numpy())
    stress = stats(tr.stress_r.to_numpy())
    candidate_days = sorted(complete_days)
    trades_per_day = float(len(tr) / len(candidate_days)) if candidate_days else 0.0

    by_year = {}
    for y in SOURCE_YEARS:
        z = tr[tr.year == y]
        by_year[str(y)] = {
            "primary": stats(z.primary_r.to_numpy()),
            "stress": stats(z.stress_r.to_numpy()),
        }
    by_month = {}
    for m, z in tr.groupby("month", sort=True):
        by_month[str(m)] = {"primary": stats(z.primary_r.to_numpy()), "stress": stats(z.stress_r.to_numpy())}

    by_model = {}
    for model, z in tr.groupby("model", sort=True):
        by_model[str(model)] = {
            "primary": stats(z.primary_r.to_numpy()),
            "stress": stats(z.stress_r.to_numpy()),
            "share_of_trades": float(len(z) / len(tr)) if len(tr) else 0.0,
        }

    daily = tr.groupby("date", sort=True).agg(primary_r=("primary_r", "sum"), stress_r=("stress_r", "sum"), n=("primary_r", "size")).reset_index()
    daily.to_csv(OUT / "DAILY.csv", index=False)
    worst_daily_r = float(daily.primary_r.min()) if len(daily) else 0.0
    best_daily_r = float(daily.primary_r.max()) if len(daily) else 0.0

    n_remove = int(math.ceil(len(tr) * 0.10)) if len(tr) else 0
    sorted_best = tr.sort_values("primary_r", ascending=False)
    removed = sorted_best.head(n_remove)
    remaining = sorted_best.iloc[n_remove:]
    remove_best = {
        "removed_n": n_remove,
        "removed_sum_r": float(removed.primary_r.sum()) if n_remove else 0.0,
        "remaining_n": int(len(remaining)),
        "remaining_expectancy": float(remaining.primary_r.mean()) if len(remaining) else None,
        "top10_share_of_total_r": float(removed.primary_r.sum() / tr.primary_r.sum()) if len(tr) and tr.primary_r.sum() != 0 else None,
    }

    half = len(tr) // 2
    halves = {
        "first": stats(tr.iloc[:half].primary_r.to_numpy()),
        "second": stats(tr.iloc[half:].primary_r.to_numpy()),
    }

    full_years_positive = sum(1 for y in (2021, 2022, 2023, 2024) if by_year[str(y)]["primary"]["sum"] > 0)
    plan = challenge_plan(primary["mean"], trades_per_day, primary["max_dd"], worst_daily_r)
    speed_ok = any(
        x is not None and x["admissible_daily_limit_buffer"] and
        x["step1_days_theoretical"] is not None and x["step1_days_theoretical"] <= 45 and
        x["total_2step_days_theoretical"] is not None and x["total_2step_days_theoretical"] <= 70
        for x in plan.values()
    )

    gate = {
        "n_ge_1000": primary["n"] >= 1000,
        "trades_per_day_ge_2": trades_per_day >= 2.0,
        "primary_expectancy_ge_0_08": primary["mean"] >= 0.08,
        "primary_pf_ge_1_20": primary["pf"] is not None and primary["pf"] >= 1.20,
        "primary_max_dd_le_18R": primary["max_dd"] <= 18.0,
        "full_years_positive_ge_3": full_years_positive >= 3,
        "stress_expectancy_gt_0": stress["mean"] > 0,
        "stress_pf_ge_1_10": stress["pf"] is not None and stress["pf"] >= 1.10,
        "remove_best_10pct_expectancy_ge_0": remove_best["remaining_expectancy"] is not None and remove_best["remaining_expectancy"] >= 0,
        "challenge_speed_gate": bool(speed_ok),
    }
    passed = all(gate.values())
    result = {
        "status": "V5_PROMISING_FOR_FTMO_NATIVE_FORWARD" if passed else "NATIVE_12MODEL_PORT_V5_NO_GO",
        "classification": "ZERO_PAID_DATA_DIRECT_PORT_NO_PARAMETER_SEARCH",
        "source_repo": SOURCE_REPO,
        "source_commit": SOURCE_COMMIT,
        "external_repo": EXT_REPO,
        "external_commit": EXT_COMMIT,
        "timestamp_translation_hours_server_to_ny": -SERVER_TO_NY_HOURS,
        "spread_point_price": SPREAD_POINT_PRICE,
        "model_tick_size": MODEL_TICK_SIZE,
        "data_qa": qa,
        "candidate_complete_rth_days": int(len(candidate_days)),
        "trades_per_day": trades_per_day,
        "PRIMARY": primary,
        "STRESS": stress,
        "full_years_2021_2024_positive": int(full_years_positive),
        "by_year": by_year,
        "by_month": by_month,
        "by_model": by_model,
        "worst_daily_r": worst_daily_r,
        "best_daily_r": best_daily_r,
        "remove_best_10pct": remove_best,
        "halves": halves,
        "challenge_plan_10k": plan,
        "gate": gate,
        "pass": bool(passed),
        "notes": [
            "No USTEC outcome was used to tune the frozen external 12-model parameters in V5.",
            "Historical years are screening/translation evidence only; clean validation must be prospective FTMO native-feed forward.",
            "No paid market-data source is required by the proposed live architecture."
        ],
    }
    dump(result, "RESULT.json")
    print(json.dumps(result, indent=2, allow_nan=False, default=str))


if __name__ == "__main__":
    main()
