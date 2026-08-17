from __future__ import annotations

import numpy as np
import pandas as pd

TARGET_RS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)


def _effective_side(rec):
    side = str(rec["side"])
    if side == "NEUTRAL":
        return "RESISTANCE" if int(rec.get("approach_direction", 0)) > 0 else "SUPPORT"
    return side


def _active_array(bars):
    if "quote_active" in bars.columns:
        return bars["quote_active"].astype(bool).to_numpy()
    cols = [c for c in ("open", "high", "low", "close") if c in bars.columns]
    arr = bars[cols].to_numpy(float)
    move = np.nanmax(arr, axis=1) - np.nanmin(arr, axis=1)
    d = np.r_[np.nan, np.abs(np.diff(bars["close"].to_numpy(float)))]
    return (move > 0) | (d > 0)


def _next_active(active, start, max_wait=3):
    n = len(active)
    for j in range(start, min(n, start + max_wait + 1)):
        if active[j]:
            return j
    return -1


def _spread_at(bars, i):
    if "spread" in bars.columns:
        v = float(bars["spread"].iloc[i])
        if np.isfinite(v) and v >= 0:
            return v
    return max(0.0, float(bars["close_ask"].iloc[i]) - float(bars["close_bid"].iloc[i]))


def _buffer(bars, i, sigma, mult=0.10):
    return max(2.0 * _spread_at(bars, i), mult * float(sigma))


def build_entry(rec, bars, behavior, acceptance_minutes=5, retest_minutes=30, buffer_mult=0.10):
    """Build one causal entry from a Phase-B event."""
    n = len(bars)
    active = _active_array(bars)
    ci = int(rec["contact_idx"])
    lo = float(rec["lower"])
    up = float(rec["upper"])
    sig = float(rec["sigma60"])
    if not np.isfinite(sig) or sig <= 0:
        return None
    se = _effective_side(rec)
    long_reject = se == "SUPPORT"

    if behavior == "TOUCH_NEXT_OPEN":
        ei = _next_active(active, ci + 1, 2)
        if ei < 0: return None
        direction = "LONG" if long_reject else "SHORT"
        confirm_i = ci
        sweep_extreme = np.nan
    elif behavior == "CLEAN_REJECTION":
        if str(rec.get("behavior_v2", "")) != "CLEAN_REJECTION": return None
        m = rec.get("first_reclaim_minutes_v2", np.nan)
        if not np.isfinite(m): return None
        confirm_i = ci + int(m)
        ei = _next_active(active, confirm_i + 1, 2)
        if ei < 0: return None
        direction = "LONG" if long_reject else "SHORT"
        sweep_extreme = np.nan
    elif behavior == "FAILED_AUCTION":
        if str(rec.get("behavior_v2", "")) != "FAILED_AUCTION": return None
        m = rec.get("reclaim_after_breach_minutes_v2", np.nan)
        if not np.isfinite(m): return None
        confirm_i = ci + int(m)
        ei = _next_active(active, confirm_i + 1, 2)
        if ei < 0: return None
        direction = "LONG" if long_reject else "SHORT"
        sweep_extreme = float(bars["low"].iloc[ci:confirm_i+1].min()) if direction == "LONG" else float(bars["high"].iloc[ci:confirm_i+1].max())
    elif behavior == "ACCEPTANCE_RETEST":
        if str(rec.get("behavior_v2", "")) != "ACCEPTED_BREAK": return None
        confirm_i = ci + int(acceptance_minutes) - 1
        start = confirm_i + 1
        end = min(n, start + int(retest_minutes))
        if se == "SUPPORT":
            direction = "SHORT"; level = lo
            arr = bars["high_bid"].to_numpy(float)
            candidates = np.flatnonzero((arr[start:end] >= level) & active[start:end])
        else:
            direction = "LONG"; level = up
            arr = bars["low_ask"].to_numpy(float)
            candidates = np.flatnonzero((arr[start:end] <= level) & active[start:end])
        if len(candidates) == 0: return None
        ei = start + int(candidates[0])
        sweep_extreme = np.nan
    else:
        raise ValueError(behavior)

    if direction == "LONG":
        entry = float(up) if behavior == "ACCEPTANCE_RETEST" else float(bars["open_ask"].iloc[ei])
    else:
        entry = float(lo) if behavior == "ACCEPTANCE_RETEST" else float(bars["open_bid"].iloc[ei])

    buf = _buffer(bars, ei, sig, buffer_mult)
    if behavior == "FAILED_AUCTION":
        stop = sweep_extreme - buf if direction == "LONG" else sweep_extreme + buf
    elif behavior == "ACCEPTANCE_RETEST":
        stop = lo - buf if direction == "LONG" else up + buf
    else:
        stop = lo - buf if direction == "LONG" else up + buf
    risk = entry - stop if direction == "LONG" else stop - entry
    if not np.isfinite(risk) or risk <= 0: return None
    return {
        "entry_model": behavior, "direction": direction, "contact_idx": ci,
        "confirm_idx": confirm_i, "entry_idx": ei, "entry_price": entry,
        "stop_price": float(stop), "risk_price": float(risk), "buffer_price": float(buf),
        "entry_delay_minutes": int(ei-ci), "sigma60": sig,
        "intrabar_limit_entry": bool(behavior == "ACCEPTANCE_RETEST"),
    }


