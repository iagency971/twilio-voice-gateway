from __future__ import annotations

import numpy as np

from . import entries_v1 as v1

TARGET_RS = v1.TARGET_RS
simulate_one = v1.simulate_one
simulate_surface = v1.simulate_surface


def build_entry(rec, bars, behavior, acceptance_minutes=5, retest_minutes=30,
                passive_wait_minutes=15, reclaim_pullback_minutes=15, buffer_mult=0.10):
    """Phase-C v2 entry builder.

    Adds the preregistered R2 RECLAIM_PULLBACK model without changing any v1 model.
    After a causal reclaim confirmation, a standing limit is placed at the proximal
    edge for at most 15 minutes. The order is cancelled if structural invalidation
    occurs before the fill. A fill and stop in the same M1 are handled conservatively
    by entries_v1.simulate_one (stop wins).
    """
    if behavior != 'RECLAIM_PULLBACK':
        return v1.build_entry(
            rec, bars, behavior, acceptance_minutes=acceptance_minutes,
            retest_minutes=retest_minutes, passive_wait_minutes=passive_wait_minutes,
            buffer_mult=buffer_mult,
        )

    b = str(rec.get('behavior_v2', ''))
    if b not in {'CLEAN_REJECTION', 'FAILED_AUCTION'}:
        return None

    n = len(bars)
    active = v1._active_array(bars)
    ci = int(rec['contact_idx'])
    lo = float(rec['lower']); up = float(rec['upper'])
    sig = float(rec['sigma60'])
    if not np.isfinite(sig) or sig <= 0:
        return None
    se = v1._effective_side(rec)
    direction = 'LONG' if se == 'SUPPORT' else 'SHORT'

    if b == 'FAILED_AUCTION':
        m = rec.get('reclaim_after_breach_minutes_v2', np.nan)
    else:
        m = rec.get('first_reclaim_minutes_v2', np.nan)
    if not np.isfinite(m):
        return None
    confirm_i = ci + int(m)
    if confirm_i >= n:
        return None

    # Stop and buffer are known when the reclaim is confirmed; no future bar is used.
    buf = v1._buffer(bars, confirm_i, sig, buffer_mult)
    if b == 'FAILED_AUCTION':
        if direction == 'LONG':
            extreme = float(bars['low'].iloc[ci:confirm_i+1].min())
            stop = extreme - buf
        else:
            extreme = float(bars['high'].iloc[ci:confirm_i+1].max())
            stop = extreme + buf
    else:
        stop = lo - buf if direction == 'LONG' else up + buf

    level = up if direction == 'LONG' else lo  # reclaimed proximal edge
    start = confirm_i + 1
    end = min(n, start + int(reclaim_pullback_minutes))
    if start >= end:
        return None

    ei = -1
    if direction == 'LONG':
        for j in range(start, end):
            if not active[j]:
                continue
            fill = float(bars['low_ask'].iloc[j]) <= level
            invalid = float(bars['low_bid'].iloc[j]) <= stop
            if invalid and not fill:
                return None
            if fill:
                ei = j; break
    else:
        for j in range(start, end):
            if not active[j]:
                continue
            fill = float(bars['high_bid'].iloc[j]) >= level
            invalid = float(bars['high_ask'].iloc[j]) >= stop
            if invalid and not fill:
                return None
            if fill:
                ei = j; break
    if ei < 0:
        return None

    entry = float(level)
    risk = entry - stop if direction == 'LONG' else stop - entry
    if not np.isfinite(risk) or risk <= 0:
        return None
    return {
        'entry_model': behavior, 'direction': direction, 'contact_idx': ci,
        'confirm_idx': confirm_i, 'entry_idx': ei, 'entry_price': entry,
        'stop_price': float(stop), 'risk_price': float(risk), 'buffer_price': float(buf),
        'entry_delay_minutes': int(ei-ci), 'sigma60': sig,
        'intrabar_limit_entry': True,
    }
