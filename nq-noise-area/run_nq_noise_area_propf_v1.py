#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DATA_URL = "https://raw.githubusercontent.com/getdata-finance/nq-1m-ohlcv-stocks-historical-data/main/NQ_1m.csv"
TZ = "America/New_York"
LOOKBACK = 14
POINT_VALUE = 20.0
TICK_SIZE = 0.25
CHECK_MINUTES = list(range(10 * 60, 15 * 60 + 31, 30))  # 10:00 ... 15:30

SCENARIOS = {
    "PRIMARY": {"slip_ticks_side": 1.0, "commission_side_usd": 2.50},
    "STRESS": {"slip_ticks_side": 2.0, "commission_side_usd": 2.50},
}


def load_data(out: Path) -> pd.DataFrame:
    r = requests.get(DATA_URL, timeout=180)
    r.raise_for_status()
    raw = r.content
    if len(raw) < 1_000_000:
        raise RuntimeError(f"download unexpectedly small: {len(raw)} bytes")

    sha = hashlib.sha256(raw).hexdigest()
    df = pd.read_csv(io.BytesIO(raw))
    need = {"datetime", "open", "high", "low", "close", "volume"}
    if not need.issubset(df.columns):
        raise RuntimeError(f"missing columns: {sorted(need - set(df.columns))}")

    df["datetime"] = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["datetime", "open", "high", "low", "close", "volume"]).copy()
    df = df.sort_values("datetime").drop_duplicates("datetime", keep="last")
    df = df.set_index("datetime").tz_convert(TZ)

    # RTH labels 09:30..15:59 ET. Ignore any post-16:00 cash-extension rows.
    df = df.between_time("09:30", "15:59").copy()
    df = df[df.index.weekday < 5]
    if df.empty:
        raise RuntimeError("no RTH rows")

    day = df.index.normalize()
    counts = pd.Series(1, index=df.index).groupby(day).sum()
    first = df.groupby(day).head(1)
    last = df.groupby(day).tail(1)
    qa = {
        "url": DATA_URL,
        "sha256": sha,
        "bytes": len(raw),
        "rows_rth": int(len(df)),
        "utc_source_min": str(pd.to_datetime(pd.read_csv(io.BytesIO(raw), nrows=1)["datetime"].iloc[0], utc=True)),
        "et_min": str(df.index.min()),
        "et_max": str(df.index.max()),
        "rth_days": int(counts.size),
        "median_bars_per_day": float(counts.median()),
        "days_ge_380_bars": int((counts >= 380).sum()),
        "duplicate_timestamps": int(df.index.duplicated().sum()),
        "first_bar_time_mode": str(first.index.time[0]) if len(first) else None,
        "last_bar_time_mode": str(last.index.time[-1]) if len(last) else None,
    }
    (out / "data_qa.json").write_text(json.dumps(qa, indent=2))
    return df


