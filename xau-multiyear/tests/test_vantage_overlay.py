import pandas as pd
import pytest

from rzr.vantage_overlay import apply_fixed_spread_overlay, break_even_mid_move_usd


def _bars():
    idx = pd.date_range('2026-01-01', periods=2, freq='min', tz='UTC')
    return pd.DataFrame({'open':[4000.0,4000.2],'high':[4000.5,4000.7],'low':[3999.8,4000.0],'close':[4000.2,4000.4]}, index=idx)


def test_fixed_spread_overlay_preserves_mid_and_builds_quotes():
    b = _bars(); o = apply_fixed_spread_overlay(b, 0.10)
    assert o['open'].equals(b['open'])
    assert o['open_bid'].iloc[0] == pytest.approx(3999.95)
    assert o['open_ask'].iloc[0] == pytest.approx(4000.05)
    assert (o['open_ask'] - o['open_bid']).iloc[0] == pytest.approx(0.10)
    assert (o['high_ask'] - o['high_bid']).iloc[1] == pytest.approx(0.10)
    assert (o['spread'] == 0.10).all()


def test_break_even_move_raw_examples():
    assert break_even_mid_move_usd(0.10, 6.0, 100.0) == pytest.approx(0.16)
    assert break_even_mid_move_usd(0.11, 6.0, 100.0) == pytest.approx(0.17)
    assert break_even_mid_move_usd(0.12, 6.0, 100.0) == pytest.approx(0.18)
    assert break_even_mid_move_usd(0.18, 9.0, 100.0) == pytest.approx(0.27)


def test_invalid_spread_rejected():
    with pytest.raises(ValueError):
        apply_fixed_spread_overlay(_bars(), -0.01)
