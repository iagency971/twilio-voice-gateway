from __future__ import annotations

import bisect
import json
from typing import List

import numpy as np
import pandas as pd

from .config import ResearchConfig
from .features import (
    quote_activity_mask,
    recent_quote_activity_mask,
    robust_sigma60,
    session_instance_key,
    trading_day_key,
)
from .types import Zone, ZoneFamily, ZoneSide
from .zones import _make_zone_id, displacement_origin_zones


ONE_MINUTE = pd.Timedelta(minutes=1)


def opening_quote_mask(bars: pd.DataFrame) -> pd.Series:
    """Quote availability known at row open; never uses row H/L/C."""
    if not all(c in bars.columns for c in ("open_bid", "open_ask")):
        raise ValueError("open_bid/open_ask required for causal opening-quote availability")
    bid = pd.to_numeric(bars["open_bid"], errors="coerce")
    ask = pd.to_numeric(bars["open_ask"], errors="coerce")
    ok = np.isfinite(bid) & np.isfinite(ask) & (bid > 0) & (ask > 0) & (ask >= bid)
    return pd.Series(ok, index=bars.index, name="opening_quote_available", dtype=bool)


class OpeningQuoteLookup:
    """O(log n) first-valid-opening-quote lookup for one fixed M1 frame."""
    def __init__(self, bars: pd.DataFrame):
        self.index = bars.index
        self.valid_positions = np.flatnonzero(opening_quote_mask(bars).to_numpy(bool))

    def at_or_after(self, ts: pd.Timestamp) -> pd.Timestamp | None:
        pos = int(self.index.searchsorted(pd.Timestamp(ts), side="left"))
        k = int(np.searchsorted(self.valid_positions, pos, side="left"))
        if k >= len(self.valid_positions):
            return None
        return pd.Timestamp(self.index[int(self.valid_positions[k])])


def first_open_quote_at_or_after(bars: pd.DataFrame, ts: pd.Timestamp) -> pd.Timestamp | None:
    return OpeningQuoteLookup(bars).at_or_after(ts)


def causal_open_spread_series(bars: pd.DataFrame) -> pd.Series:
    mask = opening_quote_mask(bars)
    bid = pd.to_numeric(bars["open_bid"], errors="coerce")
    ask = pd.to_numeric(bars["open_ask"], errors="coerce")
    return (ask - bid).where(mask).rename("open_spread")


def causal_point_half_width(bars: pd.DataFrame, sigma60: pd.Series, config: ResearchConfig) -> pd.Series:
    spread = causal_open_spread_series(bars)
    sig = sigma60.reindex(bars.index).astype(float)
    sv = spread.to_numpy(float)
    gv = sig.to_numpy(float)
    vals = np.maximum(2.0 * sv, config.point_zone_sigma_mult * gv)
    vals[~np.isfinite(sv) | ~np.isfinite(gv)] = np.nan
    return pd.Series(vals, index=bars.index, name="causal_point_half_width")


def _iso(ts) -> str | None:
    return None if ts is None else pd.Timestamp(ts).isoformat()


def _metadata(*, source_last, information_time, width_spread=None, width_source=None, extra=None) -> str:
    d = {
        "source_last_m1_timestamp_used": _iso(source_last),
        "information_available_time": _iso(information_time),
    }
    if width_spread is not None:
        d["width_open_spread"] = float(width_spread)
    if width_source is not None:
        d["width_spread_source"] = str(width_source)
    if extra:
        d.update(extra)
    return json.dumps(d, sort_keys=True)


def _trading_day_start_utc(d, timezone: str) -> pd.Timestamp:
    return (pd.Timestamp(f"{d} 17:00:00", tz=timezone) - pd.Timedelta(days=1)).tz_convert("UTC")


def _week_start_utc(week_start_date, timezone: str) -> pd.Timestamp:
    return (pd.Timestamp(f"{week_start_date} 17:00:00", tz=timezone) - pd.Timedelta(days=1)).tz_convert("UTC")


def _session_end_utc(key: tuple[str, object], timezone: str) -> pd.Timestamp:
    name, d = key
    end_hour = {"ASIA_CME": 3, "LONDON": 8, "NY_AM": 12, "NY_PM": 16, "TRANSITION": 18}[str(name)]
    return pd.Timestamp(f"{d} {end_hour:02d}:00:00", tz=timezone).tz_convert("UTC")


