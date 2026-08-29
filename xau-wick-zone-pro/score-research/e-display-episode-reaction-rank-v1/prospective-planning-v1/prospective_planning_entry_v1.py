#!/usr/bin/env python3
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import pandas as pd

import prospective_planning_tool_v1 as core

# Canonical repository path repair: PKG.parents[1] is xau-wick-zone-pro.
core.ENTRY = core.PKG.parents[1] / 'entry-research'
core.ENGINE = core.ENTRY / 'geometry-shifted-grid-parity' / 'xau_z4_c5_geometry_shifted_grid_equivalent.py'

# The canonical prospective archive intentionally stores normalized UTC `time`.
# The frozen historical Z4 engine intentionally remains unchanged and expects
# raw-style `timestamp` milliseconds. Bridge only the input schema here.
_ORIGINAL_Z4_SESSION = core.z4_session


def z4_session_timestamp_bridge(args):
    old_files = list(args.files)
    with tempfile.TemporaryDirectory(prefix='pros_z4_schema_bridge_') as td:
        td = Path(td)
        compat = []
        for i, f in enumerate(old_files):
            d, _ = core.normalize_raw_files([f])
            t = pd.to_datetime(d['time'], utc=True)
            q = pd.DataFrame({
                'timestamp': (t.astype('int64') // 1_000_000).astype('int64'),
                'open': d['open'].to_numpy(float),
                'high': d['high'].to_numpy(float),
                'low': d['low'].to_numpy(float),
                'close': d['close'].to_numpy(float),
            })
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
