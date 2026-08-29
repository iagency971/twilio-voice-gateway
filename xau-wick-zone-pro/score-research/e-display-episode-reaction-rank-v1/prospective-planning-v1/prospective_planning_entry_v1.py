#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

import prospective_planning_tool_v1 as core

# Canonical repository path repair: PKG.parents[1] is xau-wick-zone-pro.
core.ENTRY = core.PKG.parents[1] / 'entry-research'
core.ENGINE = core.ENTRY / 'geometry-shifted-grid-parity' / 'xau_z4_c5_geometry_shifted_grid_equivalent.py'

# The canonical prospective archive stores normalized UTC `time`, while the
# frozen historical Z4 engine remains unchanged and expects `timestamp` ms.
# This adapter changes schema only. It also accepts the QA fixture where a
# canonical time-based prefix is concatenated with raw timestamp-based future
# rows, filling one time representation from the other row by row.
_ORIGINAL_Z4_SESSION = core.z4_session


def z4_session_timestamp_bridge(args):
    old_files = list(args.files)
    with tempfile.TemporaryDirectory(prefix='pros_z4_schema_bridge_') as td:
        td = Path(td)
        compat = []
        for i, f in enumerate(old_files):
            d = pd.read_csv(f, compression='infer')
            if 'time' in d.columns:
                t = pd.to_datetime(d['time'], utc=True, errors='coerce')
            else:
                t = pd.Series(pd.NaT, index=d.index, dtype='datetime64[ns, UTC]')
            if 'timestamp' in d.columns:
                ts = pd.to_datetime(pd.to_numeric(d['timestamp'], errors='coerce'), unit='ms', utc=True, errors='coerce')
                t = t.fillna(ts)
            if t.isna().any():
                raise RuntimeError(f'{f}: unresolved M1 timestamps after time/timestamp bridge')
            for c in ['open', 'high', 'low', 'close']:
                if c not in d.columns:
                    raise RuntimeError(f'{f}: missing {c}')
                d[c] = pd.to_numeric(d[c], errors='raise').astype(float)
            q = pd.DataFrame({
                'timestamp': (t.astype('int64') // 1_000_000).astype('int64'),
                'open': d['open'].to_numpy(float),
                'high': d['high'].to_numpy(float),
                'low': d['low'].to_numpy(float),
                'close': d['close'].to_numpy(float),
            }).sort_values('timestamp').drop_duplicates('timestamp', keep='first').reset_index(drop=True)
            p = td / f'input_{i:02d}.csv'
            q.to_csv(p, index=False)
            compat.append(str(p))
        args.files = compat
        try:
            return _ORIGINAL_Z4_SESSION(args)
        finally:
            args.files = old_files


core.z4_session = z4_session_timestamp_bridge

if __name__ == '__main__':
    core.main()