def previous_period_levels_full_m1(bars: pd.DataFrame, sigma60: pd.Series, config: ResearchConfig) -> List[Zone]:
    out: List[Zone] = []
    lookup = OpeningQuoteLookup(bars)
    widths = causal_point_half_width(bars, sigma60, config)
    open_spread = causal_open_spread_series(bars)
    active = bars.loc[quote_activity_mask(bars)]
    if active.empty:
        return out
    day_key = pd.Series([trading_day_key(ts, config.timezone) for ts in active.index], index=active.index)
    daily = []
    for d, idxs in day_key.groupby(day_key, sort=True).groups.items():
        g = active.loc[list(idxs)]
        if not g.empty:
            daily.append((d, g.index[0], g.index[-1], float(g.high.max()), float(g.low.min())))
    daily.sort(key=lambda x: x[1])
    for i in range(1, len(daily)):
        prev, cur = daily[i - 1], daily[i]
        known = lookup.at_or_after(_trading_day_start_utc(cur[0], config.timezone))
        if known is None or pd.isna(widths.loc[known]):
            continue
        w, sp = float(widths.loc[known]), float(open_spread.loc[known])
        for label, px, side in (("PDH", prev[3], ZoneSide.RESISTANCE), ("PDL", prev[4], ZoneSide.SUPPORT)):
            out.append(Zone(
                _make_zone_id(label, len(out)), ZoneFamily.OBJECTIVE_LIQUIDITY, label, side,
                prev[2], known, px - w, px + w, px, "D1",
                _metadata(source_last=prev[2], information_time=known, width_spread=sp,
                          width_source="OPEN_BID_ASK_AT_KNOWN_TIME", extra={"source_trading_date": str(prev[0])}),
            ))
    week_keys = pd.Series([pd.Timestamp(d).to_period("W-SUN").start_time.date() for d in day_key], index=active.index)
    weekly = []
    for key, idxs in week_keys.groupby(week_keys, sort=True).groups.items():
        g = active.loc[list(idxs)]
        weekly.append((key, g.index[0], g.index[-1], float(g.high.max()), float(g.low.min())))
    weekly.sort(key=lambda x: x[1])
    for i in range(1, len(weekly)):
        prev, cur = weekly[i - 1], weekly[i]
        known = lookup.at_or_after(_week_start_utc(cur[0], config.timezone))
        if known is None or pd.isna(widths.loc[known]):
            continue
        w, sp = float(widths.loc[known]), float(open_spread.loc[known])
        for label, px, side in (("PWH", prev[3], ZoneSide.RESISTANCE), ("PWL", prev[4], ZoneSide.SUPPORT)):
            out.append(Zone(
                _make_zone_id(label, len(out)), ZoneFamily.OBJECTIVE_LIQUIDITY, label, side,
                prev[2], known, px - w, px + w, px, "W1",
                _metadata(source_last=prev[2], information_time=known, width_spread=sp,
                          width_source="OPEN_BID_ASK_AT_KNOWN_TIME", extra={"source_week": str(prev[0])}),
            ))
    return out


def completed_session_levels_full_m1(bars: pd.DataFrame, sigma60: pd.Series, config: ResearchConfig) -> List[Zone]:
    lookup = OpeningQuoteLookup(bars)
    widths = causal_point_half_width(bars, sigma60, config)
    open_spread = causal_open_spread_series(bars)
    active = bars.loc[quote_activity_mask(bars)]
    out: List[Zone] = []
    if active.empty:
        return out
    keys = pd.Series([session_instance_key(ts, config.timezone) for ts in active.index], index=active.index, dtype=object)
    instances, seen = [], set()
    for _, key in keys.items():
        if key not in seen:
            seen.add(key); instances.append(key)
    for key in instances:
        idxs = keys.index[keys.map(lambda v: v == key)]
        g = active.loc[idxs]
        if g.empty:
            continue
        known = lookup.at_or_after(_session_end_utc(key, config.timezone))
        if known is None or pd.isna(widths.loc[known]):
            continue
        name = key[0]
        hi, lo, w, sp = float(g.high.max()), float(g.low.min()), float(widths.loc[known]), float(open_spread.loc[known])
        common = dict(source_last=g.index[-1], information_time=known, width_spread=sp,
                      width_source="OPEN_BID_ASK_AT_KNOWN_TIME", extra={"session_date": str(key[1])})
        out.append(Zone(_make_zone_id(f"{name}_H", len(out)), ZoneFamily.OBJECTIVE_LIQUIDITY,
                        f"{name}_HIGH", ZoneSide.RESISTANCE, g.index[-1], known,
                        hi - w, hi + w, hi, "SESSION", _metadata(**common)))
        out.append(Zone(_make_zone_id(f"{name}_L", len(out)), ZoneFamily.OBJECTIVE_LIQUIDITY,
                        f"{name}_LOW", ZoneSide.SUPPORT, g.index[-1], known,
                        lo - w, lo + w, lo, "SESSION", _metadata(**common)))
    return out


