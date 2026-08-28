#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ENTRY = HERE.parent / 'entry-research'
EPS = 1e-12
WINDOWS = {
    'H1': (pd.Timestamp('2024-08-01T00:00:00Z'), pd.Timestamp('2025-08-01T00:00:00Z')),
    'H2': (pd.Timestamp('2025-08-01T00:00:00Z'), pd.Timestamp('2026-08-01T00:00:00Z')),
}
SESSIONS = {
    'US': '08:00-17:00 America/New_York',
    'ASIA_BROAD': '18:00-03:00 America/New_York',
    'ASIA_CORE_STANDALONE': '21:00-03:00 America/New_York standalone',
    'EUROPE': '03:00-08:00 America/New_York',
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


v04 = load_module('direct_esell_v04', ENTRY / 'xau_ebuy_coverage_v0_4_sticky.py')
v01 = v04.v01


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--session', choices=sorted(SESSIONS), required=True)
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--z4-pkl', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--contacts-csv', required=True)
    p.add_argument('--trades-csv', required=True)
    return p.parse_args()


def in_session(t, name):
    h = pd.Timestamp(t).tz_convert('America/New_York').hour
    if name == 'US':
        return 8 <= h < 17
    if name == 'ASIA_BROAD':
        return h >= 18 or h < 3
    if name == 'ASIA_CORE_STANDALONE':
        return h >= 21 or h < 3
    if name == 'EUROPE':
        return 3 <= h < 8
    raise ValueError(name)


def session_id(t, name):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    if not in_session(t, name):
        return None
    if name in ('ASIA_BROAD', 'ASIA_CORE_STANDALONE') and q.hour < 3:
        return (q.date() - pd.Timedelta(days=1)).isoformat()
    return q.date().isoformat()


def reflect_raw(raw):
    r = raw.copy()
    r['open'] = -raw['open'].astype(float)
    r['high'] = -raw['low'].astype(float)
    r['low'] = -raw['high'].astype(float)
    r['close'] = -raw['close'].astype(float)
    return r


def reflect_z4(z):
    r = z.copy()
    lo = z['zlo'].astype(float).copy()
    hi = z['zhi'].astype(float).copy()
    r['center'] = -z['center'].astype(float)
    r['zlo'] = -hi
    r['zhi'] = -lo
    r['side'] = -z['side'].astype(int)
    return r.sort_values(['time','side','center']).reset_index(drop=True)


def raw_index(raw, t, side='right'):
    arr = raw.time.to_numpy(dtype='datetime64[ns]')
    q = np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None))
    return int(np.searchsorted(arr, q, side=side) - 1)


def build_state_map(raw, z4, snaps, displays, session):
    z4_by = {pd.Timestamp(t): g.copy() for t, g in z4.groupby('time', sort=True)}
    state_for_raw = {}
    states = []
    for s, zs in zip(snaps, displays):
        t = pd.Timestamp(s['time'])
        g = z4_by.get(t)
        if g is None:
            continue
        k = len(states)
        states.append({'time': t, 'snap': s, 'display': list(zs), 'z4': g})
        i0 = raw_index(raw, t, 'right') + 1
        i1 = raw_index(raw, t + pd.Timedelta(minutes=5), 'right')
        for j in range(max(0, i0), min(len(raw)-1, i1) + 1):
            tj = pd.Timestamp(raw.at[j, 'time'])
            if in_session(tj, session) and tj > t and tj <= t + pd.Timedelta(minutes=5):
                state_for_raw[j] = k
    return state_for_raw, states


def orig_zone_from_reflected(z):
    return {
        'zlo': float(-z.zhi),
        'center': float(-z.center),
        'zhi': float(-z.zlo),
        'family': str(z.family),
    }


def orig_z4s_from_reflected(g):
    rows = []
    for _, r in g.iterrows():
        rows.append({
            'zlo': float(-r.zhi),
            'center': float(-r.center),
            'zhi': float(-r.zlo),
            'side': int(-r.side),
        })
    rows.sort(key=lambda x: (x['center'], x['zlo'], x['zhi']))
    return rows


