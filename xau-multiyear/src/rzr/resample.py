from __future__ import annotations

import pandas as pd


def resample_ohlc(bars: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample start-stamped M1 bars into right-labelled closed-left HTF bars.

    A bar labelled 13:15 for a 15-minute rule contains source bars whose start
    timestamps are in [13:00, 13:15), so the HTF bar is fully observable at
    13:15. ``source_last_m1_timestamp`` is retained for causal provenance gates.
    """
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in bars.columns:
        agg["volume"] = "sum"

    kwargs = {"label": "right", "closed": "left"}
    out = bars.resample(rule, **kwargs).agg(agg).dropna(subset=["open", "high", "low", "close"])
    source_last = bars.index.to_series().resample(rule, **kwargs).max().reindex(out.index)
    out["source_last_m1_timestamp"] = source_last
    out["timestamp"] = out.index
    return out
