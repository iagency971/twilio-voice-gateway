#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ENTRY = ROOT / 'entry-research'


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


v01 = load_module('prov_v01', ENTRY / 'xau_ebuy_coverage_v0_1.py')
v02 = load_module('prov_v02', ENTRY / 'xau_ebuy_coverage_v0_2.py')
v03 = load_module('prov_v03', ENTRY / 'xau_ebuy_coverage_v0_3.py')
v04 = load_module('prov_v04', ENTRY / 'xau_ebuy_coverage_v0_4_sticky.py')

FIXED_ESM = 'ESM_BOTH_G120M'
EPM_CONFIG = 'EPM_M1_R2_A8H'
EWM_CONFIG = 'EWM_G60M'
ES_CONFIG = 'ES_M1_8H_R2_T0.50'


@dataclass(frozen=True)
class PZone:
    center: float
    zlo: float
    zhi: float
    family: str
    rank: float
    source_provenance_id: str
    source_provenance_members: tuple[str, ...] = ()


def sid(prefix: str, *parts) -> str:
    payload = '|'.join(str(x) for x in parts)
    return prefix + ':' + hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]


def ts(x) -> str:
    return pd.Timestamp(x).tz_convert('UTC').isoformat()


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--z4-pkl', required=True)
    p.add_argument('--output-csv', required=True)
    p.add_argument('--manifest', required=True)
    p.add_argument('--reference-v04-csv')
    return p.parse_args()


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


def z4_provenance_lists(snaps, z4):
    z = z4.copy()
    z['time'] = pd.to_datetime(z['time'], utc=True)
    by = {pd.Timestamp(t): g for t, g in z.groupby('time', sort=True)}
    out = []
    for s in snaps:
        g = by.get(pd.Timestamp(s['time']))
        cur = []
        if g is not None:
            for _, r in g[g.side == -1].iterrows():
                c = float(r.center); lo = float(r.zlo); hi = float(r.zhi)
                if 0 < (s['close'] - c) / s['v'] <= 2.0:
                    landmark = int(r.landmark_i) if 'landmark_i' in r else -1
                    pid = sid('Z4', ts(s['time']), landmark, c, lo, hi, -1)
                    cur.append(PZone(c, lo, hi, 'Z4', 0.0, pid, (pid,)))
        out.append(cur)
    return out


def esm_outputs_with_ids(raw, active, all_c5):
    states = []
    outputs = {}
    prev_t = None
    grace = pd.Timedelta(minutes=120)
    birth_seq = 0
    for s in all_c5:
        t = s['time']; close = s['close']; v = s['v']
        if prev_t is None:
            seg = np.array([], dtype=float)
        else:
            i0 = v03.raw_index(raw, prev_t) + 1
            i1 = v03.raw_index(raw, t)
            seg = raw.close.iloc[max(0, i0):i1 + 1].to_numpy(float) if i1 >= max(0, i0) else np.array([], dtype=float)
        kept = []
        for st in states:
            if t - st['last_seen'] > grace:
                continue
            if len(seg) and np.any(seg < st['zone'].zlo):
                continue
            kept.append(st)
        states = kept

        observations = v03.structure_observations(active, s, 'BOTH', FIXED_ESM)
        matched_states = set()
        for z in observations:
            candidates = []
            for j, st in enumerate(states):
                if j in matched_states:
                    continue
                q = st['zone']
                if v01.overlap(z, q) or abs(z.center - q.center) <= 0.20 * v:
                    candidates.append((abs(z.center - q.center), j))
            if candidates:
                _, j = min(candidates, key=lambda x: (x[0], x[1]))
                old = states[j]
                pz = PZone(float(z.center), float(z.zlo), float(z.zhi), FIXED_ESM, float(z.rank), old['id'], (old['id'],))
                states[j] = {'zone': pz, 'last_seen': t, 'id': old['id']}
                matched_states.add(j)
            else:
                birth_seq += 1
                pid = sid('ESM', birth_seq, ts(t), z.center, z.zlo, z.zhi)
                pz = PZone(float(z.center), float(z.zlo), float(z.zhi), FIXED_ESM, float(z.rank), pid, (pid,))
                states.append({'zone': pz, 'last_seen': t, 'id': pid})
                matched_states.add(len(states) - 1)
        current = []
        for st in states:
            z = st['zone']; dist = (close - z.center) / v
            if 0 < dist <= 2.0:
                current.append(z)
        current.sort(key=lambda z: (close - z.center, z.center, z.zlo, z.zhi))
        outputs[t] = current[:3]
        prev_t = t
    return outputs


