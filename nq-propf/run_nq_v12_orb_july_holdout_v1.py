#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

GETDATA_URL = "https://raw.githubusercontent.com/getdata-finance/nq-1m-ohlcv-stocks-historical-data/main/NQ_1m.csv"
AXB_15M_URL = "https://raw.githubusercontent.com/axb0306/cme-futures-ohlc/main/NQ/NQ_15min_20260120_20260415.csv"
ET = ZoneInfo("America/New_York")

HOLDOUT_START = pd.Timestamp("2026-07-06")
HOLDOUT_END = pd.Timestamp("2026-07-31")

OR_MIN = 55.0
OR_MAX = 110.0
BRK_BUF = 4.0
GAP_FILTER = 20.0
MIN_BRK_VOL = 200.0
REGIME_MIN = 0.18
REGIME_LEN = 14
STOP_DIST = 27.0
TARGET_DIST = 54.0
COMMISSION_RT_POINTS = 5.0 / 20.0  # $5 RT / $20 per NQ point

SCENARIOS = {
    "PRIMARY": {"entry_slip": 0.50, "stop_slip": 0.50, "time_slip": 0.50},
    "STRESS":  {"entry_slip": 1.00, "stop_slip": 1.00, "time_slip": 1.00},
}


@dataclass
class DayContext:
    date: pd.Timestamp
    high: float
    low: float
    close: float
    vwap: float
    range: float


def download_csv(url: str, timeout: int = 120) -> pd.DataFrame:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    if len(r.content) < 100_000:
        raise RuntimeError(f"download unexpectedly small: {url} bytes={len(r.content)}")
    from io import BytesIO
    return pd.read_csv(BytesIO(r.content))


def load_getdata() -> pd.DataFrame:
    d = download_csv(GETDATA_URL)
    req = {"datetime", "open", "high", "low", "close", "volume"}
    if not req.issubset(d.columns):
        raise RuntimeError(f"GetData missing columns: {sorted(req-set(d.columns))}")
    d["utc"] = pd.to_datetime(d["datetime"], utc=True, errors="coerce")
    for c in ["open", "high", "low", "close", "volume"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["utc", "open", "high", "low", "close", "volume"]).copy()
    d = d.sort_values("utc").drop_duplicates("utc", keep="last")
    d["et"] = d["utc"].dt.tz_convert(ET)
    d["date"] = d["et"].dt.tz_localize(None).dt.normalize()
    d["minute"] = d["et"].dt.hour * 60 + d["et"].dt.minute
    return d


