#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / 'entry-research'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


v04 = load_module('asia_v2_v04', ENTRY / 'xau_ebuy_coverage_v0_4_sticky.py')
v01, v02, v03 = v04.v01, v04.v02, v04.v03

WINDOWS = {
    'H1': (pd.Timestamp('2024-08-01T00:00:00Z'), pd.Timestamp('2025-08-01T00:00:00Z')),
    'H2': (pd.Timestamp('2025-08-01T00:00:00Z'), pd.Timestamp('2026-08-01T00:00:00Z')),
}
MODES = ('LOW', 'BODYLOW', 'BOTH')
GRACES = (30, 60, 120)
SHAPES = (
    ('ESM', ('ESM',)),
    ('ESM_EPM', ('ESM', 'EPM')),
    ('ESM_EWM', ('ESM', 'EWM')),
    ('ESM_EPM_EWM', ('ESM', 'EPM', 'EWM')),
    ('ESM_EPM_EWM_ESWING', ('ESM', 'EPM', 'EWM', 'ESWING')),
)
V1_ID = 'ESM_BOTH_G120M__ESM_EPM_EWM_ESWING'
V1_ANCHORS = {
    'H1': {'snapshots': 19998, 'c1': 0.7855285528552856, 'c15': 0.8972897289728973,
           'c2': 0.9468946894689469, 'nearest_p90': 1.2401391826985517,
           'survival': 0.979634054694372, 'unexplained': 0.02036594530562794},
    'H2': {'snapshots': 21392, 'c1': 0.8048335826477188, 'c15': 0.9087976813762154,
           'c2': 0.956572550486163, 'nearest_p90': 1.2141176033727707,
           'survival': 0.9804149947823574, 'unexplained': 0.019585005217642606},
}


def args():
    p = argparse.ArgumentParser()
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--z4-pkl', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--selected-csv', required=True)
    return p.parse_args()


def asia_ny(t):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    return q.hour >= 18 or q.hour < 3


def asia_session_id(t):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    d = q.date() if q.hour >= 18 else (q - pd.Timedelta(days=1)).date()
    return d.isoformat()


def asia_subperiod(t):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    m = q.hour * 60 + q.minute
    if m >= 18 * 60 and m < 21 * 60:
        return 'ASIA_EARLY_18_21'
    if m >= 21 * 60:
        return 'ASIA_LATE_PRE_MIDNIGHT_21_00'
    if m < 3 * 60:
        return 'ASIA_POST_MIDNIGHT_00_03'
    return 'NON_ASIA'


def threshold(m, st):
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


def filter_parallel(snaps, displays, pools, lo, hi, subperiod=None):
    ix = []
    for i, s in enumerate(snaps):
        t = pd.Timestamp(s['time'])
        if not (lo <= t < hi):
            continue
        if subperiod is not None and asia_subperiod(t) != subperiod:
            continue
        ix.append(i)
    return [snaps[i] for i in ix], [displays[i] for i in ix], [pools[i] for i in ix]


def summarize(raw, snaps, displays, pools):
    m = v01.metrics(snaps, displays)
    st = v04.stability(raw, snaps, displays, pools)
    fam = Counter(z.family for zs in displays for z in zs)
    sessions = Counter(asia_session_id(s['time']) for s in snaps)
    return {
        'eligible_snapshot_count': int(len(snaps)),
        'asia_session_count': int(len(sessions)),
        'mean_displayed_zone_count': float(np.mean([len(x) for x in displays])) if displays else None,
        'metrics': m,
        'stability': st,
        'displayed_family_mix': {k: int(v) for k, v in sorted(fam.items())},
        'gate': threshold(m, st),
    }


def supp_count(shape_name):
    return {'ESM': 1, 'ESM_EPM': 2, 'ESM_EWM': 2, 'ESM_EPM_EWM': 3, 'ESM_EPM_EWM_ESWING': 4}[shape_name]


def build_pools(snaps, z4_lists, family_lists):
    out = []
    for i, s in enumerate(snaps):
        fams = [x[i] for x in family_lists]
        out.append(v04.dedup_full_pool(s, z4_lists[i], fams))
    return out


