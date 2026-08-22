#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

BRANCH_ROOT = Path("us100-zero-data")
LEDGER = BRANCH_ROOT / "results/native_12model_port_v5/TRADES_RESCORED.csv"
OUT = BRANCH_ROOT / "results/v11_fast_challenge_subset_search"
EXPECTED_RAW_SHA = "c2c705318ff19aee4fb1137b7ec2102e98a848b297701b334e1b777a0d5b7d31"
DEV_YEARS = (2021, 2022, 2023)
VAL_YEARS = (2024, 2025)
SESSIONS = {"DEV": 746, "2024": 246, "2025": 83}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pf(a: np.ndarray):
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg > 0:
        return pos / neg
    if pos > 0:
        return 1e99
    return None


def stats(vals) -> dict:
    a = np.asarray(vals, dtype=float)
    if len(a) == 0:
        return {"n": 0, "mean": None, "sum": 0.0, "pf": None,
                "win_rate": None, "max_dd": None, "losing_streak": None}
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


def daily_worst(df: pd.DataFrame, col: str) -> float:
    if df.empty:
        return 0.0
    return float(df.groupby("date", sort=True)[col].sum().min())


def remove_best10_mean(df: pd.DataFrame, col: str = "primary_r"):
    if df.empty:
        return None
    n_remove = int(math.ceil(len(df) * 0.10))
    rem = df.sort_values(col, ascending=False).iloc[n_remove:]
    return float(rem[col].mean()) if len(rem) else None


def risk_from_dev(stress_dd: float, stress_worst_day: float) -> float:
    dd_term = 0.01 if not stress_dd or stress_dd <= 0 else 0.08 / (1.5 * stress_dd)
    daily_term = 0.01
    if stress_worst_day < 0:
        daily_term = 0.04 / (1.25 * abs(stress_worst_day))
    return float(min(0.01, dd_term, daily_term))


def path_test(df: pd.DataFrame, col: str, risk: float, target: float) -> dict:
    if df.empty:
        return {"status": "NO_TRADES", "days_to_target": None, "final_return": 0.0,
                "max_total_dd": 0.0, "worst_intraday_from_day_start": 0.0}
    z = df.sort_values(["entry_time", "exit_time"]).copy()
    balance = 0.0
    peak = 0.0
    max_dd = 0.0
    days_seen = 0
    worst_intraday = 0.0
    for d, g in z.groupby("date", sort=True):
        days_seen += 1
        day_start = balance
        for row in g.itertuples(index=False):
            r = float(getattr(row, col))
            balance += r * risk
            peak = max(peak, balance)
            max_dd = max(max_dd, peak - balance)
            day_move = balance - day_start
            worst_intraday = min(worst_intraday, day_move)
            if day_move <= -0.05:
                return {"status": "FAIL_DAILY", "days_to_target": None,
                        "final_return": float(balance), "max_total_dd": float(max_dd),
                        "worst_intraday_from_day_start": float(worst_intraday)}
            if balance <= -0.10:
                return {"status": "FAIL_TOTAL", "days_to_target": None,
                        "final_return": float(balance), "max_total_dd": float(max_dd),
                        "worst_intraday_from_day_start": float(worst_intraday)}
            if balance >= target:
                return {"status": "PASS", "days_to_target": int(days_seen),
                        "final_return": float(balance), "max_total_dd": float(max_dd),
                        "worst_intraday_from_day_start": float(worst_intraday)}
    return {"status": "NOT_REACHED", "days_to_target": None,
            "final_return": float(balance), "max_total_dd": float(max_dd),
            "worst_intraday_from_day_start": float(worst_intraday)}


