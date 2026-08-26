#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1] / 'entry-research'


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


v01 = load_module('c1_gate_v01', HERE / 'xau_ebuy_coverage_v0_1.py')
v02 = load_module('c1_gate_v02', HERE / 'xau_ebuy_coverage_v0_2.py')
v03 = load_module('c1_gate_v03', HERE / 'xau_ebuy_coverage_v0_3.py')
v04 = load_module('c1_gate_v04', HERE / 'xau_ebuy_coverage_v0_4_sticky.py')
Zone = v01.Zone
FIXED_ESM = 'ESM_BOTH_G120M'
CATS = ('MATCHED_DISPLAY','CROSSED_BELOW','NO_LONGER_LOCAL','UNDERLYING_PRESENT_NOT_DISPLAYED','UNEXPLAINED_DISAPPEARANCE')


def args():
    p = argparse.ArgumentParser()
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--c1-pkl', required=True)
    p.add_argument('--c5-pkl', required=True)
    p.add_argument('--runtime-c1-sec', type=float, default=None)
    p.add_argument('--runtime-c5-sec', type=float, default=None)
    p.add_argument('--side', required=True)
    p.add_argument('--output', required=True)
    return p.parse_args()


def ny_us(t):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    return 8 <= q.hour < 17


def make_eval_times(active, z4, cadence, warmup):
    eligible = active.index[(active.index >= v01.Z4_LOOKBACK - 1) &
                            (active.time.dt.minute % cadence == 0) &
                            (active.time.dt.second == 0)].to_numpy()
    if len(eligible) <= warmup:
        raise RuntimeError(f'too few C{cadence} landmarks')
    warm_cut = int(eligible[warmup - 1])
    z4_by = {pd.Timestamp(t): g.copy() for t, g in z4.groupby('time', sort=True)}
    out = []
    for i in eligible:
        if i < warm_cut:
            continue
        t = pd.Timestamp(active.at[i, 'time'])
        if not ny_us(t):
            continue
        g = z4_by.get(t)
        if g is None or not (g.side == 1).any():
            continue
        v = float(active.at[i, 'v60'])
        if not np.isfinite(v) or v <= 0:
            continue
        close = float(active.at[i, 'close'])
        upper = g[g.side == 1]
        below = g[g.side == -1]
        out.append({
            'active_i': int(i), 'time': t, 'close': close, 'v': v,
            'upper_z4_count': int(len(upper)),
            'nearest_upper_z4_dist_v': float(((upper.center - close) / v).min()),
            'z4_below': [Zone(float(r.center), float(r.zlo), float(r.zhi), 'Z4', 0.0)
                         for _, r in below.iterrows() if 0 < (close - float(r.center)) / v <= 2.0]
        })
    return out


def all_snapshots(active, cadence, warmup):
    idx = active.index[(active.index >= v01.Z4_LOOKBACK - 1) &
                       (active.time.dt.minute % cadence == 0) &
                       (active.time.dt.second == 0)].to_numpy()
    if len(idx) <= warmup:
        return []
    cut = int(idx[warmup - 1])
    out = []
    for i in idx:
        if i < cut:
            continue
        v = float(active.at[i, 'v60'])
        if not np.isfinite(v) or v <= 0:
            continue
        out.append({'active_i': int(i), 'time': pd.Timestamp(active.at[i, 'time']),
                    'close': float(active.at[i, 'close']), 'v': v})
    return out


def raw_index(raw, t, side='right'):
    arr = raw.time.to_numpy(dtype='datetime64[ns]')
    q = np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None))
    return int(np.searchsorted(arr, q, side=side) - 1)


def crossed_below(raw, t0, t1, zlo):
    i0 = raw_index(raw, t0, 'right') + 1
    i1 = raw_index(raw, t1, 'right')
    if i1 < max(0, i0):
        return False
    seg = raw.close.iloc[max(0, i0):i1 + 1].to_numpy(float)
    return bool(len(seg) and np.any(seg < zlo))


def matching(a, b, tol):
    return v01.overlap(a, b) or abs(a.center - b.center) <= tol


