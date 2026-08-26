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


v01 = load_module('asia_reaction_v01', ENTRY / 'xau_ebuy_coverage_v0_1.py')
base = load_module('asia_reaction_base', ENTRY / 'xau_ebuy_reaction_dev_v1_0.py')
Zone = v01.Zone

WINDOWS = {
    'H1': (pd.Timestamp('2024-08-01T00:00:00Z'), pd.Timestamp('2025-08-01T00:00:00Z')),
    'H2': (pd.Timestamp('2025-08-01T00:00:00Z'), pd.Timestamp('2026-08-01T00:00:00Z')),
}
AMBIG = {'AMBIGUOUS', 'AMBIGUOUS_CONTACT_BAR'}


def args():
    p = argparse.ArgumentParser()
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--z4-pkl', required=True)
    p.add_argument('--candidates-csv', required=True)
    p.add_argument('--gate-result', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--contacts-csv', required=True)
    p.add_argument('--br-csv', required=True)
    return p.parse_args()


def asia_ny(t) -> bool:
    q = pd.Timestamp(t).tz_convert('America/New_York')
    return q.hour >= 18 or q.hour < 3


def asia_session_id(t) -> str:
    q = pd.Timestamp(t).tz_convert('America/New_York')
    d = q.date() if q.hour >= 18 else (q - pd.Timedelta(days=1)).date()
    return d.isoformat()


def asia_end(t):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    if q.hour >= 18:
        d = (q + pd.Timedelta(days=1)).date()
    elif q.hour < 3:
        d = q.date()
    else:
        raise RuntimeError(f'non-Asia timestamp {q}')
    return pd.Timestamp(year=d.year, month=d.month, day=d.day, hour=3, tz='America/New_York').tz_convert('UTC')


def asia_subperiod(t):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    if q.hour >= 18:
        return 'ASIA_EVENING_PRE_MIDNIGHT'
    if q.hour < 3:
        return 'ASIA_POST_MIDNIGHT'
    return 'NON_ASIA'


def raw_index(raw, t, side='right'):
    arr = raw.time.to_numpy(dtype='datetime64[ns]')
    q = np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None))
    return int(np.searchsorted(arr, q, side=side) - 1)


def target_map(z4, snaps):
    by = {pd.Timestamp(t): g for t, g in z4.groupby('time', sort=True)}
    out = {}
    for s in snaps:
        g = by.get(pd.Timestamp(s['time']))
        if g is None:
            continue
        close = float(s['close'])
        u = g[(g.side == 1) & (g.zlo > close)]
        if len(u) == 0:
            u = g[g.side == 1]
        if len(u) == 0:
            continue
        r = u.iloc[int(np.argmin(u.zlo.to_numpy(float) - close))]
        out[pd.Timestamp(s['time'])] = {'center': float(r.center), 'zlo': float(r.zlo), 'zhi': float(r.zhi)}
    return out


def match(a, b, tol):
    return v01.overlap(a, b) or abs(float(a.center) - float(b.center)) <= tol


def next_states(prev_states, prev_s, s, zs, next_id):
    contig = prev_s is not None and pd.Timestamp(s['time']) - pd.Timestamp(prev_s['time']) == pd.Timedelta(minutes=5)
    tol = .25 * max(float(prev_s['v']), float(s['v'])) if contig else 0.0
    used = set(); cur = []
    for slot, z in enumerate(zs, 1):
        cand = []
        if contig:
            for j, old in enumerate(prev_states):
                if j in used:
                    continue
                if match(old['zone'], z, tol):
                    cand.append((abs(float(old['zone'].center) - float(z.center)), j, old))
        if cand:
            _, j, old = min(cand, key=lambda x: (x[0], x[1])); used.add(j)
            st = {
                'id': old['id'], 'age': old['age'] + 1, 'zone': z, 'slot': slot,
                'armed': bool(old['armed']), 'arm_time': old['arm_time'], 'arm_close': old['arm_close'],
                'consumed_session_id': old.get('consumed_session_id'), 'origin_family': old['origin_family'],
            }
        else:
            st = {
                'id': next_id, 'age': 1, 'zone': z, 'slot': slot,
                'armed': False, 'arm_time': None, 'arm_close': None,
                'consumed_session_id': None, 'origin_family': z.family,
            }
            next_id += 1
        cur.append(st)
    return cur, next_id


def qpack(vals):
    a = np.asarray([float(x) for x in vals if x is not None and np.isfinite(float(x))], float)
    return {'median': float(np.median(a)) if len(a) else None,
            'p90': float(np.quantile(a, .9)) if len(a) else None}