def simulate_one(entry, bars, target_r, horizon_minutes=120, commission_rt_per_lot=22.0, contract_oz=100.0):
    """Simulate with executable BID/ASK OHLC and adverse ambiguity resolution.

    For an intrabar limit retest fill, the entry minute cannot reveal the order of fill/high/low.
    A stop range touch on that minute is therefore counted as a loss; a target range touch is
    ignored until the next minute. Market-at-open entries may use the whole entry bar.
    """
    d = entry["direction"]
    ei = int(entry["entry_idx"])
    ep = float(entry["entry_price"])
    stop = float(entry["stop_price"])
    risk = float(entry["risk_price"])
    n = len(bars)
    target = ep + (target_r*risk if d == "LONG" else -target_r*risk)
    end = min(n, ei + int(horizon_minutes) + 1)
    result = "TIME"; exit_i = end-1; exit_price = np.nan; ambiguous = False
    intrabar = bool(entry.get("intrabar_limit_entry", False))

    if d == "LONG":
        hi = bars["high_bid"].to_numpy(float); lo = bars["low_bid"].to_numpy(float); op = bars["open_bid"].to_numpy(float)
        loop_start = ei
        if intrabar:
            if lo[ei] <= stop:
                result = "SL"; ambiguous = True; exit_i = ei; exit_price = min(stop, op[ei])
            loop_start = ei + 1
        for j in range(loop_start, end) if result == "TIME" else []:
            sl = lo[j] <= stop; tp = hi[j] >= target
            if sl and tp:
                result = "SL"; ambiguous = True; exit_i = j; exit_price = min(stop, op[j]); break
            if sl:
                result = "SL"; exit_i = j; exit_price = min(stop, op[j]); break
            if tp:
                result = "TP"; exit_i = j; exit_price = target; break
        if result == "TIME": exit_price = float(bars["close_bid"].iloc[exit_i])
        gross = (exit_price-ep)/risk
    else:
        hi = bars["high_ask"].to_numpy(float); lo = bars["low_ask"].to_numpy(float); op = bars["open_ask"].to_numpy(float)
        loop_start = ei
        if intrabar:
            if hi[ei] >= stop:
                result = "SL"; ambiguous = True; exit_i = ei; exit_price = max(stop, op[ei])
            loop_start = ei + 1
        for j in range(loop_start, end) if result == "TIME" else []:
            sl = hi[j] >= stop; tp = lo[j] <= target
            if sl and tp:
                result = "SL"; ambiguous = True; exit_i = j; exit_price = max(stop, op[j]); break
            if sl:
                result = "SL"; exit_i = j; exit_price = max(stop, op[j]); break
            if tp:
                result = "TP"; exit_i = j; exit_price = target; break
        if result == "TIME": exit_price = float(bars["close_ask"].iloc[exit_i])
        gross = (ep-exit_price)/risk

    commission_r = float(commission_rt_per_lot)/(float(contract_oz)*risk) if commission_rt_per_lot is not None else 0.0
    return {
        "target_r": float(target_r), "result": result, "ambiguous_same_bar": ambiguous,
        "exit_idx": int(exit_i), "exit_price": float(exit_price), "gross_R": float(gross),
        "legacy_commission_R": float(commission_r), "net_R_legacy22": float(gross-commission_r),
    }


def simulate_surface(entry, bars, target_rs=TARGET_RS, horizon_minutes=120):
    return [simulate_one(entry, bars, r, horizon_minutes=horizon_minutes) for r in target_rs]
