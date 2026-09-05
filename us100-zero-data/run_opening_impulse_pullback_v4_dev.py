#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

import run_or_family_dev_v1 as base

YEARS = (2021, 2022, 2023)
QS = (0.67, 0.80)
RRS = (1.5, 2.0)
OR_START = 16 * 60 + 30
OR_END = 17 * 60
SIGNAL_START = 17 * 60
SIGNAL_END = 19 * 60 + 30
FLATTEN_MIN = 22 * 60 + 55
OUT = Path("us100-zero-data/results/opening_impulse_pullback_v4")


@dataclass
class Trade:
    year: int
    date: str
    q: float
    rr: float
    direction: str
    clv: float
    signal_time: str
    entry_time: str
    exit_time: str
    entry: float
    stop: float
    target: float
    exit: float
    reason: str
    risk: float
    r: float


def stats(vals) -> dict:
    a = np.asarray(list(vals), dtype=float)
    if len(a) == 0:
        return {"n": 0, "mean": None, "sum": 0.0, "pf": None,
                "win_rate": None, "max_dd": None, "losing_streak": None}
    eq = np.cumsum(a)
    peaks = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(peaks - eq, 0.0)
    pos = float(a[a > 0].sum()); neg = float(-a[a < 0].sum())
    pf = pos / neg if neg > 0 else (1e99 if pos > 0 else None)
    cur = longest = 0
    for v in a:
        if v < 0:
            cur += 1; longest = max(longest, cur)
        else:
            cur = 0
    return {
        "n": int(len(a)), "mean": float(a.mean()), "sum": float(a.sum()),
        "pf": float(pf) if pf is not None else None,
        "win_rate": float((a > 0).mean()),
        "max_dd": float(dd.max(initial=0.0)), "losing_streak": int(longest),
    }


def candidate_session(g: pd.DataFrame) -> bool:
    orb = g[(g.minute >= OR_START) & (g.minute < OR_END)]
    if len(orb) != 30:
        return False
    expected = pd.date_range(orb.time.iloc[0], periods=30, freq="min")
    if not np.array_equal(orb.time.to_numpy(), expected.to_numpy()):
        return False
    sig = g[(g.minute >= SIGNAL_START) & (g.minute < SIGNAL_END)]
    return len(sig) >= 120


def add_vwap(g0: pd.DataFrame) -> pd.DataFrame:
    g = g0.reset_index(drop=True).copy()
    g["vwap"] = np.nan
    idx = g.index[g.minute >= OR_START]
    if len(idx) == 0:
        return g
    s = g.loc[idx].copy()
    tp = (s.high + s.low + s.close) / 3.0
    vol = s.volume.clip(lower=0).fillna(0.0)
    cv = vol.cumsum()
    vw = (tp * vol).cumsum() / cv.replace(0, np.nan)
    g.loc[idx, "vwap"] = vw.to_numpy()
    return g


def opening_bias(g: pd.DataFrame, q: float) -> tuple[Optional[str], Optional[float]]:
    orb = g[(g.minute >= OR_START) & (g.minute < OR_END)]
    if len(orb) != 30:
        return None, None
    hi = float(orb.high.max()); lo = float(orb.low.min()); close = float(orb.close.iloc[-1])
    width = hi - lo
    if width <= 0:
        return None, None
    clv = (close - lo) / width
    if clv >= q:
        return "long", float(clv)
    if clv <= 1.0 - q:
        return "short", float(clv)
    return None, float(clv)


def find_signal(g: pd.DataFrame, bias: str) -> Optional[int]:
    for idx, b in g[(g.minute >= SIGNAL_START) & (g.minute < SIGNAL_END)].iterrows():
        if not np.isfinite(b.vwap):
            continue
        if bias == "long" and float(b.low) <= float(b.vwap) and float(b.close) > float(b.vwap):
            return int(idx)
        if bias == "short" and float(b.high) >= float(b.vwap) and float(b.close) < float(b.vwap):
            return int(idx)
    return None


def simulate(g0: pd.DataFrame, year: int, q: float, rr: float,
             spread_mult: float) -> Optional[Trade]:
    if not candidate_session(g0):
        return None
    g = add_vwap(g0)
    bias, clv = opening_bias(g, q)
    if bias is None:
        return None
    sig_idx = find_signal(g, bias)
    if sig_idx is None:
        return None
    fill_idx = sig_idx + 1
    if fill_idx >= len(g):
        return None
    sig = g.iloc[sig_idx]; fill = g.iloc[fill_idx]
    if fill.time.date() != sig.time.date():
        return None
    spr_fill = float(fill.spread_px) * spread_mult

    if bias == "long":
        entry = float(fill.open) + spr_fill
        stop = float(sig.low)
        risk = entry - stop
        if risk <= 0:
            return None
        target = entry + rr * risk
    else:
        entry = float(fill.open)
        stop = float(sig.high)
        if entry + spr_fill >= stop:
            return None
        risk = stop - entry
        if risk <= 0:
            return None
        target = entry - rr * risk

    exit_price = None; exit_time = None; reason = None
    for i in range(fill_idx, len(g)):
        b = g.iloc[i]
        if b.time.date() != sig.time.date():
            break
        spr = float(b.spread_px) * spread_mult
        if bias == "long":
            hit_stop = float(b.low) <= stop
            hit_target = float(b.high) >= target
        else:
            hit_stop = float(b.high) + spr >= stop
            hit_target = float(b.low) + spr <= target
        if hit_stop and hit_target:
            hit_target = False
        if hit_stop:
            exit_price = stop; exit_time = b.time; reason = "stop"; break
        if hit_target:
            exit_price = target; exit_time = b.time; reason = "target"; break
        if int(b.minute) >= FLATTEN_MIN:
            exit_price = float(b.close) if bias == "long" else float(b.close) + spr
            exit_time = b.time; reason = "time_exit"; break
    if exit_price is None:
        tail = g[(g.time.dt.date == sig.time.date()) & (g.index >= fill_idx)]
        if tail.empty:
            return None
        b = tail.iloc[-1]; spr = float(b.spread_px) * spread_mult
        exit_price = float(b.close) if bias == "long" else float(b.close) + spr
        exit_time = b.time; reason = "end_of_day_data"

    pnl = exit_price - entry if bias == "long" else entry - exit_price
    rval = float(pnl / risk)
    return Trade(year, str(sig.time.date()), q, rr, bias, float(clv), str(sig.time),
                 str(fill.time), str(exit_time), float(entry), float(stop), float(target),
                 float(exit_price), str(reason), float(risk), rval)


