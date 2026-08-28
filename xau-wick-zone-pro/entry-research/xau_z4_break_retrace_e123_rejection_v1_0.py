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
EPS = 1e-12
WINDOWS = {
    'H1': (pd.Timestamp('2024-08-01T00:00:00Z'), pd.Timestamp('2025-08-01T00:00:00Z')),
    'H2': (pd.Timestamp('2025-08-01T00:00:00Z'), pd.Timestamp('2026-08-01T00:00:00Z')),
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


v01 = load_module('z4br_e123_v01', HERE / 'xau_ebuy_coverage_v0_1.py')
v04 = load_module('z4br_e123_v04', HERE / 'xau_ebuy_coverage_v0_4_sticky.py')
Zone = v01.Zone


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--z4-pkl', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--episodes-csv', required=True)
    p.add_argument('--contacts-csv', required=True)
    p.add_argument('--trades-csv', required=True)
    return p.parse_args()


def raw_index(raw, t, side='right'):
    arr = raw.time.to_numpy(dtype='datetime64[ns]')
    q = np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None))
    return int(np.searchsorted(arr, q, side=side) - 1)


def is_us(t):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    return 8 <= q.hour < 17


def us_session_id(t):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    return q.date().isoformat() if 8 <= q.hour < 17 else None


def qpack(vals):
    a = np.asarray([float(x) for x in vals if x is not None and np.isfinite(float(x))], float)
    if not len(a):
        return {'n': 0, 'median': None, 'p90': None}
    return {'n': int(len(a)), 'median': float(np.median(a)), 'p90': float(np.quantile(a, .90))}


def zone_relation(z, main):
    zl, zh = float(z.zlo), float(z.zhi)
    ml, mh = float(main['main_zlo']), float(main['main_zhi'])
    if zl >= ml - EPS and zh <= mh + EPS:
        return 'INSIDE_MAIN'
    if zl > mh + EPS:
        return 'ABOVE_MAIN'
    if zh < ml - EPS:
        return 'BELOW_MAIN'
    return 'OVERLAP_MAIN'


def same_structural_zone(ep, r, vcur):
    overlap = min(float(ep['main_zhi']), float(r.zhi)) >= max(float(ep['main_zlo']), float(r.zlo)) - EPS
    tol = .25 * max(float(ep['v_breakout']), float(vcur))
    return overlap or abs(float(ep['main_center']) - float(r.center)) <= tol + EPS


def bull_rejection(row):
    rng = float(row.high - row.low)
    cp = float((row.close - row.low) / rng) if rng > 0 else 0.0
    return bool(float(row.close) > float(row.open) and cp >= .70), cp


def summarize_outcomes(trades):
    c = Counter(str(x['outcome']) for x in trades)
    amb = int(c['AMBIGUOUS'])
    resolved_den = int(c['TP_FIRST'] + c['INVALIDATION_FIRST'] + c['NEITHER'])
    terminal_den = int(c['TP_FIRST'] + c['INVALIDATION_FIRST'])
    return {
        'executed_trades': int(len(trades)),
        'TP_FIRST': int(c['TP_FIRST']),
        'INVALIDATION_FIRST': int(c['INVALIDATION_FIRST']),
        'NEITHER': int(c['NEITHER']),
        'AMBIGUOUS': amb,
        'resolved_denominator_ex_ambiguous': resolved_den,
        'tp_rate_ex_ambiguous_including_neither': float(c['TP_FIRST'] / resolved_den) if resolved_den else None,
        'terminal_denominator_tp_or_invalidation': terminal_den,
        'terminal_tp_rate': float(c['TP_FIRST'] / terminal_den) if terminal_den else None,
        'stop_distance_v': qpack([x.get('stop_distance_v') for x in trades]),
        'target_distance_v': qpack([x.get('target_distance_v') for x in trades]),
        'nominal_rr': qpack([x.get('nominal_rr') for x in trades]),
        'mfe_v': qpack([x.get('mfe_v') for x in trades]),
        'mae_v': qpack([x.get('mae_v') for x in trades]),
    }


def stratify(contacts, trades, field):
    vals = sorted({str(x[field]) for x in contacts} | {str(x[field]) for x in trades})
    out = {}
    for val in vals:
        cc = [x for x in contacts if str(x[field]) == val]
        tt = [x for x in trades if str(x[field]) == val]
        o = summarize_outcomes(tt)
        o['contact_events'] = int(len(cc))
        o['bull_rejection_contact_events'] = int(sum(bool(x.get('bull_rejection')) for x in cc))
        o['fired_share_per_contact_event'] = float(len(tt) / len(cc)) if cc else None
        out[val] = o
    return out