def round_number_levels_full_m1(bars: pd.DataFrame, sigma60: pd.Series, config: ResearchConfig) -> List[Zone]:
    lookup = OpeningQuoteLookup(bars)
    widths = causal_point_half_width(bars, sigma60, config)
    open_spread = causal_open_spread_series(bars)
    out: List[Zone] = []
    seen = set()
    source_active = quote_activity_mask(bars)
    for ts, row in bars.loc[source_active].iterrows():
        sig = float(sigma60.loc[ts]) if ts in sigma60.index and not pd.isna(sigma60.loc[ts]) else np.nan
        if not np.isfinite(sig) or sig <= 0:
            continue
        known = lookup.at_or_after(pd.Timestamp(ts) + ONE_MINUTE)
        if known is None or pd.isna(widths.loc[known]):
            continue
        c, w, sp = float(row.close), float(widths.loc[known]), float(open_spread.loc[known])
        for step in config.round_number_steps:
            base = round(c / step) * step
            for px in (base - step, base, base + step):
                key = (step, round(px, 6))
                if key in seen:
                    continue
                if abs(c - px) <= 3.0 * sig:
                    seen.add(key)
                    out.append(Zone(
                        _make_zone_id(f"ROUND_{step:g}", len(out)), ZoneFamily.OBJECTIVE_LIQUIDITY,
                        f"ROUND_{step:g}", ZoneSide.NEUTRAL, ts, known, px - w, px + w, px, "PRICE",
                        _metadata(source_last=ts, information_time=known, width_spread=sp,
                                  width_source="OPEN_BID_ASK_AT_KNOWN_TIME", extra={"step": step}),
                    ))
    return out


def directional_change_turns_full_m1(bars: pd.DataFrame, sigma60: pd.Series, config: ResearchConfig) -> pd.DataFrame:
    lookup = OpeningQuoteLookup(bars)
    pos = np.flatnonzero(quote_activity_mask(bars).to_numpy(bool))
    if len(pos) == 0:
        return pd.DataFrame()
    times = bars.index
    hi, lo, close = bars.high.to_numpy(float), bars.low.to_numpy(float), bars.close.to_numpy(float)
    sigmas = sigma60.reindex(bars.index).to_numpy(float)
    records = []
    for delta_mult in config.directional_change_deltas:
        mode, extreme_price, extreme_time = 0, None, None
        for i in pos:
            sig = sigmas[i]
            if not np.isfinite(sig) or sig <= 0:
                continue
            h, l, c, ts = hi[i], lo[i], close[i], pd.Timestamp(times[i])
            threshold = float(delta_mult * sig)
            if extreme_price is None:
                extreme_price, extreme_time, mode = c, ts, +1
                continue
            if mode >= 0:
                if h > extreme_price:
                    extreme_price, extreme_time = h, ts
                if extreme_price - l >= threshold:
                    known = lookup.at_or_after(ts + ONE_MINUTE)
                    if known is not None:
                        records.append({"delta_mult": delta_mult, "kind": "HIGH", "origin_time": extreme_time,
                                        "source_last_m1_timestamp_used": ts, "information_available_time": known,
                                        "known_time": known, "price": extreme_price,
                                        "reaction_amplitude": extreme_price - l})
                    mode, extreme_price, extreme_time = -1, l, ts
            else:
                if l < extreme_price:
                    extreme_price, extreme_time = l, ts
                if h - extreme_price >= threshold:
                    known = lookup.at_or_after(ts + ONE_MINUTE)
                    if known is not None:
                        records.append({"delta_mult": delta_mult, "kind": "LOW", "origin_time": extreme_time,
                                        "source_last_m1_timestamp_used": ts, "information_available_time": known,
                                        "known_time": known, "price": extreme_price,
                                        "reaction_amplitude": h - extreme_price})
                    mode, extreme_price, extreme_time = +1, h, ts
    return pd.DataFrame.from_records(records)


