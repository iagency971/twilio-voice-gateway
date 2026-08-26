#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / 'xau_ebuy_c1_refresh_outcome_blind_gate_v1_0.py'

spec = importlib.util.spec_from_file_location('c1_gate_v10', BASE_PATH)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)

_orig_churn = base.churn


def churn_accounting_repaired(snaps, displays, cadence):
    out = _orig_churn(snaps, displays, cadence)
    # v1.0 counted session/sequence initializations among total births while the
    # denominator used only contiguous transitions. That derived rate is therefore
    # not interpretable. Geometry, matching, lifetimes, deaths, rank changes and
    # drift are unchanged; only the misleading derived birth rate is suppressed.
    out['births_per_100_transitions'] = None
    out['birth_rate_accounting_note'] = (
        'v1.0 total births include non-contiguous sequence/session starts; '
        'no per-transition birth rate is reported in v1.1.'
    )
    return out


base.churn = churn_accounting_repaired

if __name__ == '__main__':
    # Preserve the v1.0 causal/scientific engine exactly, then relabel only the
    # accounting-repaired result file after base.main() completes.
    base.main()
    argv = sys.argv[1:]
    if '--output' in argv:
        p = Path(argv[argv.index('--output') + 1])
        x = json.loads(p.read_text())
        x['study'] = 'E_BUY_C1_MINUTE_REFRESH_OUTCOME_BLIND_DEV_GATE_V1_1_ACCOUNTING_REPAIR'
        x['accounting_repair_only'] = True
        x['accounting_repair_note'] = (
            'Suppresses the invalid v1.0 births-per-contiguous-transition derived rate. '
            'No zone geometry, matching, coverage, stability, lifetime, rank-change or drift calculation changed.'
        )
        p.write_text(json.dumps(x, indent=2))