def data_identity_qa(getdata: pd.DataFrame, out: Path) -> dict:
    a = download_csv(AXB_15M_URL)
    req = {"datetime", "open", "high", "low", "close", "volume"}
    if not req.issubset(a.columns):
        raise RuntimeError("AXB source missing required columns")
    a["utc"] = pd.to_datetime(a["datetime"], utc=True, errors="coerce")
    for c in ["open", "high", "low", "close", "volume"]:
        a[c] = pd.to_numeric(a[c], errors="coerce")
    a = a.dropna(subset=["utc", "open", "high", "low", "close", "volume"]).copy()

    # Use February only: comfortably away from the March futures roll.
    lo = pd.Timestamp("2026-02-02", tz="UTC")
    hi = pd.Timestamp("2026-03-01", tz="UTC")
    g = getdata[(getdata.utc >= lo) & (getdata.utc < hi)].copy()
    # Restrict to RTH in ET before aggregation.
    g = g[(g.minute >= 570) & (g.minute < 960)].copy()
    gi = g.set_index("utc")
    g15 = gi.resample("15min", label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum"), count=("close", "count")
    ).dropna(subset=["open", "high", "low", "close"])
    g15 = g15[g15["count"] >= 10]

    a = a[(a.utc >= lo) & (a.utc < hi)].copy().set_index("utc")
    j = g15.add_prefix("g_").join(a[["open", "high", "low", "close", "volume"]].add_prefix("a_"), how="inner")
    if len(j) < 300:
        raise RuntimeError(f"cross-source overlap too small: {len(j)} bars")

    for c in ["open", "high", "low", "close"]:
        j[f"d_{c}"] = (j[f"g_{c}"] - j[f"a_{c}"]).abs()
    j["d_ohlc_max"] = j[["d_open", "d_high", "d_low", "d_close"]].max(axis=1)
    med_close = float(j.d_close.median())
    pct_close_05 = float((j.d_close <= 0.50).mean())
    med_ohlc_max = float(j.d_ohlc_max.median())
    pct_ohlc_1 = float((j.d_ohlc_max <= 1.0).mean())
    vol_ratio = (j.g_volume / j.a_volume.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    qa = {
        "overlap_15m_bars": int(len(j)),
        "median_abs_close_diff": med_close,
        "pct_close_within_0_50": pct_close_05,
        "median_max_ohlc_diff": med_ohlc_max,
        "pct_all_ohlc_within_1pt": pct_ohlc_1,
        "median_getdata_to_axb_volume_ratio": float(vol_ratio.median()) if vol_ratio.notna().any() else None,
        "pass": bool(med_close <= 0.25 and pct_close_05 >= 0.95),
    }
    j.reset_index().to_csv(out / "cross_source_february_15m.csv", index=False)
    (out / "data_identity_qa.json").write_text(json.dumps(qa, indent=2))
    return qa


def build_rth_days(d: pd.DataFrame):
    rth = d[(d.minute >= 570) & (d.minute < 960)].copy()
    days = {}
    qc = []
    for date, g in rth.groupby("date", sort=True):
        g = g.sort_values("minute").drop_duplicates("minute", keep="last").copy()
        required = {570, 575, 584, 585, 629, 955}
        have = set(g.minute.astype(int))
        # Previous-day context may use partial sessions, but current strategy days require morning bars.
        morning_ok = all(m in have for m in [570, 575, 584, 585, 629])
        if not morning_ok:
            qc.append({"date": str(date.date()), "bars": int(len(g)), "morning_ok": False})
            continue
        days[date] = g.reset_index(drop=True)
        qc.append({"date": str(date.date()), "bars": int(len(g)), "morning_ok": True,
                   "first_minute": int(g.minute.min()), "last_minute": int(g.minute.max())})
    return days, pd.DataFrame(qc)


def day_context(g: pd.DataFrame) -> DayContext:
    vol = g.volume.astype(float)
    vden = float(vol.sum())
    vwap = float((g.close.astype(float) * vol).sum() / vden) if vden > 0 else float(g.close.iloc[-1])
    return DayContext(
        date=pd.Timestamp(g.date.iloc[0]), high=float(g.high.max()), low=float(g.low.min()),
        close=float(g.close.iloc[-1]), vwap=vwap, range=float(g.high.max() - g.low.min())
    )


def confidence_score(g: pd.DataFrame, prev: DayContext, direction: int) -> tuple[int, dict]:
    # Current-day close-based VWAP snapshots include each named minute, matching v12.
    pre935 = g[(g.minute >= 570) & (g.minute <= 575)]
    pre944 = g[(g.minute >= 570) & (g.minute <= 584)]
    if pre935.empty or pre944.empty:
        return -1, {}
    def cvwap(x):
        v = x.volume.astype(float)
        den = float(v.sum())
        return float((x.close.astype(float) * v).sum() / den) if den > 0 else float(x.close.iloc[-1])
    v935, v944 = cvwap(pre935), cvwap(pre944)
    or_close = float(g.loc[g.minute.eq(584), "close"].iloc[-1])

    H, L, C = prev.high, prev.low, prev.close
    P = (H + L + C) / 3.0
    R1 = 2 * P - L
    R2 = P + (H - L)
    S1 = 2 * P - H
    S2 = P - (H - L)
    score = 0
    if (direction == 1 and or_close > P) or (direction == -1 and or_close < P):
        score += 1
    if (direction == 1 and or_close > prev.vwap) or (direction == -1 and or_close < prev.vwap):
        score += 1
    if direction == 1 and R1 <= or_close <= R2:
        score += 1
    elif direction == -1 and S2 <= or_close <= S1:
        score += 1
    slope = v944 - v935
    if (direction == 1 and slope > 0) or (direction == -1 and slope < 0):
        score += 1
    return score, {"or_close": or_close, "vwap_935": v935, "vwap_944": v944, "vwap_slope": slope,
                   "P": P, "R1": R1, "R2": R2, "S1": S1, "S2": S2}


def signal_ok(row: pd.Series, direction: int, or_hi: float, or_lo: float,
              gap: float, conf: int) -> bool:
    close = float(row["close"])
    brk = close > or_hi + BRK_BUF if direction == 1 else close < or_lo - BRK_BUF
    gap_ok = gap > GAP_FILTER if direction == 1 else gap < -GAP_FILTER
    return bool(brk and gap_ok and float(row["volume"]) >= MIN_BRK_VOL and conf >= 3)


def find_signal(g: pd.DataFrame, start_min: int, or_hi: float, or_lo: float,
                gap: float, conf_long: int, conf_short: int):
    scan = g[(g.minute >= max(586, start_min)) & (g.minute <= 629)].copy()
    for idx, row in scan.iterrows():
        close = float(row["close"])
        if close > or_hi + BRK_BUF and signal_ok(row, 1, or_hi, or_lo, gap, conf_long):
            return idx, 1
        if close < or_lo - BRK_BUF and signal_ok(row, -1, or_hi, or_lo, gap, conf_short):
            return idx, -1
    return None, None


def simulate_trade(g: pd.DataFrame, sig_idx: int, direction: int, scenario: dict):
    # sig_idx is the original DataFrame index; locate it positionally.
    pos_list = list(g.index)
    try:
        p = pos_list.index(sig_idx)
    except ValueError:
        return None
    if p + 1 >= len(g):
        return None
    sig = g.loc[sig_idx]
    entry_bar = g.iloc[p + 1]
    if int(entry_bar.minute) > 630:  # a 10:29 signal may enter 10:30, never later
        return None

    sig_close = float(sig.close)
    entry_open = float(entry_bar.open)
    es = float(scenario["entry_slip"])
    ss = float(scenario["stop_slip"])
    ts = float(scenario["time_slip"])
    entry = entry_open + es if direction == 1 else entry_open - es
    stop = sig_close - STOP_DIST if direction == 1 else sig_close + STOP_DIST
    target = sig_close + TARGET_DIST if direction == 1 else sig_close - TARGET_DIST

    bars = g.iloc[p + 1:].copy()
    exit_price = None
    exit_idx = None
    reason = None
    for idx, b in bars.iterrows():
        minute = int(b.minute)
        if minute > 955:
            break
        o, h, l, c = map(float, [b.open, b.high, b.low, b.close])
        if direction == 1:
            # Gap through stop is worse than the stop price.
            if o <= stop:
                exit_price = o - ss; exit_idx = idx; reason = "SL_GAP"; break
            if o >= target:
                exit_price = target; exit_idx = idx; reason = "TP_GAP_CAPPED"; break
            hit_stop = l <= stop
            hit_target = h >= target
            if hit_stop:  # conservative if both in same bar
                exit_price = stop - ss; exit_idx = idx; reason = "SL_AMBIG" if hit_target else "SL"; break
            if hit_target:
                exit_price = target; exit_idx = idx; reason = "TP"; break
        else:
            if o >= stop:
                exit_price = o + ss; exit_idx = idx; reason = "SL_GAP"; break
            if o <= target:
                exit_price = target; exit_idx = idx; reason = "TP_GAP_CAPPED"; break
            hit_stop = h >= stop
            hit_target = l <= target
            if hit_stop:
                exit_price = stop + ss; exit_idx = idx; reason = "SL_AMBIG" if hit_target else "SL"; break
            if hit_target:
                exit_price = target; exit_idx = idx; reason = "TP"; break

        if minute >= 955:
            exit_price = c - ts if direction == 1 else c + ts
            exit_idx = idx; reason = "TIME"; break

    if exit_price is None:
        last = bars.iloc[-1]
        exit_price = float(last.close) - ts if direction == 1 else float(last.close) + ts
        exit_idx = bars.index[-1]; reason = "TIME_LAST"

    gross_points = direction * (exit_price - entry)
    net_points = gross_points - COMMISSION_RT_POINTS
    return {
        "signal_index": int(sig_idx), "exit_index": int(exit_idx), "direction": "LONG" if direction == 1 else "SHORT",
        "signal_time": str(sig.et), "entry_time": str(entry_bar.et), "exit_time": str(g.loc[exit_idx].et),
        "signal_close": sig_close, "entry_open": entry_open, "entry_fill": entry,
        "stop": stop, "target": target, "exit_fill": exit_price, "exit_reason": reason,
        "gross_points": gross_points, "net_points": net_points, "net_R": net_points / STOP_DIST,
    }


def metrics(x: pd.DataFrame) -> dict:
    if x.empty:
        return {"n": 0, "mean_R": None, "sum_R": 0.0, "pf": None, "win_rate": None,
                "max_dd_R": None, "sum_points": 0.0, "mean_points": None}
    r = x.net_R.astype(float).to_numpy()
    pts = x.net_points.astype(float).to_numpy()
    pos = r[r > 0].sum(); neg = -r[r < 0].sum()
    pf = float(pos / neg) if neg > 0 else (float("inf") if pos > 0 else None)
    eq = np.cumsum(r); peak = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(peak - eq, 0)
    return {"n": int(len(r)), "mean_R": float(r.mean()), "sum_R": float(r.sum()), "pf": pf,
            "win_rate": float((r > 0).mean()), "max_dd_R": float(dd.max(initial=0.0)),
            "sum_points": float(pts.sum()), "mean_points": float(pts.mean())}


def run_scenario(days: dict, contexts: dict, scenario_name: str, scenario: dict):
    trades = []
    day_rows = []
    prior_ranges = []
    sorted_dates = sorted(days)
    for date in sorted_dates:
        g = days[date]
        # Use context from the immediately previous available trading session.
        prev_dates = [d for d in sorted_dates if d < date and d in contexts]
        if not prev_dates:
            ctx = contexts.get(date)
            if ctx: prior_ranges.append(ctx.range)
            continue
        prev_date = prev_dates[-1]
        prev = contexts[prev_date]
        is_holdout = HOLDOUT_START <= date <= HOLDOUT_END

        # The regime queue contains only completed prior sessions.
        avg_range = float(np.mean(prior_ranges[-REGIME_LEN:])) if prior_ranges else None

        # Compute today's OR even on skipped days for diagnostics, but no trade Monday.
        org = g[(g.minute >= 570) & (g.minute <= 584)]
        if len(org) < 10:
            if date in contexts: prior_ranges.append(contexts[date].range)
            continue
        or_hi = float(org.high.max()); or_lo = float(org.low.min()); or_range = or_hi - or_lo
        gap = (or_hi + or_lo) / 2.0 - prev.close
        c_long, detail_long = confidence_score(g, prev, 1)
        c_short, detail_short = confidence_score(g, prev, -1)
        weekday = int(date.dayofweek)  # Mon=0
        eligible_day = weekday != 0 and OR_MIN <= or_range <= OR_MAX
        if len(prior_ranges) >= 3 and avg_range is not None:
            eligible_day = eligible_day and (or_range >= avg_range * REGIME_MIN)

        n_day_trades = 0
        day_net = 0.0
        orb1_reason = None
        orb2_reason = None
        if is_holdout and eligible_day:
            sig_idx, direction = find_signal(g, 586, or_hi, or_lo, gap, c_long, c_short)
            if sig_idx is not None:
                t1 = simulate_trade(g, sig_idx, direction, scenario)
                if t1 is not None:
                    t1.update({"date": str(date.date()), "scenario": scenario_name, "slot": "ORB1",
                               "or_high": or_hi, "or_low": or_lo, "or_range": or_range,
                               "prev_close": prev.close, "pseudo_gap": gap,
                               "confidence": c_long if direction == 1 else c_short,
                               "avg_prior_range": avg_range})
                    trades.append(t1); n_day_trades += 1; day_net += t1["net_R"]; orb1_reason = t1["exit_reason"]

                    # v12 permits exactly one re-entry only after a target exit.
                    if str(t1["exit_reason"]).startswith("TP"):
                        exit_min = int(g.loc[t1["exit_index"], "minute"])
                        if exit_min <= 629:
                            s2_idx, d2 = find_signal(g, max(600, exit_min), or_hi, or_lo, gap, c_long, c_short)
                            if s2_idx is not None:
                                t2 = simulate_trade(g, s2_idx, d2, scenario)
                                if t2 is not None:
                                    t2.update({"date": str(date.date()), "scenario": scenario_name, "slot": "ORB2",
                                               "or_high": or_hi, "or_low": or_lo, "or_range": or_range,
                                               "prev_close": prev.close, "pseudo_gap": gap,
                                               "confidence": c_long if d2 == 1 else c_short,
                                               "avg_prior_range": avg_range})
                                    trades.append(t2); n_day_trades += 1; day_net += t2["net_R"]; orb2_reason = t2["exit_reason"]

        if is_holdout:
            day_rows.append({"date": str(date.date()), "weekday": weekday, "eligible_day": bool(eligible_day),
                             "or_range": or_range, "pseudo_gap": gap, "conf_long": c_long, "conf_short": c_short,
                             "avg_prior_range": avg_range, "trades": n_day_trades, "day_net_R": day_net,
                             "orb1_exit": orb1_reason, "orb2_exit": orb2_reason})
        if date in contexts:
            prior_ranges.append(contexts[date].range)

    return pd.DataFrame(trades), pd.DataFrame(day_rows)


def main():
    out = Path("nq-propf/results/v12_orb_july_holdout_v1")
    out.mkdir(parents=True, exist_ok=True)
    try:
        d = load_getdata()
        diag = {"rows": int(len(d)), "utc_min": str(d.utc.min()), "utc_max": str(d.utc.max()),
                "holdout_start": str(HOLDOUT_START.date()), "holdout_end": str(HOLDOUT_END.date())}
        qa = data_identity_qa(d, out)
        if not qa["pass"]:
            result = {"status": "NQ_V12_ORB_JULY_HOLDOUT_V1_INVALID_DATA_ABORT", "data": diag, "data_qa": qa}
            (out / "RESULT.json").write_text(json.dumps(result, indent=2)); print(json.dumps(result, indent=2)); return

        days, qc = build_rth_days(d)
        qc.to_csv(out / "rth_day_qc.csv", index=False)
        contexts = {date: day_context(g) for date, g in days.items()}
        holdout_days = [x for x in sorted(days) if HOLDOUT_START <= x <= HOLDOUT_END]
        diag.update({"rth_days": int(len(days)), "holdout_rth_days": int(len(holdout_days)),
                     "holdout_dates": [str(x.date()) for x in holdout_days]})

        all_trades = []; summaries = {}; day_tables = []
        for name, sc in SCENARIOS.items():
            tr, dr = run_scenario(days, contexts, name, sc)
            if not tr.empty: all_trades.append(tr)
            dr["scenario"] = name; day_tables.append(dr)
            summaries[name] = metrics(tr)

        trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
        days_out = pd.concat(day_tables, ignore_index=True) if day_tables else pd.DataFrame()
        trades.to_csv(out / "holdout_trades.csv", index=False)
        days_out.to_csv(out / "holdout_days.csv", index=False)

        p = summaries["PRIMARY"]; s = summaries["STRESS"]
        if p["n"] < 5:
            status = "NQ_V12_ORB_JULY_HOLDOUT_V1_INCONCLUSIVE_LOW_N"
            gates = {"n_ge_5": False}
        else:
            gates = {
                "n_ge_5": True,
                "primary_total_positive": p["sum_R"] > 0,
                "primary_mean_gt_0_10R": p["mean_R"] is not None and p["mean_R"] > 0.10,
                "primary_pf_ge_1_25": p["pf"] is not None and p["pf"] >= 1.25,
                "primary_dd_le_4R": p["max_dd_R"] is not None and p["max_dd_R"] <= 4.0,
                "stress_total_nonnegative": s["sum_R"] >= 0,
                "stress_pf_ge_1_05": s["pf"] is not None and s["pf"] >= 1.05,
            }
            status = ("NQ_V12_ORB_JULY_HOLDOUT_V1_PASS_FOR_EXTENDED_VALIDATION"
                      if all(gates.values()) else "NQ_V12_ORB_JULY_HOLDOUT_V1_NO_GO")

        result = {"status": status, "data": diag, "data_qa": qa,
                  "summaries": summaries, "gates": gates,
                  "freeze_note": "Rules frozen before opening July 6-31 outcomes; external strategy repository had no commits after July 4, 2026.",
                  "interpretation": "A PASS is a short prospective holdout signal only, not live-trading authorization."}
        (out / "RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        print(json.dumps(result, indent=2, allow_nan=False))
    except Exception as e:
        result = {"status": "NQ_V12_ORB_JULY_HOLDOUT_V1_INVALID_ABORT", "error": repr(e)}
        (out / "RESULT.json").write_text(json.dumps(result, indent=2)); print(json.dumps(result, indent=2)); raise


if __name__ == "__main__":
    main()
