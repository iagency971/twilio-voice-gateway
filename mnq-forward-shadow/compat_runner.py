#!/usr/bin/env python3
"""Technical compatibility wrapper for Yahoo's <=8-day 1m request limit.
No strategy or forward-gate logic is changed.

Also enforces the preregistered append-only ledger rule: once a completed day has
been frozen, later Yahoo re-downloads may not retroactively add/remove trades on
that day. Only trades strictly after the previously frozen max day can be added.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
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


def _load_frozen_snapshot():
    if not mod.LEDGER.exists():
        return pd.DataFrame(), None
    old = pd.read_csv(mod.LEDGER)
    if old.empty or 'entry_time' not in old.columns:
        return old, None
    old['entry_time'] = pd.to_datetime(old['entry_time'], errors='coerce')
    max_day = old['entry_time'].dt.normalize().max()
    return old, max_day


def _restore_append_only(old: pd.DataFrame, old_max_day):
    if old.empty or old_max_day is None or not mod.LEDGER.exists():
        return
    cur = pd.read_csv(mod.LEDGER)
    if cur.empty:
        frozen = old.copy()
    else:
        cur['entry_time'] = pd.to_datetime(cur['entry_time'], errors='coerce')
        old_keys = set(old['key'].astype(str)) if 'key' in old.columns else set()
        new = cur[~cur['key'].astype(str).isin(old_keys)].copy()
        new = new[new['entry_time'].dt.normalize() > old_max_day]
        frozen = pd.concat([old, new], ignore_index=True)
        if 'key' in frozen.columns:
            frozen = frozen.drop_duplicates('key', keep='first')
        frozen = frozen.sort_values('entry_time')
    frozen.to_csv(mod.LEDGER, index=False)

    summary_path = mod.RESULTS / 'SUMMARY.json'
    latest_day = None
    if summary_path.exists():
        try:
            latest_day = json.loads(summary_path.read_text()).get('latest_complete_day')
        except Exception:
            latest_day = None
    if latest_day is None:
        latest_day = str(pd.to_datetime(frozen['entry_time']).dt.normalize().max().date())
    obj = mod.summary(frozen, latest_day)
    obj['ledger_sha256'] = hashlib.sha256(mod.LEDGER.read_bytes()).hexdigest()
    summary_path.write_text(json.dumps(obj, indent=2, allow_nan=False))


old, old_max_day = _load_frozen_snapshot()
mod.download_recent = download_recent_chunked
mod.main()
_restore_append_only(old, old_max_day)
