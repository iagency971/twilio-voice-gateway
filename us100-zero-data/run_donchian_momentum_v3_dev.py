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
LOOKBACKS = (20, 40, 60)
ATR_MULTS = (1.0, 1.5)
RRS = (1.5, 2.0)
SESSION_START = 16 * 60 + 30
SIGNAL_START = 17 * 60
SIGNAL_END = 20 * 60 + 30
FLATTEN_MIN = 22 * 60 + 55
OUT = Path("us100-zero-data/results/donchian_momentum_v3")


@dataclass
class Trade:
    year: int
    date: str
    lookback: int
    atr_mult: float
    rr: float
    direction: str
    signal_time: str
    entry_time: str
    exit_time: str
    entry: float
    stop: float
    target: float
    exit: float
    reason: str
    atr14: float
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


def candidate_session(g: pd.DataFrame) -> bool:
    pre = g[(g.minute >= SESSION_START) & (g.minute < SIGNAL_START)]
    if len(pre) != 30:
        return False
    expected = pd.date_range(pre.time.iloc[0], periods=30, freq="min")
    if not np.array_equal(pre.time.to_numpy(), expected.to_numpy()):
        return False
    sig = g[(g.minute >= SIGNAL_START) & (g.minute < SIGNAL_END)]
    return len(sig) >= 120