def epm_base_events_with_ids(raw, active):
    piv = v01.pivot_records(raw, 2)
    rt = raw.time.to_numpy(dtype='datetime64[ns]')
    cl = raw.close.to_numpy(float)
    events = []
    for pi, ci, low in piv:
        pi = int(pi); ci = int(ci); low = float(low)
        pivot_time = pd.Timestamp(raw.at[pi, 'time'])
        confirm = pd.Timestamp(raw.at[ci, 'time'])
        vc = v02.latest_v(active, confirm)
        if vc is None:
            continue
        zlo = low - .10 * vc; zhi = low + .20 * vc
        q = np.datetime64(confirm.tz_convert('UTC').tz_localize(None))
        start = int(np.searchsorted(rt, q, side='right') - 1)
        if start < 0:
            continue
        end = min(len(raw), start + 8 * 60 + 2)
        bad = np.where(cl[start + 1:end] < zlo)[0]
        invalid = pd.Timestamp(raw.at[start + 1 + int(bad[0]), 'time']) if len(bad) else None
        pid = sid('EPM', 'M1', 2, pi, ci, ts(pivot_time), ts(confirm), low, zlo, zhi)
        events.append({'start': confirm, 'center': low, 'zlo': zlo, 'zhi': zhi, 'invalid': invalid, 'id': pid})
    events.sort(key=lambda e: e['start'])
    return events


def epm_lists_with_ids(eval_snaps, events):
    out = []
    cap = pd.Timedelta(hours=8)
    if not events:
        return [[] for _ in eval_snaps]
    starts_ns = pd.DatetimeIndex([e['start'] for e in events]).view('int64')
    for s in eval_snaps:
        t = s['time']; close = s['close']; v = s['v']; zs = []
        tns = int(pd.Timestamp(t).value); lns = int((pd.Timestamp(t) - cap).value)
        lo = int(np.searchsorted(starts_ns, lns, side='left'))
        hi = int(np.searchsorted(starts_ns, tns, side='right'))
        for e in events[lo:hi]:
            if e['invalid'] is not None and e['invalid'] <= t:
                continue
            dist = (close - e['center']) / v
            if not (0 < dist <= 2.0):
                continue
            age_hours = max(0., (t - e['start']).total_seconds() / 3600.)
            rank = 1. / ((1. + dist) * (1. + age_hours / 8.))
            zs.append(PZone(float(e['center']), float(e['zlo']), float(e['zhi']), EPM_CONFIG, float(rank), e['id'], (e['id'],)))
        zs.sort(key=lambda z: (-z.rank, close - z.center, z.center))
        out.append(zs[:3])
    return out


def ewm_outputs_with_ids(raw, all_c5):
    states = []
    outputs = {}
    prev_t = None
    grace = pd.Timedelta(minutes=60)
    birth_seq = 0
    for s in all_c5:
        t = s['time']; close = s['close']; v = s['v']
        if prev_t is not None:
            i0 = max(0, v02.raw_index(raw, prev_t, 'right') + 1)
            i1 = v02.raw_index(raw, t, 'right')
            seg = raw.close.iloc[i0:i1 + 1].to_numpy(float) if i1 >= i0 else np.array([], float)
        else:
            seg = np.array([], float)
        kept = []
        for st in states:
            if t - st['last_seen'] > grace:
                continue
            if len(seg) and np.any(seg < st['zone'].zlo):
                continue
            kept.append(st)
        states = kept
        ei = v01.source_index_at_snapshot('M1', raw, t)
        det = [] if ei < 0 else v01.wick_candidates(raw, ei, 480, .25, close, v, 'EW_M1_8H_S0.25')
        for z in det:
            matches = []
            for j, st in enumerate(states):
                if v01.overlap(z, st['zone']) or abs(z.center - st['zone'].center) <= .25 * v:
                    matches.append((abs(z.center - st['zone'].center), j))
            if matches:
                _, j = min(matches)
                old = states[j]
                pz = PZone(float(z.center), float(z.zlo), float(z.zhi), EWM_CONFIG, float(z.rank), old['id'], (old['id'],))
                states[j] = {'zone': pz, 'last_seen': t, 'id': old['id']}
            else:
                birth_seq += 1
                pid = sid('EWM', birth_seq, ts(t), z.center, z.zlo, z.zhi)
                pz = PZone(float(z.center), float(z.zlo), float(z.zhi), EWM_CONFIG, float(z.rank), pid, (pid,))
                states.append({'zone': pz, 'last_seen': t, 'id': pid})
        zs = []
        for st in states:
            z = st['zone']; dist = (close - z.center) / v
            if 0 < dist <= 2.0:
                zs.append(z)
        zs.sort(key=lambda z: (close - z.center, z.center))
        outputs[t] = zs[:3]
        prev_t = t
    return outputs


