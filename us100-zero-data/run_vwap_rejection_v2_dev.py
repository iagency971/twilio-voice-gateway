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
KS = (1.0, 1.5, 2.0)
RRS = (1.0, 1.5, 2.0)
SESSION_START = 16 * 60 + 30
SIGNAL_START = 17 * 60
SIGNAL_END = 20 * 60 + 30
FLATTEN_MIN = 22 * 60 + 55
OUT = Path("us100-zero-data/results/vwap_rejection_v2")


@dataclass
class Trade:
    year: int
    date: str
    k: float
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
    pre = g[(g.minute >= SESSION_START) & (g.minute < SIGNAL_START)]
    if len(pre) != 30:
        return False
    expected = pd.date_range(pre.time.iloc[0], periods=30, freq="min")
    if not np.array_equal(pre.time.to_numpy(), expected.to_numpy()):
        return False
    sig = g[(g.minute >= SIGNAL_START) & (g.minute < SIGNAL_END)]
    return len(sig) >= 120


def add_features(g0: pd.DataFrame) -> pd.DataFrame:
    g = g0.reset_index(drop=True).copy()
    sess = g[g.minute >= SESSION_START].copy()
    if sess.empty:
        return g.assign(vwap=np.nan, atr14=np.nan)
    tp = (sess.high + sess.low + sess.close) / 3.0
    vol = sess.volume.clip(lower=0).fillna(0.0)
    cumv = vol.cumsum()
    vwap = (tp * vol).cumsum() / cumv.replace(0, np.nan)
    prev = sess.close.shift(1)
    tr = pd.concat([
        sess.high - sess.low,
        (sess.high - prev).abs(),
        (sess.low - prev).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=14).mean()
    g["vwap"] = np.nan; g["atr14"] = np.nan
    g.loc[sess.index, "vwap"] = vwap.to_numpy()
    g.loc[sess.index, "atr14"] = atr.to_numpy()
    return g


def find_signal(g: pd.DataFrame, k: float) -> tuple[Optional[int], Optional[str]]:
    for idx, b in g[(g.minute >= SIGNAL_START) & (g.minute < SIGNAL_END)].iterrows():
        if not np.isfinite(b.vwap) or not np.isfinite(b.atr14) or b.atr14 <= 0:
            continue
        lower = float(b.vwap - k * b.atr14)
        upper = float(b.vwap + k * b.atr14)
        long_sig = float(b.low) < lower and float(b.close) > lower
        short_sig = float(b.high) > upper and float(b.close) < upper
        if long_sig and short_sig:
            continue
        if long_sig:
            return int(idx), "long"
        if short_sig:
            return int(idx), "short"
    return None, None


def simulate(g0: pd.DataFrame, year: int, k: float, rr: float,
             spread_mult: float) -> Optional[Trade]:
    g = add_features(g0)
    if not candidate_session(g):
        return None
    sig_idx, direction = find_signal(g, k)
    if sig_idx is None or direction is None:
        return None
    fill_idx = sig_idx + 1
    if fill_idx >= len(g):
        return None
    sig = g.iloc[sig_idx]; fill = g.iloc[fill_idx]
    if fill.time.date() != sig.time.date():
        return None
    spr_fill = float(fill.spread_px) * spread_mult
    if direction == "long":
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
        b = tail.iloc[-1]; spr = float(b.spread_px) * spread_mult
        exit_price = float(b.close) if direction == "long" else float(b.close) + spr
        exit_time = b.time; reason = "end_of_day_data"
    pnl = exit_price - entry if direction == "long" else entry - exit_price
    rval = pnl / risk
    return Trade(year, str(sig.time.date()), k, rr, direction, str(sig.time), str(fill.time),
                 str(exit_time), float(entry), float(stop), float(target), float(exit_price),
                 str(reason), float(risk), float(rval))


def load_dev():
    data = {}; qa = {}
    for y in YEARS:
        d, q0 = base.load_year(y)
        candidate = sum(candidate_session(g.reset_index(drop=True)) for _, g in d.groupby("date", sort=True))
        q = dict(q0); q["v2_candidate_sessions"] = int(candidate)
        q["pass"] = bool(q0["duplicates"] == 0 and q0["ohlc_violations"] == 0 and
                         q0["bad_spread"] == 0 and candidate >= 200)
        data[y] = d; qa[str(y)] = q
    return data, qa


def run_variant(data, k, rr, spread_mult):
    trades = []; sessions = 0
    for y, d in data.items():
        for _, g in d.groupby("date", sort=True):
            g = g.reset_index(drop=True)
            if candidate_session(g):
                sessions += 1
            t = simulate(g, y, k, rr, spread_mult)
            if t is not None:
                trades.append(t)
    return trades, sessions


def summarize(trades, sessions):
    overall = stats([t.r for t in trades]); overall["sessions"] = sessions
    overall["frequency"] = len(trades) / sessions if sessions else 0.0
    by_year = {str(y): stats([t.r for t in trades if t.year == y]) for y in YEARS}
    return {"overall": overall, "by_year": by_year}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data, qa = load_dev()
    if not all(q["pass"] for q in qa.values()):
        result = {"status": "VWAP_REJECTION_V2_DATA_QA_FAIL_NO_ECONOMICS", "data_qa": qa}
        (OUT / "DEV_RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        print(json.dumps(result, indent=2, allow_nan=False)); return

    variants = []; trade_rows = []
    for k in KS:
        for rr in RRS:
            pt, sessions = run_variant(data, k, rr, 1.0)
            st, s_sessions = run_variant(data, k, rr, 2.0)
            if sessions != s_sessions:
                raise RuntimeError("session denominator mismatch")
            p = summarize(pt, sessions); s = summarize(st, sessions)
            po = p["overall"]; so = s["overall"]
            years_positive = sum(p["by_year"][str(y)]["sum"] > 0 for y in YEARS)
            median_year = float(np.median([p["by_year"][str(y)]["mean"] for y in YEARS]))
            gate = {
                "n_ge_250": po["n"] >= 250,
                "frequency_ge_0_35": po["frequency"] >= 0.35,
                "expectancy_ge_0_05": po["mean"] is not None and po["mean"] >= 0.05,
                "pf_ge_1_15": po["pf"] is not None and po["pf"] >= 1.15,
                "max_dd_le_15R": po["max_dd"] is not None and po["max_dd"] <= 15.0,
                "all_3_years_positive": years_positive == 3,
                "stress_expectancy_gt_0": so["mean"] is not None and so["mean"] > 0,
                "stress_pf_ge_1_05": so["pf"] is not None and so["pf"] >= 1.05,
            }
            row = {"k": k, "rr": rr, "primary": p, "stress": s,
                   "years_positive": int(years_positive),
                   "median_calendar_year_expectancy": median_year,
                   "gate": gate, "pass": all(gate.values())}
            variants.append(row)
            trade_rows.extend([{**t.__dict__, "scenario": "PRIMARY"} for t in pt])
            trade_rows.extend([{**t.__dict__, "scenario": "STRESS"} for t in st])

    eligible = [v for v in variants if v["pass"]]
    eligible.sort(key=lambda v: (-v["median_calendar_year_expectancy"],
                                 v["primary"]["overall"]["max_dd"],
                                 -v["primary"]["overall"]["n"]))
    sel = eligible[0] if eligible else None
    status = "VWAP_REJECTION_V2_DEV_PASS_SELECTION_READY" if sel else "VWAP_REJECTION_V2_DEV_NO_GO"
    result = {
        "status": status,
        "source_repo": base.SOURCE_REPO, "source_commit": base.SOURCE_COMMIT,
        "dev_years": list(YEARS), "v2_oos_2024_opened": False,
        "data_qa": qa, "variants": variants,
        "selected": ({"k": sel["k"], "rr": sel["rr"],
                      "median_calendar_year_expectancy": sel["median_calendar_year_expectancy"],
                      "primary": sel["primary"], "stress": sel["stress"]} if sel else None),
    }
    (OUT / "DEV_RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    pd.DataFrame(trade_rows).to_csv(OUT / "DEV_TRADES.csv", index=False)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