def parity_v1(result):
    got = result[V1_ID]
    checks = {}
    for w in ('H1', 'H2'):
        q = got['windows'][w]; a = V1_ANCHORS[w]
        vals = {
            'snapshots': q['eligible_snapshot_count'],
            'c1': q['metrics']['coverage']['1.0'],
            'c15': q['metrics']['coverage']['1.5'],
            'c2': q['metrics']['coverage']['2.0'],
            'nearest_p90': q['metrics']['nearest_distance_v_p90'],
            'survival': q['stability']['survival_aware_display_persistence'],
            'unexplained': q['stability']['unexplained_share_of_survival_eligible'],
        }
        wc = {}
        for k, exp in a.items():
            if k == 'snapshots':
                wc[k] = vals[k] == exp
            else:
                wc[k] = abs(float(vals[k]) - float(exp)) <= 1e-12
        checks[w] = wc
    passed = all(all(x.values()) for x in checks.values())
    if not passed:
        raise RuntimeError({'v1_parity_failed': checks, 'got': got})
    return {'pass': True, 'checks': checks, 'anchors': V1_ANCHORS}


def main():
    a = args(); t0 = time.time()
    raw = v01.load_raw(a.files); active = v01.active_m1(raw)
    z4 = pd.read_pickle(a.z4_pkl).copy(); z4['time'] = pd.to_datetime(z4.time, utc=True)
    bad = sorted(v01.FORBIDDEN & set(z4.columns))
    if bad:
        raise RuntimeError(f'future outcome columns present: {bad}')

    # The only population change versus the generic E-BUY code is the frozen Asia filter.
    v01.ny_us = asia_ny
    snaps = v01.make_eval_times(active, z4)
    all_c5 = v02.all_c5_snapshots(active)
    z4_lists = [s['z4_below'] for s in snaps]
    print('ASIA_V2_SNAPSHOTS', len(snaps), 'ALL_C5', len(all_c5), flush=True)

    # Fixed prior families once for all candidates.
    epm_events = v02.pivot_base_events(raw, 'M1', 2, raw, active)
    epm = v02.pivot_memory_lists(snaps, epm_events, 8, 'EPM_M1_R2_A8H')
    ewm_map = v02.wick_memory_all_c5(raw, all_c5, 60, 'EWM_G60M')
    ewm = [ewm_map.get(s['time'], []) for s in snaps]
    eswing = v02.fixed_swing_lists(raw, snaps)

    esm = {}
    for mode in MODES:
        for grace in GRACES:
            name = f'ESM_{mode}_G{grace}M'
            mp = v03.esm_stateful_outputs(raw, active, all_c5, mode, grace, name)
            esm[name] = [mp.get(s['time'], []) for s in snaps]
            print('ESM_READY', name, flush=True)

    candidates = {}
    cache_selected = {}
    for esm_name, esm_list in esm.items():
        family_map = {'ESM': esm_list, 'EPM': epm, 'EWM': ewm, 'ESWING': eswing}
        for shape_name, shape in SHAPES:
            cid = f'{esm_name}__{shape_name}'
            pools = build_pools(snaps, z4_lists, [family_map[x] for x in shape])
            displays = v04.sticky_display(raw, snaps, pools)
            windows = {}
            for w, (lo, hi) in WINDOWS.items():
                sw, dw, pw = filter_parallel(snaps, displays, pools, lo, hi)
                windows[w] = summarize(raw, sw, dw, pw)
            both = bool(windows['H1']['gate']['pass'] and windows['H2']['gate']['pass'])
            candidates[cid] = {
                'esm': esm_name, 'shape': shape_name, 'supplemental_family_count': supp_count(shape_name),
                'windows': windows, 'passes_both_windows': both,
            }
            cache_selected[cid] = (pools, displays)
            print('CANDIDATE', cid, 'PASS_BOTH', both,
                  'H1_C1', windows['H1']['metrics']['coverage']['1.0'],
                  'H2_C1', windows['H2']['metrics']['coverage']['1.0'], flush=True)

    v1_parity = parity_v1(candidates)
    passers = [k for k, q in candidates.items() if q['passes_both_windows']]

    selected = None
    if passers:
        def key(cid):
            q = candidates[cid]; h1 = q['windows']['H1']; h2 = q['windows']['H2']
            worst_c1 = min(h1['metrics']['coverage']['1.0'], h2['metrics']['coverage']['1.0'])
            worst_c15 = min(h1['metrics']['coverage']['1.5'], h2['metrics']['coverage']['1.5'])
            worst_p = min(h1['stability']['survival_aware_display_persistence'], h2['stability']['survival_aware_display_persistence'])
            worst_near = max(h1['metrics']['nearest_distance_v_p90'], h2['metrics']['nearest_distance_v_p90'])
            return (q['supplemental_family_count'], -worst_c1, -worst_c15, -worst_p, worst_near, cid)
        selected = sorted(passers, key=key)[0]

    rows = []; subperiods = {}
    if selected is not None:
        pools, displays = cache_selected[selected]
        for w, (lo, hi) in WINDOWS.items():
            subperiods[w] = {}
            for sp in ('ASIA_EARLY_18_21', 'ASIA_LATE_PRE_MIDNIGHT_21_00', 'ASIA_POST_MIDNIGHT_00_03'):
                sw, dw, pw = filter_parallel(snaps, displays, pools, lo, hi, sp)
                subperiods[w][sp] = summarize(raw, sw, dw, pw) if sw else None
        for s, zs in zip(snaps, displays):
            t = pd.Timestamp(s['time'])
            w = 'H1' if WINDOWS['H1'][0] <= t < WINDOWS['H1'][1] else ('H2' if WINDOWS['H2'][0] <= t < WINDOWS['H2'][1] else None)
            if w is None:
                continue
            for rank, z in enumerate(zs, 1):
                rows.append({
                    'window': w, 'asia_session_id': asia_session_id(t), 'asia_subperiod': asia_subperiod(t),
                    'time': t, 'close': s['close'], 'v60': s['v'], 'upper_z4_count': s['upper_z4_count'],
                    'nearest_upper_z4_dist_v': s['nearest_upper_z4_dist_v'], 'entry_rank': rank,
                    'family': z.family, 'center': z.center, 'zlo': z.zlo, 'zhi': z.zhi,
                    'distance_v': (s['close'] - z.center) / s['v'],
                })
    pd.DataFrame(rows).to_csv(a.selected_csv, index=False)

    out = {
        'status': 'ASIA_V2_ARCHITECTURE_GATE_PASS' if selected else 'ASIA_V2_ARCHITECTURE_GATE_FAIL',
        'scope': 'C5_ASIA_18_03_OUTCOME_BLIND_PREEXISTING_ARCHITECTURE_GRID',
        'future_price_outcomes_used': False, 'score_used': False,
        'candidate_count': len(candidates), 'passer_count': len(passers),
        'v1_current_architecture_parity': v1_parity,
        'selection_rule': 'pass H1+H2; fewest supplemental families; max worst C1; max worst C1.5; max worst survival persistence; min worst nearest p90; ID',
        'all_candidates': candidates, 'selected_architecture': selected,
        'selected_candidate_rows': int(len(rows)), 'selected_subperiod_diagnostics': subperiods if selected else {},
        'reaction_study_authorized': bool(selected),
        'authorization': 'AUTHORIZE_ASIA_V2_REACTION_STUDY' if selected else 'STOP_RETAIN_US_ONLY',
        'production_authorization': 'NONE', 'runtime_sec': float(time.time() - t0),
    }
    Path(a.output).write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({
        'status': out['status'], 'candidate_count': len(candidates), 'passer_count': len(passers),
        'selected': selected,
        'selected_H1': candidates[selected]['windows']['H1'] if selected else None,
        'selected_H2': candidates[selected]['windows']['H2'] if selected else None,
    }, indent=2, default=str), flush=True)


if __name__ == '__main__':
    main()
