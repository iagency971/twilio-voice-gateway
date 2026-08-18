from __future__ import annotations

import numpy as np
import pandas as pd


def apply_fixed_spread_overlay(bars: pd.DataFrame, spread_usd: float) -> pd.DataFrame:
    """Return a copy with synthetic symmetric BID/ASK OHLC around the existing mid OHLC.

    This function changes execution quotes only. The source mid OHLC columns remain untouched
    so zone generation and behavior classification are invariant to the broker overlay.
    """
    s = float(spread_usd)
    if not np.isfinite(s) or s < 0:
        raise ValueError("spread_usd must be finite and >= 0")
    out = bars.copy()
    half = 0.5 * s
    for c in ("open", "high", "low", "close"):
        if c not in out.columns:
            raise ValueError(f"missing mid column {c}")
        mid = pd.to_numeric(out[c], errors="raise").astype(float)
        out[f"{c}_bid"] = mid - half
        out[f"{c}_ask"] = mid + half
    out["spread"] = s
    return out


def break_even_mid_move_usd(spread_usd: float, commission_rt_usd: float, contract_oz: float = 100.0) -> float:
    """Approximate mid-price move needed to cover fixed spread + round-turn commission."""
    s = float(spread_usd); c = float(commission_rt_usd); q = float(contract_oz)
    if s < 0 or c < 0 or q <= 0:
        raise ValueError("invalid cost inputs")
    return s + c / q
