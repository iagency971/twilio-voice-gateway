#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ENTRY = HERE.parent / 'entry-research'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


SESSIONS = {
    'ASIA_BROAD': {'start': 18, 'end': 3, 'label': '18:00-03:00 America/New_York'},
    'ASIA_CORE_STANDALONE': {'start': 21, 'end': 3, 'label': '21:00-03:00 America/New_York'},
    'EUROPE': {'start': 3, 'end': 8, 'label': '03:00-08:00 America/New_York'},
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--session', choices=sorted(SESSIONS), required=True)
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--z4-pkl', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--episodes-csv', required=True)
    p.add_argument('--contacts-csv', required=True)
    p.add_argument('--trades-csv', required=True)
    return p.parse_args()


def ny(t):
    return pd.Timestamp(t).tz_convert('America/New_York')


def in_session(t, name):
    h = ny(t).hour
    if name == 'ASIA_BROAD':
        return h >= 18 or h < 3
    if name == 'ASIA_CORE_STANDALONE':
        return h >= 21 or h < 3
    if name == 'EUROPE':
        return 3 <= h < 8
    raise ValueError(name)


def session_id(t, name):
    q = ny(t)
    if not in_session(t, name):
        return None
    if name in ('ASIA_BROAD', 'ASIA_CORE_STANDALONE') and q.hour < 3:
        return (q.date() - pd.Timedelta(days=1)).isoformat()
    return q.date().isoformat()


def subperiod(t, name):
    q = ny(t); h = q.hour
    if name == 'ASIA_BROAD':
        return 'ASIA_EXP_18_21' if 18 <= h < 21 else 'ASIA_CORE_PART_21_03'
    if name == 'ASIA_CORE_STANDALONE':
        return 'ASIA_CORE_21_03'
    return 'EUROPE_03_08'


def wilson(tp, n):
    if not n:
        return [None, None]
    p = tp / n; z = 1.959963984540054
    den = 1 + z*z/n
    c = (p + z*z/(2*n))/den
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return [max(0., c-h), min(1., c+h)]


def terminal_diag(df):
    if len(df) == 0:
        return {'n_terminal': 0, 'TP_FIRST': 0, 'INVALIDATION_FIRST': 0, 'terminal_tp_rate': None,
                'wilson95': [None, None], 'expectancy_R_before_costs': None, 'profit_factor_R': None}
    d = df[df.outcome.isin(['TP_FIRST','INVALIDATION_FIRST'])].copy()
    tp = int((d.outcome == 'TP_FIRST').sum()); sl = int((d.outcome == 'INVALIDATION_FIRST').sum()); n = tp + sl
    vals = []
    for _, r in d.iterrows():
        vals.append(float(r.nominal_rr) if r.outcome == 'TP_FIRST' else -1.0)
    pos = float(sum(x for x in vals if x > 0)); neg = float(-sum(x for x in vals if x < 0))
    return {
        'n_terminal': n, 'TP_FIRST': tp, 'INVALIDATION_FIRST': sl,
        'terminal_tp_rate': float(tp/n) if n else None,
        'wilson95': wilson(tp,n),
        'expectancy_R_before_costs': float(np.mean(vals)) if vals else None,
        'profit_factor_R': float(pos/neg) if neg > 0 else (None if not vals else float('inf')),
    }


