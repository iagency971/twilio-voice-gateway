#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

EPS = 1e-12
NY = 'America/New_York'
CONTROL_OFFSETS = (-0.50, -0.25, 0.25, 0.50)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--z4-pkl', required=True)
    p.add_argument('--target-start', required=True)
    p.add_argument('--target-end', required=True)
    p.add_argument('--episodes-out', required=True)
    p.add_argument('--candidates-out', required=True)
    p.add_argument('--controls-out', required=True)
    p.add_argument('--candidate-contacts-out', required=True)
    p.add_argument('--control-contacts-out', required=True)
    p.add_argument('--manifest', required=True)
    p.add_argument('--tag', default='V3_PREOUTCOME')
    return p.parse_args()


def load_raw(files):
    frames = []
    for f in files:
        d = pd.read_csv(f)
        if list(d.columns) != ['timestamp', 'open', 'high', 'low', 'close']:
            raise RuntimeError(f'{f}: schema {list(d.columns)}')
        d['time'] = pd.to_datetime(d.timestamp, unit='ms', utc=True)
        frames.append(d[['time', 'open', 'high', 'low', 'close']])
    if not frames:
        raise RuntimeError('no files')
    d = pd.concat(frames, ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    for c in ['open', 'high', 'low', 'close']:
        d[c] = pd.to_numeric(d[c], errors='raise').astype(float)
    return d


def write_gz(df, path):
    raw = df.to_csv(index=False, lineterminator='\n', float_format='%.17g', na_rep='').encode()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as fh:
        with gzip.GzipFile(fileobj=fh, mode='wb', mtime=0, filename='') as gz:
            gz.write(raw)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def us_session_id(t):
    q = pd.Timestamp(t).tz_convert(NY)
    return q.date().isoformat() if 8 <= q.hour < 17 else None


def contact_minute_ny(t):
    q = pd.Timestamp(t).tz_convert(NY)
    return int((q.hour - 8) * 60 + q.minute)


def build_state_map(raw, z4):
    z = z4.copy()
    z['time'] = pd.to_datetime(z.time, utc=True)
    if 'tr' not in z.columns:
        raise RuntimeError('Z4 missing causal tr volatility')
    arr = raw.time.to_numpy(dtype='datetime64[ns]')
    state_for_raw, states = {}, []
    for t, g in z.groupby('time', sort=True):
        t = pd.Timestamp(t)
        rec = {'time': t, 'z4': g.copy(), 'v': float(g.tr.iloc[0])}
        k = len(states)
        states.append(rec)
        q0 = np.datetime64(t.tz_convert('UTC').tz_localize(None))
        q1 = np.datetime64((t + pd.Timedelta(minutes=5)).tz_convert('UTC').tz_localize(None))
        i0 = int(np.searchsorted(arr, q0, side='right'))
        i1 = int(np.searchsorted(arr, q1, side='right')) - 1
        for j in range(max(0, i0), min(len(raw) - 1, i1) + 1):
            tj = pd.Timestamp(raw.at[j, 'time'])
            if us_session_id(tj) is not None and tj > t and tj <= t + pd.Timedelta(minutes=5):
                state_for_raw[j] = k
    return state_for_raw, states


def pivot_maps(raw):
    H, L = raw.high.to_numpy(float), raw.low.to_numpy(float)
    highs, lows = [], []
    hi_by_confirm, lo_by_confirm = defaultdict(list), defaultdict(list)
    for i in range(2, len(raw) - 2):
        if H[i] > H[i-2] and H[i] > H[i-1] and H[i] > H[i+1] and H[i] > H[i+2]:
            r = {'pivot_idx': i, 'confirm_idx': i + 2, 'level': float(H[i])}
            highs.append(r)
            hi_by_confirm[i + 2].append(r)
        if L[i] < L[i-2] and L[i] < L[i-1] and L[i] < L[i+1] and L[i] < L[i+2]:
            r = {'pivot_idx': i, 'confirm_idx': i + 2, 'level': float(L[i])}
            lows.append(r)
            lo_by_confirm[i + 2].append(r)
    return highs, lows, hi_by_confirm, lo_by_confirm


def same_structural_zone(ep, r, vcur):
    overlap = min(float(ep['main_zhi']), float(r.zhi)) >= max(float(ep['main_zlo']), float(r.zlo)) - EPS
    tol = .25 * max(float(ep['v_breakout']), float(vcur))
    return overlap or abs(float(ep['main_center']) - float(r.center)) <= tol + EPS


def authority_episode(active_eps):
    if not active_eps:
        return None
    return sorted(active_eps, key=lambda e: (-float(e['main_zhi']), -pd.Timestamp(e['breakout_time']).value, int(e['episode_id'])))[0]


def inside_corridor(ep, level):
    return float(ep['main_zhi']) + EPS < float(level) < float(ep['target_zlo']) - EPS


def candidate_raw(family, source_id, level, birth_idx, birth_time, v_birth):
    return {
        'family': family, 'source_id': str(source_id), 'level': float(level),
        'birth_idx': int(birth_idx), 'birth_time': pd.Timestamp(birth_time), 'v_birth': float(v_birth)
    }


def linked(a, b):
    return abs(float(a['level']) - float(b['level'])) <= .10 * min(float(a['v_birth']), float(b['v_birth'])) + EPS


def connected_components(raws):
    seen, out = set(), []
    for i in range(len(raws)):
        if i in seen:
            continue
        stack, comp = [i], []
        seen.add(i)
        while stack:
            u = stack.pop()
            comp.append(raws[u])
            for v in range(len(raws)):
                if v not in seen and linked(raws[u], raws[v]):
                    seen.add(v)
                    stack.append(v)
        out.append(comp)
    out.sort(key=lambda c: (float(np.median([x['level'] for x in c])), sorted(x['source_id'] for x in c)))
    return out


def member_key(comp):
    return tuple(sorted((x['family'], x['source_id']) for x in comp))


def birth_member(comp):
    return sorted(comp, key=lambda x: (x['birth_idx'], x['birth_time'].value, x['family'], x['source_id']))[-1]


def cluster_record(ep, cluster_id, comp):
    bm = birth_member(comp)
    fams = sorted(set(x['family'] for x in comp))
    members = sorted([
        {'family': x['family'], 'source_id': x['source_id'], 'level': float(x['level']),
         'birth_idx': int(x['birth_idx']), 'birth_time': str(pd.Timestamp(x['birth_time'])), 'v_birth': float(x['v_birth'])}
        for x in comp
    ], key=lambda z: (z['family'], z['source_id']))
    return {
        'cluster_id': str(cluster_id), 'episode_id': int(ep['episode_id']), 'session_id': ep['session_id'],
        'center': float(np.median([x['level'] for x in comp])), 'birth_idx': int(bm['birth_idx']),
        'birth_time': pd.Timestamp(bm['birth_time']), 'v_birth': float(bm['v_birth']),
        'candidate_family_set': '|'.join(fams), 'confluence_count': int(len(fams)),
        'members_json': json.dumps(members, sort_keys=True), 'status': 'LIVE', 'contacted': False,
        'contact_idx': None, 'contact_time': None, 'control_generation': 0, 'controls': [], '_raw_members': comp
    }


def controls_for_cluster(ep, cl, all_centers, current_close, next_control_id):
    controls = []
    vb, center = float(cl['v_birth']), float(cl['center'])
    for off in CONTROL_OFFSETS:
        level = center + off * vb
        if not inside_corridor(ep, level):
            continue
        if not level < float(current_close) - EPS:
            continue
        if any(abs(level - float(c)) <= .10 * vb + EPS for c in all_centers):
            continue
        cid = f'C{next_control_id[0]:09d}'
        next_control_id[0] += 1
        controls.append({
            'control_id': cid, 'cluster_id': cl['cluster_id'], 'episode_id': int(ep['episode_id']),
            'session_id': ep['session_id'], 'offset_v_birth': float(off), 'level': float(level),
            'birth_idx': int(cl['birth_idx']), 'birth_time': pd.Timestamp(cl['birth_time']),
            'v_birth': vb, 'status': 'LIVE', 'contacted': False, 'contact_idx': None,
            'contact_time': None, 'censor_time': None
        })
    return controls


def expire_uncontacted_controls(cl, reason):
    for c in cl.get('controls', []):
        if not c['contacted'] and c['status'] == 'LIVE':
            c['status'] = reason


def recluster(ep, new_raws, current_time, current_close, next_cluster_id, next_control_id, all_cluster_versions, all_controls):
    if not new_raws:
        return
    old = [c for c in ep['clusters'] if c['status'] == 'LIVE' and not c['contacted']]
    fixed = [c for c in ep['clusters'] if not (c['status'] == 'LIVE' and not c['contacted'])]
    pool = []
    for c in old:
        pool.extend(c['_raw_members'])
    pool.extend(new_raws)
    dd = {(r['family'], r['source_id']): r for r in pool}
    comps = connected_components(list(dd.values()))
    old_by_key = {member_key(c['_raw_members']): c for c in old}
    resulting, changed, used_old = [], [], set()
    for comp in comps:
        k = member_key(comp)
        if k in old_by_key:
            c = old_by_key[k]
            resulting.append(c)
            used_old.add(c['cluster_id'])
        else:
            cid = f'K{next_cluster_id[0]:09d}'
            next_cluster_id[0] += 1
            c = cluster_record(ep, cid, comp)
            all_cluster_versions.append(c)
            resulting.append(c)
            changed.append(c)
    for c in old:
        if c['cluster_id'] not in used_old:
            c['status'] = 'SUPERSEDED'
            expire_uncontacted_controls(c, 'SUPERSEDED')
    ep['clusters'] = fixed + resulting
    centers = [c['center'] for c in ep['clusters'] if c['status'] in {'LIVE', 'CONTACTED'}]

    # Addendum B: prospective neutrality maintenance.
    for parent in ep['clusters']:
        for ctrl in parent.get('controls', []):
            if ctrl['status'] == 'LIVE' and not ctrl['contacted']:
                if any(abs(float(ctrl['level']) - float(cen)) <= .10 * float(ctrl['v_birth']) + EPS for cen in centers):
                    ctrl['status'] = 'CENSORED_STRUCTURAL_LEVEL_BORN'
                    ctrl['censor_time'] = pd.Timestamp(current_time)

    for c in changed:
        c['control_generation'] += 1
        c['controls'] = controls_for_cluster(ep, c, centers, current_close, next_control_id)
        all_controls.extend(c['controls'])


def trend_v(raw, j, n, v):
    if j - n < 0 or not np.isfinite(v) or v <= 0:
        return np.nan
    return float((float(raw.at[j, 'close']) - float(raw.at[j-n, 'close'])) / v)


def contact_features(raw, j, ep, level, v, birth_time):
    width = float(ep['target_zlo']) - float(ep['main_zhi'])
    return {
        'relative_corridor_coordinate': float((float(level) - float(ep['main_zhi'])) / width) if width > EPS else np.nan,
        'contact_minute': contact_minute_ny(raw.at[j, 'time']),
        'log_v_contact': float(math.log(v)) if v > 0 else np.nan,
        'trend15_v': trend_v(raw, j, 15, v), 'trend60_v': trend_v(raw, j, 60, v),
        'trend240_v': trend_v(raw, j, 240, v),
        'birth_to_contact_min': float((pd.Timestamp(raw.at[j, 'time']) - pd.Timestamp(birth_time)).total_seconds() / 60.0)
    }


def main():
    a = parse_args()
    start, end = pd.Timestamp(a.target_start), pd.Timestamp(a.target_end)
    start = start.tz_localize('UTC') if start.tzinfo is None else start.tz_convert('UTC')
    end = end.tz_localize('UTC') if end.tzinfo is None else end.tz_convert('UTC')
    raw = load_raw(a.files)
    z4 = pd.read_pickle(a.z4_pkl).copy()
    z4['time'] = pd.to_datetime(z4.time, utc=True)
    forbidden = {c for c in z4.columns if any(q in c.lower() for q in ['reaction', 'outcome', 'mfe', 'mae', 'w5', 'w15', 'w60', 'nrb'])}
    if forbidden:
        raise RuntimeError(f'forbidden Z4 outcome fields: {sorted(forbidden)}')
    state_for_raw, states = build_state_map(raw, z4)
    pivot_highs, _, _, lo_by_confirm = pivot_maps(raw)
    ph_conf = np.array([x['confirm_idx'] for x in pivot_highs], dtype=int) if pivot_highs else np.array([], dtype=int)

    sessions = defaultdict(list)
    for j, t in enumerate(raw.time):
        sid = us_session_id(t)
        if sid is not None:
            sessions[sid].append(j)

    episodes, all_cluster_versions, all_controls = [], [], []
    candidate_contacts, control_contacts = [], []
    next_episode_id, next_cluster_id, next_control_id = 1, [1], [1]

    for sid in sorted(sessions):
        idxs, active = sessions[sid], []
        for j in idxs:
            row, t = raw.loc[j], pd.Timestamp(raw.at[j, 'time'])
            st = states[state_for_raw[j]] if j in state_for_raw else None
            vcur = float(st['v']) if st is not None else np.nan

            # Addendum A ordering: TARGET, MAIN close invalidation, contacts, births, then new breakout discovery.
            survivors = []
            for ep in active:
                if float(row.high) >= float(ep['target_zlo']) - EPS:
                    ep['status'], ep['end_time'] = 'TARGET_REACHED', t
                    for cl in ep['clusters']:
                        if cl['status'] == 'LIVE' and not cl['contacted']:
                            cl['status'] = 'EXPIRED_TARGET'
                        expire_uncontacted_controls(cl, 'EXPIRED_TARGET')
                    continue
                if float(row.close) < float(ep['main_zlo']) - EPS:
                    ep['status'], ep['end_time'] = 'CLOSE_INVALIDATED', t
                    for cl in ep['clusters']:
                        if cl['status'] == 'LIVE' and not cl['contacted']:
                            cl['status'] = 'EXPIRED_MAIN'
                        expire_uncontacted_controls(cl, 'EXPIRED_MAIN')
                    continue
                survivors.append(ep)
            active = survivors
            ep = authority_episode(active)

            if ep is not None and st is not None and np.isfinite(vcur) and vcur > 0:
                # Candidate/control contacts born strictly before this bar.
                for cl in ep['clusters']:
                    if cl['status'] not in {'LIVE', 'CONTACTED'}:
                        continue
                    if (not cl['contacted']) and t > pd.Timestamp(cl['birth_time']):
                        if float(row.low) <= float(cl['center']) + EPS and float(row.high) >= float(cl['center']) - EPS:
                            cl['contacted'], cl['contact_idx'], cl['contact_time'], cl['status'] = True, int(j), t, 'CONTACTED'
                            rec = {
                                'kind': 'CANDIDATE', 'cluster_id': cl['cluster_id'], 'episode_id': int(ep['episode_id']),
                                'session_id': sid, 'contact_idx': int(j), 'contact_time': t, 'level': float(cl['center']),
                                'birth_time': pd.Timestamp(cl['birth_time']), 'v_contact': float(vcur),
                                'candidate_family_set': cl['candidate_family_set'], 'confluence_count': int(cl['confluence_count']),
                                'main_zlo': float(ep['main_zlo']), 'main_zhi': float(ep['main_zhi']), 'target_zlo': float(ep['target_zlo'])
                            }
                            rec.update(contact_features(raw, j, ep, cl['center'], vcur, cl['birth_time']))
                            candidate_contacts.append(rec)
                        elif float(row.high) < float(cl['center']) - EPS:
                            cl['status'] = 'PASSED_BELOW_WITHOUT_TOUCH'
                    for c in cl.get('controls', []):
                        if c['status'] == 'LIVE' and not c['contacted'] and t > pd.Timestamp(c['birth_time']):
                            if float(row.low) <= float(c['level']) + EPS and float(row.high) >= float(c['level']) - EPS:
                                c['contacted'], c['contact_idx'], c['contact_time'], c['status'] = True, int(j), t, 'CONTACTED'
                                rec = {
                                    'kind': 'CONTROL', 'control_id': c['control_id'], 'cluster_id': cl['cluster_id'],
                                    'episode_id': int(ep['episode_id']), 'session_id': sid, 'contact_idx': int(j),
                                    'contact_time': t, 'level': float(c['level']), 'offset_v_birth': float(c['offset_v_birth']),
                                    'birth_time': pd.Timestamp(c['birth_time']), 'v_contact': float(vcur),
                                    'main_zlo': float(ep['main_zlo']), 'main_zhi': float(ep['main_zhi']), 'target_zlo': float(ep['target_zlo'])
                                }
                                rec.update(contact_features(raw, j, ep, c['level'], vcur, c['birth_time']))
                                control_contacts.append(rec)
                            elif float(row.high) < float(c['level']) - EPS:
                                c['status'] = 'PASSED_BELOW_WITHOUT_TOUCH'

                # Candidate births at this close. They cannot contact on this same bar.
                new_raws = []
                if j > int(ep['breakout_idx']):
                    if len(pivot_highs):
                        left = int(np.searchsorted(ph_conf, j - 240, side='left'))
                        right = int(np.searchsorted(ph_conf, j, side='left'))
                        for r in pivot_highs[left:right]:
                            source = f'PH{int(r["pivot_idx"])}'
                            key = ('BROKEN_PIVOT_HIGH', source)
                            level = float(r['level'])
                            if key not in ep['raw_seen'] and inside_corridor(ep, level) and float(row.close) > level + EPS:
                                ep['raw_seen'].add(key)
                                new_raws.append(candidate_raw('BROKEN_PIVOT_HIGH', source, level, j, t, vcur))
                    for r in lo_by_confirm.get(j, []):
                        if int(r['pivot_idx']) <= int(ep['breakout_idx']):
                            continue
                        source = f'PL{int(r["pivot_idx"])}'
                        key = ('POST_BREAK_PIVOT_LOW', source)
                        level = float(r['level'])
                        if key not in ep['raw_seen'] and inside_corridor(ep, level) and float(row.close) > level + EPS:
                            ep['raw_seen'].add(key)
                            new_raws.append(candidate_raw('POST_BREAK_PIVOT_LOW', source, level, j, t, vcur))
                    if j >= 2 and float(raw.at[j, 'low']) > float(raw.at[j-2, 'high']) + EPS:
                        level = .5 * (float(raw.at[j, 'low']) + float(raw.at[j-2, 'high']))
                        source = f'FVG{j}'
                        key = ('BULL_FVG_MID', source)
                        if key not in ep['raw_seen'] and inside_corridor(ep, level):
                            ep['raw_seen'].add(key)
                            new_raws.append(candidate_raw('BULL_FVG_MID', source, level, j, t, vcur))
                recluster(ep, new_raws, t, float(row.close), next_cluster_id, next_control_id, all_cluster_versions, all_controls)

            # Exact frozen MAIN breakout and nearest-higher TARGET discovery.
            if st is not None and j > 0 and np.isfinite(vcur) and vcur > 0 and start <= t < end:
                g = st['z4']
                upper = g[g.side == 1].copy() if 'side' in g.columns else g.iloc[0:0].copy()
                if len(upper):
                    prev_close, cur_close = float(raw.at[j-1, 'close']), float(row.close)
                    crossed = upper[(upper.zhi < cur_close - EPS) & (upper.zhi >= prev_close - EPS)].copy()
                    if len(crossed):
                        candidates = []
                        for _, r in crossed.iterrows():
                            if any(same_structural_zone(e, r, vcur) for e in active if e['status'] == 'ACTIVE'):
                                continue
                            candidates.append(r)
                        if candidates:
                            main = max(candidates, key=lambda r: (float(r.zhi), float(r.center)))
                            higher = upper[upper.zlo > float(main.zhi) + EPS].copy()
                            target = higher.iloc[int(np.argmin(higher.zlo.to_numpy(float) - float(main.zhi)))] if len(higher) else None
                            ep2 = {
                                'episode_id': int(next_episode_id), 'session_id': sid, 'breakout_idx': int(j),
                                'breakout_time': t, 'breakout_close': cur_close, 'v_breakout': float(vcur),
                                'main_zlo': float(main.zlo), 'main_center': float(main.center), 'main_zhi': float(main.zhi),
                                'target_zlo': float(target.zlo) if target is not None else None,
                                'target_center': float(target.center) if target is not None else None,
                                'target_zhi': float(target.zhi) if target is not None else None,
                                'status': 'ACTIVE' if target is not None else 'NO_HIGHER_Z4_TARGET', 'end_time': None,
                                'clusters': [], 'raw_seen': set()
                            }
                            next_episode_id += 1
                            episodes.append(ep2)
                            if target is not None and float(row.high) >= float(target.zlo) - EPS:
                                ep2['status'], ep2['end_time'] = 'TARGET_REACHED_ON_BREAKOUT_BAR', t
                            elif target is not None:
                                active.append(ep2)

        endt = pd.Timestamp(raw.at[idxs[-1], 'time'])
        for ep in active:
            ep['status'], ep['end_time'] = 'SESSION_END', endt
            for cl in ep['clusters']:
                if cl['status'] == 'LIVE' and not cl['contacted']:
                    cl['status'] = 'EXPIRED_SESSION'
                expire_uncontacted_controls(cl, 'EXPIRED_SESSION')

    eps = [{k: v for k, v in e.items() if k not in {'clusters', 'raw_seen'}} for e in episodes]
    cls = [{k: v for k, v in c.items() if k not in {'controls', '_raw_members'}} for c in all_cluster_versions]
    ctrls = [dict(c) for c in all_controls]
    edf, cdf, odf = pd.DataFrame(eps), pd.DataFrame(cls), pd.DataFrame(ctrls)
    ccdf, ocdf = pd.DataFrame(candidate_contacts), pd.DataFrame(control_contacts)

    write_gz(edf, a.episodes_out)
    write_gz(cdf, a.candidates_out)
    write_gz(odf, a.controls_out)
    write_gz(ccdf, a.candidate_contacts_out)
    write_gz(ocdf, a.control_contacts_out)

    matched = 0
    if len(ccdf) and len(ocdf):
        counts = ocdf.groupby('cluster_id').size().to_dict()
        matched = sum(int(counts.get(x, 0)) >= 2 for x in ccdf.cluster_id.astype(str))
    fam_counts = defaultdict(int)
    for c in all_cluster_versions:
        for f in str(c.get('candidate_family_set', '')).split('|'):
            if f:
                fam_counts[f] += 1
    m = {
        'status': 'Z4_CORRIDOR_V3_PREOUTCOME_PASS', 'tag': a.tag,
        'target_start': start.isoformat(), 'target_end': end.isoformat(),
        'future_v3_reaction_outcomes_used': False, 'legacy_br70_used': False, 'e_zones_or_scores_used': False,
        'episodes': int(len(edf)), 'candidate_cluster_versions': int(len(cdf)),
        'candidate_contacts': int(len(ccdf)), 'controls': int(len(odf)), 'control_contacts': int(len(ocdf)),
        'candidate_contacts_with_ge2_contacted_controls': int(matched),
        'cluster_version_family_presence_counts': {k: int(v) for k, v in sorted(fam_counts.items())},
        'sha256': {}
    }
    for name, path in [
        ('episodes', a.episodes_out), ('candidates', a.candidates_out), ('controls', a.controls_out),
        ('candidate_contacts', a.candidate_contacts_out), ('control_contacts', a.control_contacts_out)
    ]:
        m['sha256'][name] = sha256(path)
    Path(a.manifest).write_text(json.dumps(m, indent=2, sort_keys=True) + '\n')
    print(json.dumps(m, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
