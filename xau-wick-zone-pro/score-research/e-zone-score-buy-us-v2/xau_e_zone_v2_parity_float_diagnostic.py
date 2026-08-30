#!/usr/bin/env python3
from __future__ import annotations

"""Outcome-blind diagnostic for the 7 residual V0.4 geometry parity floats.

This does not change detector geometry or approve any tolerance.  It intercepts
only the parity comparison so the exact mismatching rows/deltas can be frozen
for methodological adjudication before any V2 reaction outcome is opened.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import xau_e_zone_v2_instrument as inst


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--z4-pkl', required=True)
    p.add_argument('--reference-v04-csv', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--scratch-dir', required=True)
    p.add_argument('--target-start', default='2024-08-01T00:00:00Z')
    p.add_argument('--target-end', default='2026-08-01T00:00:00Z')
    return p.parse_args()


def main():
    a = parse_args()
    out = Path(a.scratch_dir)
    out.mkdir(parents=True, exist_ok=True)
    report_path = Path(a.report)
    original = inst.exact_parity

    def diagnostic(reference_path, got, target_start, target_end):
        ref = pd.read_csv(reference_path, compression='infer', float_precision='round_trip')
        ref['time'] = pd.to_datetime(ref.time, utc=True)
        ref = ref[(ref.time >= target_start) & (ref.time < target_end)].copy().sort_values(['time','entry_rank']).reset_index(drop=True)
        g = got.copy().sort_values(['time','entry_rank']).reset_index(drop=True)
        cols = ['time','entry_rank','family','center','zlo','zhi']
        details = []
        exact_counts = {}
        tol_counts = {}
        for c in cols:
            if c == 'time':
                neq = ref[c].to_numpy() != g[c].to_numpy()
                close = ~neq
            elif c in {'entry_rank','family'}:
                neq = ref[c].astype(str).to_numpy() != g[c].astype(str).to_numpy()
                close = ~neq
            else:
                rv = ref[c].to_numpy(float)
                gv = g[c].to_numpy(float)
                neq = rv != gv
                close = np.isclose(rv, gv, rtol=0.0, atol=1e-12, equal_nan=True)
                for i in np.flatnonzero(neq):
                    spacing = max(abs(float(np.spacing(rv[i]))), abs(float(np.spacing(gv[i]))), np.finfo(float).tiny)
                    details.append({
                        'column': c,
                        'row_index': int(i),
                        'time': pd.Timestamp(ref.at[i,'time']).isoformat(),
                        'entry_rank': int(ref.at[i,'entry_rank']),
                        'family': str(ref.at[i,'family']),
                        'reference': float(rv[i]),
                        'instrumented': float(gv[i]),
                        'absolute_delta': float(abs(rv[i]-gv[i])),
                        'delta_in_max_local_ulp': float(abs(rv[i]-gv[i]) / spacing),
                        'within_atol_1e_12': bool(close[i]),
                    })
            exact_counts[c] = int(np.sum(neq))
            tol_counts[c] = int(np.sum(~close))

        exact_bad = {k:v for k,v in exact_counts.items() if v}
        tol_bad = {k:v for k,v in tol_counts.items() if v}
        r = {
            'status': 'V2_V04_PARITY_FLOAT_DIAGNOSTIC_COMPLETE',
            'future_price_outcomes_used': False,
            'reference_rows': int(len(ref)),
            'instrumented_rows': int(len(g)),
            'exact_float64_parity_pass': len(ref) == len(g) and not exact_bad,
            'exact_mismatch_counts': exact_bad,
            'canonical_v1_atol_1e12_comparator_pass': len(ref) == len(g) and not tol_bad,
            'atol_1e12_mismatch_counts': tol_bad,
            'mismatches': details,
            'max_absolute_delta': max((d['absolute_delta'] for d in details), default=0.0),
            'max_delta_in_local_ulp': max((d['delta_in_max_local_ulp'] for d in details), default=0.0),
            'interpretation_guard': 'DIAGNOSTIC_ONLY_NO_PARITY_RULE_CHANGE_NO_OUTCOME_AUTHORIZATION',
        }
        report_path.write_text(json.dumps(r, indent=2, sort_keys=True) + '\n')
        # Preserve the original fail-closed behavior after the report is frozen.
        return original(reference_path, got, target_start, target_end)

    inst.exact_parity = diagnostic
    sys.argv = [
        str(inst.__file__),
        '--files', *a.files,
        '--z4-pkl', a.z4_pkl,
        '--output-features', str(out/'features.csv.gz'),
        '--output-display-all', str(out/'display_all.csv.gz'),
        '--output-full-pool', str(out/'full_pool.csv.gz'),
        '--output-context', str(out/'context.csv.gz'),
        '--manifest', str(out/'instrument_manifest.json'),
        '--target-start', a.target_start,
        '--target-end', a.target_end,
        '--reference-v04-csv', a.reference_v04_csv,
    ]
    try:
        inst.main()
    except RuntimeError as e:
        if 'V04_EXACT_PARITY_FAIL' not in str(e):
            raise
    if not report_path.is_file():
        raise RuntimeError('PARITY_DIAGNOSTIC_REPORT_NOT_WRITTEN')
    r = json.loads(report_path.read_text())
    if r['future_price_outcomes_used'] is not False:
        raise RuntimeError('PARITY_DIAGNOSTIC_OUTCOME_GUARD_FAIL')
    print(json.dumps(r, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
