#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from nq_breakout import Config, SimFlags, resample_5min, run_backtest

DATA_URL = "https://raw.githubusercontent.com/axb0306/cme-futures-ohlc/main/NQ/NQ_1min_20260120_20260415.csv"
CUT_OFF = pd.Timestamp("2026-04-08 23:59:59")
STOP_DOLLARS = 2000.0

SCENARIOS = {
    "PRIMARY": {"slippage_ticks_per_side": 1.5},
    "STRESS": {"slippage_ticks_per_side": 4.0},
}


def load_source(out: Path) -> pd.DataFrame:
    r = requests.get(DATA_URL, timeout=180)
    r.raise_for_status()
    raw = r.content
    if len(raw) < 1_000_000:
        raise RuntimeError(f"unexpectedly small data download: {len(raw)} bytes")
    sha = hashlib.sha256(raw).hexdigest()
    x = pd.read_csv(io.BytesIO(raw))
    need = {"datetime", "open", "high", "low", "close", "volume"}
    if not need.issubset(x.columns):
        raise RuntimeError(f"missing columns {sorted(need - set(x.columns))}")
    x["datetime"] = pd.to_datetime(x["datetime"], utc=True, errors="coerce")
    for c in ["open", "high", "low", "close", "volume"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=["datetime", "open", "high", "low", "close", "volume"]).copy()
    x = x.sort_values("datetime").drop_duplicates("datetime", keep="last")
    utc_min, utc_max = x["datetime"].min(), x["datetime"].max()

    # External engine expects naive US/Central timestamps.
    x["date"] = x["datetime"].dt.tz_convert("America/Chicago").dt.tz_localize(None)
    x = x.rename(columns={"volume": "totalvolume"})
    df = x[["date", "open", "high", "low", "close", "totalvolume"]].sort_values("date").reset_index(drop=True)

    # Basic independent-source QA.
    dti = pd.DatetimeIndex(df["date"])
    rth = df[(dti.time >= pd.Timestamp("08:30").time()) & (dti.time <= pd.Timestamp("15:00").time())].copy()
    cash_days = sorted(pd.DatetimeIndex(rth["date"]).normalize().unique())
    cash_days_cut = [d for d in cash_days if d <= CUT_OFF.normalize()]
    qa = {
        "url": DATA_URL,
        "sha256": sha,
        "bytes": len(raw),
        "rows_1m": int(len(df)),
        "utc_min": str(utc_min),
        "utc_max": str(utc_max),
        "ct_min": str(df["date"].min()),
        "ct_max": str(df["date"].max()),
        "duplicate_ct_timestamps": int(df["date"].duplicated().sum()),
        "cash_trading_days_total": int(len(cash_days)),
        "cash_trading_days_to_cutoff": int(len(cash_days_cut)),
    }
    (out / "data_qa.json").write_text(json.dumps(qa, indent=2))
    return df


def trade_metrics(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"n": 0, "mean_R": None, "sum_R": 0.0, "pf": None, "win_rate": None,
                "avg_win_R": None, "avg_loss_R": None, "max_dd_R": None, "losing_streak": None}
    y = t.sort_values("exit_time").copy()
    r = y["pnl_per_contract"].astype(float).to_numpy() / STOP_DOLLARS
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
        "n": int(len(r)),
        "mean_R": float(r.mean()),
        "sum_R": float(r.sum()),
        "pf": pf,
        "win_rate": float((r > 0).mean()),
        "avg_win_R": float(pos.mean()) if len(pos) else None,
        "avg_loss_R": float(neg.mean()) if len(neg) else None,
        "max_dd_R": float(dd.max(initial=0.0)),
        "losing_streak": int(streak),
    }


def diagnostics(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"by_direction": {}, "by_month": {}, "exit_reasons": {}, "remove_best_5pct_mean_R": None}
    z = t.copy()
    z["entry_time"] = pd.to_datetime(z["entry_time"])
    z["exit_time"] = pd.to_datetime(z["exit_time"])
    z["month"] = z["entry_time"].dt.strftime("%Y-%m")
    by_direction = {str(k): trade_metrics(g) for k, g in z.groupby("direction")}
    by_month = {str(k): trade_metrics(g) for k, g in z.groupby("month")}
    exit_reasons = {str(k): int(v) for k, v in z["exit_reason"].value_counts().items()}
    r = (z["pnl_per_contract"].astype(float) / STOP_DOLLARS).sort_values(ascending=False).reset_index(drop=True)
    remove_n = max(1, int(np.ceil(len(r) * 0.05))) if len(r) >= 20 else 0
    rem_mean = float(r.iloc[remove_n:].mean()) if remove_n and len(r) > remove_n else None
    return {"by_direction": by_direction, "by_month": by_month,
            "exit_reasons": exit_reasons, "remove_best_5pct_mean_R": rem_mean}


