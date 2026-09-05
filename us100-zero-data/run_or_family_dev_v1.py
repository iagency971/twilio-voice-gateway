#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests

SOURCE_COMMIT = "50052606c16d71850755e6dbdda02d43b4399c2b"
SOURCE_REPO = "CodyOutcast/Academic-Paper-Data-Source"
YEARS = (2021, 2022, 2023, 2024)
POINT = 0.1
OUT = Path("us100-zero-data/results/or_family_v1")
CACHE = Path("/tmp/us100_or_family_v1")

OR_START_MIN = 16 * 60 + 30
SIGNAL_CUTOFF_MIN = 19 * 60
FLATTEN_MIN = 22 * 60 + 55
RANGE_LENGTHS = (15, 30)
RRS = (1.0, 1.5, 2.0)
FAMILIES = ("ORB", "ORF")


@dataclass
class Trade:
    year: int
    date: str
    family: str
    range_min: int
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


def url_for(year: int) -> str:
    assert year in YEARS
    return (
        f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/"
        f"OHLC-USTEC-M1-{year}.csv"
    )


def download_dev(year: int) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"OHLC-USTEC-M1-{year}.csv"
    if p.exists() and p.stat().st_size > 1000:
        return p
    r = requests.get(url_for(year), timeout=120)
    r.raise_for_status()
    p.write_bytes(r.content)
    return p


def load_year(year: int) -> tuple[pd.DataFrame, dict]:
    p = download_dev(year)
    d = pd.read_csv(p, sep=";")
    d.columns = [str(c).strip().lower() for c in d.columns]
    expected = ["time", "open", "high", "low", "close", "volume", "spread"]
    missing = [c for c in expected if c not in d.columns]
    if missing:
        raise RuntimeError(f"{year}: missing columns {missing}")
    d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    for c in ["open", "high", "low", "close", "volume", "spread"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["time", "open", "high", "low", "close", "spread"]).copy()
    d = d.sort_values("time").reset_index(drop=True)
    dup = int(d.duplicated("time").sum())
    bad_ohlc = int(((d.low > d.high) | (d.open < d.low) | (d.open > d.high) |
                    (d.close < d.low) | (d.close > d.high)).sum())
    bad_spread = int(((~np.isfinite(d.spread)) | (d.spread < 0)).sum())
    d["spread_px"] = d["spread"] * POINT
    d["date"] = d["time"].dt.date
    d["minute"] = d["time"].dt.hour * 60 + d["time"].dt.minute

    # A candidate NY session needs a complete 30-minute opening range and enough
    # bars afterward to make the 19:00 signal cutoff meaningful. We do not fill gaps.
    session_counts = d[(d.minute >= OR_START_MIN) & (d.minute < SIGNAL_CUTOFF_MIN)].groupby("date").size()
    candidate_sessions = int((session_counts >= 120).sum())
    qa = {
        "year": year,
        "rows": int(len(d)),
        "first": str(d.time.min()),
        "last": str(d.time.max()),
        "duplicates": dup,
        "ohlc_violations": bad_ohlc,
        "bad_spread": bad_spread,
        "candidate_sessions": candidate_sessions,
        "median_recorded_spread_points": float(d.spread.median()),
        "median_spread_price": float(d.spread_px.median()),
        "pass": bool(dup == 0 and bad_ohlc == 0 and bad_spread == 0 and candidate_sessions >= 200),
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
    }
    return d, qa


def _stats(vals) -> dict:
    a = np.asarray(list(vals), dtype=float)
    if len(a) == 0:
        return {"n": 0, "mean": None, "sum": 0.0, "pf": None,
                "win_rate": None, "max_dd": None, "losing_streak": None}
    eq = np.cumsum(a)
    peaks = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(peaks - eq, 0.0)
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    pf = (pos / neg) if neg > 0 else (1e99 if pos > 0 else None)
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
        "pf": float(pf) if pf is not None else None,
        "win_rate": float((a > 0).mean()),
        "max_dd": float(dd.max(initial=0.0)),
        "losing_streak": int(longest),
    }