def es_lists_with_ids(raw, eval_snaps):
    piv = v01.pivot_records(raw, 2)
    out = []
    for s in eval_snaps:
        end_idx = v01.source_index_at_snapshot('M1', raw, s['time'])
        close = s['close']; v = s['v']; window = 480; tol = .50 * v
        if end_idx < 0 or len(piv) == 0:
            out.append([]); continue
        lo_i = max(0, end_idx - window + 1)
        m = (piv[:, 1] <= end_idx) & (piv[:, 0] >= lo_i)
        rows = piv[m]
        rows = rows[(rows[:, 2] < close) & (rows[:, 2] >= close - 2 * v)]
        if len(rows) < 2:
            out.append([]); continue
        rows = rows[np.argsort(rows[:, 2], kind='mergesort')]
        clusters = []
        cur = [rows[0]]
        for r in rows[1:]:
            if float(r[2]) - float(cur[-1][2]) <= tol + v01.EPS:
                cur.append(r)
            else:
                clusters.append(cur); cur = [r]
        clusters.append(cur)
        zs = []
        for cl in clusters:
            if len(cl) < 2:
                continue
            vals = [float(r[2]) for r in cl]
            center = float(np.median(vals)); dist = (close - center) / v
            if not (0 < dist <= 2.0):
                continue
            zlo = float(min(vals) - .10 * v); zhi = float(max(vals) + .10 * v)
            if center >= close:
                continue
            rank = len(vals) / (1. + dist)
            members = tuple(sorted(sid('ESPIV', int(r[0]), int(r[1]), float(r[2])) for r in cl))
            pid = sid('ESSET', *members)
            zs.append(PZone(center, zlo, zhi, ES_CONFIG, float(rank), pid, members))
        zs.sort(key=lambda z: (-z.rank, close - z.center, z.center))
        out.append(zs[:3])
    return out


def dedup_full_pool(s, z4_list, families):
    close = s['close']; v = s['v']
    z4 = [z for z in z4_list if 0 < (close - z.center) / v <= 2.0]
    supp = []
    for fam in families:
        supp.extend(z for z in fam if 0 < (close - z.center) / v <= 2.0)
    z4.sort(key=lambda z: (close - z.center, z.center))
    supp.sort(key=lambda z: (close - z.center, z.family, z.center))
    kept = []
    for z in z4 + supp:
        if any(v01.overlap(z, q) or abs(z.center - q.center) <= .20 * v for q in kept):
            continue
        kept.append(z)
    kept.sort(key=lambda z: (close - z.center, 0 if z.family == 'Z4' else 1, z.family, z.center))
    return kept


def sticky_display(raw, snaps, pools):
    out = []
    prev = []; prev_s = None
    for s, pool in zip(snaps, pools):
        cur = []; remaining = list(pool)
        if prev_s is not None and s['time'] - prev_s['time'] == pd.Timedelta(minutes=5):
            tol = .25 * max(prev_s['v'], s['v'])
            for old in prev:
                if crossed_below(raw, prev_s['time'], s['time'], old.zlo):
                    continue
                d = (s['close'] - old.center) / s['v']
                if not (0 < d <= 2.0):
                    continue
                matches = [(abs(old.center - q.center), j, q) for j, q in enumerate(remaining) if matching(old, q, tol)]
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
        prev = cur[:3]; prev_s = s
    return out


