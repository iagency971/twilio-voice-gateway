#!/usr/bin/env python3
"""Technical compatibility wrapper for Yahoo's <=8-day 1m request limit.
No strategy or forward-gate logic is changed.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import pandas as pd
import yfinance as yf

base = Path(__file__).with_name('run_daily_shadow_v1.py')
spec = importlib.util.spec_from_file_location('shadow_v1', base)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def download_recent_chunked():
    now = pd.Timestamp.now(tz=mod.TZ)
    end = (now.normalize() + pd.Timedelta(days=1)).tz_localize(None)
    start = end - pd.Timedelta(days=28)
    frames = []
    cur = start
    while cur < end:
        nxt = min(cur + pd.Timedelta(days=7), end)
        raw = yf.download(
            mod.TICKER,
            start=cur.strftime('%Y-%m-%d'),
            end=nxt.strftime('%Y-%m-%d'),
            interval='1m', prepost=True, auto_adjust=False,
            progress=False, threads=False, timeout=30,
        )
        f = mod.normalize(raw)
        if not f.empty:
            frames.append(f)
        cur = nxt
    if not frames:
        raise RuntimeError('Yahoo returned no recent NQ=F 1m data across chunked requests')
    return (pd.concat(frames, ignore_index=True)
              .sort_values('datetime')
              .drop_duplicates('datetime', keep='last'))

mod.download_recent = download_recent_chunked
mod.main()
