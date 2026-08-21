#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DATA_URL = "https://raw.githubusercontent.com/getdata-finance/nq-1m-ohlcv-stocks-historical-data/main/NQ_1m.csv"
TZ = "America/New_York"
OOS_START = pd.Timestamp("2026-04-16")
OOS_END_EXCL = pd.Timestamp("2026-08-01")
POINT_VALUE = 20.0
STOP_POINTS = 100.0
TARGET_POINTS = 200.0
R_DOLLARS = STOP_POINTS * POINT_VALUE
SCENARIOS = {"PRIMARY": 20.0, "STRESS": 45.0}


def load_data(out: Path) -> pd.DataFrame:
    r = requests.get(DATA_URL, timeout=180)
    r.raise_for_status()
    raw = r.content
    if len(raw) < 1_000_000:
        raise RuntimeError(f"download too small: {len(raw)}")
    sha = hashlib.sha256(raw).hexdigest()
    x = pd.read_csv(io.BytesIO(raw))
    x["datetime"] = pd.to_datetime(x["datetime"], utc=True, errors="coerce")
    for c in ["open", "high", "low", "close", "volume"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=["datetime", "open", "high", "low", "close", "volume"]).copy()
    x = x.sort_values("datetime").drop_duplicates("datetime", keep="last")
    x.index = x["datetime"].dt.tz_convert(TZ)
    x = x[["open", "high", "low", "close", "volume"]].between_time("09:30", "15:59")
    x = x[x.index.weekday < 5]
    if x.empty:
        raise RuntimeError("no RTH data")

    day = x.index.normalize()
    counts = pd.Series(1, index=x.index).groupby(day).sum()
    qa = {
        "url": DATA_URL,
        "sha256": sha,
        "bytes": len(raw),
        "rows_rth": int(len(x)),
        "et_min": str(x.index.min()),
        "et_max": str(x.index.max()),
        "rth_days": int(counts.size),
        "median_rows_per_day": float(counts.median()),
        "duplicates": int(x.index.duplicated().sum()),
    }
    (out / "data_qa.json").write_text(json.dumps(qa, indent=2))
    return x


def resample_5m(x: pd.DataFrame) -> pd.DataFrame:
    # Group by ET date so no session can bleed into another day.
    parts = []
    for day, g in x.groupby(x.index.normalize(), sort=True):
        b = g.resample("5min", label="left", closed="left").agg(
            open=("open", "first"), high=("high", "max"), low=("low", "min"),
            close=("close", "last"), volume=("volume", "sum"))
        b = b.dropna(subset=["open", "high", "low", "close"])
        parts.append(b)
    return pd.concat(parts).sort_index() if parts else pd.DataFrame()


def simulate(bars: pd.DataFrame, scenario: str, round_turn_cost: float) -> pd.DataFrame:
    trades = []
    for day, g in bars.groupby(bars.index.normalize(), sort=True):
        day_naive = pd.Timestamp(day.date())
        if not (OOS_START <= day_naive < OOS_END_EXCL):
            continue
        g = g.sort_index()
        win = g[(g.index.time >= pd.Timestamp("09:30").time()) &
                (g.index.time < pd.Timestamp("11:00").time())]
        if win.empty:
            continue
        range_low = float(win["low"].min())
        trad = g[(g.index.time >= pd.Timestamp("11:00").time()) &
                 (g.index.time <= pd.Timestamp("15:30").time())]
        if trad.empty:
            continue
        last_ts = trad.index.max()
        open_trade = None
        count = 0

        def close_trade(ts, exit_px, reason):
            nonlocal open_trade
            gross_points = float(open_trade["entry"] - exit_px)
            gross_usd = gross_points * POINT_VALUE
            net_usd = gross_usd - round_turn_cost
            trades.append({
                "scenario": scenario,
                "date": str(day.date()),
                "entry_time": open_trade["entry_time"],
                "exit_time": ts,
                "entry": float(open_trade["entry"]),
                "exit": float(exit_px),
                "gross_points": gross_points,
                "gross_usd": gross_usd,
                "costs_usd": round_turn_cost,
                "net_usd": net_usd,
                "net_R": net_usd / R_DOLLARS,
                "exit_reason": reason,
            })
            open_trade = None

        for ts, row in trad.iterrows():
            is_last = ts == last_ts
            exited = False
            if open_trade is not None and ts > open_trade["entry_time"]:
                stop = open_trade["stop"]
                target = open_trade["target"]
                if float(row.open) >= stop:
                    close_trade(ts, float(row.open), "stop_gap")
                    exited = True
                elif float(row.high) >= stop:
                    close_trade(ts, stop, "stop")
                    exited = True
                elif float(row.open) <= target:
                    close_trade(ts, float(row.open), "target_gap")
                    exited = True
                elif float(row.low) <= target:
                    close_trade(ts, target, "target")
                    exited = True

            # Corrected source convention blocks entry on the final 15:30 bar.
            if open_trade is None and not exited and count < 2 and not is_last:
                if float(row.low) < range_low:
                    entry = min(range_low, float(row.open))
                    open_trade = {
                        "entry_time": ts,
                        "entry": entry,
                        "stop": entry + STOP_POINTS,
                        "target": entry - TARGET_POINTS,
                    }
                    count += 1

            if is_last and open_trade is not None:
                close_trade(ts, float(row.close), "eod_short")

    return pd.DataFrame(trades)