def session_is_candidate(g: pd.DataFrame, L: int) -> bool:
    orbars = g[(g.minute >= OR_START_MIN) & (g.minute < OR_START_MIN + L)]
    if len(orbars) != L:
        return False
    expected = pd.date_range(orbars.time.iloc[0], periods=L, freq="min")
    if not np.array_equal(orbars.time.to_numpy(), expected.to_numpy()):
        return False
    sigbars = g[(g.minute >= OR_START_MIN + L) & (g.minute < SIGNAL_CUTOFF_MIN)]
    return len(sigbars) >= 60


def find_signal(g: pd.DataFrame, family: str, L: int) -> tuple[Optional[int], Optional[str], Optional[float], Optional[float]]:
    orbars = g[(g.minute >= OR_START_MIN) & (g.minute < OR_START_MIN + L)]
    if len(orbars) != L:
        return None, None, None, None
    orh = float(orbars.high.max())
    orl = float(orbars.low.min())
    start_min = OR_START_MIN + L
    for idx, b in g[(g.minute >= start_min) & (g.minute < SIGNAL_CUTOFF_MIN)].iterrows():
        if family == "ORB":
            if float(b.close) > orh:
                return int(idx), "long", orh, orl
            if float(b.close) < orl:
                return int(idx), "short", orh, orl
        elif family == "ORF":
            if float(b.high) > orh and float(b.close) < orh:
                return int(idx), "short", orh, orl
            if float(b.low) < orl and float(b.close) > orl:
                return int(idx), "long", orh, orl
        else:
            raise ValueError(family)
    return None, None, orh, orl


def simulate_day(g0: pd.DataFrame, year: int, family: str, L: int, rr: float,
                 spread_mult: float) -> Optional[Trade]:
    g = g0.reset_index(drop=True).copy()
    if not session_is_candidate(g, L):
        return None
    sig_idx, direction, orh, orl = find_signal(g, family, L)
    if sig_idx is None or direction is None:
        return None
    fill_idx = sig_idx + 1
    if fill_idx >= len(g):
        return None
    sig = g.iloc[sig_idx]
    fill = g.iloc[fill_idx]
    if fill.time.date() != sig.time.date():
        return None
    spr_fill = float(fill.spread_px) * spread_mult

    if direction == "long":
        entry = float(fill.open) + spr_fill
        stop = float(orl) if family == "ORB" else float(sig.low)
        risk = entry - stop
        if risk <= 0:
            return None
        target = entry + rr * risk
    else:
        entry = float(fill.open)
        stop = float(orh) if family == "ORB" else float(sig.high)
        # A short SL is triggered by ask. Reject a fill whose ask is already at/above stop.
        if entry + spr_fill >= stop:
            return None
        risk = stop - entry
        if risk <= 0:
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
            ask_high = float(b.high) + spr
            ask_low = float(b.low) + spr
            hit_stop = ask_high >= stop
            hit_target = ask_low <= target

        if hit_stop and hit_target:
            hit_target = False  # adverse same-bar ambiguity
        if hit_stop:
            exit_price = stop
            exit_time = b.time
            reason = "stop"
            break
        if hit_target:
            exit_price = target
            exit_time = b.time
            reason = "target"
            break
        if int(b.minute) >= FLATTEN_MIN:
            exit_price = float(b.close) if direction == "long" else float(b.close) + spr
            exit_time = b.time
            reason = "time_exit"
            break

    if exit_price is None:
        # If the archive ends early, close on last same-day available bar rather than inventing data.
        tail = g[(g.time.dt.date == sig.time.date()) & (g.index >= fill_idx)]
        if tail.empty:
            return None
        b = tail.iloc[-1]
        spr = float(b.spread_px) * spread_mult
        exit_price = float(b.close) if direction == "long" else float(b.close) + spr
        exit_time = b.time
        reason = "end_of_day_data"

    pnl = (exit_price - entry) if direction == "long" else (entry - exit_price)
    rval = pnl / risk
    return Trade(
        year=year, date=str(sig.time.date()), family=family, range_min=L, rr=rr,
        direction=direction, signal_time=str(sig.time), entry_time=str(fill.time),
        exit_time=str(exit_time), entry=float(entry), stop=float(stop), target=float(target),
        exit=float(exit_price), reason=str(reason), risk=float(risk), r=float(rval),
    )


def run_variant(data: dict[int, pd.DataFrame], family: str, L: int, rr: float,
                spread_mult: float) -> tuple[list[Trade], int]:
    trades: list[Trade] = []
    sessions = 0
    for year, d in data.items():
        for _, g in d.groupby("date", sort=True):
            g = g.reset_index(drop=True)
            if session_is_candidate(g, L):
                sessions += 1
            t = simulate_day(g, year, family, L, rr, spread_mult)
            if t is not None:
                trades.append(t)
    return trades, sessions