def build_fixed(raw, active, z4, cadence, warmup):
    snaps = make_eval_times(active, z4, cadence, warmup)
    all_s = all_snapshots(active, cadence, warmup)
    z4_lists = [s['z4_below'] for s in snaps]
    esm_map = v03.esm_stateful_outputs(raw, active, all_s, 'BOTH', 120, FIXED_ESM)
    esm = [esm_map.get(s['time'], []) for s in snaps]
    epm_events = v02.pivot_base_events(raw, 'M1', 2, raw, active)
    epm = v02.pivot_memory_lists(snaps, epm_events, 8, 'EPM_M1_R2_A8H')
    ewm_map = v02.wick_memory_all_c5(raw, all_s, 60, 'EWM_G60M')
    ewm = [ewm_map.get(s['time'], []) for s in snaps]
    eswing = v02.fixed_swing_lists(raw, snaps)
    pools = [v04.dedup_full_pool(s, z4_lists[i], [esm[i], epm[i], ewm[i], eswing[i]])
             for i, s in enumerate(snaps)]
    return snaps, pools


def sticky_display(raw, snaps, pools, cadence):
    out = []
    prev = []
    prev_s = None
    delta = pd.Timedelta(minutes=cadence)
    for s, pool in zip(snaps, pools):
        cur = []
        remaining = list(pool)
        if prev_s is not None and s['time'] - prev_s['time'] == delta:
            tol = .25 * max(prev_s['v'], s['v'])
            for old in prev:
                if crossed_below(raw, prev_s['time'], s['time'], old.zlo):
                    continue
                d = (s['close'] - old.center) / s['v']
                if not (0 < d <= 2.0):
                    continue
                matches = [(abs(old.center - q.center), j, q) for j, q in enumerate(remaining)
                           if matching(old, q, tol)]
                if matches:
                    _, j, q = min(matches, key=lambda x: (x[0], x[2].family, x[2].center, x[1]))
                    if not any(v01.overlap(q, k) or abs(q.center - k.center) <= .20 * s['v'] for k in cur):
                        cur.append(q)
                    remaining.pop(j)
                if len(cur) >= 3:
                    break
        for q in remaining:
            if len(cur) >= 3:
                break
            if any(v01.overlap(q, k) or abs(q.center - k.center) <= .20 * s['v'] for k in cur):
                continue
            cur.append(q)
        out.append(cur[:3])
        prev = cur[:3]
        prev_s = s
    return out


def metric_pack(snaps, displays, cadence):
    n = len(snaps)
    counts = np.asarray([len(x) for x in displays], float)
    nearest = []
    cover = {b: 0 for b in (1.0, 1.5, 2.0)}
    for s, zs in zip(snaps, displays):
        ds = [(s['close'] - z.center) / s['v'] for z in zs if 0 < (s['close'] - z.center) / s['v'] <= 2.0]
        if ds:
            d = min(ds)
            nearest.append(d)
            for b in cover:
                if d <= b:
                    cover[b] += 1
    na = np.asarray(nearest, float)
    return {
        'eligible_snapshot_count': int(n),
        'zone_count_mean': float(counts.mean()) if n else None,
        'zone_count_median': float(np.median(counts)) if n else None,
        'zone_count_p90': float(np.quantile(counts, .9)) if n else None,
        'coverage': {str(b): float(cover[b] / n) if n else None for b in cover},
        'nearest_distance_v_median': float(np.median(na)) if len(na) else None,
        'nearest_distance_v_p90': float(np.quantile(na, .9)) if len(na) else None,
        'cadence_min': cadence,
    }


