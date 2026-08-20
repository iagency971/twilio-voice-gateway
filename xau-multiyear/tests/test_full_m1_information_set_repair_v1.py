from __future__ import annotations

import numpy as np
import pandas as pd

from rzr.config import ResearchConfig
from rzr.contacts import find_first_contacts
from rzr.full_m1_zones_v1 import (
    causal_point_half_width,
    dedupe_directional_turns_streaming,
    directional_change_turns_full_m1,
    fvg_zones_full_m1,
    opening_quote_mask,
)
from build_xau_core_causal_confluence_preoutcome_full_m1_v1 import _next_open_quote


def bars_with_quotes(start: str, rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    idx = pd.date_range(start, periods=len(rows), freq="min")
    d = pd.DataFrame(rows, index=idx, columns=["open", "high", "low", "close"])
    d["open_bid"] = d["open"] - 0.05
    d["open_ask"] = d["open"] + 0.05
    d["high_bid"] = d["high"] - 0.05
    d["high_ask"] = d["high"] + 0.05
    d["low_bid"] = d["low"] - 0.05
    d["low_ask"] = d["low"] + 0.05
    d["close_bid"] = d["close"] - 0.05
    d["close_ask"] = d["close"] + 0.05
    d["spread"] = d["close_ask"] - d["close_bid"]
    d["quote_active"] = True
    return d


def test_fvg_completed_at_1000_cannot_be_known_or_contacted_at_1000():
    bars = bars_with_quotes(
        "2026-01-01T09:58:00Z",
        [
            (99.5, 100.0, 99.0, 99.7),
            (100.2, 101.0, 100.0, 100.5),
            (102.2, 103.0, 102.0, 102.5),  # 10:00 completes bullish FVG vs 09:58 high=100
            (101.0, 101.5, 100.5, 101.2),  # 10:01 first possible contact
        ],
    )
    cfg = ResearchConfig()
    zones = fvg_zones_full_m1(bars, cfg)
    z = [z for z in zones if z.variant == "FVG_3BAR" and z.side.value == "SUPPORT"][0]
    assert z.known_time == pd.Timestamp("2026-01-01T10:01:00Z")
    sigma = pd.Series(1.0, index=bars.index)
    raw = find_first_contacts(bars, [z], sigma, cfg)
    assert len(raw) == 1
    assert pd.Timestamp(raw.iloc[0]["contact_time"]) == pd.Timestamp("2026-01-01T10:01:00Z")


def test_directional_turn_information_time_is_after_source_m1():
    bars = bars_with_quotes(
        "2026-01-01T10:00:00Z",
        [
            (100.0, 100.1, 99.9, 100.0),
            (100.0, 101.0, 99.0, 99.5),
            (99.5, 99.8, 99.2, 99.6),
        ],
    )
    sigma = pd.Series(0.5, index=bars.index)
    cfg = ResearchConfig(directional_change_deltas=(0.5,))
    turns = directional_change_turns_full_m1(bars, sigma, cfg)
    assert len(turns) >= 1
    assert (pd.to_datetime(turns["known_time"], utc=True) > pd.to_datetime(turns["source_last_m1_timestamp_used"], utc=True)).all()


def test_later_larger_memory_scale_cannot_rewrite_earliest_activation():
    origin = pd.Timestamp("2026-01-01T09:55:00Z")
    turns = pd.DataFrame([
        {
            "delta_mult": 0.5, "kind": "HIGH", "origin_time": origin,
            "source_last_m1_timestamp_used": pd.Timestamp("2026-01-01T10:00:00Z"),
            "information_available_time": pd.Timestamp("2026-01-01T10:01:00Z"),
            "known_time": pd.Timestamp("2026-01-01T10:01:00Z"),
            "price": 100.0, "reaction_amplitude": 1.0,
        },
        {
            "delta_mult": 2.0, "kind": "HIGH", "origin_time": origin,
            "source_last_m1_timestamp_used": pd.Timestamp("2026-01-01T10:02:00Z"),
            "information_available_time": pd.Timestamp("2026-01-01T10:03:00Z"),
            "known_time": pd.Timestamp("2026-01-01T10:03:00Z"),
            "price": 100.0, "reaction_amplitude": 2.0,
        },
    ])
    d, violations = dedupe_directional_turns_streaming(turns)
    assert violations == 0
    assert len(d) == 1
    assert pd.Timestamp(d.iloc[0]["known_time"]) == pd.Timestamp("2026-01-01T10:01:00Z")
    assert float(d.iloc[0]["delta_mult_max_at_activation"]) == 0.5
    assert int(d.iloc[0]["later_scale_confirmations_ignored"]) == 1


def test_zone_width_uses_open_spread_not_same_minute_close_spread():
    bars = bars_with_quotes(
        "2026-01-01T10:00:00Z",
        [(100.0, 101.0, 99.0, 100.0), (100.0, 101.0, 99.0, 100.0)],
    )
    sigma = pd.Series(1.0, index=bars.index)
    cfg = ResearchConfig(point_zone_sigma_mult=0.10)
    w1 = causal_point_half_width(bars, sigma, cfg)
    bars2 = bars.copy()
    bars2["close_ask"] = bars2["close_bid"] + 50.0
    bars2["spread"] = 50.0
    w2 = causal_point_half_width(bars2, sigma, cfg)
    assert np.allclose(w1.to_numpy(float), w2.to_numpy(float), equal_nan=True)


def test_entry_selector_is_invariant_to_entry_minute_future_hlc():
    bars = bars_with_quotes(
        "2026-01-01T10:00:00Z",
        [(100.0, 100.1, 99.9, 100.0), (100.2, 100.3, 100.1, 100.2), (100.4, 100.5, 100.3, 100.4)],
    )
    m1 = opening_quote_mask(bars).to_numpy(bool)
    i1 = _next_open_quote(m1, 1, 2)
    px1 = (float(bars["open_bid"].iloc[i1]), float(bars["open_ask"].iloc[i1]))

    mutated = bars.copy()
    mutated.loc[mutated.index[1], ["high", "low", "close", "high_bid", "low_bid", "close_bid", "high_ask", "low_ask", "close_ask"]] = [999, 1, 500, 998.95, 0.95, 499.95, 999.05, 1.05, 500.05]
    m2 = opening_quote_mask(mutated).to_numpy(bool)
    i2 = _next_open_quote(m2, 1, 2)
    px2 = (float(mutated["open_bid"].iloc[i2]), float(mutated["open_ask"].iloc[i2]))
    assert i1 == i2 == 1
    assert px1 == px2
