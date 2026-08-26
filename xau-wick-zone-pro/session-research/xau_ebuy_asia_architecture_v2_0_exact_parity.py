#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location('asia_v2_parent_exact', HERE / 'xau_ebuy_asia_architecture_v2_0.py')
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

# Exact values read from immutable Asia v1 artifact run 33018338282.
# This repairs only the parity guard; no architecture, threshold, population,
# session, selection or reaction rule changes.
mod.V1_ANCHORS = {
    'H1': {
        'snapshots': 19998,
        'c1': 0.7855285528552856,
        'c15': 0.8972897289728973,
        'c2': 0.946894689468947,
        'nearest_p90': 1.2401388670627616,
        'survival': 0.9796342932223804,
        'unexplained': 0.020365706777619622,
    },
    'H2': {
        'snapshots': 21392,
        'c1': 0.8048335826477188,
        'c15': 0.9087976813762154,
        'c2': 0.9565725504861631,
        'nearest_p90': 1.2141177114472754,
        'survival': 0.9804150264858823,
        'unexplained': 0.019584973514117705,
    },
}

if __name__ == '__main__':
    mod.main()