def validation_block(df: pd.DataFrame, year: int, models: tuple[str, ...], risk: float) -> dict:
    z = df[(df.year == year) & (df.model.isin(models))].copy()
    sessions = SESSIONS[str(year)]
    p = stats(z.primary_r.to_numpy())
    s = stats(z.stress_r.to_numpy())
    p_worst = daily_worst(z, "primary_r")
    s_worst = daily_worst(z, "stress_r")
    p_rpd = p["sum"] / sessions
    s_rpd = s["sum"] / sessions
    p_daily = p_rpd * risk
    s_daily = s_rpd * risk
    return {
        "year": year,
        "sessions": sessions,
        "trades_per_session": float(len(z) / sessions),
        "primary": p,
        "stress": s,
        "primary_worst_day_r": p_worst,
        "stress_worst_day_r": s_worst,
        "risk_fraction": risk,
        "risk_dollars_10k": risk * 10000.0,
        "stress_scaled_max_dd_pct": None if s["max_dd"] is None else s["max_dd"] * risk,
        "stress_scaled_worst_day_pct": abs(min(0.0, s_worst)) * risk,
        "primary_r_per_session": p_rpd,
        "stress_r_per_session": s_rpd,
        "primary_step1_days_implied": (0.10 / p_daily) if p_daily > 0 else None,
        "stress_step1_days_implied": (0.10 / s_daily) if s_daily > 0 else None,
        "primary_step2_days_implied": (0.05 / p_daily) if p_daily > 0 else None,
        "stress_step2_days_implied": (0.05 / s_daily) if s_daily > 0 else None,
        "primary_path_step1": path_test(z, "primary_r", risk, 0.10),
        "stress_path_step1": path_test(z, "stress_r", risk, 0.10),
        "primary_path_step2": path_test(z, "primary_r", risk, 0.05),
        "stress_path_step2": path_test(z, "stress_r", risk, 0.05),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not LEDGER.exists():
        raise RuntimeError(f"missing ledger {LEDGER}")

    d = pd.read_csv(LEDGER)
    required = {"entry_time", "exit_time", "model", "direction", "primary_r", "stress_r", "year", "date"}
    missing = required - set(d.columns)
    if missing:
        raise RuntimeError(f"missing columns {sorted(missing)}")
    d["entry_time"] = pd.to_datetime(d.entry_time, errors="coerce")
    d["exit_time"] = pd.to_datetime(d.exit_time, errors="coerce")
    d["year"] = pd.to_numeric(d.year, errors="coerce").astype("Int64")
    d["primary_r"] = pd.to_numeric(d.primary_r, errors="coerce")
    d["stress_r"] = pd.to_numeric(d.stress_r, errors="coerce")
    d = d.dropna(subset=["entry_time", "exit_time", "model", "primary_r", "stress_r", "year"]).copy()
    d["year"] = d.year.astype(int)
    d["date"] = d.entry_time.dt.date
    d = d.sort_values(["entry_time", "exit_time"]).reset_index(drop=True)

    models = tuple(sorted(d.model.astype(str).unique().tolist()))
    if len(models) != 12:
        raise RuntimeError(f"expected 12 models, got {len(models)}: {models}")

    dev = d[d.year.isin(DEV_YEARS)].copy()
    eligible = []
    all_rows = []

    for mask in range(1, 1 << len(models)):
        subset = tuple(models[i] for i in range(len(models)) if mask & (1 << i))
        z = dev[dev.model.isin(subset)]
        p = stats(z.primary_r.to_numpy())
        s = stats(z.stress_r.to_numpy())
        if p["n"] == 0:
            continue
        p_by_year = {}
        positive_years = 0
        worst_year_mean = 1e99
        for y in DEV_YEARS:
            zy = z[z.year == y]
            sy = stats(zy.primary_r.to_numpy())
            p_by_year[str(y)] = sy
            if sy["sum"] > 0:
                positive_years += 1
            if sy["mean"] is not None:
                worst_year_mean = min(worst_year_mean, sy["mean"])
        p_worst_day = daily_worst(z, "primary_r")
        s_worst_day = daily_worst(z, "stress_r")
        rb10 = remove_best10_mean(z, "primary_r")
        risk = risk_from_dev(s["max_dd"], s_worst_day)
        stress_rpd = s["sum"] / SESSIONS["DEV"]
        daily_return = stress_rpd * risk
        step1 = 0.10 / daily_return if daily_return > 0 else None
        row = {
            "models": subset,
            "model_count": len(subset),
            "primary": p,
            "stress": s,
            "trades_per_session": float(len(z) / SESSIONS["DEV"]),
            "positive_years": positive_years,
            "worst_year_mean": None if worst_year_mean == 1e99 else float(worst_year_mean),
            "remove_best10_mean": rb10,
            "primary_worst_day_r": p_worst_day,
            "stress_worst_day_r": s_worst_day,
            "risk_fraction": risk,
            "risk_dollars_10k": risk * 10000.0,
            "stress_r_per_session": stress_rpd,
            "expected_stress_daily_return_pct": daily_return,
            "theoretical_stress_step1_days": step1,
            "theoretical_stress_step2_days": (0.05 / daily_return) if daily_return > 0 else None,
        }
        gates = {
            "n_ge_250": p["n"] >= 250,
            "primary_mean_gt_0": p["mean"] is not None and p["mean"] > 0,
            "primary_pf_ge_1_20": p["pf"] is not None and p["pf"] >= 1.20,
            "stress_mean_ge_0_05": s["mean"] is not None and s["mean"] >= 0.05,
            "stress_pf_ge_1_12": s["pf"] is not None and s["pf"] >= 1.12,
            "positive_years_ge_2": positive_years >= 2,
            "worst_year_mean_ge_minus_0_05": row["worst_year_mean"] is not None and row["worst_year_mean"] >= -0.05,
            "remove_best10_mean_ge_0": rb10 is not None and rb10 >= 0.0,
        }
        row["gates"] = gates
        row["eligible"] = all(gates.values()) and step1 is not None
        all_rows.append(row)
        if row["eligible"]:
            eligible.append(row)

    def key(r):
        return (
            r["theoretical_stress_step1_days"],
            r["stress"]["max_dd"],
            r["risk_fraction"],
            r["model_count"],
            ",".join(r["models"]),
        )

    eligible.sort(key=key)
    selected = eligible[0] if eligible else None

    result = {
        "status": "V11_NO_ELIGIBLE_SUBSET" if selected is None else "V11_DEV_SELECTED_VALIDATION_OPENED",
        "ledger_sha256": sha256_file(LEDGER),
        "expected_raw_ledger_sha256": EXPECTED_RAW_SHA,
        "model_names": models,
        "subsets_tested": int((1 << len(models)) - 1),
        "dev_years": DEV_YEARS,
        "dev_sessions": SESSIONS["DEV"],
        "eligible_subset_count": len(eligible),
        "top_20_eligible": eligible[:20],
        "selected_dev": selected,
        "validation": None,
        "pass": False,
    }

    if selected is not None:
        models_sel = tuple(selected["models"])
        risk = float(selected["risk_fraction"])
        v2024 = validation_block(d, 2024, models_sel, risk)
        v2025 = validation_block(d, 2025, models_sel, risk)
        gates = {
            "2024_stress_sum_gt_0": v2024["stress"]["sum"] > 0,
            "2024_stress_pf_ge_1_10": v2024["stress"]["pf"] is not None and v2024["stress"]["pf"] >= 1.10,
            "2025_stress_sum_gt_0": v2025["stress"]["sum"] > 0,
            "2025_stress_pf_ge_1_10": v2025["stress"]["pf"] is not None and v2025["stress"]["pf"] >= 1.10,
            "2024_scaled_dd_lt_8pct": v2024["stress_scaled_max_dd_pct"] is not None and v2024["stress_scaled_max_dd_pct"] < 0.08,
            "2025_scaled_dd_lt_8pct": v2025["stress_scaled_max_dd_pct"] is not None and v2025["stress_scaled_max_dd_pct"] < 0.08,
            "2024_scaled_worst_day_lt_4pct": v2024["stress_scaled_worst_day_pct"] < 0.04,
            "2025_scaled_worst_day_lt_4pct": v2025["stress_scaled_worst_day_pct"] < 0.04,
            "2024_stress_step1_pace_le_45": v2024["stress_step1_days_implied"] is not None and v2024["stress_step1_days_implied"] <= 45,
            "2025_stress_step1_pace_le_45": v2025["stress_step1_days_implied"] is not None and v2025["stress_step1_days_implied"] <= 45,
        }
        result["validation"] = {"2024": v2024, "2025": v2025, "gates": gates}
        result["pass"] = all(gates.values())
        result["status"] = "V11_PROMISING_FOR_MONTE_CARLO" if result["pass"] else "V11_VALIDATION_NO_GO"

    (OUT / "RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False, default=str))

    # Compact CSV for manual inspection of the best eligible DEV candidates.
    compact = []
    for r in eligible[:100]:
        compact.append({
            "models": "+".join(r["models"]),
            "model_count": r["model_count"],
            "n": r["primary"]["n"],
            "tpd": r["trades_per_session"],
            "primary_mean": r["primary"]["mean"],
            "primary_pf": r["primary"]["pf"],
            "stress_mean": r["stress"]["mean"],
            "stress_pf": r["stress"]["pf"],
            "stress_dd": r["stress"]["max_dd"],
            "remove_best10_mean": r["remove_best10_mean"],
            "risk_pct": 100 * r["risk_fraction"],
            "risk_dollars_10k": r["risk_dollars_10k"],
            "stress_r_per_day": r["stress_r_per_session"],
            "step1_days": r["theoretical_stress_step1_days"],
            "step2_days": r["theoretical_stress_step2_days"],
        })
    pd.DataFrame(compact).to_csv(OUT / "TOP_ELIGIBLE.csv", index=False)
    print(json.dumps({
        "status": result["status"],
        "eligible_subset_count": len(eligible),
        "selected_models": None if selected is None else selected["models"],
        "selected_risk_pct": None if selected is None else selected["risk_fraction"] * 100,
        "selected_step1_days_dev_stress": None if selected is None else selected["theoretical_stress_step1_days"],
        "validation_pass": result["pass"],
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