def dedupe_directional_turns_streaming(turns: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if turns.empty:
        return turns, 0
    x = turns.sort_values(["known_time", "origin_time", "kind", "delta_mult"], kind="mergesort").copy()
    grouped, prefix_viol = [], 0
    for (_, _), g in x.groupby(["origin_time", "kind"], sort=False):
        earliest = pd.Timestamp(g["known_time"].min())
        available = g[pd.to_datetime(g["known_time"], utc=True) == earliest]
        if available.empty:
            prefix_viol += 1; continue
        row = available.sort_values("delta_mult", kind="mergesort").iloc[-1].to_dict()
        row["known_time"] = earliest
        row["information_available_time"] = earliest
        row["scale_count_at_activation"] = int(len(available))
        row["delta_mult_max_at_activation"] = float(available["delta_mult"].max())
        row["reaction_amplitude"] = float(available["reaction_amplitude"].max())
        row["later_scale_confirmations_ignored"] = int((pd.to_datetime(g["known_time"], utc=True) > earliest).sum())
        if pd.Timestamp(row["known_time"]) != earliest:
            prefix_viol += 1
        grouped.append(row)
    out = pd.DataFrame(grouped)
    if len(out):
        out = out.sort_values(["known_time", "origin_time", "kind"], kind="mergesort").reset_index(drop=True)
    return out, int(prefix_viol)


def memory_zones_full_m1(bars: pd.DataFrame, sigma60: pd.Series, config: ResearchConfig) -> tuple[List[Zone], dict]:
    raw_turns = directional_change_turns_full_m1(bars, sigma60, config)
    turns, prefix_viol = dedupe_directional_turns_streaming(raw_turns)
    if turns.empty:
        return [], {"memory_raw_turns": int(len(raw_turns)), "memory_deduped_turns": 0,
                    "memory_prefix_invariance_violations": int(prefix_viol)}
    widths = causal_point_half_width(bars, sigma60, config)
    open_spread = causal_open_spread_series(bars)
    clusters, spatial, out = [], [], []
    min_sep = pd.Timedelta(minutes=config.memory_min_separation_minutes)
    for tr in turns.itertuples(index=False):
        kt = pd.Timestamp(tr.known_time)
        if pd.isna(widths.loc[kt]):
            continue
        w, px = float(widths.loc[kt]), float(tr.price)
        left, right = bisect.bisect_left(spatial, (px - w, -1)), bisect.bisect_right(spatial, (px + w, 10**18))
        best, best_key = None, None
        for center, ci in spatial[left:right]:
            cl = clusters[ci]
            if kt - cl["last_known_time"] < min_sep:
                continue
            d = abs(px - cl["center"])
            if d <= w and (best_key is None or (d, ci) < best_key):
                best_key, best = (d, ci), ci
        reaction_amp, tr_kind = float(tr.reaction_amplitude), str(tr.kind)
        tr_scale = float(getattr(tr, "delta_mult_max_at_activation", tr.delta_mult))
        source_last = pd.Timestamp(tr.source_last_m1_timestamp_used)
        if best is None:
            ci = len(clusters)
            clusters.append({"center": px, "weight": max(reaction_amp, 1e-9), "count": 1,
                             "origin_time": pd.Timestamp(tr.origin_time), "known_time": kt,
                             "last_known_time": kt, "kind_high": int(tr_kind == "HIGH"),
                             "kind_low": int(tr_kind == "LOW"), "max_scale": tr_scale,
                             "source_last_m1_timestamp_used": source_last})
            bisect.insort(spatial, (px, ci)); continue
        cl = clusters[best]
        old_pair = (cl["center"], best)
        k = bisect.bisect_left(spatial, old_pair)
        if k < len(spatial) and spatial[k] == old_pair: spatial.pop(k)
        else: spatial.remove(old_pair)
        wt = max(reaction_amp, 1e-9)
        cl["center"] = (cl["center"] * cl["weight"] + px * wt) / (cl["weight"] + wt)
        cl["weight"] += wt; cl["count"] += 1; cl["known_time"] = kt; cl["last_known_time"] = kt
        cl["kind_high"] += int(tr_kind == "HIGH"); cl["kind_low"] += int(tr_kind == "LOW")
        cl["max_scale"] = max(cl["max_scale"], tr_scale); cl["source_last_m1_timestamp_used"] = source_last
        bisect.insort(spatial, (cl["center"], best))
        if cl["count"] == 2:
            side = (ZoneSide.RESISTANCE if cl["kind_high"] > cl["kind_low"] else
                    ZoneSide.SUPPORT if cl["kind_low"] > cl["kind_high"] else ZoneSide.NEUTRAL)
            sp = float(open_spread.loc[kt])
            out.append(Zone(
                _make_zone_id("MEM", len(out)), ZoneFamily.MEMORY, "DIRECTIONAL_CHANGE_CLUSTER", side,
                cl["origin_time"], kt, cl["center"] - w, cl["center"] + w, cl["center"], "M1",
                _metadata(source_last=source_last, information_time=kt, width_spread=sp,
                          width_source="OPEN_BID_ASK_AT_KNOWN_TIME",
                          extra={"constituents_at_activation": 2, "max_delta_scale": cl["max_scale"]}),
            ))
    return out, {"memory_raw_turns": int(len(raw_turns)), "memory_deduped_turns": int(len(turns)),
                 "memory_prefix_invariance_violations": int(prefix_viol)}


def fvg_zones_full_m1(bars: pd.DataFrame, config: ResearchConfig) -> List[Zone]:
    lookup = OpeningQuoteLookup(bars)
    out: List[Zone] = []
    hi2, lo2 = bars.high.shift(2), bars.low.shift(2)
    recent = recent_quote_activity_mask(bars, lookback_minutes=3)
    valid3 = recent & recent.shift(1, fill_value=False) & recent.shift(2, fill_value=False)
    for i, ts in enumerate(bars.index):
        if i < 2 or not bool(valid3.iloc[i]):
            continue
        known = lookup.at_or_after(pd.Timestamp(ts) + ONE_MINUTE)
        if known is None:
            continue
        low, high = float(bars.at[ts, "low"]), float(bars.at[ts, "high"])
        if low > float(hi2.loc[ts]):
            lo, up = float(hi2.loc[ts]), low
            out.append(Zone(_make_zone_id("FVG_B", len(out)), ZoneFamily.FVG, "FVG_3BAR", ZoneSide.SUPPORT,
                            bars.index[i - 2], known, lo, up, (lo + up) / 2, "M1",
                            _metadata(source_last=pd.Timestamp(ts), information_time=known)))
        if high < float(lo2.loc[ts]):
            lo, up = high, float(lo2.loc[ts])
            out.append(Zone(_make_zone_id("FVG_S", len(out)), ZoneFamily.FVG, "FVG_3BAR", ZoneSide.RESISTANCE,
                            bars.index[i - 2], known, lo, up, (lo + up) / 2, "M1",
                            _metadata(source_last=pd.Timestamp(ts), information_time=known)))
    return out


def generate_baseline_zones_full_m1(bars: pd.DataFrame, config: ResearchConfig) -> tuple[List[Zone], dict]:
    sigma = robust_sigma60(bars)
    zones: List[Zone] = []
    zones.extend(previous_period_levels_full_m1(bars, sigma, config))
    zones.extend(completed_session_levels_full_m1(bars, sigma, config))
    zones.extend(round_number_levels_full_m1(bars, sigma, config))
    memory, memory_stats = memory_zones_full_m1(bars, sigma, config)
    zones.extend(memory)
    zones.extend(fvg_zones_full_m1(bars, config))
    zones.extend(displacement_origin_zones(bars, config))
    return zones, memory_stats