def outcome_scan(raw, entry_idx, end_idx, ep, entry_price, v):
    target = float(ep['target_zlo']); stop = float(ep['main_zlo'])
    status = 'NEITHER'; terminal_idx = end_idx
    for k in range(entry_idx, end_idx + 1):
        tp = float(raw.at[k, 'high']) >= target - EPS
        inv = float(raw.at[k, 'close']) < stop - EPS
        if tp and inv:
            status = 'AMBIGUOUS'; terminal_idx = k; break
        if tp:
            status = 'TP_FIRST'; terminal_idx = k; break
        if inv:
            status = 'INVALIDATION_FIRST'; terminal_idx = k; break
    h = raw.high.iloc[entry_idx:terminal_idx + 1].to_numpy(float)
    l = raw.low.iloc[entry_idx:terminal_idx + 1].to_numpy(float)
    mfe = float(max(0.0, np.max(h) - entry_price) / v) if len(h) else 0.0
    mae = float(max(0.0, entry_price - np.min(l)) / v) if len(l) else 0.0
    return status, terminal_idx, mfe, mae


def build_state_map(raw, z4, snaps, displays):
    z4_by = {pd.Timestamp(t): g.copy() for t, g in z4.groupby('time', sort=True)}
    state_for_raw = {}
    state_records = []
    for s, zs in zip(snaps, displays):
        t = pd.Timestamp(s['time'])
        g = z4_by.get(t)
        if g is None:
            continue
        rec = {'time': t, 'snap': s, 'display': zs, 'z4': g}
        k = len(state_records); state_records.append(rec)
        i0 = raw_index(raw, t, 'right') + 1
        i1 = raw_index(raw, t + pd.Timedelta(minutes=5), 'right')
        if i1 < i0:
            continue
        for j in range(max(0, i0), min(len(raw) - 1, i1) + 1):
            tj = pd.Timestamp(raw.at[j, 'time'])
            if is_us(tj) and tj > t and tj <= t + pd.Timedelta(minutes=5):
                state_for_raw[j] = k
    return state_for_raw, state_records


