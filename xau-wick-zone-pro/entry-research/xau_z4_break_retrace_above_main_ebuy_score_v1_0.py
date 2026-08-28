#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

H1_LO = pd.Timestamp('2024-08-01T00:00:00Z')
H1_HI = pd.Timestamp('2025-08-01T00:00:00Z')
H1_OOF_LO = pd.Timestamp('2024-12-01T00:00:00Z')
H2_LO = pd.Timestamp('2025-08-01T00:00:00Z')
H2_HI = pd.Timestamp('2026-08-01T00:00:00Z')
THRESHOLDS = (0, 50, 60, 70, 80, 90)
BOOT_REPS = 10000
BOOT_SEED = 20260828
GEOM_TOL = 1e-6


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--structural-trades', required=True)
    p.add_argument('--h1-triggers', required=True)
    p.add_argument('--h1-oof', required=True)
    p.add_argument('--h2-scored', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--mapped-csv', required=True)
    return p.parse_args()


def as_bool(s: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(s):
        return s.fillna(False)
    return s.astype(str).str.lower().isin({'true', '1', 'yes'})


def tstamp(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True, errors='coerce')
    return df


def wilson(tp: int, n: int):
    if n <= 0:
        return [None, None]
    z = 1.959963984540054
    p = tp / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return [max(0.0, center-half), min(1.0, center+half)]


def r_stats(d: pd.DataFrame):
    if len(d) == 0:
        return {'expectancy_R': None, 'profit_factor_R': None}
    vals = []
    win_r = 0.0
    losses = 0
    for _, r in d.iterrows():
        if r['outcome'] == 'TP_FIRST':
            rr = float(r['nominal_rr'])
            vals.append(rr)
            win_r += rr
        elif r['outcome'] == 'INVALIDATION_FIRST':
            vals.append(-1.0)
            losses += 1
    return {
        'expectancy_R': float(np.mean(vals)) if vals else None,
        'profit_factor_R': float(win_r / losses) if losses else None,
    }


def threshold_table(d: pd.DataFrame):
    out = {}
    base = float((d.outcome == 'TP_FIRST').mean()) if len(d) else None
    for cut in THRESHOLDS:
        q = d[d.E_BUY_US >= cut].copy()
        tp = int((q.outcome == 'TP_FIRST').sum())
        sl = int((q.outcome == 'INVALIDATION_FIRST').sum())
        n = tp + sl
        rate = tp/n if n else None
        rs = r_stats(q)
        out[f'E>={cut}'] = {
            'terminal_n': n,
            'TP_FIRST': tp,
            'INVALIDATION_FIRST': sl,
            'terminal_tp_rate': rate,
            'wilson95': wilson(tp, n),
            'absolute_lift_vs_all_scored': (float(rate-base) if rate is not None and base is not None else None),
            **rs,
        }
    return out


def exclusive_bands(d: pd.DataFrame):
    edges = [(0,50),(50,60),(60,70),(70,80),(80,90),(90,100.0000001)]
    out = {}
    for lo, hi in edges:
        q = d[(d.E_BUY_US >= lo) & (d.E_BUY_US < hi)].copy()
        tp = int((q.outcome == 'TP_FIRST').sum())
        sl = int((q.outcome == 'INVALIDATION_FIRST').sum())
        n = tp + sl
        out[f'[{lo},{100 if hi>100 else hi})'] = {
            'terminal_n': n,
            'TP_FIRST': tp,
            'INVALIDATION_FIRST': sl,
            'terminal_tp_rate': (tp/n if n else None),
        }
    return out


def cluster_boot_auc(d: pd.DataFrame):
    if len(d) == 0 or d.outcome.nunique() < 2:
        return {'reps_requested': BOOT_REPS, 'valid_reps': 0, 'invalid_one_class_reps': BOOT_REPS, 'ci95': [None,None]}
    groups = {sid: g.copy() for sid, g in d.groupby('session_id', sort=True)}
    keys = list(groups)
    rng = np.random.default_rng(BOOT_SEED)
    vals = []
    invalid = 0
    for _ in range(BOOT_REPS):
        sample = rng.choice(keys, size=len(keys), replace=True)
        q = pd.concat([groups[k] for k in sample], ignore_index=True)
        y = (q.outcome == 'TP_FIRST').astype(int).to_numpy()
        if len(np.unique(y)) < 2:
            invalid += 1
            continue
        vals.append(float(roc_auc_score(y, q.E_BUY_US.to_numpy(float))))
    if vals:
        ci = [float(np.quantile(vals, .025)), float(np.quantile(vals, .975))]
    else:
        ci = [None, None]
    return {'reps_requested': BOOT_REPS, 'valid_reps': len(vals), 'invalid_one_class_reps': invalid, 'seed': BOOT_SEED, 'ci95': ci}


def score_metrics(d: pd.DataFrame):
    d = d[d.outcome.isin(['TP_FIRST','INVALIDATION_FIRST'])].copy()
    y = (d.outcome == 'TP_FIRST').astype(int).to_numpy()
    if len(d) and len(np.unique(y)) == 2:
        auc = float(roc_auc_score(y, d.E_BUY_US.to_numpy(float)))
        sp = spearmanr(d.E_BUY_US.to_numpy(float), y)
        rho = float(sp.statistic)
        pval = float(sp.pvalue)
    else:
        auc = rho = pval = None
    tp_e = d.loc[d.outcome == 'TP_FIRST', 'E_BUY_US'].to_numpy(float)
    sl_e = d.loc[d.outcome == 'INVALIDATION_FIRST', 'E_BUY_US'].to_numpy(float)
    tp = int((d.outcome == 'TP_FIRST').sum())
    sl = int((d.outcome == 'INVALIDATION_FIRST').sum())
    n = tp + sl
    return {
        'terminal_n': n,
        'TP_FIRST': tp,
        'INVALIDATION_FIRST': sl,
        'unfiltered_terminal_tp_rate': (tp/n if n else None),
        'continuous_auc': auc,
        'session_cluster_bootstrap_auc': cluster_boot_auc(d),
        'spearman_E_vs_terminal_outcome': {'rho': rho, 'pvalue_descriptive': pval},
        'median_E_TP': (float(np.median(tp_e)) if len(tp_e) else None),
        'median_E_INVALIDATION': (float(np.median(sl_e)) if len(sl_e) else None),
        'thresholds': threshold_table(d),
        'exclusive_bands_descriptive': exclusive_bands(d),
    }


def prepare_h1_score_rows(h1_triggers: pd.DataFrame, h1_oof: pd.DataFrame):
    h1_triggers = h1_triggers.copy()
    h1_oof = h1_oof.copy()
    tstamp(h1_triggers, ['trigger_time','exec_time','contact_time','c5_time'])
    tstamp(h1_oof, ['observation_time'])
    if 'trigger' in h1_triggers.columns:
        h1_triggers = h1_triggers[h1_triggers.trigger.astype(str) == 'BULL_REJECTION'].copy()
    if 'fired' in h1_triggers.columns:
        h1_triggers = h1_triggers[as_bool(h1_triggers.fired)].copy()
    h1_oof = h1_oof[h1_oof.model.astype(str) == 'M1_LOGISTIC'].copy()
    need_oof = {'episode_id','observation_time','E_BUY_US'}
    missing = need_oof - set(h1_oof.columns)
    if missing:
        raise RuntimeError(f'H1 OOF missing columns: {sorted(missing)}')
    if h1_oof.duplicated(['episode_id','observation_time']).any():
        raise RuntimeError('H1 OOF duplicate episode_id/observation_time keys')
    q = h1_triggers.merge(
        h1_oof[['episode_id','observation_time','E_BUY_US'] + (['score'] if 'score' in h1_oof.columns else [])],
        left_on=['episode_id','exec_time'], right_on=['episode_id','observation_time'], how='inner', validate='many_to_one'
    )
    return q


def prepare_h2_score_rows(h2_scored: pd.DataFrame):
    q = h2_scored.copy()
    tstamp(q, ['trigger_time','exec_time','contact_time','c5_time','observation_time'])
    if 'E_BUY_US' not in q.columns:
        raise RuntimeError('H2 scored table missing E_BUY_US')
    return q


def match_structural(struct: pd.DataFrame, official: pd.DataFrame, time_eligible_lo: pd.Timestamp, time_eligible_hi: pd.Timestamp, window_name: str):
    official = official.copy()
    required = {'trigger_time','family','slot_rank','zlo','center','zhi','E_BUY_US'}
    missing = required - set(official.columns)
    if missing:
        raise RuntimeError(f'{window_name} official score rows missing columns: {sorted(missing)}')
    official['slot_rank'] = pd.to_numeric(official.slot_rank, errors='coerce')
    for c in ['zlo','center','zhi','E_BUY_US']:
        official[c] = pd.to_numeric(official[c], errors='coerce')
    bytime = {pd.Timestamp(t): g.copy() for t, g in official.groupby('trigger_time', sort=False)}

    mapped = []
    total = len(struct)
    unavailable_time = 0
    no_match = 0
    ambiguous = 0
    eligible = 0
    for _, r in struct.iterrows():
        et = pd.Timestamp(r['entry_time'])
        if not (time_eligible_lo <= et < time_eligible_hi):
            unavailable_time += 1
            continue
        eligible += 1
        tt = pd.Timestamp(r['trigger_time'])
        cand = bytime.get(tt)
        if cand is None or len(cand) == 0:
            no_match += 1
            continue
        cand = cand[(cand.family.astype(str) == str(r['family'])) & (cand.slot_rank == float(r['entry_rank']))].copy()
        if len(cand):
            geom = (
                (cand.zlo - float(r['e_zlo'])).abs() <= GEOM_TOL
            ) & (
                (cand.center - float(r['e_center'])).abs() <= GEOM_TOL
            ) & (
                (cand.zhi - float(r['e_zhi'])).abs() <= GEOM_TOL
            )
            cand = cand[geom].copy()
        if len(cand) == 0:
            no_match += 1
            continue
        if len(cand) > 1:
            ambiguous += 1
            continue
        s = cand.iloc[0]
        x = r.to_dict()
        x.update({
            'score_window': window_name,
            'E_BUY_US': float(s.E_BUY_US),
            'official_score_episode_id': s.get('episode_id'),
            'official_score_exec_time': s.get('exec_time', s.get('observation_time')),
        })
        mapped.append(x)
    den = eligible
    return pd.DataFrame(mapped), {
        'structural_terminal_above_main_total': total,
        'score_time_eligible_terminal': eligible,
        'time_unavailable_no_OOF_or_outside_window': unavailable_time,
        'unique_score_matched_terminal': len(mapped),
        'eligible_no_match': no_match,
        'eligible_ambiguous_multi_match': ambiguous,
        'coverage_share_of_time_eligible': (len(mapped)/den if den else None),
        'ambiguity_share_of_candidate_resolution': (ambiguous/(len(mapped)+ambiguous) if len(mapped)+ambiguous else 0.0),
        'geometry_tolerance': GEOM_TOL,
    }


def main():
    a = parse_args()
    st = pd.read_csv(a.structural_trades, compression='gzip', low_memory=False)
    tstamp(st, ['breakout_time','first_retrace_time','trigger_time','entry_time','outcome_time'])
    for c in ['entry_rank','e_zlo','e_center','e_zhi','nominal_rr']:
        st[c] = pd.to_numeric(st[c], errors='coerce')
    above = st[st.e_main_relation.astype(str) == 'ABOVE_MAIN'].copy()
    terminal = above[above.outcome.astype(str).isin(['TP_FIRST','INVALIDATION_FIRST'])].copy()

    h1_struct = terminal[(terminal.breakout_time >= H1_LO) & (terminal.breakout_time < H1_HI)].copy()
    h2_struct = terminal[(terminal.breakout_time >= H2_LO) & (terminal.breakout_time < H2_HI)].copy()

    h1tr = pd.read_csv(a.h1_triggers, compression='gzip', low_memory=False)
    h1oof = pd.read_csv(a.h1_oof, compression='gzip', low_memory=False)
    h2s = pd.read_csv(a.h2_scored, compression='gzip', low_memory=False)
    h1score = prepare_h1_score_rows(h1tr, h1oof)
    h2score = prepare_h2_score_rows(h2s)

    h1map, h1gate = match_structural(h1_struct, h1score, H1_OOF_LO, H1_HI, 'H1_OOF')
    h2map, h2gate = match_structural(h2_struct, h2score, H2_LO, H2_HI, 'H2_FROZEN_MODEL')
    mapped = pd.concat([h1map, h2map], ignore_index=True, sort=False)
    mapped.to_csv(a.mapped_csv, index=False, compression='gzip')

    h1met = score_metrics(h1map)
    h2met = score_metrics(h2map)

    amb_share = h2gate['ambiguity_share_of_candidate_resolution'] or 0.0
    if h2gate['unique_score_matched_terminal'] < 20 or amb_share > .02:
        classification = 'E_SCORE_MAPPING_INSUFFICIENT'
    else:
        a1 = h1met['continuous_auc']; a2 = h2met['continuous_auc']
        lo2 = h2met['session_cluster_bootstrap_auc']['ci95'][0]
        if a1 is None or a2 is None or a1 <= .50 or a2 <= .50:
            classification = 'E_SCORE_NOT_STABLE'
        elif lo2 is not None and lo2 > .50:
            classification = 'E_SCORE_DIRECTIONALLY_SUPPORTED'
        else:
            classification = 'E_SCORE_DIRECTIONAL_BUT_UNCERTAIN'

    out = {
        'status': 'ABOVE_MAIN_EBUY_SCORE_RETROSPECTIVE_COMPLETE',
        'classification': classification,
        'scope': 'US_08_17_NY_ABOVE_MAIN_STRUCTURAL_TERMINAL_TRADES',
        'score_definition': {
            'name': 'E_BUY_US',
            'model': 'M1_LOGISTIC_v1.1',
            'model_sha256': 'ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342',
            'meaning': 'percentile/rank in frozen H1 training score CDF; not calibrated probability',
            'refit': False,
            'recalibration': False,
        },
        'structural_definition_unchanged': True,
        'mapping': {'H1_OOF': h1gate, 'H2_FROZEN_MODEL': h2gate},
        'results': {'H1_OOF': h1met, 'H2_FROZEN_MODEL': h2met},
        'fixed_thresholds_reported': list(THRESHOLDS),
        'threshold_selection_authorized': False,
        'production_authorization': 'NONE_RETROSPECTIVE_INTERACTION_STUDY',
        'explicit_nonclaims': [
            'ABOVE_MAIN was discovered after historical structural outcomes were inspected',
            'E_BUY_US is not a probability',
            'No live profitability claim',
            'No spread/commission/slippage validation',
            'No new optimal E threshold selected',
        ],
    }
    Path(a.output).write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == '__main__':
    main()