def build_displays(snaps, candidates):
    c = candidates.copy(); c['time'] = pd.to_datetime(c.time, utc=True)
    by = {pd.Timestamp(t): g.sort_values('entry_rank') for t, g in c.groupby('time', sort=True)}
    displays = []
    for s in snaps:
        g = by.get(pd.Timestamp(s['time']))
        zs = []
        if g is not None:
            if len(g) > 3:
                raise RuntimeError(f'>3 Asia displayed zones at {s["time"]}')
            for _, r in g.iterrows():
                zs.append(Zone(float(r.center), float(r.zlo), float(r.zhi), str(r.family), 0.0))
        displays.append(zs)
    # Every candidate timestamp must be a valid Asia evaluation snapshot.
    known = {pd.Timestamp(s['time']) for s in snaps}
    extra = sorted(set(pd.to_datetime(c.time, utc=True)) - known)
    if extra:
        raise RuntimeError(f'candidate timestamps outside Asia snapshot chronology: {extra[:5]}')
    return displays


def run_contacts(raw, z4, snaps, displays):
    # Patch only the session end used by the frozen BULL_REJECTION trigger engine.
    base.ny_end = asia_end
    targets = target_map(z4, snaps)
    contacts = []; trades = []
    prev_states = []; prev_s = None; next_id = 1

    for s, zs in zip(snaps, displays):
        t = pd.Timestamp(s['time'])
        states, next_id = next_states(prev_states, prev_s, s, zs, next_id)
        sid = asia_session_id(t)

        for st in states:
            z = st['zone']
            if not st['armed'] and float(s['close']) > float(z.zhi):
                st['armed'] = True; st['arm_time'] = t; st['arm_close'] = float(s['close'])

        tp = targets.get(t)
        end = min(t + pd.Timedelta(minutes=5), asia_end(t))
        i0 = raw_index(raw, t, 'right') + 1
        i1 = raw_index(raw, end - pd.Timedelta(nanoseconds=1), 'right')
        if tp is not None and i1 >= i0:
            for st in states:
                if st.get('consumed_session_id') == sid:
                    continue
                z = st['zone']; contact_idx = None
                for j in range(max(0, i0), min(len(raw) - 1, i1) + 1):
                    rr = raw.loc[j]
                    if not st['armed']:
                        if float(rr.close) > float(z.zhi):
                            st['armed'] = True; st['arm_time'] = pd.Timestamp(rr.time); st['arm_close'] = float(rr.close)
                        continue
                    if float(rr.high) >= float(z.zlo) and float(rr.low) <= float(z.zhi):
                        contact_idx = j; break
                if contact_idx is None:
                    continue

                ct = pd.Timestamp(raw.at[contact_idx, 'time'])
                contact_sid = asia_session_id(ct)
                st['consumed_session_id'] = contact_sid
                v = float(s['v']); rr = raw.loc[contact_idx]
                width = max(float(z.zhi) - float(z.zlo), 1e-12)
                rec = {
                    'episode_id': int(st['id']), 'state_time': t, 'contact_time': ct,
                    'asia_session_id': contact_sid, 'family': z.family, 'episode_origin_family': st['origin_family'],
                    'slot_rank': int(st['slot']), 'episode_age_c5': int(st['age']),
                    'zlo': float(z.zlo), 'center': float(z.center), 'zhi': float(z.zhi),
                    'zone_width_v': float(width / v), 'v_contact': v,
                    'arm_time': st['arm_time'], 'arm_close': st['arm_close'],
                    'tp1_zlo': float(tp['zlo']), 'tp1_center': float(tp['center']), 'tp1_zhi': float(tp['zhi']),
                    'tp1_distance_from_touch_ref_v': float((float(tp['zlo']) - float(z.zhi)) / v),
                    'minutes_to_asia_end': float((asia_end(ct) - ct).total_seconds() / 60.0),
                    'asia_subperiod': asia_subperiod(ct),
                    'contact_bull': int(float(rr.close) > float(rr.open)),
                }
                contacts.append(rec)
                ej = raw_index(raw, asia_end(ct) - pd.Timedelta(nanoseconds=1), 'right')
                outcome = base.trigger_outcome(raw, contact_idx, ej, z, tp, v, 'BULL_REJECTION')
                trades.append({**rec, **outcome})

        prev_states = states; prev_s = s
    return contacts, trades


def stratify(contacts, trades, field):
    out = {}
    for val in sorted({str(x[field]) for x in contacts}):
        cc = [x for x in contacts if str(x[field]) == val]
        tt = [x for x in trades if str(x[field]) == val and bool(x.get('fired'))]
        if len(cc) < 100:
            out[val] = {'sparse': True, 'contact_count': len(cc), 'fired_count': len(tt)}
            continue
        c = Counter(str(x.get('tp1_invalidation_status')) for x in tt)
        amb = sum(c[k] for k in AMBIG); res = len(tt) - amb
        out[val] = {
            'sparse': False, 'contact_count': len(cc), 'fired_count': len(tt),
            'fired_share': float(len(tt) / len(cc)) if cc else None,
            'tp1_resolved_rate': float(c['TP1_FIRST'] / res) if res else None,
        }
    return out