def add_features(g0: pd.DataFrame, n: int) -> pd.DataFrame:
    g = g0.reset_index(drop=True).copy()
    g["atr14"] = np.nan
    g["prior_high"] = np.nan
    g["prior_low"] = np.nan
    sess_idx = g.index[g.minute >= SESSION_START]
    if len(sess_idx) == 0:
        return g
    sess = g.loc[sess_idx].copy()
    prev = sess.close.shift(1)
    tr = pd.concat([
        sess.high - sess.low,
        (sess.high - prev).abs(),
        (sess.low - prev).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=14).mean()
    ph = sess.high.shift(1).rolling(n, min_periods=n).max()
    pl = sess.low.shift(1).rolling(n, min_periods=n).min()
    g.loc[sess_idx, "atr14"] = atr.to_numpy()
    g.loc[sess_idx, "prior_high"] = ph.to_numpy()
    g.loc[sess_idx, "prior_low"] = pl.to_numpy()
    return g


def find_signal(g: pd.DataFrame) -> tuple[Optional[int], Optional[str]]:
    for idx, b in g[(g.minute >= SIGNAL_START) & (g.minute < SIGNAL_END)].iterrows():
        if not (np.isfinite(b.atr14) and np.isfinite(b.prior_high) and np.isfinite(b.prior_low)):
            continue
        long_sig = float(b.close) > float(b.prior_high)
        short_sig = float(b.close) < float(b.prior_low)
        if long_sig and short_sig:
            continue
        if long_sig:
            return int(idx), "long"
        if short_sig:
            return int(idx), "short"
    return None, None


def simulate(g0: pd.DataFrame, year: int, n: int, m: float, rr: float,
             spread_mult: float) -> Optional[Trade]:
    if not candidate_session(g0):
        return None
    g = add_features(g0, n)
    sig_idx, direction = find_signal(g)
    if sig_idx is None or direction is None:
        return None
    fill_idx = sig_idx + 1
    if fill_idx >= len(g):
        return None
    sig = g.iloc[sig_idx]
    fill = g.iloc[fill_idx]
    if fill.time.date() != sig.time.date():
        return None
    atr = float(sig.atr14)
    if not np.isfinite(atr) or atr <= 0:
        return None
    risk = float(m * atr)
    if risk <= 0:
        return None
    spr_fill = float(fill.spread_px) * spread_mult

    if direction == "long":
        entry = float(fill.open) + spr_fill
        stop = entry - risk
        target = entry + rr * risk
    else:
        entry = float(fill.open)
        stop = entry + risk
        if entry + spr_fill >= stop:
            return None
        target = entry - rr * risk

    exit_price = None
    exit_time = None
    reason = None
    for i in range(fill_idx, len(g)):
        b = g.iloc[i]
        if b.time.date() != sig.time.date():
            break
        spr = float(b.spread_px) * spread_mult
        if direction == "long":
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
            exit_price = float(b.close) if direction == "long" else float(b.close) + spr
            exit_time = b.time; reason = "time_exit"; break

    if exit_price is None:
        tail = g[(g.time.dt.date == sig.time.date()) & (g.index >= fill_idx)]
        if tail.empty:
            return None
        b = tail.iloc[-1]
        spr = float(b.spread_px) * spread_mult
        exit_price = float(b.close) if direction == "long" else float(b.close) + spr
        exit_time = b.time; reason = "end_of_day_data"

    pnl = exit_price - entry if direction == "long" else entry - exit_price
    rval = float(pnl / risk)
    return Trade(year, str(sig.time.date()), n, m, rr, direction,
                 str(sig.time), str(fill.time), str(exit_time), float(entry),
                 float(stop), float(target), float(exit_price), str(reason),
                 atr, risk, rval)


def load_dev():
    data = {}; qa = {}
    for y in YEARS:
        d, q0 = base.load_year(y)
        candidate = sum(candidate_session(g.reset_index(drop=True))
                        for _, g in d.groupby("date", sort=True))
        q = dict(q0)
        q["v3_candidate_sessions"] = int(candidate)
        q["pass"] = bool(q0["duplicates"] == 0 and q0["ohlc_violations"] == 0 and
                         q0["bad_spread"] == 0 and candidate >= 200)
        data[y] = d; qa[str(y)] = q
    return data, qa


def run_variant(data, n, m, rr, spread_mult):
    trades = []; sessions = 0
    for y, d in data.items():
        for _, g in d.groupby("date", sort=True):
            g = g.reset_index(drop=True)
            if candidate_session(g):
                sessions += 1
            t = simulate(g, y, n, m, rr, spread_mult)
            if t is not None:
                trades.append(t)
    return trades, sessions


def summarize(trades, sessions):
    overall = stats([t.r for t in trades])
    overall["sessions"] = int(sessions)
    overall["frequency"] = float(len(trades) / sessions) if sessions else 0.0
    by_year = {str(y): stats([t.r for t in trades if t.year == y]) for y in YEARS}
    return {"overall": overall, "by_year": by_year}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data, qa = load_dev()
    if not all(q["pass"] for q in qa.values()):
        result = {"status": "DONCHIAN_MOMENTUM_V3_DATA_QA_FAIL_NO_ECONOMICS", "data_qa": qa}
        (OUT / "DEV_RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        print(json.dumps(result, indent=2, allow_nan=False))
        return

    variants = []; trade_rows = []
    for n in LOOKBACKS:
        for m in ATR_MULTS:
            for rr in RRS:
                pt, sessions = run_variant(data, n, m, rr, 1.0)
                st, s_sessions = run_variant(data, n, m, rr, 2.0)
                if sessions != s_sessions:
                    raise RuntimeError("session denominator mismatch")
                p = summarize(pt, sessions); s = summarize(st, sessions)
                po = p["overall"]; so = s["overall"]
                years_positive = sum(p["by_year"][str(y)]["sum"] > 0 for y in YEARS)
                med = float(np.median([p["by_year"][str(y)]["mean"] for y in YEARS]))
                gate = {
                    "n_ge_250": po["n"] >= 250,
                    "frequency_ge_0_30": po["frequency"] >= 0.30,
                    "expectancy_ge_0_08": po["mean"] is not None and po["mean"] >= 0.08,
                    "pf_ge_1_20": po["pf"] is not None and po["pf"] >= 1.20,
                    "max_dd_le_15R": po["max_dd"] is not None and po["max_dd"] <= 15.0,
                    "all_3_years_positive": years_positive == 3,
                    "stress_expectancy_ge_0_03": so["mean"] is not None and so["mean"] >= 0.03,
                    "stress_pf_ge_1_10": so["pf"] is not None and so["pf"] >= 1.10,
                }
                row = {
                    "lookback": n, "atr_mult": m, "rr": rr,
                    "primary": p, "stress": s,
                    "years_positive": int(years_positive),
                    "median_calendar_year_expectancy": med,
                    "gate": gate, "pass": all(gate.values()),
                }
                variants.append(row)
                trade_rows.extend([{**t.__dict__, "scenario": "PRIMARY"} for t in pt])
                trade_rows.extend([{**t.__dict__, "scenario": "STRESS"} for t in st])

    eligible = [v for v in variants if v["pass"]]
    eligible.sort(key=lambda v: (-v["median_calendar_year_expectancy"],
                                 v["primary"]["overall"]["max_dd"],
                                 -v["primary"]["overall"]["n"]))
    sel = eligible[0] if eligible else None
    status = "DONCHIAN_MOMENTUM_V3_DEV_PASS_SELECTION_READY" if sel else "DONCHIAN_MOMENTUM_V3_DEV_NO_GO"
    result = {
        "status": status,
        "source_repo": base.SOURCE_REPO, "source_commit": base.SOURCE_COMMIT,
        "dev_years": list(YEARS), "v3_oos_2024_opened": False,
        "data_qa": qa, "variants": variants,
        "selected": ({"lookback": sel["lookback"], "atr_mult": sel["atr_mult"],
                      "rr": sel["rr"],
                      "median_calendar_year_expectancy": sel["median_calendar_year_expectancy"],
                      "primary": sel["primary"], "stress": sel["stress"]} if sel else None),
    }
    (OUT / "DEV_RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    pd.DataFrame(trade_rows).to_csv(OUT / "DEV_TRADES.csv", index=False)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
