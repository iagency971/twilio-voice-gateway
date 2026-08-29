#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

E_FAMILIES = {
    'ESM_BOTH_G120M',
    'EPM_M1_R2_A8H',
    'EWM_G60M',
    'ES_M1_8H_R2_T0.50',
}
MODEL_FEATURES = ['zone_width_v', 'display_persistence_c5', 'current_family']
FORBIDDEN_TOKENS = ('contact', 'trigger', 'rejection', 'exec_', 'tp', 'sl', 'mfe', 'mae', 'success', 'reaction', 'outcome', 'p&l', 'return')


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--candidates', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--dev-output', required=True)
    p.add_argument('--replication-output', required=True)
    p.add_argument('--manifest', required=True)
    return p.parse_args()


def canonical(v):
    if isinstance(v, pd.Timestamp):
        return v.tz_convert('UTC').isoformat()
    if pd.isna(v):
        return None
    if isinstance(v, (np.integer, int)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return format(float(v), '.17g')
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v)


def row_hash(row: dict) -> str:
    payload = {k: canonical(v) for k, v in sorted(row.items()) if k != 'row_sha256'}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def members(s) -> frozenset[str]:
    if pd.isna(s) or str(s) == '':
        return frozenset()
    return frozenset(x for x in str(s).split(';') if x)


def session_date_ny(t: pd.Timestamp) -> str:
    return t.tz_convert('America/New_York').date().isoformat()


def write_gzip_csv(df: pd.DataFrame, path: str):
    raw = df.to_csv(index=False, lineterminator='\n').encode('utf-8')
    with open(path, 'wb') as fh:
        with gzip.GzipFile(fileobj=fh, mode='wb', mtime=0, filename='') as gz:
            gz.write(raw)


def new_episode_id(session: str, seq: int, family: str, t: pd.Timestamp, prov: str) -> str:
    x = f'{session}|{seq}|{family}|{t.tz_convert("UTC").isoformat()}|{prov}'
    return 'EDEP:' + hashlib.sha256(x.encode()).hexdigest()[:24]


def candidate_edges(prev_rows, cur_rows):
    edges = []
    for pi, p in enumerate(prev_rows):
        for ci, c in enumerate(cur_rows):
            if p['family'] != c['family']:
                continue
            fam = c['family']
            if fam in {'ESM_BOTH_G120M', 'EPM_M1_R2_A8H', 'EWM_G60M'}:
                if p['source_provenance_id'] == c['source_provenance_id']:
                    edges.append((0, 0.0, abs(p['center'] - c['center']), p['display_episode_id'], c['source_provenance_id'], pi, ci))
            elif fam == 'ES_M1_8H_R2_T0.50':
                a = p['_members']; b = c['_members']; inter = len(a & b)
                if inter:
                    union = len(a | b)
                    jac = inter / union if union else 0.0
                    edges.append((-inter, -jac, abs(p['center'] - c['center']), p['display_episode_id'], c['source_provenance_id'], pi, ci))
    edges.sort()
    return edges


