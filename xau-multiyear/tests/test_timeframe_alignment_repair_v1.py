from __future__ import annotations

import pandas as pd

from rzr.resample import resample_ohlc
from build_xau_core_causal_confluence_preoutcome_timeframe_aligned_v1 import self_test as aligned_self_test


def minute_bars(start: str, periods: int) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="min")
    vals = list(range(periods))
    return pd.DataFrame(
        {
            "open": vals,
            "high": [v + 0.5 for v in vals],
            "low": [v - 0.5 for v in vals],
            "close": vals,
        },
        index=idx,
    )


def test_m15_uses_1300_through_1314_and_excludes_1315():
    bars = minute_bars("2026-01-01T13:00:00Z", 16)
    bars.loc[pd.Timestamp("2026-01-01T13:15:00Z"), ["open", "high", "low", "close"]] = [999, 999, 999, 999]
    x = resample_ohlc(bars, "15min")
    row = x.loc[pd.Timestamp("2026-01-01T13:15:00Z")]
    assert float(row.open) == 0.0
    assert float(row.close) == 14.0
    assert float(row.high) == 14.5
    assert pd.Timestamp(row.source_last_m1_timestamp) == pd.Timestamp("2026-01-01T13:14:00Z")
    assert pd.Timestamp(row.source_last_m1_timestamp) < pd.Timestamp("2026-01-01T13:15:00Z")


def test_m30_uses_1300_through_1329_and_excludes_1330():
    bars = minute_bars("2026-01-01T13:00:00Z", 31)
    bars.loc[pd.Timestamp("2026-01-01T13:30:00Z"), ["open", "high", "low", "close"]] = [999, 999, 999, 999]
    x = resample_ohlc(bars, "30min")
    row = x.loc[pd.Timestamp("2026-01-01T13:30:00Z")]
    assert float(row.open) == 0.0
    assert float(row.close) == 29.0
    assert float(row.high) == 29.5
    assert pd.Timestamp(row.source_last_m1_timestamp) == pd.Timestamp("2026-01-01T13:29:00Z")
    assert pd.Timestamp(row.source_last_m1_timestamp) < pd.Timestamp("2026-01-01T13:30:00Z")


def test_h1_uses_1300_through_1359_and_excludes_1400():
    bars = minute_bars("2026-01-01T13:00:00Z", 61)
    bars.loc[pd.Timestamp("2026-01-01T14:00:00Z"), ["open", "high", "low", "close"]] = [999, 999, 999, 999]
    x = resample_ohlc(bars, "1h")
    row = x.loc[pd.Timestamp("2026-01-01T14:00:00Z")]
    assert float(row.open) == 0.0
    assert float(row.close) == 59.0
    assert float(row.high) == 59.5
    assert pd.Timestamp(row.source_last_m1_timestamp) == pd.Timestamp("2026-01-01T13:59:00Z")
    assert pd.Timestamp(row.source_last_m1_timestamp) < pd.Timestamp("2026-01-01T14:00:00Z")


def test_aligned_builder_keeps_prior_causal_trigger_tests():
    aligned_self_test()