def build(raw, active, z4):
    snaps = v01.make_eval_times(active, z4)
    all_c5 = v02.all_c5_snapshots(active)
    z4_lists = z4_provenance_lists(snaps, z4)
    esm_map = esm_outputs_with_ids(raw, active, all_c5)
    esm = [esm_map.get(s['time'], []) for s in snaps]
    epm = epm_lists_with_ids(snaps, epm_base_events_with_ids(raw, active))
    ewm_map = ewm_outputs_with_ids(raw, all_c5)
    ewm = [ewm_map.get(s['time'], []) for s in snaps]
    es = es_lists_with_ids(raw, snaps)
    pools = [dedup_full_pool(s, z4_lists[i], [esm[i], epm[i], ewm[i], es[i]]) for i, s in enumerate(snaps)]
    return snaps, sticky_display(raw, snaps, pools)


def rows_from(snaps, displays):
    rows = []
    for s, zs in zip(snaps, displays):
        for rank, z in enumerate(zs, 1):
            rows.append({
                'time': s['time'], 'close': s['close'], 'v60': s['v'],
                'upper_z4_count': s['upper_z4_count'], 'nearest_upper_z4_dist_v': s['nearest_upper_z4_dist_v'],
                'entry_rank': rank, 'family': z.family, 'center': z.center, 'zlo': z.zlo, 'zhi': z.zhi,
                'distance_v': (s['close'] - z.center) / s['v'],
                'source_provenance_id': z.source_provenance_id,
                'source_provenance_members': ';'.join(z.source_provenance_members),
            })
    return pd.DataFrame(rows)


def parity(reference_path, got):
    ref = pd.read_csv(reference_path, compression='infer')
    ref['time'] = pd.to_datetime(ref['time'], utc=True)
    g = got.copy(); g['time'] = pd.to_datetime(g['time'], utc=True)
    cols = ['time', 'close', 'v60', 'upper_z4_count', 'nearest_upper_z4_dist_v', 'entry_rank', 'family', 'center', 'zlo', 'zhi', 'distance_v']
    if len(ref) != len(g):
        return {'pass': False, 'reason': 'row_count', 'reference_rows': len(ref), 'instrumented_rows': len(g)}
    bad = {}
    for c in cols:
        if c in ('family',):
            neq = ref[c].astype(str).to_numpy() != g[c].astype(str).to_numpy()
        elif c == 'time':
            neq = ref[c].to_numpy() != g[c].to_numpy()
        elif c in ('entry_rank', 'upper_z4_count'):
            neq = ref[c].to_numpy() != g[c].to_numpy()
        else:
            neq = ~np.isclose(ref[c].to_numpy(float), g[c].to_numpy(float), rtol=0.0, atol=1e-12, equal_nan=True)
        n = int(np.sum(neq))
        if n:
            bad[c] = n
    return {'pass': not bad, 'reference_rows': len(ref), 'instrumented_rows': len(g), 'mismatch_counts': bad}


def main():
    a = parse_args()
    raw = v01.load_raw(a.files)
    active = v01.active_m1(raw)
    z4 = pd.read_pickle(a.z4_pkl).copy(); z4['time'] = pd.to_datetime(z4.time, utc=True)
    bad = sorted(v01.FORBIDDEN & set(z4.columns))
    if bad:
        raise RuntimeError(f'future outcome columns present in Z4 input: {bad}')
    snaps, displays = build(raw, active, z4)
    df = rows_from(snaps, displays)
    Path(a.output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.output_csv, index=False, compression={'method': 'gzip', 'mtime': 0})
    pq = parity(a.reference_v04_csv, df) if a.reference_v04_csv else None
    if pq is not None and not pq['pass']:
        raise RuntimeError(f'V04_GEOMETRY_PARITY_FAIL {pq}')
    fam = df['family'].value_counts().sort_index().to_dict() if len(df) else {}
    manifest = {
        'status': 'E_PROVENANCE_INSTRUMENT_V1_PASS',
        'future_price_outcomes_used': False,
        'architecture': 'Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50',
        'rows': int(len(df)), 'snapshots': int(df['time'].nunique()) if len(df) else 0,
        'first_snapshot_utc': str(df['time'].min()) if len(df) else None,
        'last_snapshot_utc': str(df['time'].max()) if len(df) else None,
        'family_counts': {str(k): int(v) for k, v in fam.items()},
        'geometry_parity': pq,
        'real_outcome_authorization': 'FORBIDDEN_PENDING_NEW_PRO_GATE'
    }
    Path(a.manifest).write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