def main():
    a = parse_args()
    raw = v01.load_raw(a.files)
    active = v01.active_m1(raw)
    z4 = pd.read_pickle(a.z4_pkl).copy()
    z4['time'] = pd.to_datetime(z4.time, utc=True)
    bad = sorted(v01.FORBIDDEN & set(z4.columns))
    if bad:
        raise RuntimeError(f'future outcome columns present in causal Z4 geometry: {bad}')

    # Exact frozen E-BUY architecture and sticky display.
    snaps, pools = v04.build_fixed_pools(raw, active, z4)
    displays = v04.sticky_display(raw, snaps, pools)
    state_for_raw, states = build_state_map(raw, z4, snaps, displays)

    # US raw-session indices.
    sessions = defaultdict(list)
    for j, t in enumerate(raw.time):
        sid = us_session_id(t)
        if sid is not None:
            sessions[sid].append(j)

    episodes = []
    contacts = []
    trades = []
    next_episode_id = 1

    for sid in sorted(sessions):
        idxs = sessions[sid]
        if not idxs:
            continue
        idxset = set(idxs)
        end_idx = idxs[-1]
        active_eps = []

        for j in idxs:
            row = raw.loc[j]
            t = pd.Timestamp(row.time)
            st = states[state_for_raw[j]] if j in state_for_raw else None
            zs = list(st['display']) if st is not None else []
            vcur = float(st['snap']['v']) if st is not None else np.nan

            trigger_candidates = []
            survivors = []

            # Existing breakout episodes are updated before discovering a new breakout on this close.
            for ep in active_eps:
                if ep['status'] != 'ACTIVE':
                    continue
                ep['preentry_min_low'] = min(float(ep['preentry_min_low']), float(row.low))
                if float(row.low) < float(ep['main_zlo']) - EPS:
                    ep['wick_below_main_preentry'] = True

                # Target before next-open entry terminates the setup.
                if float(row.high) >= float(ep['target_zlo']) - EPS:
                    ep['status'] = 'TARGET_REACHED_BEFORE_ENTRY'
                    ep['end_time'] = t
                    continue

                # User-defined structural invalidation: M1 CLOSE only.
                if float(row.close) < float(ep['main_zlo']) - EPS:
                    ep['status'] = 'CLOSE_INVALIDATED_BEFORE_ENTRY'
                    ep['end_time'] = t
                    continue

                # Breakout candle itself cannot be the retracement candle.
                if t > pd.Timestamp(ep['breakout_time']):
                    intersects_main = float(row.high) >= float(ep['main_zlo']) - EPS and float(row.low) <= float(ep['main_zhi']) + EPS
                    if intersects_main and not ep['main_retrace_seen']:
                        ep['main_retrace_seen'] = True
                        ep['first_retrace_time'] = t
                        ep['first_retrace_low'] = float(row.low)

                if ep['main_retrace_seen'] and st is not None and np.isfinite(vcur) and vcur > 0:
                    touched = []
                    for slot, z in enumerate(zs, 1):
                        if float(row.high) >= float(z.zlo) - EPS and float(row.low) <= float(z.zhi) + EPS:
                            touched.append((slot, z))
                    if touched:
                        br, cp = bull_rejection(row)
                        for slot, z in touched:
                            contacts.append({
                                'episode_id': int(ep['episode_id']),
                                'breakout_time': ep['breakout_time'],
                                'contact_time': t,
                                'session_id': sid,
                                'entry_rank': int(slot),
                                'entry_label': f'E{slot}',
                                'family': str(z.family),
                                'e_zlo': float(z.zlo), 'e_center': float(z.center), 'e_zhi': float(z.zhi),
                                'e_main_relation': zone_relation(z, ep),
                                'main_zlo': float(ep['main_zlo']), 'main_center': float(ep['main_center']), 'main_zhi': float(ep['main_zhi']),
                                'target_zlo': float(ep['target_zlo']),
                                'v_contact': float(vcur),
                                'bull_rejection': bool(br),
                                'close_position': float(cp),
                                'contact_low_below_main': bool(float(row.low) < float(ep['main_zlo']) - EPS),
                            })
                        if br:
                            slot, z = sorted(touched, key=lambda q: q[0])[0]
                            trigger_candidates.append((float(ep['main_zhi']), pd.Timestamp(ep['breakout_time']), ep, slot, z, float(vcur), float(cp)))

                survivors.append(ep)

            active_eps = survivors

            # One rejection candle can execute at most one structural episode.
            if trigger_candidates:
                _, _, ep, slot, z, vtr, cp = sorted(
                    trigger_candidates,
                    key=lambda q: (-q[0], -q[1].value, q[3])
                )[0]
                ex = j + 1
                ep['trigger_time'] = t
                ep['trigger_entry_rank'] = int(slot)
                ep['trigger_family'] = str(z.family)
                ep['trigger_relation'] = zone_relation(z, ep)
                ep['trigger_close_position'] = float(cp)

                if ex not in idxset:
                    ep['status'] = 'NO_NEXT_M1_BEFORE_US_END'
                    ep['end_time'] = t
                else:
                    entry_time = pd.Timestamp(raw.at[ex, 'time'])
                    entry = float(raw.at[ex, 'open'])
                    if entry >= float(ep['target_zlo']) - EPS:
                        ep['status'] = 'TARGET_REACHED_BEFORE_ENTRY_NEXT_OPEN'
                        ep['end_time'] = entry_time
                    elif entry <= float(ep['main_zlo']) + EPS:
                        ep['status'] = 'MAIN_INVALID_AT_NEXT_OPEN'
                        ep['end_time'] = entry_time
                    else:
                        ep['status'] = 'EXECUTED'
                        ep['entry_time'] = entry_time
                        ep['entry_price'] = entry
                        ep['end_time'] = entry_time
                        stop_d = entry - float(ep['main_zlo'])
                        target_d = float(ep['target_zlo']) - entry
                        rr = target_d / stop_d if stop_d > EPS and target_d > 0 else None
                        outcome, terminal_idx, mfe, mae = outcome_scan(raw, ex, end_idx, ep, entry, vtr)
                        tr = {
                            'episode_id': int(ep['episode_id']),
                            'session_id': sid,
                            'breakout_time': ep['breakout_time'],
                            'first_retrace_time': ep['first_retrace_time'],
                            'trigger_time': t,
                            'entry_time': entry_time,
                            'entry_price': entry,
                            'entry_rank': int(slot),
                            'entry_label': f'E{slot}',
                            'family': str(z.family),
                            'e_zlo': float(z.zlo), 'e_center': float(z.center), 'e_zhi': float(z.zhi),
                            'e_main_relation': zone_relation(z, ep),
                            'main_zlo': float(ep['main_zlo']), 'main_center': float(ep['main_center']), 'main_zhi': float(ep['main_zhi']),
                            'target_zlo': float(ep['target_zlo']), 'target_center': float(ep['target_center']), 'target_zhi': float(ep['target_zhi']),
                            'v_entry_context': float(vtr),
                            'stop_distance_v': float(stop_d / vtr),
                            'target_distance_v': float(target_d / vtr),
                            'nominal_rr': float(rr) if rr is not None else None,
                            'wick_below_main_preentry': bool(ep['wick_below_main_preentry']),
                            'preentry_min_low': float(ep['preentry_min_low']),
                            'outcome': outcome,
                            'outcome_time': pd.Timestamp(raw.at[terminal_idx, 'time']),
                            'mfe_v': float(mfe), 'mae_v': float(mae),
                            'minutes_breakout_to_retrace': float((pd.Timestamp(ep['first_retrace_time']) - pd.Timestamp(ep['breakout_time'])).total_seconds() / 60.0),
                            'minutes_retrace_to_trigger': float((t - pd.Timestamp(ep['first_retrace_time'])).total_seconds() / 60.0),
                            'minutes_entry_to_outcome': float((pd.Timestamp(raw.at[terminal_idx, 'time']) - entry_time).total_seconds() / 60.0),
                        }
                        trades.append(tr)
                active_eps = [x for x in active_eps if x['episode_id'] != ep['episode_id']]

            # Discover a new upward main-Z4 crossing using only the causal state preceding this M1 close.
            if st is not None and j > 0 and np.isfinite(vcur) and vcur > 0:
                g = st['z4']
                upper = g[g.side == 1].copy() if 'side' in g.columns else g.iloc[0:0].copy()
                if len(upper):
                    prev_close = float(raw.at[j - 1, 'close'])
                    crossed = upper[(upper.zhi < float(row.close) - EPS) & (upper.zhi >= prev_close - EPS)].copy()
                    if len(crossed):
                        candidates = []
                        for _, r in crossed.iterrows():
                            if any(same_structural_zone(ep0, r, vcur) for ep0 in active_eps if ep0['status'] == 'ACTIVE'):
                                continue
                            candidates.append(r)
                        if candidates:
                            main = max(candidates, key=lambda r: (float(r.zhi), float(r.center)))
                            higher = upper[upper.zlo > float(main.zhi) + EPS].copy()
                            target = None
                            if len(higher):
                                target = higher.iloc[int(np.argmin(higher.zlo.to_numpy(float) - float(main.zhi)))]
                            ep = {
                                'episode_id': int(next_episode_id),
                                'session_id': sid,
                                'state_time': st['time'],
                                'breakout_time': t,
                                'breakout_close': float(row.close),
                                'v_breakout': float(vcur),
                                'main_zlo': float(main.zlo), 'main_center': float(main.center), 'main_zhi': float(main.zhi),
                                'target_zlo': float(target.zlo) if target is not None else None,
                                'target_center': float(target.center) if target is not None else None,
                                'target_zhi': float(target.zhi) if target is not None else None,
                                'main_retrace_seen': False,
                                'first_retrace_time': None,
                                'first_retrace_low': None,
                                'preentry_min_low': float(row.low),
                                'wick_below_main_preentry': bool(float(row.low) < float(main.zlo) - EPS),
                                'trigger_time': None,
                                'trigger_entry_rank': None,
                                'trigger_family': None,
                                'trigger_relation': None,
                                'entry_time': None,
                                'entry_price': None,
                                'end_time': None,
                                'status': 'ACTIVE' if target is not None else 'NO_HIGHER_Z4_TARGET',
                            }
                            next_episode_id += 1
                            if target is not None and float(row.high) >= float(target.zlo) - EPS:
                                ep['status'] = 'TARGET_REACHED_ON_BREAKOUT_BAR'
                                ep['end_time'] = t
                            episodes.append(ep)
                            if ep['status'] == 'ACTIVE':
                                active_eps.append(ep)

        # Anything still open at 17:00 is an unfilled structural episode.
        for ep in active_eps:
            if ep['status'] == 'ACTIVE':
                ep['status'] = 'SESSION_END_NO_ENTRY'
                ep['end_time'] = pd.Timestamp(raw.at[end_idx, 'time'])

    # CSV evidence.
    epdf = pd.DataFrame(episodes)
    cdf = pd.DataFrame(contacts)
    tdf = pd.DataFrame(trades)
    epdf.to_csv(a.episodes_csv, index=False, compression='gzip')
    cdf.to_csv(a.contacts_csv, index=False, compression='gzip')
    tdf.to_csv(a.trades_csv, index=False, compression='gzip')

    def summary_for(lo, hi):
        ee = [x for x in episodes if lo <= pd.Timestamp(x['breakout_time']) < hi]
        ids = {int(x['episode_id']) for x in ee}
        cc = [x for x in contacts if int(x['episode_id']) in ids]
        tt = [x for x in trades if int(x['episode_id']) in ids]
        statuses = Counter(str(x['status']) for x in ee)
        retr = [x for x in ee if bool(x.get('main_retrace_seen'))]
        base = summarize_outcomes(tt)
        base.update({
            'main_z4_bullish_breakouts': int(len(ee)),
            'with_higher_z4_target': int(sum(x.get('target_zlo') is not None for x in ee)),
            'main_z4_retraced_by_wick_or_more': int(len(retr)),
            'close_invalidated_before_entry': int(statuses['CLOSE_INVALIDATED_BEFORE_ENTRY']),
            'target_reached_before_entry_total': int(statuses['TARGET_REACHED_BEFORE_ENTRY'] + statuses['TARGET_REACHED_ON_BREAKOUT_BAR'] + statuses['TARGET_REACHED_BEFORE_ENTRY_NEXT_OPEN']),
            'session_end_no_entry': int(statuses['SESSION_END_NO_ENTRY'] + statuses['NO_NEXT_M1_BEFORE_US_END']),
            'no_higher_target': int(statuses['NO_HIGHER_Z4_TARGET']),
            'main_invalid_at_next_open': int(statuses['MAIN_INVALID_AT_NEXT_OPEN']),
            'e_contact_events_after_main_retrace': int(len(cc)),
            'e_bull_rejection_contact_events': int(sum(bool(x.get('bull_rejection')) for x in cc)),
            'episode_status_counts': {str(k): int(v) for k, v in sorted(statuses.items())},
            'breakout_to_first_retrace_min': qpack([
                (pd.Timestamp(x['first_retrace_time']) - pd.Timestamp(x['breakout_time'])).total_seconds() / 60.0
                for x in retr if x.get('first_retrace_time') is not None
            ]),
            'retrace_to_trigger_min': qpack([x.get('minutes_retrace_to_trigger') for x in tt]),
            'entry_to_outcome_min': qpack([x.get('minutes_entry_to_outcome') for x in tt]),
            'by_entry_rank': stratify(cc, tt, 'entry_label'),
            'by_family': stratify(cc, tt, 'family'),
            'by_e_main_relation': stratify(cc, tt, 'e_main_relation'),
        })
        wb = [x for x in tt if bool(x.get('wick_below_main_preentry'))]
        nw = [x for x in tt if not bool(x.get('wick_below_main_preentry'))]
        base['wick_below_main_allowed_diagnostic'] = {
            'executed_with_wick_below_main_count': int(len(wb)),
            'executed_with_wick_below_main_share': float(len(wb) / len(tt)) if tt else None,
            'with_wick_below_main': summarize_outcomes(wb),
            'without_wick_below_main': summarize_outcomes(nw),
        }
        return base

    results = {w: summary_for(lo, hi) for w, (lo, hi) in WINDOWS.items()}
    pooled = summary_for(WINDOWS['H1'][0], WINDOWS['H2'][1])

    out = {
        'status': 'Z4_BREAK_RETRACE_E123_REJECTION_RETROSPECTIVE_COMPLETE',
        'scope': 'BUY_ONLY_US_C5_Z4_BREAK_RETRACE_E1_E2_E3_BULL_REJECTION',
        'session': '08:00-17:00 America/New_York',
        'main_zone': 'causal Z4 frozen at bullish breakout',
        'main_retrace_gate': 'post-breakout M1 range intersects main Z4; wick sufficient',
        'main_invalidation': 'M1 close strictly below frozen main_zlo; wick below allowed',
        'entry_zones': 'current causal sticky E1/E2/E3; may be inside/overlap/above/below main Z4',
        'trigger': 'BULL_REJECTION: close>open and close_position>=0.70',
        'execution': 'next M1 open',
        'target': 'next higher causal Z4 frozen at breakout; TP at target_zlo',
        'window_assignment': 'by breakout timestamp',
        'model_refit': False,
        'score_used': False,
        'results': results,
        'pooled': pooled,
        'production_authorization': 'NONE_RETROSPECTIVE_HYPOTHESIS_TEST',
    }
    Path(a.output).write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({'status': out['status'], 'H1': results['H1'], 'H2': results['H2']}, indent=2, default=str), flush=True)


if __name__ == '__main__':
    main()
