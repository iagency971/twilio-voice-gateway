from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ResearchConfig


def quote_activity_mask(bars: pd.DataFrame, eps: float = 1e-12) -> pd.Series:
    """Causal quote-activity flag for padded M1 grids."""
    o = bars["open"].astype(float)
    h = bars["high"].astype(float)
    l = bars["low"].astype(float)
    c = bars["close"].astype(float)
    prev = c.shift(1)
    active = ((h - l).abs() > eps) | ((c - prev).abs() > eps) | ((o - prev).abs() > eps)
    if len(active):
        active.iloc[0] = bool(abs(float(h.iloc[0] - l.iloc[0])) > eps)
    return active.fillna(False).rename("quote_active")


def recent_quote_activity_mask(bars: pd.DataFrame, lookback_minutes: int = 3) -> pd.Series:
    active = quote_activity_mask(bars).astype(int)
    return active.rolling(lookback_minutes, min_periods=1).max().astype(bool).rename("market_recently_active")


APPROACH_ABS_BANDS = (0.25, 0.50, 1.00, 2.00)


def approach_state_arrays(bars: pd.DataFrame, sigma60: pd.Series, timezone: str = "America/New_York", lookback: int = 5):
    close = bars["close"].astype(float).to_numpy()
    sig = sigma60.reindex(bars.index).to_numpy(float)
    n = len(bars)
    move = np.zeros(n, dtype=float)
    if n > 1:
        idx = np.arange(1, n)
        base_idx = np.maximum(0, idx - int(lookback))
        move[idx] = close[idx - 1] - close[base_idx]
    norm = np.full(n, np.nan, dtype=float)
    good = np.isfinite(sig) & (sig > 0)
    norm[good] = move[good] / sig[good]
    direction = np.sign(np.nan_to_num(norm, nan=0.0)).astype(np.int8)
    abs_norm = np.abs(norm)
    band = np.full(n, -1, dtype=np.int8)
    finite = np.isfinite(abs_norm)
    band[finite] = np.digitize(abs_norm[finite], APPROACH_ABS_BANDS, right=False).astype(np.int8)
    local_hour = np.asarray([ts.tz_convert(timezone).hour for ts in bars.index], dtype=np.int8)
    return {
        "approach_move": move,
        "approach_move_sigma": norm,
        "approach_abs_sigma": abs_norm,
        "approach_direction": direction,
        "approach_band": band,
        "local_hour": local_hour,
    }


def robust_sigma60(bars: pd.DataFrame, window: int = 60) -> pd.Series:
    close = bars["close"].astype(float)
    logret = np.log(close).diff()
    active = quote_activity_mask(bars)
    active_ret = logret[active & logret.notna()]

    def _mad(x: np.ndarray) -> float:
        m = np.nanmedian(x)
        return float(np.nanmedian(np.abs(x - m)))

    mad_active = active_ret.rolling(window=window, min_periods=window).apply(_mad, raw=True)
    robust_active = 1.4826 * mad_active
    robust_pre = robust_active.reindex(bars.index).ffill().shift(1)
    price_scale = close.shift(1) * robust_pre * np.sqrt(float(window))
    return price_scale.rename("sigma60")


def spread_series(bars: pd.DataFrame, config: ResearchConfig) -> pd.Series:
    if "spread" in bars.columns:
        s = bars["spread"].astype(float).where(bars["spread"].astype(float) >= 0)
        return s.fillna(config.reference_spread).rename("spread")
    if "ask" in bars.columns and "bid" in bars.columns:
        s = (bars["ask"].astype(float) - bars["bid"].astype(float)).clip(lower=0)
        return s.fillna(config.reference_spread).rename("spread")
    return pd.Series(config.reference_spread, index=bars.index, name="spread", dtype=float)


def point_half_width(bars: pd.DataFrame, sigma60: pd.Series, config: ResearchConfig) -> pd.Series:
    spread = spread_series(bars, config)
    width = np.maximum(2.0 * spread, config.point_zone_sigma_mult * sigma60)
    return pd.Series(width, index=bars.index, name="point_half_width")


def trading_day_key(ts: pd.Timestamp, timezone: str = "America/New_York", boundary_hour: int = 17):
    local = ts.tz_convert(timezone)
    d = local.date()
    if local.hour >= boundary_hour:
        d = (local + pd.Timedelta(days=1)).date()
    return d


def session_bucket(ts: pd.Timestamp, timezone: str = "America/New_York") -> str:
    local = ts.tz_convert(timezone)
    h = local.hour
    if h >= 18 or h < 3:
        return "ASIA_CME"
    if h < 8:
        return "LONDON"
    if h < 12:
        return "NY_AM"
    if h < 16:
        return "NY_PM"
    return "TRANSITION"


def session_instance_key(ts: pd.Timestamp, timezone: str = "America/New_York") -> tuple[str, object]:
    local = ts.tz_convert(timezone)
    sess = session_bucket(ts, timezone)
    if sess == "ASIA_CME":
        d = (local + pd.Timedelta(days=1)).date() if local.hour >= 18 else local.date()
    else:
        d = local.date()
    return sess, d