def classify_geometry(e, z4s):
    if not z4s:
        return None
    top = max(z4s, key=lambda x: (x['zhi'], x['center']))
    if e['zlo'] > top['zhi'] + EPS:
        return {
            'geometry': 'ABOVE_HIGHEST_Z4_STRICT',
            'target': top,
            'upper_neighbor': None,
        }
    zs = sorted(z4s, key=lambda x: (x['center'], x['zlo'], x['zhi']))
    for lo, hi in zip(zs[:-1], zs[1:]):
        if e['zlo'] > lo['zhi'] + EPS and e['zhi'] < hi['zlo'] - EPS:
            return {
                'geometry': 'BETWEEN_Z4_STRICT',
                'target': lo,
                'upper_neighbor': hi,
            }
    return None


def bearish_rejection(row):
    rng = float(row.high - row.low)
    cp = float((row.high - row.close) / rng) if rng > 0 else 0.0
    return bool(float(row.close) < float(row.open) and cp >= 0.70), cp


def same_identity(a, b):
    overlap = min(a['zhi'], b['zhi']) >= max(a['zlo'], b['zlo']) - EPS
    tol = 0.25 * max(float(a['v']), float(b['v']))
    return overlap or abs(float(a['center']) - float(b['center'])) <= tol + EPS


def outcome_scan(raw, entry_idx, end_idx, entry, target_zhi, stop_zhi, v):
    status = 'NEITHER'
    terminal_idx = end_idx
    for k in range(entry_idx, end_idx + 1):
        tp = float(raw.at[k, 'low']) <= target_zhi + EPS
        inv = float(raw.at[k, 'close']) > stop_zhi + EPS
        if tp and inv:
            status = 'AMBIGUOUS'; terminal_idx = k; break
        if tp:
            status = 'TP_FIRST'; terminal_idx = k; break
        if inv:
            status = 'INVALIDATION_FIRST'; terminal_idx = k; break
    hs = raw.high.iloc[entry_idx:terminal_idx+1].to_numpy(float)
    ls = raw.low.iloc[entry_idx:terminal_idx+1].to_numpy(float)
    mfe = float(max(0.0, entry - np.min(ls)) / v) if len(ls) else 0.0
    mae = float(max(0.0, np.max(hs) - entry) / v) if len(hs) else 0.0
    return status, terminal_idx, mfe, mae


def wilson(tp, n):
    if not n:
        return [None, None]
    p = tp / n; z = 1.959963984540054
    den = 1 + z*z/n
    c = (p + z*z/(2*n))/den
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return [max(0., c-h), min(1., c+h)]


def diag(df):
    if len(df) == 0:
        return {'executed':0,'terminal_n':0,'TP_FIRST':0,'INVALIDATION_FIRST':0,'NEITHER':0,'AMBIGUOUS':0,
                'terminal_tp_rate':None,'wilson95':[None,None],'expectancy_R_before_costs':None,'profit_factor_R':None}
    c = Counter(df.outcome.astype(str))
    tp = int(c['TP_FIRST']); sl = int(c['INVALIDATION_FIRST']); n = tp + sl
    vals = []
    for _, r in df[df.outcome.isin(['TP_FIRST','INVALIDATION_FIRST'])].iterrows():
        vals.append(float(r.nominal_rr) if r.outcome == 'TP_FIRST' else -1.0)
    pos = float(sum(x for x in vals if x > 0)); neg = float(-sum(x for x in vals if x < 0))
    return {
        'executed': int(len(df)), 'terminal_n': n, 'TP_FIRST': tp, 'INVALIDATION_FIRST': sl,
        'NEITHER': int(c['NEITHER']), 'AMBIGUOUS': int(c['AMBIGUOUS']),
        'terminal_tp_rate': float(tp/n) if n else None, 'wilson95': wilson(tp,n),
        'expectancy_R_before_costs': float(np.mean(vals)) if vals else None,
        'profit_factor_R': float(pos/neg) if neg > 0 else (float('inf') if pos > 0 else None),
    }


