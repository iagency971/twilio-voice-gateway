#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


parent = load_module('asia_v2_single_parent', HERE / 'xau_ebuy_asia_architecture_v2_0_exact_parity.py')
p = parent.mod
v01, v02, v03, v04 = p.v01, p.v02, p.v03, p.v04


def args():
    q = argparse.ArgumentParser()
    q.add_argument('--files', nargs='+', required=True)
    q.add_argument('--z4-pkl', required=True)
    q.add_argument('--mode', choices=list(p.MODES), required=True)
    q.add_argument('--grace', type=int, choices=list(p.GRACES), required=True)
    q.add_argument('--output', required=True)
    q.add_argument('--csv-dir', required=True)
    return q.parse_args()


def main():
    a = args(); t0 = time.time()
    raw = v01.load_raw(a.files); active = v01.active_m1(raw)
    z4 = pd.read_pickle(a.z4_pkl).copy(); z4['time'] = pd.to_datetime(z4.time, utc=True)
    bad = sorted(v01.FORBIDDEN & set(z4.columns))
    if bad:
        raise RuntimeError(f'future outcome columns present: {bad}')

    v01.ny_us = p.asia_ny
    snaps = v01.make_eval_times(active, z4)
    all_c5 = v02.all_c5_snapshots(active)
    z4_lists = [s['z4_below'] for s in snaps]

    epm_events = v02.pivot_base_events(raw, 'M1', 2, raw, active)
    epm = v02.pivot_memory_lists(snaps, epm_events, 8, 'EPM_M1_R2_A8H')
    ewm_map = v02.wick_memory_all_c5(raw, all_c5, 60, 'EWM_G60M')
    ewm = [ewm_map.get(s['time'], []) for s in snaps]
    eswing = v02.fixed_swing_lists(raw, snaps)

    esm_name = f'ESM_{a.mode}_G{a.grace}M'
    esm_map = v03.esm_stateful_outputs(raw, active, all_c5, a.mode, a.grace, esm_name)
    esm = [esm_map.get(s['time'], []) for s in snaps]
    family_map = {'ESM': esm, 'EPM': epm, 'EWM': ewm, 'ESWING': eswing}

    out = {}
    csv_dir = Path(a.csv_dir); csv_dir.mkdir(parents=True, exist_ok=True)
    for shape_name, shape in p.SHAPES:
        cid = f'{esm_name}__{shape_name}'
        pools = p.build_pools(snaps, z4_lists, [family_map[x] for x in shape])
        displays = v04.sticky_display(raw, snaps, pools)
        windows = {}
        for w, (lo, hi) in p.WINDOWS.items():
            sw, dw, pw = p.filter_parallel(snaps, displays, pools, lo, hi)
            windows[w] = p.summarize(raw, sw, dw, pw)
        both = bool(windows['H1']['gate']['pass'] and windows['H2']['gate']['pass'])
        out[cid] = {
            'esm': esm_name, 'shape': shape_name,
            'supplemental_family_count': p.supp_count(shape_name),
            'windows': windows, 'passes_both_windows': both,
        }

        rows = []
        for s, zs in zip(snaps, displays):
            t = pd.Timestamp(s['time'])
            w = 'H1' if p.WINDOWS['H1'][0] <= t < p.WINDOWS['H1'][1] else ('H2' if p.WINDOWS['H2'][0] <= t < p.WINDOWS['H2'][1] else None)
            if w is None:
                continue
            for rank, z in enumerate(zs, 1):
                rows.append({
                    'window': w, 'asia_session_id': p.asia_session_id(t), 'asia_subperiod': p.asia_subperiod(t),
                    'time': t, 'close': s['close'], 'v60': s['v'],
                    'upper_z4_count': s['upper_z4_count'], 'nearest_upper_z4_dist_v': s['nearest_upper_z4_dist_v'],
                    'entry_rank': rank, 'family': z.family, 'center': z.center, 'zlo': z.zlo, 'zhi': z.zhi,
                    'distance_v': (s['close'] - z.center) / s['v'],
                })
        pd.DataFrame(rows).to_csv(csv_dir / f'{cid}.csv.gz', index=False, compression='gzip')
        print('ASIA_V2_SINGLE', cid, 'PASS_BOTH', both,
              'H1', windows['H1']['metrics']['coverage'],
              'H2', windows['H2']['metrics']['coverage'], flush=True)

    result = {
        'status': 'ASIA_V2_SINGLE_ESM_COMPLETE', 'esm': esm_name,
        'future_price_outcomes_used': False, 'score_used': False,
        'candidate_count': len(out), 'candidates': out,
        'runtime_sec': float(time.time() - t0),
    }
    Path(a.output).write_text(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