def stability(raw, snaps, displays, pools, cadence):
    c = Counter()
    total = 0
    delta = pd.Timedelta(minutes=cadence)
    for i, (s, zs) in enumerate(zip(snaps, displays)):
        if i + 1 >= len(snaps):
            continue
        sn = snaps[i + 1]
        if sn['time'] - s['time'] != delta:
            continue
        nxt = displays[i + 1]
        under = pools[i + 1]
        tol = .25 * max(s['v'], sn['v'])
        for z in zs:
            total += 1
            if any(matching(z, q, tol) for q in nxt):
                cat = 'MATCHED_DISPLAY'
            elif crossed_below(raw, s['time'], sn['time'], z.zlo):
                cat = 'CROSSED_BELOW'
            else:
                d = (sn['close'] - z.center) / sn['v']
                if not (0 < d <= 2.0):
                    cat = 'NO_LONGER_LOCAL'
                elif any(matching(z, q, tol) for q in under):
                    cat = 'UNDERLYING_PRESENT_NOT_DISPLAYED'
                else:
                    cat = 'UNEXPLAINED_DISAPPEARANCE'
            c[cat] += 1
    matched = c['MATCHED_DISPLAY']
    hidden = c['UNDERLYING_PRESENT_NOT_DISPLAYED']
    unexpl = c['UNEXPLAINED_DISAPPEARANCE']
    survival = matched + hidden + unexpl
    return {
        'transition_zone_denominator': int(total),
        'category_counts': {k: int(c[k]) for k in CATS},
        'category_shares': {k: float(c[k] / total) if total else None for k in CATS},
        'raw_display_persistence': float(matched / total) if total else None,
        'survival_aware_display_persistence': float(matched / survival) if survival else None,
        'unexplained_share_of_survival_eligible': float(unexpl / survival) if survival else None,
        'display_churn_share_of_survival_eligible': float(hidden / survival) if survival else None,
    }


def churn(snaps, displays, cadence):
    delta = pd.Timedelta(minutes=cadence)
    next_id = 1
    prev_states = []
    prev_s = None
    episodes = {}
    contiguous_transitions = 0
    births = deaths = rank_changes = matched_total = top1_changes = 0
    center_drift = []
    zlo_drift = []
    zhi_drift = []

    for s, zs in zip(snaps, displays):
        contig = prev_s is not None and s['time'] - prev_s['time'] == delta
        tol = .25 * max(prev_s['v'], s['v']) if contig else 0.0
        cur_states = []
        used_prev = set()
        if contig:
            contiguous_transitions += 1
        for slot, z in enumerate(zs, 1):
            candidates = []
            if contig:
                for j, st in enumerate(prev_states):
                    if j in used_prev:
                        continue
                    if matching(st['zone'], z, tol):
                        candidates.append((abs(st['zone'].center - z.center), j, st))
            if candidates:
                _, j, old = min(candidates, key=lambda x: (x[0], x[1]))
                used_prev.add(j)
                eid = old['id']
                matched_total += 1
                if old['slot'] != slot:
                    rank_changes += 1
                vv = max(float(prev_s['v']), float(s['v']), 1e-12)
                center_drift.append(abs(float(z.center) - float(old['zone'].center)) / vv)
                zlo_drift.append(abs(float(z.zlo) - float(old['zone'].zlo)) / vv)
                zhi_drift.append(abs(float(z.zhi) - float(old['zone'].zhi)) / vv)
                ep = episodes[eid]
                ep['last'] = s['time']
                ep['steps'] += 1
                ep['slots'].add(slot)
            else:
                eid = next_id
                next_id += 1
                births += 1
                episodes[eid] = {'first': s['time'], 'last': s['time'], 'steps': 1, 'slots': {slot}}
            cur_states.append({'id': eid, 'zone': z, 'slot': slot})

        if contig:
            deaths += len(prev_states) - len(used_prev)
            if prev_states and cur_states:
                if not matching(prev_states[0]['zone'], cur_states[0]['zone'], tol):
                    top1_changes += 1
            elif bool(prev_states) != bool(cur_states):
                top1_changes += 1
        prev_states = cur_states
        prev_s = s

    life = np.asarray([ep['steps'] * cadence for ep in episodes.values()], float)

    def qpack(a):
        a = np.asarray(a, float)
        return {
            'median': float(np.median(a)) if len(a) else None,
            'p90': float(np.quantile(a, .9)) if len(a) else None,
            'p95': float(np.quantile(a, .95)) if len(a) else None,
        }

    return {
        'episode_count': int(len(episodes)),
        'episode_lifetime_active_min': qpack(life),
        'contiguous_snapshot_transitions': int(contiguous_transitions),
        'births': int(births),
        'deaths_on_contiguous_transitions': int(deaths),
        'births_per_100_transitions': float(100 * births / contiguous_transitions) if contiguous_transitions else None,
        'deaths_per_100_transitions': float(100 * deaths / contiguous_transitions) if contiguous_transitions else None,
        'matched_display_pairs': int(matched_total),
        'slot_rank_change_share_of_matches': float(rank_changes / matched_total) if matched_total else None,
        'top1_material_change_share': float(top1_changes / contiguous_transitions) if contiguous_transitions else None,
        'matched_center_drift_v': qpack(center_drift),
        'matched_zlo_drift_v': qpack(zlo_drift),
        'matched_zhi_drift_v': qpack(zhi_drift),
    }


