from __future__ import annotations

import pandas as pd

_REQUIRED = ["timestamp", "open", "high", "low", "close"]


def load_ohlc_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in _REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    ts = pd.to_datetime(df["timestamp"], utc=True, errors="raise")
    df = df.copy()
    df["timestamp"] = ts
    df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    for c in ["open", "high", "low", "close", "volume", "bid", "ask", "spread"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if df[["open", "high", "low", "close"]].isna().any().any():
        raise ValueError("NaN in required OHLC columns after parsing")
    if (df["high"] < df[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("Invalid high values")
    if (df["low"] > df[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("Invalid low values")
    return df.set_index("timestamp", drop=False)
