from __future__ import annotations

import pandas as pd


def resample_ohlc(bars: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in bars.columns:
        agg["volume"] = "sum"
    out = bars.resample(rule, label="right", closed="right").agg(agg).dropna(subset=["open", "high", "low", "close"])
    out["timestamp"] = out.index
    return out