def load_dev():
    data = {}; qa = {}
    for y in YEARS:
        d, q0 = base.load_year(y)
        candidate = sum(candidate_session(g.reset_index(drop=True))
                        for _, g in d.groupby("date", sort=True))
        q = dict(q0); q["v4_candidate_sessions"] = int(candidate)
        q["pass"] = bool(q0["duplicates"] == 0 and q0["ohlc_violations"] == 0 and
                         q0["bad_spread"] == 0 and candidate >= 200)
        data[y] = d; qa[str(y)] = q
    return data, qa


def run_variant(data, q, rr, spread_mult):
    trades = []; sessions = 0
    for y, d in data.items():
        for _, g in d.groupby("date", sort=True):
            g = g.reset_index(drop=True)
            if candidate_session(g):
                sessions += 1
            t = simulate(g, y, q, rr, spread_mult)
            if t is not None:
                trades.append(t)
    return trades, sessions


def summarize(trades, sessions):
    overall = stats([t.r for t in trades]); overall["sessions"] = int(sessions)
    overall["frequency"] = float(len(trades) / sessions) if sessions else 0.0
    by_year = {str(y): stats([t.r for t in trades if t.year == y]) for y in YEARS}
    return {"overall": overall, "by_year": by_year}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data, qa = load_dev()
    if not all(q["pass"] for q in qa.values()):
        result = {"status": "OPENING_IMPULSE_PULLBACK_V4_DATA_QA_FAIL_NO_ECONOMICS", "data_qa": qa}
        (OUT / "DEV_RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        print(json.dumps(result, indent=2, allow_nan=False)); return

    variants = []; trade_rows = []
    for q in QS:
        for rr in RRS:
            pt, sessions = run_variant(data, q, rr, 1.0)
            st, s_sessions = run_variant(data, q, rr, 2.0)
            if sessions != s_sessions:
                raise RuntimeError("session denominator mismatch")
            p = summarize(pt, sessions); s = summarize(st, sessions)
            po = p["overall"]; so = s["overall"]
            years_positive = sum(p["by_year"][str(y)]["sum"] > 0 for y in YEARS)
            means = [p["by_year"][str(y)]["mean"] for y in YEARS if p["by_year"][str(y)]["mean"] is not None]
            med = float(np.median(means)) if means else -1e99
            gate = {
                "n_ge_180": po["n"] >= 180,
                "frequency_ge_0_25": po["frequency"] >= 0.25,
                "expectancy_ge_0_10": po["mean"] is not None and po["mean"] >= 0.10,
                "pf_ge_1_25": po["pf"] is not None and po["pf"] >= 1.25,
                "max_dd_le_12R": po["max_dd"] is not None and po["max_dd"] <= 12.0,
                "all_3_years_positive": years_positive == 3,
                "stress_expectancy_ge_0_05": so["mean"] is not None and so["mean"] >= 0.05,
                "stress_pf_ge_1_15": so["pf"] is not None and so["pf"] >= 1.15,
            }
            row = {"q": q, "rr": rr, "primary": p, "stress": s,
                   "years_positive": int(years_positive),
                   "median_calendar_year_expectancy": med,
                   "gate": gate, "pass": all(gate.values())}
            variants.append(row)
            trade_rows.extend([{**t.__dict__, "scenario": "PRIMARY"} for t in pt])
            trade_rows.extend([{**t.__dict__, "scenario": "STRESS"} for t in st])

    eligible = [v for v in variants if v["pass"]]
    eligible.sort(key=lambda v: (-v["median_calendar_year_expectancy"],
                                 v["primary"]["overall"]["max_dd"],
                                 -v["primary"]["overall"]["n"]))
    sel = eligible[0] if eligible else None
    status = "OPENING_IMPULSE_PULLBACK_V4_DEV_PASS_SELECTION_READY" if sel else "OPENING_IMPULSE_PULLBACK_V4_DEV_NO_GO"
    result = {
        "status": status,
        "source_repo": base.SOURCE_REPO, "source_commit": base.SOURCE_COMMIT,
        "dev_years": list(YEARS), "v4_oos_2024_opened": False,
        "data_qa": qa, "variants": variants,
        "selected": ({"q": sel["q"], "rr": sel["rr"],
                      "median_calendar_year_expectancy": sel["median_calendar_year_expectancy"],
                      "primary": sel["primary"], "stress": sel["stress"]} if sel else None),
    }
    (OUT / "DEV_RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    pd.DataFrame(trade_rows).to_csv(OUT / "DEV_TRADES.csv", index=False)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