def main():
    out = Path("nq-2022-breakout-full/results/v1")
    out.mkdir(parents=True, exist_ok=True)
    try:
        df1 = load_source(out)
        df5 = resample_5min(df1)
        if df5.empty:
            raise RuntimeError("no 5m bars after resampling")

        # Frequency denominator: actual cash-session trading days through cutoff.
        td = pd.DatetimeIndex(df1["date"])
        cash_mask = ((td.time >= pd.Timestamp("08:30").time()) &
                     (td.time <= pd.Timestamp("15:00").time()) &
                     (td.normalize() <= CUT_OFF.normalize()))
        eval_days = int(pd.DatetimeIndex(df1.loc[cash_mask, "date"]).normalize().nunique())

        results = {}
        ledgers = []
        for name, spec in SCENARIOS.items():
            cfg = Config(slippage_ticks_per_side=float(spec["slippage_ticks_per_side"]), entry_mode="stop")
            bt = run_backtest(df5, cfg, SimFlags())
            tr = bt.trades.copy()
            if not tr.empty:
                tr["entry_time"] = pd.to_datetime(tr["entry_time"])
                tr["exit_time"] = pd.to_datetime(tr["exit_time"])
                tr = tr[tr["entry_time"] <= CUT_OFF].copy()
                tr["scenario"] = name
            m = trade_metrics(tr)
            d = diagnostics(tr)
            results[name] = {"metrics": m, "diagnostics": d,
                             "round_turn_cost_usd": float(cfg.round_turn_cost)}
            ledgers.append(tr)

        ledger = pd.concat(ledgers, ignore_index=True) if ledgers else pd.DataFrame()
        ledger.to_csv(out / "trades.csv", index=False)

        p = results["PRIMARY"]["metrics"]
        s = results["STRESS"]["metrics"]
        pmonths = results["PRIMARY"]["diagnostics"]["by_month"]
        pos_fma = sum(1 for mo in ["2026-02", "2026-03", "2026-04"]
                      if mo in pmonths and pmonths[mo]["sum_R"] > 0)
        trades_per_5d = float(p["n"] / eval_days * 5.0) if eval_days > 0 else 0.0

        gates = {
            "primary_n_ge_25": p["n"] >= 25,
            "primary_trades_per_5d_ge_2": trades_per_5d >= 2.0,
            "primary_mean_R_ge_0_10": p["mean_R"] is not None and p["mean_R"] >= 0.10,
            "primary_pf_ge_1_30": p["pf"] is not None and p["pf"] >= 1.30,
            "primary_positive_feb_mar_apr_ge_2": pos_fma >= 2,
            "primary_max_dd_R_le_8": p["max_dd_R"] is not None and p["max_dd_R"] <= 8.0,
            "stress_mean_R_positive": s["mean_R"] is not None and s["mean_R"] > 0,
            "stress_pf_ge_1_15": s["pf"] is not None and s["pf"] >= 1.15,
        }
        passed = all(gates.values())
        if p["n"] < 25:
            status = "NQ_2022_BREAKOUT_FULL_OOS_V1_INCONCLUSIVE_LOW_N"
        else:
            status = "NQ_2022_BREAKOUT_FULL_OOS_V1_PASS_FOR_PROPFIRM_SIZING" if passed else "NQ_2022_BREAKOUT_FULL_OOS_V1_NO_GO"

        result = {
            "status": status,
            "external_engine_commit": "c5ed61a8cf61c57e2e612d7c7e080c7ec76c8ce1",
            "data_entry_cutoff_ct": str(CUT_OFF),
            "evaluation_cash_days": eval_days,
            "primary_trades_per_5_trading_days": trades_per_5d,
            "positive_feb_mar_apr_months": pos_fma,
            "scenarios": results,
            "gates": gates,
            "notes": [
                "Author's corrected executable engine used directly; no reimplementation of strategy logic.",
                "Full Globex source retained for overnight long exits.",
                "Entries after 2026-04-08 excluded from evaluation to avoid sample-end force-close bias.",
                "Diagnostics are not rescue filters and cannot change this verdict.",
            ],
        }
        (out / "RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        print(json.dumps(result, indent=2, allow_nan=False))
    except Exception as e:
        result = {"status": "NQ_2022_BREAKOUT_FULL_OOS_V1_INVALID_ABORT", "error": repr(e)}
        (out / "RESULT.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        raise


if __name__ == "__main__":
    main()
