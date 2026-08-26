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
HERE = Path(__file__).resolve().parent
AMBIG = {'AMBIGUOUS', 'AMBIGUOUS_CONTACT_BAR'}
SEED = 20260826


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


v04 = load_module('core_v04', ENTRY / 'xau_ebuy_coverage_v0_4_sticky.py')
v01 = v04.v01
final = load_module('core_final_preoutcome', ENTRY / 'xau_ebuy_reaction_dev_v1_0_3_final_preoutcome.py')
asia = load_module('core_asia_plumbing', HERE / 'xau_ebuy_asia_reaction_v1_0.py')
asia.base = final.base

H1_LO = pd.Timestamp('2024-08-01T00:00:00Z')
H1_HI = pd.Timestamp('2025-08-01T00:00:00Z')
H2_LO = H1_HI
H2_HI = pd.Timestamp('2026-08-01T00:00:00Z')


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--z4-pkl', required=True)
    p.add_argument('--mode', choices=['historical', 'fresh'], required=True)
    p.add_argument('--fresh-session-ids-json')
    p.add_argument('--output', required=True)
    p.add_argument('--contacts-csv', required=True)
    p.add_argument('--br-csv', required=True)
    p.add_argument('--candidates-csv', required=True)
    return p.parse_args()


def core_ny(t):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    return q.hour >= 21 or q.hour < 3


def core_session_id(t):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    d = q.date() if q.hour >= 21 else (q - pd.Timedelta(days=1)).date()
    return d.isoformat()


def core_end(t):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    if q.hour >= 21:
        d = (q + pd.Timedelta(days=1)).date()
    elif q.hour < 3:
        d = q.date()
    else:
        raise RuntimeError(f'non Asia-Core timestamp: {q}')
    return pd.Timestamp(year=d.year, month=d.month, day=d.day, hour=3,
                        tz='America/New_York').tz_convert('UTC')


def core_subperiod(t):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    return 'ASIA_CORE_21_00' if q.hour >= 21 else 'ASIA_CORE_00_03'


def candidate_rows(snaps, displays):
    rows = []
    for s, zs in zip(snaps, displays):
        for rank, z in enumerate(zs, 1):
            rows.append({
                'time': s['time'], 'asia_session_id': core_session_id(s['time']),
                'entry_rank': rank, 'family': z.family,
                'center': z.center, 'zlo': z.zlo, 'zhi': z.zhi,
                'close': s['close'], 'v60': s['v'],
                'distance_v': (s['close'] - z.center) / s['v'],
            })
    return rows


def summary(contacts, trades):
    q = asia.summarize(contacts, trades)
    fired = [x for x in trades if bool(x.get('fired'))]
    amb = sum(1 for x in fired if str(x.get('tp1_invalidation_status')) in AMBIG)
    q['resolved_share'] = float((len(fired) - amb) / len(fired)) if fired else None
    pairs = Counter((str(x['asia_session_id']), int(x['episode_id'])) for x in contacts)
    q['duplicate_contact_session_episode_max'] = max(pairs.values()) if pairs else 0
    q['duplicate_contact_guard_pass'] = bool(not pairs or max(pairs.values()) <= 1)
    return q


def bootstrap_tp(trades, eligible_session_ids, nrep=10000):
    sessions = sorted(set(str(x) for x in eligible_session_ids))
    if not sessions:
        return {'n_sessions': 0, 'replications': nrep, 'p2_5': None, 'p50': None, 'p97_5': None}
    by = {s: [0, 0] for s in sessions}  # tp, resolved(non-ambiguous fired)
    for x in trades:
        if not bool(x.get('fired')):
            continue
        s = str(x['asia_session_id'])
        if s not in by:
            continue
        st = str(x.get('tp1_invalidation_status'))
        if st in AMBIG:
            continue
        by[s][1] += 1
        if st == 'TP1_FIRST':
            by[s][0] += 1
    arr = np.asarray([by[s] for s in sessions], dtype=np.int64)
    rng = np.random.default_rng(SEED)
    vals = []
    for _ in range(nrep):
        ix = rng.integers(0, len(arr), size=len(arr))
        q = arr[ix].sum(axis=0)
        if q[1] > 0:
            vals.append(q[0] / q[1])
    a = np.asarray(vals, float)
    return {
        'n_sessions': int(len(sessions)), 'replications': int(nrep), 'valid_replications': int(len(a)),
        'p2_5': float(np.quantile(a, .025)) if len(a) else None,
        'p50': float(np.quantile(a, .50)) if len(a) else None,
        'p97_5': float(np.quantile(a, .975)) if len(a) else None,
    }


def window_ids(snaps, lo, hi):
    return sorted({core_session_id(s['time']) for s in snaps if lo <= pd.Timestamp(s['time']) < hi})


def ratio(a, b):
    if a is None or b is None or not np.isfinite(float(a)) or not np.isfinite(float(b)) or float(a) == 0:
        return None
    return float(b) / float(a)


