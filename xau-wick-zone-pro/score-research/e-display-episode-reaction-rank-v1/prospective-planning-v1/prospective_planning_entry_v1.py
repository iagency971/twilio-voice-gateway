#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

import prospective_planning_tool_v1 as core

# Canonical repository path repair: PKG.parents[1] is xau-wick-zone-pro.
core.ENTRY = core.PKG.parents[1] / 'entry-research'
core.ENGINE = core.ENTRY / 'geometry-shifted-grid-parity' / 'xau_z4_c5_geometry_shifted_grid_equivalent.py'

# The prospective archive intentionally stores normalized UTC `time`, while
# the frozen historical Z4/E source engines remain unchanged and expect the
# original Dukascopy-style `timestamp` in milliseconds.  This bridge is
# schema-only: no prices, ordering rules, geometry rules, eligibility rules or
# future information are changed.  Conflicting duplicate timestamps fail
# closed; exact duplicates may be collapsed deterministically.


def _resolved_time_frame(path: str) -> pd.DataFrame:
    d = pd.read_csv(path, compression='infer')
    if 'time' in d.columns:
        t = pd.to_datetime(d['time'], utc=True, errors='coerce')
    else:
        t = pd.Series(pd.NaT, index=d.index, dtype='datetime64[ns, UTC]')
    if 'timestamp' in d.columns:
        ts = pd.to_datetime(pd.to_numeric(d['timestamp'], errors='coerce'), unit='ms', utc=True, errors='coerce')
        t = t.fillna(ts)
    if t.isna().any():
        raise RuntimeError(f'{path}: unresolved M1 timestamps after time/timestamp bridge')
    for c in ['open', 'high', 'low', 'close']:
        if c not in d.columns:
            raise RuntimeError(f'{path}: missing {c}')
        d[c] = pd.to_numeric(d[c], errors='raise').astype(float)
    q = pd.DataFrame({
        'timestamp': (t.astype('int64') // 1_000_000).astype('int64'),
        'open': d['open'].to_numpy(float),
        'high': d['high'].to_numpy(float),
        'low': d['low'].to_numpy(float),
        'close': d['close'].to_numpy(float),
    }).sort_values('timestamp').reset_index(drop=True)
    dup = q[q.duplicated('timestamp', keep=False)]
    if len(dup):
        for ts_value, g in dup.groupby('timestamp'):
            if len(g[['open', 'high', 'low', 'close']].drop_duplicates()) > 1:
                raise RuntimeError(f'{path}: conflicting duplicate timestamp {ts_value}')
    return q.drop_duplicates('timestamp', keep='first').reset_index(drop=True)


@contextmanager
def timestamp_schema_bridge(files: list[str], prefix: str):
    with tempfile.TemporaryDirectory(prefix=prefix) as td:
        td = Path(td)
        compat = []
        for i, f in enumerate(files):
            q = _resolved_time_frame(f)
            p = td / f'input_{i:02d}.csv'
            q.to_csv(p, index=False)
            compat.append(str(p))
        yield compat


_ORIGINAL_Z4_SESSION = core.z4_session
_ORIGINAL_FEATURE_SESSION = core.prospective_feature_session


def z4_session_timestamp_bridge(args):
    old_files = list(args.files)
    with timestamp_schema_bridge(old_files, 'pros_z4_schema_bridge_') as compat:
        args.files = compat
        try:
            return _ORIGINAL_Z4_SESSION(args)
        finally:
            args.files = old_files


def feature_session_timestamp_bridge(args):
    old_files = list(args.files)
    with timestamp_schema_bridge(old_files, 'pros_e_schema_bridge_') as compat:
        args.files = compat
        try:
            return _ORIGINAL_FEATURE_SESSION(args)
        finally:
            args.files = old_files


core.z4_session = z4_session_timestamp_bridge
core.prospective_feature_session = feature_session_timestamp_bridge

if __name__ == '__main__':
    core.main()
