#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ALLOWED_FAMILIES = {'BROKEN_PIVOT_HIGH', 'POST_BREAK_PIVOT_LOW', 'BULL_FVG_MID'}
BALANCE = ['relative_corridor_coordinate', 'contact_minute', 'log_v_contact', 'trend15_v', 'trend60_v', 'trend240_v']
FORBIDDEN_TOKENS = ('outcome', 'primary_binary', 'favorable', 'adverse', 'mfe', 'mae', 'tp_first', 'invalidation_first', 'score', 'e1', 'e2', 'e3')


def args():
    p = argparse.ArgumentParser()
    p.add_argument('--phase', choices=['DEV', 'VAL', 'REP', 'BENCH'], required=True)
    p.add_argument('--episodes', required=True)
    p.add_argument('--candidates', required=True)
    p.add_argument('--controls', required=True)
    p.add_argument('--candidate-contacts', required=True)
    p.add_argument('--control-contacts', required=True)
    p.add_argument('--manifest', required=True)
    p.add_argument('--output', required=True)
    return p.parse_args()


def read(path):
    return pd.read_csv(path, compression='infer', float_precision='round_trip')


def weighted_mean_var(x, w):
    x, w = np.asarray(x, float), np.asarray(w, float)
    ok = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x, w = x[ok], w[ok]
    if not len(x):
        return None, None
    w = w / w.sum()
    mu = float(np.sum(w * x))
    var = float(np.sum(w * (x - mu) ** 2))
    return mu, var


def smd(candidate, control, control_w):
    a = np.asarray(candidate, float)
    a = a[np.isfinite(a)]
    if not len(a):
        return None
    ma, va = float(a.mean()), float(a.var(ddof=0))
    mb, vb = weighted_mean_var(control, control_w)
    if mb is None:
        return None
    den = math.sqrt(max((va + vb) / 2.0, 0.0))
    if den == 0:
        return 0.0 if abs(ma - mb) < 1e-15 else None
    return float((ma - mb) / den)