def main():
    a = parse_args()
    raw = v01.load_raw(a.files)
    active = v01.active_m1(raw)
    z4 = pd.read_pickle(a.z4_pkl).copy()
    z4['time'] = pd.to_datetime(z4.time, utc=True)
    bad = sorted(v01.FORBIDDEN & set(z4.columns))
    if bad:
        raise RuntimeError(f'future outcome columns present: {bad}')

    # Build the scientific display directly on the frozen 21:00-03:00 eligibility window.
    v04.v01.ny_us = core_ny
    snaps, pools = v04.build_fixed_pools(raw, active, z4)
    displays = v04.sticky_display(raw, snaps, pools)
    pd.DataFrame(candidate_rows(snaps, displays)).to_csv(a.candidates_csv, index=False, compression='gzip')

    # Patch only the Asia session boundary / identity around the final repaired reaction engine.
    asia.asia_ny = core_ny
    asia.asia_session_id = core_session_id
    asia.asia_end = core_end
    asia.asia_subperiod = core_subperiod
    asia.base = final.base
    contacts, trades = asia.run_contacts(raw, z4, snaps, displays)

    cdf = pd.DataFrame(contacts)
    tdf = pd.DataFrame(trades)
    cdf.to_csv(a.contacts_csv, index=False, compression='gzip')
    tdf.to_csv(a.br_csv, index=False, compression='gzip')

    out = {
        'status': 'ASIA_CORE_REACTION_COMPLETE',
        'mode': a.mode,
        'session': '21:00-03:00 America/New_York',
        'cadence': 'C5',
        'architecture': 'Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50',
        'reaction_engine': 'xau_ebuy_reaction_dev_v1_0_3_final_preoutcome',
        'score_used': False,
        'future_reaction_outcomes_used_for_zone_selection': False,
    }

    if a.mode == 'historical':
        results = {}
        for name, lo, hi in [('H1', H1_LO, H1_HI), ('H2', H2_LO, H2_HI)]:
            cc = [x for x in contacts if lo <= pd.Timestamp(x['contact_time']) < hi]
            tt = [x for x in trades if lo <= pd.Timestamp(x['contact_time']) < hi]
            q = summary(cc, tt)
            q['bootstrap_tp1_resolved_rate'] = bootstrap_tp(tt, window_ids(snaps, lo, hi))
            results[name] = q

        h1, h2 = results['H1'], results['H2']
        tp_ratio = ratio(h1['fired_tp_distance_v']['median'], h2['fired_tp_distance_v']['median'])
        width_ratio = ratio(h1['contact_zone_width_v']['median'], h2['contact_zone_width_v']['median'])
        checks = {
            'h1_tp1_rate_ge_030': h1['tp1_resolved_rate'] is not None and h1['tp1_resolved_rate'] >= .30,
            'h2_tp1_rate_ge_030': h2['tp1_resolved_rate'] is not None and h2['tp1_resolved_rate'] >= .30,
            'h1_resolved_share_ge_090': h1['resolved_share'] is not None and h1['resolved_share'] >= .90,
            'h2_resolved_share_ge_090': h2['resolved_share'] is not None and h2['resolved_share'] >= .90,
            'h1_duplicate_guard': h1['duplicate_contact_guard_pass'],
            'h2_duplicate_guard': h2['duplicate_contact_guard_pass'],
            'tp_distance_ratio_075_125': tp_ratio is not None and .75 <= tp_ratio <= 1.25,
            'zone_width_ratio_075_125': width_ratio is not None and .75 <= width_ratio <= 1.25,
        }
        passed = bool(all(checks.values()))
        out.update({
            'status': 'ASIA_CORE_BR_REACTION_PASS' if passed else 'ASIA_CORE_BR_REACTION_FAIL',
            'results': results,
            'geometry_ratios_h2_over_h1': {'fired_tp_distance_median_v': tp_ratio, 'contact_zone_width_median_v': width_ratio},
            'checks': checks,
            'reaction_transfer_pass': passed,
            'production_authorization': 'ASIA_CORE_BR_QA_ONLY_NO_E_SCORE' if passed else 'ASIA_CORE_ZONES_ONLY',
        })
    else:
        if not a.fresh_session_ids_json:
            raise RuntimeError('--fresh-session-ids-json required in fresh mode')
        frozen = json.load(open(a.fresh_session_ids_json))
        ids = set(str(x) for x in frozen['eligible_session_ids'])
        cc = [x for x in contacts if str(x['asia_session_id']) in ids]
        tt = [x for x in trades if str(x['asia_session_id']) in ids]
        q = summary(cc, tt)
        q['bootstrap_tp1_resolved_rate'] = bootstrap_tp(tt, ids)
        out.update({
            'status': 'ASIA_CORE_FRESH_AUG2026_REACTION_COMPLETE',
            'fresh_frozen_session_ids': sorted(ids),
            'fresh_result': q,
            'production_authorization': 'NONE_FRESH_CONFIRMATION_DIAGNOSTIC',
        })

    Path(a.output).write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == '__main__':
    main()