def day_key(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index.normalize()


def build_indicators(df: pd.DataFrame) -> pd.DataFrame:
    days = day_key(df.index)
    opens = df["open"].groupby(days).first()
    closes = df["close"].groupby(days).last()
    prev_close = closes.shift(1)

    open_per_bar = opens.reindex(days)
    open_per_bar.index = df.index
    move = (df["close"] / open_per_bar - 1.0).abs()

    frame = pd.DataFrame({"day": days, "tod": df.index.time, "move": move.to_numpy()})
    pivot = frame.pivot(index="day", columns="tod", values="move")
    # Strict frozen interpretation: require 14 prior observations for that minute.
    sigma_by_day = pivot.rolling(LOOKBACK, min_periods=LOOKBACK).mean().shift(1)
    long = sigma_by_day.stack(future_stack=True).rename("sigma")
    keys = pd.MultiIndex.from_arrays([days, df.index.time])
    sigma = pd.Series(long.reindex(keys).to_numpy(), index=df.index, name="sigma")

    upper_anchor = np.maximum(opens, prev_close)
    lower_anchor = np.minimum(opens, prev_close)

    out = df.copy()
    out["day_open"] = opens.reindex(days).to_numpy()
    out["prev_close"] = prev_close.reindex(days).to_numpy()
    out["sigma"] = sigma
    out["upper"] = upper_anchor.reindex(days).to_numpy() * (1.0 + out["sigma"])
    out["lower"] = lower_anchor.reindex(days).to_numpy() * (1.0 - out["sigma"])

    tp = (out["high"] + out["low"] + out["close"]) / 3.0
    pv = (tp * out["volume"]).groupby(days).cumsum()
    vv = out["volume"].groupby(days).cumsum()
    out["vwap"] = pv / vv.replace(0, np.nan)
    return out


def close_trade(trades, scenario, side, entry_px, entry_time, px, ts, reason, open_comm, slip_pts, comm_side):
    # side +1 long closes with sell (adverse slip down); short closes with buy (adverse slip up)
    exit_px = px - slip_pts if side > 0 else px + slip_pts
    gross_usd = side * (exit_px - entry_px) * POINT_VALUE
    net_usd = gross_usd - open_comm - comm_side
    trades.append({
        "scenario": scenario,
        "entry_time": entry_time,
        "exit_time": ts,
        "side": "long" if side > 0 else "short",
        "entry_px": float(entry_px),
        "exit_px": float(exit_px),
        "gross_usd": float(gross_usd),
        "costs_usd": float(open_comm + comm_side),
        "net_usd": float(net_usd),
        "gross_points": float(gross_usd / POINT_VALUE),
        "net_points": float(net_usd / POINT_VALUE),
        "exit_reason": reason,
    })


def run_scenario(ind: pd.DataFrame, name: str, spec: dict) -> pd.DataFrame:
    slip_pts = float(spec["slip_ticks_side"]) * TICK_SIZE
    comm_side = float(spec["commission_side_usd"])
    trades = []

    for day, g in ind.groupby(day_key(ind.index), sort=True):
        g = g.sort_index()
        side = 0
        entry_px = None
        entry_time = None
        open_comm = 0.0

        # timestamp lookup by minute-of-day
        minute_map = {ts.hour * 60 + ts.minute: ts for ts in g.index}

        for minute in CHECK_MINUTES:
            ts = minute_map.get(minute)
            if ts is None:
                continue
            row = g.loc[ts]
            px, upper, lower, vwap = map(float, [row["close"], row["upper"], row["lower"], row["vwap"]])
            if not all(np.isfinite([px, upper, lower, vwap])):
                continue

            long_sig = px > upper
            short_sig = px < lower

            def open_pos(new_side: int):
                nonlocal side, entry_px, entry_time, open_comm
                # long buy slips up; short sell slips down
                entry_px = px + slip_pts if new_side > 0 else px - slip_pts
                entry_time = ts
                open_comm = comm_side
                side = new_side

            if side > 0:
                trail = max(vwap, upper)
                if short_sig:
                    close_trade(trades, name, side, entry_px, entry_time, px, ts, "flip", open_comm, slip_pts, comm_side)
                    open_pos(-1)
                elif px < trail:
                    close_trade(trades, name, side, entry_px, entry_time, px, ts, "trail", open_comm, slip_pts, comm_side)
                    side, entry_px, entry_time, open_comm = 0, None, None, 0.0
            elif side < 0:
                trail = min(vwap, lower)
                if long_sig:
                    close_trade(trades, name, side, entry_px, entry_time, px, ts, "flip", open_comm, slip_pts, comm_side)
                    open_pos(1)
                elif px > trail:
                    close_trade(trades, name, side, entry_px, entry_time, px, ts, "trail", open_comm, slip_pts, comm_side)
                    side, entry_px, entry_time, open_comm = 0, None, None, 0.0
            else:
                if long_sig:
                    open_pos(1)
                elif short_sig:
                    open_pos(-1)

        # Forced flat at last available RTH bar (normally 15:59; early close uses its final bar).
        if side != 0:
            ts = g.index[-1]
            px = float(g.iloc[-1]["close"])
            close_trade(trades, name, side, entry_px, entry_time, px, ts, "eod", open_comm, slip_pts, comm_side)

    return pd.DataFrame(trades)


def metrics(x: pd.DataFrame) -> dict:
    if x.empty:
        return {"n": 0, "mean_net_points": None, "sum_net_points": 0.0, "sum_net_usd": 0.0,
                "pf": None, "win_rate": None, "avg_win_usd": None, "avg_loss_usd": None,
                "max_dd_usd": None, "losing_streak": None}
    x = x.sort_values("exit_time")
    r = x["net_usd"].astype(float).to_numpy()
    pos = r[r > 0]
    neg = r[r < 0]
    ps, ns = pos.sum(), -neg.sum()
    pf = float(ps / ns) if ns > 0 else (float("inf") if ps > 0 else None)
    eq = np.cumsum(r)
    running = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(running - eq, 0.0)
    cur = streak = 0
    for v in r:
        if v < 0:
            cur += 1
            streak = max(streak, cur)
        else:
            cur = 0
    return {
        "n": int(len(r)),
        "mean_net_points": float(x["net_points"].mean()),
        "sum_net_points": float(x["net_points"].sum()),
        "sum_net_usd": float(r.sum()),
        "pf": pf,
        "win_rate": float((r > 0).mean()),
        "avg_win_usd": float(pos.mean()) if len(pos) else None,
        "avg_loss_usd": float(neg.mean()) if len(neg) else None,
        "max_dd_usd": float(dd.max(initial=0.0)),
        "losing_streak": int(streak),
    }


def slice_metrics(x: pd.DataFrame, start: str | None = None, end: str | None = None) -> dict:
    if x.empty:
        return metrics(x)
    y = x.copy()
    t = pd.to_datetime(y["entry_time"])
    if start is not None:
        y = y[t >= pd.Timestamp(start, tz=TZ)]
        t = pd.to_datetime(y["entry_time"])
    if end is not None:
        y = y[t < pd.Timestamp(end, tz=TZ)]
    return metrics(y)


def main():
    out = Path("nq-noise-area/results/v1")
    out.mkdir(parents=True, exist_ok=True)
    try:
        df = load_data(out)
        ind = build_indicators(df)
        all_trades = []
        summaries = {}
        monthly_rows = []

        for scenario, spec in SCENARIOS.items():
            tr = run_scenario(ind, scenario, spec)
            if not tr.empty:
                tr["entry_time"] = pd.to_datetime(tr["entry_time"])
                tr["exit_time"] = pd.to_datetime(tr["exit_time"])
            all_trades.append(tr)
            summaries[scenario] = {
                "full": metrics(tr),
                "recent_may_jul": slice_metrics(tr, "2026-05-01", "2026-08-01"),
                "july": slice_metrics(tr, "2026-07-01", "2026-08-01"),
            }
            if not tr.empty:
                z = tr.copy()
                z["month"] = z["entry_time"].dt.strftime("%Y-%m")
                for month, g in z.groupby("month"):
                    m = metrics(g)
                    m.update({"scenario": scenario, "month": month})
                    monthly_rows.append(m)

        ledger = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
        ledger.to_csv(out / "trades.csv", index=False)
        monthly = pd.DataFrame(monthly_rows)
        monthly.to_csv(out / "monthly_metrics.csv", index=False)

        p = summaries["PRIMARY"]["full"]
        s = summaries["STRESS"]["full"]
        recent = summaries["PRIMARY"]["recent_may_jul"]
        pos_months = 0
        if not monthly.empty:
            mp = monthly[monthly["scenario"].eq("PRIMARY")]
            pos_months = int((mp["sum_net_usd"] > 0).sum())

        gates = {
            "primary_n_ge_30": p["n"] >= 30,
            "primary_mean_positive": p["mean_net_points"] is not None and p["mean_net_points"] > 0,
            "primary_pf_ge_1_20": p["pf"] is not None and p["pf"] >= 1.20,
            "primary_positive_months_ge_3": pos_months >= 3,
            "primary_max_dd_le_5000": p["max_dd_usd"] is not None and p["max_dd_usd"] <= 5000,
            "recent_may_jul_mean_nonnegative": recent["mean_net_points"] is not None and recent["mean_net_points"] >= 0,
            "stress_mean_positive": s["mean_net_points"] is not None and s["mean_net_points"] > 0,
            "stress_pf_gt_1_05": s["pf"] is not None and s["pf"] > 1.05,
        }
        all_pass = all(gates.values())
        if p["n"] < 30:
            status = "NQ_NOISE_AREA_PROPF_V1_INCONCLUSIVE_LOW_N"
        else:
            status = "NQ_NOISE_AREA_PROPF_V1_PASS_FOR_PROPFIRM_SIMULATION" if all_pass else "NQ_NOISE_AREA_PROPF_V1_NO_GO"

        result = {
            "status": status,
            "signal": {
                "lookback_days": LOOKBACK,
                "check_minutes_et": [f"{m//60:02d}:{m%60:02d}" for m in CHECK_MINUTES],
                "exit_mode": "final_vwap_and_band",
                "direction": "long_and_short_with_flips",
                "fixed_contracts": 1,
                "point_value_usd": POINT_VALUE,
            },
            "costs": SCENARIOS,
            "summaries": summaries,
            "positive_primary_months": pos_months,
            "gates": gates,
            "notes": [
                "No parameter optimisation on NQ 2026 sample.",
                "Strict 14-prior-session sigma requirement; current day excluded.",
                "Fixed one-contract NQ is used only for edge viability; prop-firm sizing is stage 2 after PASS.",
                "Signals evaluated at completed 30-minute checks; adverse slippage charged on each transaction side.",
            ],
        }
        (out / "RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        print(json.dumps(result, indent=2, allow_nan=False))
    except Exception as e:
        result = {"status": "NQ_NOISE_AREA_PROPF_V1_INVALID_ABORT", "error": repr(e)}
        (out / "RESULT.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        raise


if __name__ == "__main__":
    main()