def build(df: pd.DataFrame) -> pd.DataFrame:
    required = {'time','v60','entry_rank','family','center','zlo','zhi','source_provenance_id','source_provenance_members'}
    missing = sorted(required - set(df.columns))
    if missing:
        raise RuntimeError(f'missing candidate columns: {missing}')
    forbidden = [c for c in df.columns if any(tok in c.lower() for tok in FORBIDDEN_TOKENS)]
    if forbidden:
        raise RuntimeError(f'future/entry columns forbidden in candidate source: {forbidden}')
    df = df.copy()
    df['time'] = pd.to_datetime(df['time'], utc=True)
    df = df[df.family.isin(E_FAMILIES)].copy()
    df = df.sort_values(['time','entry_rank','family','center']).reset_index(drop=True)
    if not len(df):
        raise RuntimeError('no eligible E rows')

    out = []
    prev_rows = []
    prev_t = None
    prev_session = None
    episode_seq_by_session = {}

    for t, g in df.groupby('time', sort=True):
        t = pd.Timestamp(t)
        sess = session_date_ny(t)
        contiguous = prev_t is not None and (t - prev_t == pd.Timedelta(minutes=5)) and sess == prev_session
        cur_rows = []
        for _, r in g.sort_values(['entry_rank','family','center']).iterrows():
            cur_rows.append({
                'snapshot_time_utc': t,
                'bar_open_time_utc': t,
                'bar_close_time_utc': t + pd.Timedelta(minutes=1),
                'feature_available_time_utc': t + pd.Timedelta(minutes=1),
                'session_date_ny': sess,
                'display_slot_rank': int(r.entry_rank),
                'current_family': str(r.family),
                'family': str(r.family),
                'center': float(r.center), 'zlo': float(r.zlo), 'zhi': float(r.zhi),
                'v_snapshot': float(r.v60),
                'source_provenance_id': str(r.source_provenance_id),
                'source_provenance_members': '' if pd.isna(r.source_provenance_members) else str(r.source_provenance_members),
                '_members': members(r.source_provenance_members),
            })

        assigned_prev = set(); assigned_cur = set()
        if contiguous:
            for edge in candidate_edges(prev_rows, cur_rows):
                pi, ci = edge[-2], edge[-1]
                if pi in assigned_prev or ci in assigned_cur:
                    continue
                p = prev_rows[pi]; c = cur_rows[ci]
                c['display_episode_id'] = p['display_episode_id']
                c['display_persistence_c5'] = int(p['display_persistence_c5']) + 1
                c['is_new_display_episode'] = False
                c['prior_snapshot_time_utc'] = p['snapshot_time_utc']
                assigned_prev.add(pi); assigned_cur.add(ci)

        for ci, c in enumerate(cur_rows):
            if ci not in assigned_cur:
                seq = episode_seq_by_session.get(sess, 0) + 1
                episode_seq_by_session[sess] = seq
                c['display_episode_id'] = new_episode_id(sess, seq, c['family'], t, c['source_provenance_id'])
                c['display_persistence_c5'] = 1
                c['is_new_display_episode'] = True
                c['prior_snapshot_time_utc'] = pd.NaT
            width = c['zhi'] - c['zlo']
            if not (np.isfinite(width) and width >= 0 and np.isfinite(c['v_snapshot']) and c['v_snapshot'] > 0):
                raise RuntimeError(f'invalid geometry at {t}: {c}')
            c['zone_width_v'] = width / c['v_snapshot']
            c['feature_window'] = ('DEV_HISTORY' if pd.Timestamp('2024-08-01T00:00:00Z') <= t < pd.Timestamp('2025-08-01T00:00:00Z')
                                   else 'HISTORICAL_REPLICATION_DIAGNOSTIC' if pd.Timestamp('2025-08-01T00:00:00Z') <= t < pd.Timestamp('2026-08-01T00:00:00Z')
                                   else 'OUTSIDE_DECLARED_HISTORICAL_WINDOWS')
            clean = {k:v for k,v in c.items() if not k.startswith('_') and k != 'family'}
            clean['row_sha256'] = row_hash(clean)
            out.append(clean)

        prev_rows = cur_rows
        prev_t = t
        prev_session = sess

    ans = pd.DataFrame(out)
    cols = [
        'display_episode_id','snapshot_time_utc','bar_open_time_utc','bar_close_time_utc','feature_available_time_utc','session_date_ny',
        'display_slot_rank','current_family','source_provenance_id','source_provenance_members','center','zlo','zhi','v_snapshot',
        'zone_width_v','display_persistence_c5','is_new_display_episode','prior_snapshot_time_utc','feature_window','row_sha256'
    ]
    return ans[cols].sort_values(['snapshot_time_utc','display_slot_rank','current_family','center']).reset_index(drop=True)


def main():
    a = parse_args()
    src = pd.read_csv(a.candidates, compression='infer')
    ledger = build(src)
    dev = ledger[ledger.feature_window == 'DEV_HISTORY'].copy()
    rep = ledger[ledger.feature_window == 'HISTORICAL_REPLICATION_DIAGNOSTIC'].copy()
    if not len(dev) or not len(rep):
        raise RuntimeError(f'temporal coverage fail dev={len(dev)} replication={len(rep)}')
    for p in [a.output, a.dev_output, a.replication_output, a.manifest]:
        Path(p).parent.mkdir(parents=True, exist_ok=True)
    write_gzip_csv(ledger, a.output); write_gzip_csv(dev, a.dev_output); write_gzip_csv(rep, a.replication_output)
    ep = ledger.groupby('display_episode_id').size()
    manifest = {
        'status':'E_DISPLAY_EPISODE_SNAPSHOT_V1_BUILT_OUTCOME_BLIND',
        'future_price_outcomes_used':False,
        'model_feature_whitelist':MODEL_FEATURES,
        'rows':int(len(ledger)), 'episodes':int(ledger.display_episode_id.nunique()), 'sessions':int(ledger.session_date_ny.nunique()),
        'dev_rows':int(len(dev)), 'dev_sessions':int(dev.session_date_ny.nunique()),
        'replication_rows':int(len(rep)), 'replication_sessions':int(rep.session_date_ny.nunique()),
        'episode_length_median':float(ep.median()), 'episode_length_p90':float(ep.quantile(.90)),
        'cross_family_continuation_allowed':False,
        'timing_rule':'feature_available_time_utc = snapshot_time_utc + 1 minute',
        'real_outcome_authorization':'FORBIDDEN_PENDING_NEW_PRO_GATE'
    }
    Path(a.manifest).write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