def summarize(trades: list[Trade], sessions: int) -> dict:
    vals = [t.r for t in trades]
    overall = _stats(vals)
    by_year = {}
    for y in YEARS:
        by_year[str(y)] = _stats([t.r for t in trades if t.year == y])
    overall["sessions"] = int(sessions)
    overall["frequency"] = float(len(trades) / sessions) if sessions else 0.0
    return {"overall": overall, "by_year": by_year}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data: dict[int, pd.DataFrame] = {}
    qa = {}
    for y in YEARS:
        d, q = load_year(y)
        data[y] = d
        qa[str(y)] = q
    if not all(q["pass"] for q in qa.values()):
        result = {"status": "OR_FAMILY_V1_DATA_QA_FAIL_NO_ECONOMICS", "data_qa": qa}
        (OUT / "DEV_RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        print(json.dumps(result, indent=2, allow_nan=False))
        return

    rows = []
    all_trade_rows = []
    for family in FAMILIES:
        for L in RANGE_LENGTHS:
            for rr in RRS:
                primary_trades, sessions = run_variant(data, family, L, rr, 1.0)
                stress_trades, stress_sessions = run_variant(data, family, L, rr, 2.0)
                if sessions != stress_sessions:
                    raise RuntimeError("Session denominator changed under spread stress")
                p = summarize(primary_trades, sessions)
                s = summarize(stress_trades, sessions)
                years_positive = sum(1 for y in YEARS if p["by_year"][str(y)]["sum"] > 0)
                yearly_means = [p["by_year"][str(y)]["mean"] for y in YEARS]
                median_year_exp = float(np.median([x for x in yearly_means if x is not None]))
                po = p["overall"]
                so = s["overall"]
                gate = {
                    "n_ge_400": po["n"] >= 400,
                    "frequency_ge_0_45": po["frequency"] >= 0.45,
                    "expectancy_ge_0_05": po["mean"] is not None and po["mean"] >= 0.05,
                    "pf_ge_1_15": po["pf"] is not None and po["pf"] >= 1.15,
                    "max_dd_le_15R": po["max_dd"] is not None and po["max_dd"] <= 15.0,
                    "years_positive_ge_3": years_positive >= 3,
                    "stress_expectancy_gt_0": so["mean"] is not None and so["mean"] > 0,
                    "stress_pf_ge_1_05": so["pf"] is not None and so["pf"] >= 1.05,
                }
                passed = all(gate.values())
                row = {
                    "family": family, "range_min": L, "rr": rr,
                    "primary": p, "stress": s,
                    "years_positive": years_positive,
                    "median_calendar_year_expectancy": median_year_exp,
                    "gate": gate, "pass": passed,
                }
                rows.append(row)
                for t in primary_trades:
                    all_trade_rows.append({**t.__dict__, "scenario": "PRIMARY"})
                for t in stress_trades:
                    all_trade_rows.append({**t.__dict__, "scenario": "STRESS"})

    eligible = [r for r in rows if r["pass"]]
    eligible.sort(key=lambda r: (-r["median_calendar_year_expectancy"],
                                 r["primary"]["overall"]["max_dd"],
                                 -r["primary"]["overall"]["n"]))
    selected = eligible[0] if eligible else None
    status = "OR_FAMILY_V1_DEV_PASS_SELECTION_READY" if selected else "OR_FAMILY_V1_DEV_NO_GO"
    result = {
        "status": status,
        "source_repo": SOURCE_REPO,
        "source_commit": SOURCE_COMMIT,
        "dev_years": list(YEARS),
        "oos_2025_opened": False,
        "spread_point_price": POINT,
        "data_qa": qa,
        "variants": rows,
        "selected": ({"family": selected["family"], "range_min": selected["range_min"],
                      "rr": selected["rr"],
                      "median_calendar_year_expectancy": selected["median_calendar_year_expectancy"],
                      "primary": selected["primary"], "stress": selected["stress"]}
                     if selected else None),
    }
    (OUT / "DEV_RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    pd.DataFrame(all_trade_rows).to_csv(OUT / "DEV_TRADES.csv", index=False)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