def main():
    a = parse_args()
    raw_o = v01.load_raw(a.files)
    raw_r = reflect_raw(raw_o)
    active_r = v01.active_m1(raw_r)
    z4_o = pd.read_pickle(a.z4_pkl).copy()
    z4_o['time'] = pd.to_datetime(z4_o.time, utc=True)
    bad = sorted(v01.FORBIDDEN & set(z4_o.columns))
    if bad:
        raise RuntimeError(f'future outcome columns present in causal Z4 geometry: {bad}')
    z4_r = reflect_z4(z4_o)

    pred = lambda t: in_session(t, a.session)
    v04.v01.ny_us = pred
    snaps, pools = v04.build_fixed_pools(raw_r, active_r, z4_r)
    displays = v04.sticky_display(raw_r, snaps, pools)
    state_for_raw, states = build_state_map(raw_r, z4_r, snaps, displays, a.session)

    sessions = defaultdict(list)
    for j, t in enumerate(raw_o.time):
        sid = session_id(t, a.session)
        if sid is not None:
            sessions[sid].append(j)

    contacts = []
    trades = []

    for sid in sorted(sessions):
        idxs = sessions[sid]
        if not idxs:
            continue
        idxset = set(idxs)
        end_idx = idxs[-1]
        consumed = []

        for j in idxs:
            st = states[state_for_raw[j]] if j in state_for_raw else None
            if st is None:
                continue
            row_o = raw_o.loc[j]
            row_r = raw_r.loc[j]
            t = pd.Timestamp(row_o.time)
            v = float(st['snap']['v'])
            if not np.isfinite(v) or v <= 0:
                continue
            z4s_o = orig_z4s_from_reflected(st['z4'])
            candidates = []

            for rank, zr in enumerate(st['display'], 1):
                eo = orig_zone_from_reflected(zr)
                # Reflected E is below reflected close => original E is above original close.
                if not (eo['center'] > float(row_o.close) + EPS):
                    continue
                geo = classify_geometry(eo, z4s_o)
                if geo is None:
                    continue
                touched = float(row_o.high) >= eo['zlo'] - EPS and float(row_o.low) <= eo['zhi'] + EPS
                if not touched:
                    continue
                br, cp = bearish_rejection(row_o)
                ident = {'zlo':eo['zlo'],'center':eo['center'],'zhi':eo['zhi'],'v':v}
                already = any(same_identity(ident, q) for q in consumed)
                contacts.append({
                    'session_id': sid, 'time': t, 'entry_rank': rank, 'entry_label': f'E{rank}',
                    'family': eo['family'], 'geometry': geo['geometry'],
                    'e_zlo': eo['zlo'], 'e_center': eo['center'], 'e_zhi': eo['zhi'],
                    'target_zlo': geo['target']['zlo'], 'target_center': geo['target']['center'], 'target_zhi': geo['target']['zhi'],
                    'upper_neighbor_zlo': geo['upper_neighbor']['zlo'] if geo['upper_neighbor'] else None,
                    'upper_neighbor_zhi': geo['upper_neighbor']['zhi'] if geo['upper_neighbor'] else None,
                    'v': v, 'bearish_rejection': bool(br), 'down_close_position': cp, 'already_consumed': bool(already),
                })
                if br and not already:
                    candidates.append((rank, eo, geo, ident, cp))

            if not candidates:
                continue
            rank, eo, geo, ident, cp = sorted(candidates, key=lambda x: x[0])[0]
            consumed.append(ident)

            # Target already reached on trigger bar => no executable next-open trade.
            target_zhi = float(geo['target']['zhi'])
            stop_zhi = float(eo['zhi'])
            if float(row_o.low) <= target_zhi + EPS:
                continue
            ex = j + 1
            if ex not in idxset:
                continue
            entry_time = pd.Timestamp(raw_o.at[ex, 'time'])
            entry = float(raw_o.at[ex, 'open'])
            if entry <= target_zhi + EPS or entry >= stop_zhi - EPS:
                continue
            stop_d = stop_zhi - entry
            target_d = entry - target_zhi
            if stop_d <= EPS or target_d <= EPS:
                continue
            rr = target_d / stop_d
            outcome, terminal_idx, mfe, mae = outcome_scan(raw_o, ex, end_idx, entry, target_zhi, stop_zhi, v)
            trades.append({
                'session_id': sid, 'trigger_time': t, 'entry_time': entry_time, 'entry_price': entry,
                'entry_rank': rank, 'entry_label': f'E{rank}', 'family': eo['family'], 'geometry': geo['geometry'],
                'e_zlo': eo['zlo'], 'e_center': eo['center'], 'e_zhi': eo['zhi'],
                'target_zlo': geo['target']['zlo'], 'target_center': geo['target']['center'], 'target_zhi': target_zhi,
                'upper_neighbor_zlo': geo['upper_neighbor']['zlo'] if geo['upper_neighbor'] else None,
                'upper_neighbor_zhi': geo['upper_neighbor']['zhi'] if geo['upper_neighbor'] else None,
                'v_entry_context': v, 'stop_distance_v': stop_d/v, 'target_distance_v': target_d/v,
                'nominal_rr': rr, 'down_close_position': cp,
                'outcome': outcome, 'outcome_time': pd.Timestamp(raw_o.at[terminal_idx, 'time']),
                'mfe_v': mfe, 'mae_v': mae,
                'minutes_entry_to_outcome': float((pd.Timestamp(raw_o.at[terminal_idx,'time']) - entry_time).total_seconds()/60.0),
            })

    cdf = pd.DataFrame(contacts)
    tdf = pd.DataFrame(trades)
    cdf.to_csv(a.contacts_csv, index=False, compression='gzip')
    tdf.to_csv(a.trades_csv, index=False, compression='gzip')

    def summarize(lo, hi):
        if len(tdf):
            q = tdf[(tdf.trigger_time >= lo) & (tdf.trigger_time < hi)].copy()
        else:
            q = tdf.copy()
        if len(cdf):
            cc = cdf[(cdf.time >= lo) & (cdf.time < hi)].copy()
        else:
            cc = cdf.copy()
        by_geo = {g: diag(q[q.geometry == g]) for g in ['BETWEEN_Z4_STRICT','ABOVE_HIGHEST_Z4_STRICT']} if len(q) else {g:diag(q) for g in ['BETWEEN_Z4_STRICT','ABOVE_HIGHEST_Z4_STRICT']}
        by_rank = {r: diag(q[q.entry_label == r]) for r in ['E1','E2','E3']} if len(q) else {r:diag(q) for r in ['E1','E2','E3']}
        inter = {}
        for g in ['BETWEEN_Z4_STRICT','ABOVE_HIGHEST_Z4_STRICT']:
            inter[g] = {r: diag(q[(q.geometry == g) & (q.entry_label == r)]) for r in ['E1','E2','E3']} if len(q) else {r:diag(q) for r in ['E1','E2','E3']}
        return {
            'eligible_touch_events': int(len(cc)),
            'bearish_rejection_touch_events': int(cc.bearish_rejection.astype(bool).sum()) if len(cc) else 0,
            'all': diag(q), 'by_geometry': by_geo, 'by_entry_rank': by_rank, 'geometry_x_rank': inter,
        }

    results = {w: summarize(lo,hi) for w,(lo,hi) in WINDOWS.items()}
    pooled = summarize(WINDOWS['H1'][0], WINDOWS['H2'][1])
    out = {
        'status': 'DIRECT_E123_SELL_BETWEEN_ABOVE_Z4_RETROSPECTIVE_COMPLETE',
        'session_name': a.session, 'session': SESSIONS[a.session],
        'scope': 'SELL_DIRECT_E1_E2_E3_NO_Z4_BREAK_REQUIRED',
        'score_used': False,
        'geometry_primary': ['BETWEEN_Z4_STRICT','ABOVE_HIGHEST_Z4_STRICT'],
        'trigger': 'bearish rejection close<open and (high-close)/(high-low)>=0.70',
        'entry': 'next M1 open in same session',
        'invalidation': 'confirmed M1 close strictly above frozen E upper boundary; wick above allowed',
        'target': 'adjacent lower causal Z4 upper boundary; highest Z4 if E is above highest',
        'one_signal_per_structural_E_identity_per_session': True,
        'results': results, 'pooled': pooled,
        'production_authorization': 'NONE_RETROSPECTIVE_DIRECT_ESELL_RESEARCH',
    }
    Path(a.output).write_text(json.dumps(out, indent=2, default=str, allow_nan=False))
    print(json.dumps({'status':out['status'],'session':a.session,'H1':results['H1'],'H2':results['H2']}, indent=2, default=str, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