def detector_geometry_parity(c1, c5):
    common = sorted(set(pd.to_datetime(c1.time, utc=True)) & set(pd.to_datetime(c5.time, utc=True)))
    bad_counts = 0
    side_mismatch = 0
    center_max = zlo_max = zhi_max = 0.0
    rows = 0
    for t in common:
        a = c1[c1.time == t][['side','center','zlo','zhi']].sort_values(['side','center','zlo','zhi']).reset_index(drop=True)
        b = c5[c5.time == t][['side','center','zlo','zhi']].sort_values(['side','center','zlo','zhi']).reset_index(drop=True)
        if len(a) != len(b):
            bad_counts += 1
            continue
        if not len(a):
            continue
        rows += len(a)
        side_mismatch += int((a.side.to_numpy() != b.side.to_numpy()).sum())
        center_max = max(center_max, float(np.max(np.abs(a.center.to_numpy(float) - b.center.to_numpy(float)))))
        zlo_max = max(zlo_max, float(np.max(np.abs(a.zlo.to_numpy(float) - b.zlo.to_numpy(float)))))
        zhi_max = max(zhi_max, float(np.max(np.abs(a.zhi.to_numpy(float) - b.zhi.to_numpy(float)))))
    passed = bad_counts == 0 and side_mismatch == 0 and center_max <= 1e-12 and zlo_max <= 1e-8 and zhi_max <= 1e-8
    return {
        'common_timestamp_count': len(common), 'compared_rows': int(rows),
        'bad_zone_count_timestamps': int(bad_counts), 'side_mismatch_rows': int(side_mismatch),
        'center_max_abs_error_usd': center_max, 'zlo_max_abs_error_usd': zlo_max, 'zhi_max_abs_error_usd': zhi_max,
        'pass': bool(passed)
    }


def common_display_compare(c1_snaps, c1_disp, c5_snaps, c5_disp):
    m1 = {s['time']: (s, z) for s, z in zip(c1_snaps, c1_disp)}
    m5 = {s['time']: (s, z) for s, z in zip(c5_snaps, c5_disp)}
    common = sorted(set(m1) & set(m5))
    top1 = 0
    both_top1 = 0
    jac = []
    count_diff = []
    for t in common:
        s1, z1 = m1[t]
        s5, z5 = m5[t]
        tol = .25 * max(s1['v'], s5['v'])
        count_diff.append(abs(len(z1) - len(z5)))
        if z1 and z5:
            both_top1 += 1
            if matching(z1[0], z5[0], tol):
                top1 += 1
        used = set()
        matches = 0
        for a in z1:
            cand = [(abs(a.center - b.center), j) for j, b in enumerate(z5) if j not in used and matching(a, b, tol)]
            if cand:
                _, j = min(cand)
                used.add(j)
                matches += 1
        union = len(z1) + len(z5) - matches
        jac.append(matches / union if union else 1.0)
    return {
        'common_eligible_timestamps': len(common),
        'top1_both_present_n': both_top1,
        'top1_geometric_agreement': float(top1 / both_top1) if both_top1 else None,
        'top3_jaccard_mean': float(np.mean(jac)) if jac else None,
        'top3_jaccard_median': float(np.median(jac)) if jac else None,
        'mean_abs_zone_count_difference': float(np.mean(count_diff)) if count_diff else None,
    }


