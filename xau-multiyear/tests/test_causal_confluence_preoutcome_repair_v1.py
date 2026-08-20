from __future__ import annotations

import numpy as np
import pandas as pd

from build_xau_core_causal_confluence_preoutcome_repair_v1 import (
    causal_clean_rejection_trigger_minutes,
    side_relation,
)
from rzr.entries_v1 import _active_array, _next_active


def bars(rows):
    idx = pd.date_range("2026-01-01T00:00:00Z", periods=len(rows), freq="min")
    d = pd.DataFrame(rows, index=idx, columns=["open", "high", "low", "close"])
    d["quote_active"] = True
    return d


def rec(side="SUPPORT"):
    return {
        "contact_idx": 0,
        "side": side,
        "lower": 99.0,
        "upper": 100.0,
        "approach_direction": -1 if side == "SUPPORT" else 1,
    }


def test_reclaim_then_future_breach_does_not_revoke_trigger_or_entry():
    d = bars([
        [99.5, 99.9, 99.2, 99.7],
        [99.7, 100.4, 99.5, 100.2],  # causal reclaim at +1
        [100.2, 100.4, 98.0, 98.5],   # future distal breach after entry open
        [98.5, 101.0, 98.4, 100.5],   # future reclaim
    ])
    m = causal_clean_rejection_trigger_minutes(d, rec())
    assert m == 1.0
    confirm_i = int(m)
    entry_i = _next_active(_active_array(d), confirm_i + 1, 2)
    assert confirm_i == 1
    assert entry_i == 2


def test_breach_before_reclaim_never_triggers_clean_rejection():
    d = bars([
        [99.5, 99.8, 98.8, 99.4],
        [99.4, 100.4, 99.2, 100.2],
    ])
    assert np.isnan(causal_clean_rejection_trigger_minutes(d, rec()))


def test_same_bar_breach_and_reclaim_is_adverse_no_trigger():
    d = bars([[99.5, 100.4, 98.8, 100.2]])
    assert np.isnan(causal_clean_rejection_trigger_minutes(d, rec()))


def test_future_path_extension_cannot_move_signal_confirmation_or_entry():
    common = [
        [99.5, 99.9, 99.2, 99.7],
        [99.7, 100.4, 99.5, 100.2],
    ]
    future_paths = [
        [[100.2, 100.4, 98.0, 98.5], [98.5, 101.0, 98.4, 100.5]],
        [[100.2, 101.0, 100.0, 100.8], [100.8, 101.2, 100.7, 101.1]],
        [[100.2, 100.3, 99.9, 100.1], [100.1, 100.2, 99.8, 100.0]],
    ]
    observed = []
    for future in future_paths:
        d = bars(common + future)
        m = causal_clean_rejection_trigger_minutes(d, rec())
        confirm_i = int(m)
        entry_i = _next_active(_active_array(d), confirm_i + 1, 2)
        observed.append((m, confirm_i, entry_i))
    assert observed == [(1.0, 1, 2)] * len(future_paths)


def test_no_reclaim_in_window_has_no_trigger():
    d = bars([
        [99.5, 99.9, 99.2, 99.7],
        [99.7, 99.95, 99.4, 99.8],
        [99.8, 99.9, 99.5, 99.7],
    ])
    assert np.isnan(causal_clean_rejection_trigger_minutes(d, rec()))


def test_resistance_trigger_is_symmetric():
    d = bars([
        [100.5, 100.8, 99.5, 100.3],
        [100.3, 100.5, 98.7, 98.8],
    ])
    assert causal_clean_rejection_trigger_minutes(d, rec(side="RESISTANCE")) == 1.0


def test_side_relation_is_descriptive_only_and_deterministic():
    assert side_relation({"side": "SUPPORT"}, {"side": "SUPPORT"}) == "SAME_SIDE"
    assert side_relation({"side": "SUPPORT"}, {"side": "RESISTANCE"}) == "OPPOSITE_SIDE"
    assert side_relation({"side": "SUPPORT"}, {"side": "NEUTRAL"}) == "NEUTRAL_RESOLVED"