def decorate_result(a):
    p = Path(a.output)
    out = json.loads(p.read_text())
    out['scope'] = f"BUY_ONLY_{a.session}_C5_Z4_BREAK_RETRACE_E1_E2_E3_BULL_REJECTION"
    out['session'] = SESSIONS[a.session]['label']
    out['session_name'] = a.session
    out['score_used'] = False
    out['production_authorization'] = 'NONE_RETROSPECTIVE_SESSION_RESEARCH'
    out['legacy_metadata_note'] = 'Any internal NO_NEXT_M1_BEFORE_US_END status label is inherited text only; boundary used is the selected session end.'

    t = pd.read_csv(a.trades_csv, compression='gzip')
    if len(t):
        for c in ['breakout_time','trigger_time','entry_time','outcome_time']:
            t[c] = pd.to_datetime(t[c], utc=True, errors='coerce')
        t['trigger_subperiod'] = t.trigger_time.map(lambda x: subperiod(x, a.session))
    else:
        t['trigger_subperiod'] = []

    windows = {
        'H1': (pd.Timestamp('2024-08-01T00:00:00Z'), pd.Timestamp('2025-08-01T00:00:00Z')),
        'H2': (pd.Timestamp('2025-08-01T00:00:00Z'), pd.Timestamp('2026-08-01T00:00:00Z')),
    }
    extra = {}
    for w,(lo,hi) in windows.items():
        q = t[(t.breakout_time >= lo) & (t.breakout_time < hi)].copy() if len(t) else t.copy()
        rel = {}
        for relation in ['ABOVE_MAIN','INSIDE_MAIN','OVERLAP_MAIN','BELOW_MAIN']:
            rel[relation] = terminal_diag(q[q.e_main_relation == relation]) if len(q) else terminal_diag(q)
        rank = {}
        for label in ['E1','E2','E3']:
            rank[label] = terminal_diag(q[q.entry_label == label]) if len(q) else terminal_diag(q)
        subs = {}
        for sp in sorted(set(q.trigger_subperiod.astype(str))) if len(q) else []:
            sq = q[q.trigger_subperiod == sp]
            subs[sp] = {
                'all': terminal_diag(sq),
                'ABOVE_MAIN': terminal_diag(sq[sq.e_main_relation == 'ABOVE_MAIN']),
            }
        extra[w] = {
            'all_terminal_structural_R': terminal_diag(q),
            'by_e_main_relation_terminal_R': rel,
            'by_entry_rank_terminal_R': rank,
            'by_trigger_subperiod_terminal_R': subs,
        }

    h1 = extra['H1']['by_e_main_relation_terminal_R']['ABOVE_MAIN']
    h2 = extra['H2']['by_e_main_relation_terminal_R']['ABOVE_MAIN']
    def positive(x):
        return (x['n_terminal'] >= 20 and x['terminal_tp_rate'] is not None and x['terminal_tp_rate'] > .50 and
                x['expectancy_R_before_costs'] is not None and x['expectancy_R_before_costs'] > 0)
    extra['ABOVE_MAIN_directional_replication_gate'] = {
        'H1_pass': positive(h1), 'H2_pass': positive(h2), 'pass': bool(positive(h1) and positive(h2)),
        'rule': 'same subgroup; terminal N>=20 each window; TP rate>50% each; expectancy_R>0 each'
    }
    out['prespecified_session_diagnostics'] = extra
    p.write_text(json.dumps(out, indent=2, default=str))
    t.to_csv(a.trades_csv, index=False, compression='gzip')


def main():
    a = parse_args()
    base = load_module('z4_session_base', ENTRY / 'xau_z4_break_retrace_e123_rejection_v1_0.py')

    pred = lambda t: in_session(t, a.session)
    sid = lambda t: session_id(t, a.session)

    # Patch session predicates only. Geometry, E architecture, structural mechanics and outcomes remain frozen.
    base.is_us = pred
    base.us_session_id = sid
    base.v01.ny_us = pred
    base.v04.v01.ny_us = pred

    base.parse_args = lambda: SimpleNamespace(
        files=a.files, z4_pkl=a.z4_pkl, output=a.output,
        episodes_csv=a.episodes_csv, contacts_csv=a.contacts_csv, trades_csv=a.trades_csv)
    base.main()
    decorate_result(a)
    print(json.dumps({'status':'SESSION_STUDY_COMPLETE','session':a.session,'output':a.output}, indent=2))


if __name__ == '__main__':
    main()