def run_one(raw, active, z4, cadence, warmup):
    snaps, pools = build_fixed(raw, active, z4, cadence, warmup)
    displays = sticky_display(raw, snaps, pools, cadence)
    return snaps, pools, displays, {
        'metrics': metric_pack(snaps, displays, cadence),
        'stability': stability(raw, snaps, displays, pools, cadence),
        'churn': churn(snaps, displays, cadence),
    }


def main():
    a = args()
    raw = v01.load_raw(a.files)
    active = v01.active_m1(raw)
    c1 = pd.read_pickle(a.c1_pkl).copy(); c1['time'] = pd.to_datetime(c1.time, utc=True)
    c5 = pd.read_pickle(a.c5_pkl).copy(); c5['time'] = pd.to_datetime(c5.time, utc=True)
    bad1 = sorted(v01.FORBIDDEN & set(c1.columns)); bad5 = sorted(v01.FORBIDDEN & set(c5.columns))
    # Detector files may contain future outcome columns because they are outputs of the canonical Z4 engine;
    # this runner uses geometry fields only. Explicitly record, never consume, those columns.
    geom1 = c1[['time','side','center','zlo','zhi']].copy()
    geom5 = c5[['time','side','center','zlo','zhi']].copy()

    s1, p1, d1, r1 = run_one(raw, active, geom1, 1, 480)
    s5, p5, d5, r5 = run_one(raw, active, geom5, 5, 96)
    parity = detector_geometry_parity(geom1, geom5)
    common = common_display_compare(s1, d1, s5, d5)
    runtime = {
        'c1_sec': a.runtime_c1_sec, 'c5_sec': a.runtime_c5_sec,
        'c1_over_c5': (a.runtime_c1_sec / a.runtime_c5_sec if a.runtime_c1_sec and a.runtime_c5_sec else None)
    }
    out = {
        'status': 'OUTCOME_BLIND_C1_REFRESH_GATE_COMPLETE' if parity['pass'] else 'NO_INTERPRETATION_GEOMETRY_PARITY_FAIL',
        'study': 'E_BUY_C1_MINUTE_REFRESH_OUTCOME_BLIND_DEV_GATE_V1_0',
        'side': a.side.upper(),
        'source_window': {'start': str(raw.time.min()), 'end': str(raw.time.max())},
        'future_reaction_outcomes_used': False,
        'canonical_z4_future_columns_present_but_not_consumed': {'C1': bad1, 'C5': bad5},
        'warmup_equalized_minutes': 480,
        'C1': r1,
        'C5': r5,
        'common_c1_c5_display': common,
        'detector_common_anchor_geometry_parity': parity,
        'runtime': runtime,
        'explicit_nonclaims': ['No reaction-quality claim','No C1 production promotion','No E-score transfer claim','No Pine authorization']
    }
    Path(a.output).write_text(json.dumps(out, indent=2))
    print(json.dumps({
        'status': out['status'],
        'side': out['side'],
        'C1_snapshots': r1['metrics']['eligible_snapshot_count'],
        'C5_snapshots': r5['metrics']['eligible_snapshot_count'],
        'C1_survival_persistence': r1['stability']['survival_aware_display_persistence'],
        'C5_survival_persistence': r5['stability']['survival_aware_display_persistence'],
        'C1_life_med_min': r1['churn']['episode_lifetime_active_min']['median'],
        'C5_life_med_min': r5['churn']['episode_lifetime_active_min']['median'],
        'C1_top1_change': r1['churn']['top1_material_change_share'],
        'C5_top1_change': r5['churn']['top1_material_change_share'],
        'common_top1_agreement': common['top1_geometric_agreement'],
        'geometry_parity': parity['pass'],
        'runtime_ratio': runtime['c1_over_c5'],
    }, indent=2), flush=True)


if __name__ == '__main__':
    main()
