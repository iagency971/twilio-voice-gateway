import numpy as np
import pandas as pd

from rzr.behavior_v2 import classify_behavior_v2
from rzr.config import ResearchConfig


def _bars(rows):
    idx = pd.date_range("2026-01-01", periods=len(rows), freq="min", tz="UTC")
    return pd.DataFrame(rows, index=idx, columns=["open", "high", "low", "close"])


def _contact(side="SUPPORT", lower=99.0, upper=100.0, sigma=1.0):
    return pd.DataFrame([
        {
            "zone_id": "Z1",
            "family": "OBJECTIVE_LIQUIDITY",
            "variant": "TEST",
            "side": side,
            "contact_idx": 0,
            "contact_time": pd.Timestamp("2026-01-01", tz="UTC"),
            "lower": lower,
            "upper": upper,
            "sigma60": sigma,
            "approach_direction": -1 if side == "SUPPORT" else 1,
        }
    ])


def test_clean_rejection_requires_no_distal_breach_before_reclaim():
    bars = _bars([
        [100.2, 100.3, 99.4, 99.7],
        [99.7, 100.4, 99.5, 100.2],
        [100.2, 100.3, 100.0, 100.1],
        [100.1, 100.2, 100.0, 100.1],
        [100.1, 100.2, 100.0, 100.1],
    ])
    out = classify_behavior_v2(bars, _contact(), ResearchConfig()).iloc[0]
    assert out.behavior_v2 == "CLEAN_REJECTION"
    assert not bool(out.distal_breach_v2)
    assert not bool(out.failed_auction_v2)


def test_failed_auction_requires_breach_then_reclaim():
    bars = _bars([
        [99.7, 99.9, 98.7, 98.9],
        [98.9, 99.6, 98.8, 99.5],
        [99.5, 100.4, 99.4, 100.2],
        [100.2, 100.3, 100.0, 100.1],
        [100.1, 100.2, 100.0, 100.1],
    ])
    out = classify_behavior_v2(bars, _contact(), ResearchConfig()).iloc[0]
    assert out.behavior_v2 == "FAILED_AUCTION"
    assert bool(out.distal_breach_v2)
    assert bool(out.failed_auction_v2)
    assert out.first_breach_minutes_v2 == 0
    assert out.reclaim_after_breach_minutes_v2 == 2


def test_accepted_support_break_uses_preregistered_five_minute_rule():
    bars = _bars([
        [99.3, 99.4, 98.7, 98.8],
        [98.8, 99.0, 98.5, 98.7],
        [98.7, 98.9, 98.4, 98.6],
        [98.6, 98.9, 98.5, 98.7],
        [98.7, 98.9, 98.5, 98.8],
    ])
    out = classify_behavior_v2(bars, _contact(), ResearchConfig()).iloc[0]
    assert out.behavior_v2 == "ACCEPTED_BREAK"
    assert bool(out.accepted_break_v2)
    assert bool(out.distal_breach_v2)


def test_resistance_failed_auction_is_symmetric():
    bars = _bars([
        [100.3, 101.4, 100.2, 101.2],
        [101.2, 101.3, 100.5, 100.7],
        [100.7, 100.8, 98.8, 98.9],
        [98.9, 99.1, 98.8, 99.0],
        [99.0, 99.2, 98.9, 99.1],
    ])
    out = classify_behavior_v2(
        bars, _contact(side="RESISTANCE", lower=99.0, upper=101.0), ResearchConfig()
    ).iloc[0]
    assert out.behavior_v2 == "FAILED_AUCTION"
    assert bool(out.failed_auction_v2)
    assert out.first_breach_minutes_v2 == 0
    assert out.reclaim_after_breach_minutes_v2 == 2


def test_touch_bounce_is_not_mislabeled_failed_auction():
    bars = _bars([
        [100.0, 100.2, 99.2, 99.8],
        [99.8, 100.5, 99.6, 100.3],
        [100.3, 100.4, 100.1, 100.2],
        [100.2, 100.3, 100.1, 100.2],
        [100.2, 100.3, 100.1, 100.2],
    ])
    out = classify_behavior_v2(bars, _contact(), ResearchConfig()).iloc[0]
    assert out.behavior_v2 == "CLEAN_REJECTION"
    assert not bool(out.failed_auction_v2)