def metrics(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"n": 0, "mean_R": None, "sum_R": 0.0, "pf": None, "win_rate": None,
                "max_dd_R": None, "losing_streak": None, "avg_win_R": None, "avg_loss_R": None}
    z = t.sort_values("exit_time")
    r = z["net_R"].astype(float).to_numpy()
    pos, neg = r[r > 0], r[r < 0]
    ps, ns = pos.sum(), -neg.sum()
    pf = float(ps / ns) if ns > 0 else (float("inf") if ps > 0 else None)
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(peak - eq, 0.0)
    cur = streak = 0
    for v in r:
        if v < 0:
            cur += 1
            streak = max(streak, cur)
        else:
            cur = 0
    return {
        "n": int(len(r)), "mean_R": float(r.mean()), "sum_R": float(r.sum()), "pf": pf,
        "win_rate": float((r > 0).mean()), "max_dd_R": float(dd.max(initial=0.0)),
        "losing_streak": int(streak),
        "avg_win_R": float(pos.mean()) if len(pos) else None,
        "avg_loss_R": float(neg.mean()) if len(neg) else None,
    }


def diagnostics(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"by_month": {}, "exit_reasons": {}, "remove_best_5pct_mean_R": None}
    z = t.copy()
    z["entry_time"] = pd.to_datetime(z["entry_time"])
    z["month"] = z["entry_time"].dt.strftime("%Y-%m")
    by_month = {str(k): metrics(g) for k, g in z.groupby("month")}
    reasons = {str(k): int(v) for k, v in z["exit_reason"].value_counts().items()}
    r = z["net_R"].sort_values(ascending=False).reset_index(drop=True)
    remove_n = max(1, int(np.ceil(len(r) * 0.05))) if len(r) >= 20 else 0
    rem = float(r.iloc[remove_n:].mean()) if remove_n and len(r) > remove_n else None
    return {"by_month": by_month, "exit_reasons": reasons, "remove_best_5pct_mean_R": rem}


def main():
    out = Path("nq-breakout-short-oos2/results/v1")
    out.mkdir(parents=True, exist_ok=True)
    try:
        x = load_data(out)
        bars = resample_5m(x)
        oos_days = sorted({d.date() for d in x.index.normalize()
                           if OOS_START.date() <= d.date() < OOS_END_EXCL.date()})
        eval_days = len(oos_days)
        results = {}
        ledgers = []
        for scenario, cost in SCENARIOS.items():
            t = simulate(bars, scenario, cost)
            results[scenario] = {"metrics": metrics(t), "diagnostics": diagnostics(t),
                                 "round_turn_cost_usd": cost}
            ledgers.append(t)
        ledger = pd.concat(ledgers, ignore_index=True) if ledgers else pd.DataFrame()
        ledger.to_csv(out / "trades.csv", index=False)

        p = results["PRIMARY"]["metrics"]
        s = results["STRESS"]["metrics"]
        bym = results["PRIMARY"]["diagnostics"]["by_month"]
        positive_mjj = sum(1 for m in ["2026-05", "2026-06", "2026-07"]
                           if m in bym and bym[m]["sum_R"] > 0)
        freq = float(p["n"] / eval_days * 5.0) if eval_days else 0.0
        gates = {
            "primary_n_ge_25": p["n"] >= 25,
            "primary_trades_per_5d_ge_1_5": freq >= 1.5,
            "primary_mean_R_ge_0_10": p["mean_R"] is not None and p["mean_R"] >= 0.10,
            "primary_pf_ge_1_30": p["pf"] is not None and p["pf"] >= 1.30,
            "primary_positive_may_jun_jul_ge_2": positive_mjj >= 2,
            "primary_max_dd_R_le_8": p["max_dd_R"] is not None and p["max_dd_R"] <= 8.0,
            "stress_mean_R_positive": s["mean_R"] is not None and s["mean_R"] > 0,
            "stress_pf_ge_1_15": s["pf"] is not None and s["pf"] >= 1.15,
        }
        passed = all(gates.values())
        if p["n"] < 25:
            status = "NQ_BREAKOUT_SHORT_OOS2_V1_INCONCLUSIVE_LOW_N"
        else:
            status = "NQ_BREAKOUT_SHORT_OOS2_V1_PASS_FOR_PROPFIRM_SIZING_AND_CHALLENGE_SIM" if passed else "NQ_BREAKOUT_SHORT_OOS2_V1_NO_GO"
        result = {
            "status": status,
            "oos2_start": str(OOS_START.date()), "oos2_end": "2026-07-31",
            "evaluation_cash_days": eval_days, "primary_trades_per_5d": freq,
            "positive_may_jun_jul": positive_mjj,
            "scenarios": results, "gates": gates,
            "notes": [
                "New SHORT-only architecture frozen after Jan-Apr development diagnostic and before OOS2 calculation.",
                "Jan-Apr performance is not counted as validation for this architecture.",
                "No long positions or long-signal occupancy exist in this new architecture.",
                "OOS2 may not be used for rescue tuning after this result.",
            ],
        }
        (out / "RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        print(json.dumps(result, indent=2, allow_nan=False))
    except Exception as e:
        result = {"status": "NQ_BREAKOUT_SHORT_OOS2_V1_INVALID_ABORT", "error": repr(e)}
        (out / "RESULT.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        raise


if __name__ == "__main__":
    main()