def summarize(contacts, trades):
    fired = [x for x in trades if bool(x.get('fired'))]
    c = Counter(str(x.get('tp1_invalidation_status')) for x in fired)
    amb = sum(c[k] for k in AMBIG); res = len(fired) - amb
    sessions = sorted({x['asia_session_id'] for x in contacts})

    def elapsed(field):
        vals = []
        for x in fired:
            if not x.get(field) or not x.get('exec_time'):
                continue
            vals.append((pd.Timestamp(x[field]) - pd.Timestamp(x['exec_time'])).total_seconds() / 60.0)
        return qpack(vals)

    return {
        'contact_episode_count': int(len(contacts)),
        'unique_contact_episode_ids': int(len({int(x['episode_id']) for x in contacts})),
        'asia_session_count': int(len(sessions)),
        'contacts_per_asia_session': float(len(contacts) / len(sessions)) if sessions else None,
        'bull_rejection_fired_count': int(len(fired)),
        'bull_rejection_fired_share': float(len(fired) / len(contacts)) if contacts else None,
        'bull_rejection_fired_per_asia_session': float(len(fired) / len(sessions)) if sessions else None,
        'TP1_FIRST': int(c['TP1_FIRST']), 'INVALIDATION_FIRST': int(c['INVALIDATION_FIRST']),
        'NEITHER': int(c['NEITHER']), 'AMBIGUOUS': int(amb),
        'resolved_denominator': int(res),
        'tp1_resolved_rate': float(c['TP1_FIRST'] / res) if res else None,
        'invalidation_resolved_rate': float(c['INVALIDATION_FIRST'] / res) if res else None,
        'neither_resolved_rate': float(c['NEITHER'] / res) if res else None,
        'contact_zone_width_v': qpack([x['zone_width_v'] for x in contacts]),
        'contact_tp_distance_v': qpack([x['tp1_distance_from_touch_ref_v'] for x in contacts]),
        'fired_tp_distance_v': qpack([x.get('tp_distance_v') for x in fired]),
        'time_to_tp1_min': elapsed('tp1_time'),
        'time_to_invalidation_min': elapsed('invalidation_time'),
        'by_origin_family': stratify(contacts, trades, 'episode_origin_family'),
        'by_asia_subperiod': stratify(contacts, trades, 'asia_subperiod'),
    }


def main():
    a = args()
    gate = json.load(open(a.gate_result))
    if gate.get('status') != 'ASIA_C5_OUTCOME_BLIND_LOCATION_GATE_PASS' or gate.get('reaction_study_authorized') is not True:
        raise RuntimeError(f'Asia reaction gate not authorized: {gate.get("status")}')

    raw = v01.load_raw(a.files); active = v01.active_m1(raw)
    z4 = pd.read_pickle(a.z4_pkl).copy(); z4['time'] = pd.to_datetime(z4.time, utc=True)
    bad = sorted(v01.FORBIDDEN & set(z4.columns))
    if bad:
        raise RuntimeError(f'future outcome columns present: {bad}')

    v01.ny_us = asia_ny
    snaps = v01.make_eval_times(active, z4)
    candidates = pd.read_csv(a.candidates_csv, low_memory=False)
    displays = build_displays(snaps, candidates)
    contacts, trades = run_contacts(raw, z4, snaps, displays)

    cdf = pd.DataFrame(contacts); tdf = pd.DataFrame(trades)
    if len(cdf): cdf.to_csv(a.contacts_csv, index=False, compression='gzip')
    else: pd.DataFrame().to_csv(a.contacts_csv, index=False, compression='gzip')
    if len(tdf): tdf.to_csv(a.br_csv, index=False, compression='gzip')
    else: pd.DataFrame().to_csv(a.br_csv, index=False, compression='gzip')

    results = {}
    for w, (lo, hi) in WINDOWS.items():
        wc = [x for x in contacts if lo <= pd.Timestamp(x['contact_time']) < hi]
        wt = [x for x in trades if lo <= pd.Timestamp(x['contact_time']) < hi]
        results[w] = summarize(wc, wt)

    # Coherence is descriptive only; no score or production promotion is automatic.
    rates = [results[w]['tp1_resolved_rate'] for w in ('H1', 'H2')]
    out = {
        'status': 'ASIA_C5_BULL_REJECTION_REACTION_COMPLETE',
        'scope': 'BUY_ONLY_C5_ASIA_18_03_NY_BULL_REJECTION',
        'session_definition': '18:00-03:00 America/New_York',
        'window_assignment': 'continuous 24M episode state; H1/H2 assigned by contact timestamp',
        'score_used': False,
        'model_refit': False,
        'results': results,
        'h1_h2_tp_rate_same_direction_relative_to_us_frozen': None,
        'production_authorization': 'NONE_RETROSPECTIVE_SENSITIVITY_ONLY',
    }
    Path(a.output).write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({
        'status': out['status'],
        'H1': results['H1'],
        'H2': results['H2'],
    }, indent=2, default=str), flush=True)


if __name__ == '__main__':
    main()