def main():
    a = args()
    ep, cand, ctrl = read(a.episodes), read(a.candidates), read(a.controls)
    cc, oc = read(a.candidate_contacts), read(a.control_contacts)
    man = json.load(open(a.manifest))
    checks = {}

    checks['generator_status'] = man.get('status') == 'Z4_CORRIDOR_V3_PREOUTCOME_PASS'
    checks['future_reaction_outcomes_false'] = man.get('future_v3_reaction_outcomes_used') is False
    checks['legacy_br70_false'] = man.get('legacy_br70_used') is False
    checks['e_zones_scores_false'] = man.get('e_zones_or_scores_used') is False

    all_columns = [str(c).lower() for d in [ep, cand, ctrl, cc, oc] for c in d.columns]
    bad_cols = sorted({c for c in all_columns if any(tok in c for tok in FORBIDDEN_TOKENS)})
    checks['no_forbidden_outcome_or_e_columns'] = len(bad_cols) == 0

    fam_bad = []
    if len(cand) and 'candidate_family_set' in cand:
        for x in cand.candidate_family_set.fillna('').astype(str):
            for f in x.split('|'):
                if f and f not in ALLOWED_FAMILIES:
                    fam_bad.append(f)
    checks['candidate_families_exact'] = not fam_bad

    checks['unique_candidate_contact_per_cluster'] = (not len(cc)) or not cc.cluster_id.astype(str).duplicated().any()
    checks['unique_control_contact_per_control'] = (not len(oc)) or not oc.control_id.astype(str).duplicated().any()

    if len(cc):
        ct = pd.to_datetime(cc.contact_time, utc=True)
        bt = pd.to_datetime(cc.birth_time, utc=True)
        checks['candidate_contact_strictly_after_birth'] = bool((ct > bt).all())
        checks['candidate_contact_inside_corridor'] = bool(((cc.level.astype(float) > cc.main_zhi.astype(float)) & (cc.level.astype(float) < cc.target_zlo.astype(float))).all())
        checks['candidate_contact_same_session'] = all(t.tz_convert('America/New_York').date().isoformat() == str(s) for t, s in zip(ct, cc.session_id))
    else:
        checks['candidate_contact_strictly_after_birth'] = True
        checks['candidate_contact_inside_corridor'] = True
        checks['candidate_contact_same_session'] = True

    if len(oc):
        ct = pd.to_datetime(oc.contact_time, utc=True)
        bt = pd.to_datetime(oc.birth_time, utc=True)
        checks['control_contact_strictly_after_birth'] = bool((ct > bt).all())
        checks['control_contact_inside_corridor'] = bool(((oc.level.astype(float) > oc.main_zhi.astype(float)) & (oc.level.astype(float) < oc.target_zlo.astype(float))).all())
        checks['control_contact_same_session'] = all(t.tz_convert('America/New_York').date().isoformat() == str(s) for t, s in zip(ct, oc.session_id))
    else:
        checks['control_contact_strictly_after_birth'] = True
        checks['control_contact_inside_corridor'] = True
        checks['control_contact_same_session'] = True

    censored_ids = set(ctrl.loc[ctrl.status.astype(str).isin(['CENSORED_STRUCTURAL_LEVEL_BORN', 'PASSED_BELOW_WITHOUT_TOUCH']), 'control_id'].astype(str)) if len(ctrl) else set()
    contacted_ids = set(oc.control_id.astype(str)) if len(oc) else set()
    checks['no_censored_control_contact'] = not bool(censored_ids & contacted_ids)

    # Authority rule: all contacts at one timestamp must belong to at most one structural episode.
    both = []
    if len(cc):
        both.append(cc[['contact_time', 'episode_id']])
    if len(oc):
        both.append(oc[['contact_time', 'episode_id']])
    if both:
        q = pd.concat(both, ignore_index=True)
        checks['one_authority_episode_per_contact_time'] = bool((q.groupby('contact_time').episode_id.nunique() <= 1).all())
    else:
        checks['one_authority_episode_per_contact_time'] = True

    # Matched contact support.
    counts = oc.groupby('cluster_id').size().to_dict() if len(oc) else {}
    if len(cc):
        cc = cc.copy()
        cc['control_n'] = cc.cluster_id.astype(str).map(lambda x: int(counts.get(x, 0)))
        matched = cc[cc.control_n >= 2].copy()
    else:
        matched = cc.copy()
        matched['control_n'] = []
    frac = float(len(matched) / len(cc)) if len(cc) else 0.0
    sessions = int(matched.session_id.nunique()) if len(matched) else 0

    # Donor-equal controls: each matched candidate contributes total control weight one.
    bal = {}
    if len(matched):
        mids = set(matched.cluster_id.astype(str))
        oo = oc[oc.cluster_id.astype(str).isin(mids)].copy()
        oo['n_for_cluster'] = oo.cluster_id.astype(str).map(lambda x: int(counts.get(x, 0)))
        oo['w'] = 1.0 / oo.n_for_cluster.astype(float)
        for c in BALANCE:
            value = smd(matched[c].astype(float), oo[c].astype(float), oo.w.astype(float))
            bal[c] = {'smd': value, 'abs_smd': abs(value) if value is not None else None}
    else:
        bal = {c: {'smd': None, 'abs_smd': None} for c in BALANCE}
    max_abs = max([x['abs_smd'] for x in bal.values() if x['abs_smd'] is not None], default=None)
    balance_pass = all(x['abs_smd'] is not None and x['abs_smd'] <= .10 for x in bal.values()) if len(matched) else False

    if a.phase == 'DEV':
        support = {'minimum_matched_contacts': len(matched) >= 1000, 'minimum_sessions': sessions >= 120, 'fraction_ge2_controls': frac >= .60}
    elif a.phase == 'VAL':
        support = {'minimum_matched_contacts': len(matched) >= 500, 'minimum_sessions': sessions >= 80, 'fraction_ge2_controls': frac >= .60}
    elif a.phase == 'REP':
        # Outcome-blind design evidence only; report against the VAL-sized feasibility floor.
        support = {'minimum_matched_contacts': len(matched) >= 500, 'minimum_sessions': sessions >= 80, 'fraction_ge2_controls': frac >= .60}
    else:
        support = {'minimum_matched_contacts': True, 'minimum_sessions': True, 'fraction_ge2_controls': True}

    checks['matched_control_balance_all_abs_smd_le_010'] = balance_pass if a.phase != 'BENCH' else True
    checks.update({f'support_{k}': bool(v) for k, v in support.items()})
    status = 'Z4_CORRIDOR_V3_PREOUTCOME_QA_PASS' if all(checks.values()) else 'Z4_CORRIDOR_V3_PREOUTCOME_QA_FAIL'
    out = {
        'status': status, 'phase': a.phase, 'future_v3_reaction_outcomes_used': False,
        'candidate_contacts': int(len(cc)), 'matched_candidate_contacts_ge2_controls': int(len(matched)),
        'matched_fraction': frac, 'matched_sessions': sessions, 'balance': bal, 'max_abs_smd': max_abs,
        'support': support, 'checks': checks, 'forbidden_columns': bad_cols, 'bad_families': sorted(set(fam_bad))
    }
    Path(a.output).write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(json.dumps(out, indent=2, sort_keys=True))
    if status.endswith('_FAIL'):
        raise RuntimeError(status)


if __name__ == '__main__':
    main()
