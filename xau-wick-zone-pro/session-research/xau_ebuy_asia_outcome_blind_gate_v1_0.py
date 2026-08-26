#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / 'entry-research'


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


v04 = load_module('asia_v04', ENTRY / 'xau_ebuy_coverage_v0_4_sticky.py')
v01 = v04.v01

WINDOWS = {
    'H1': (pd.Timestamp('2024-08-01T00:00:00Z'), pd.Timestamp('2025-08-01T00:00:00Z')),
    'H2': (pd.Timestamp('2025-08-01T00:00:00Z'), pd.Timestamp('2026-08-01T00:00:00Z')),
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--z4-pkl', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--candidates-csv', required=True)
    return p.parse_args()


def asia_ny(t) -> bool:
    q = pd.Timestamp(t).tz_convert('America/New_York')
    return q.hour >= 18 or q.hour < 3


def asia_session_id(t) -> str:
    q = pd.Timestamp(t).tz_convert('America/New_York')
    d = q.date() if q.hour >= 18 else (q - pd.Timedelta(days=1)).date()
    return d.isoformat()


def metric_mean_count(displays) -> float | None:
    if not displays:
        return None
    return float(np.mean([len(x) for x in displays]))


def threshold_pack(m, st):
    checks = {
        'coverage_1v_ge_080': m['coverage']['1.0'] >= .80,
        'coverage_1p5v_ge_090': m['coverage']['1.5'] >= .90,
        'coverage_2v_ge_095': m['coverage']['2.0'] >= .95,
        'count_median_1_to_3': 1.0 <= m['candidate_count_median'] <= 3.0,
        'count_p90_le_3': m['candidate_count_p90'] <= 3.0,
        'nearest_p90_le_1p5v': m['nearest_distance_v_p90'] is not None and m['nearest_distance_v_p90'] <= 1.5,
        'survival_aware_persistence_ge_070': st['survival_aware_display_persistence'] is not None and st['survival_aware_display_persistence'] >= .70,
        'unexplained_survival_share_le_005': st['unexplained_share_of_survival_eligible'] is not None and st['unexplained_share_of_survival_eligible'] <= .05,
    }
    return {'checks': checks, 'pass': bool(all(checks.values()))}


def filter_parallel(snaps, displays, pools, lo, hi):
    idx = [i for i, s in enumerate(snaps) if lo <= pd.Timestamp(s['time']) < hi]
    return [snaps[i] for i in idx], [displays[i] for i in idx], [pools[i] for i in idx]


def summarize_window(raw, snaps, displays, pools):
    m = v01.metrics(snaps, displays)
    st = v04.stability(raw, snaps, displays, pools)
    fam = Counter(z.family for zs in displays for z in zs)
    sess = Counter(asia_session_id(s['time']) for s in snaps)
    return {
        'eligible_snapshot_count': int(len(snaps)),
        'asia_session_count': int(len(sess)),
        'snapshots_per_asia_session': {
            'median': float(np.median(list(sess.values()))) if sess else None,
            'p90': float(np.quantile(list(sess.values()), .9)) if sess else None,
        },
        'mean_displayed_zone_count': metric_mean_count(displays),
        'coverage_count_distance_metrics': m,
        'stability': st,
        'displayed_family_mix': {k: int(v) for k, v in sorted(fam.items())},
        'threshold_gate': threshold_pack(m, st),
    }


def main():
    a = parse_args()
    raw = v01.load_raw(a.files)
    active = v01.active_m1(raw)
    z4 = pd.read_pickle(a.z4_pkl).copy()
    z4['time'] = pd.to_datetime(z4.time, utc=True)
    bad = sorted(v01.FORBIDDEN & set(z4.columns))
    if bad:
        raise RuntimeError(f'future outcome columns present: {bad}')

    # Only session transfer: all scientific architecture and C5 sticky logic stay unchanged.
    v04.v01.ny_us = asia_ny
    snaps, pools = v04.build_fixed_pools(raw, active, z4)
    displays = v04.sticky_display(raw, snaps, pools)

    results = {}
    rows = []
    for w, (lo, hi) in WINDOWS.items():
        sw, dw, pw = filter_parallel(snaps, displays, pools, lo, hi)
        if not sw:
            raise RuntimeError(f'{w}: no Asia snapshots')
        results[w] = summarize_window(raw, sw, dw, pw)
        for s, zs in zip(sw, dw):
            sid = asia_session_id(s['time'])
            for rank, z in enumerate(zs, 1):
                rows.append({
                    'window': w, 'asia_session_id': sid, 'time': s['time'],
                    'close': s['close'], 'v60': s['v'], 'upper_z4_count': s['upper_z4_count'],
                    'nearest_upper_z4_dist_v': s['nearest_upper_z4_dist_v'],
                    'entry_rank': rank, 'family': z.family,
                    'center': z.center, 'zlo': z.zlo, 'zhi': z.zhi,
                    'distance_v': (s['close'] - z.center) / s['v'],
                })

    pd.DataFrame(rows).to_csv(a.candidates_csv, index=False)
    both = bool(results['H1']['threshold_gate']['pass'] and results['H2']['threshold_gate']['pass'])
    out = {
        'status': 'ASIA_C5_OUTCOME_BLIND_LOCATION_GATE_PASS' if both else 'ASIA_C5_OUTCOME_BLIND_LOCATION_GATE_FAIL',
        'scope': 'BUY_ONLY_C5_ASIA_OVERNIGHT_18_03_NY_OUTCOME_BLIND',
        'session_definition': '18:00-03:00 America/New_York; post-midnight bars belong to prior session-start date',
        'cadence': 'C5',
        'architecture': 'Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50',
        'future_price_outcomes_used': False,
        'score_used': False,
        'results': results,
        'candidate_rows': int(len(rows)),
        'reaction_study_authorized': both,
        'authorization': 'AUTHORIZE_PREREGISTERED_ASIA_REACTION_STUDY' if both else 'STOP_RETAIN_US_ONLY',
        'production_authorization': 'NONE',
    }
    Path(a.output).write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({
        'status': out['status'],
        'H1': {
            'snapshots': results['H1']['eligible_snapshot_count'],
            'coverage': results['H1']['coverage_count_distance_metrics']['coverage'],
            'nearest_p90': results['H1']['coverage_count_distance_metrics']['nearest_distance_v_p90'],
            'persistence': results['H1']['stability']['survival_aware_display_persistence'],
            'unexplained': results['H1']['stability']['unexplained_share_of_survival_eligible'],
            'gate': results['H1']['threshold_gate']['pass'],
        },
        'H2': {
            'snapshots': results['H2']['eligible_snapshot_count'],
            'coverage': results['H2']['coverage_count_distance_metrics']['coverage'],
            'nearest_p90': results['H2']['coverage_count_distance_metrics']['nearest_distance_v_p90'],
            'persistence': results['H2']['stability']['survival_aware_display_persistence'],
            'unexplained': results['H2']['stability']['unexplained_share_of_survival_eligible'],
            'gate': results['H2']['threshold_gate']['pass'],
        },
    }, indent=2), flush=True)


if __name__ == '__main__':
    main()
