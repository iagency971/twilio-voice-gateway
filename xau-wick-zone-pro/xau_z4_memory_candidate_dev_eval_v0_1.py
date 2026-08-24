import argparse, importlib.util, json, math, sys
from pathlib import Path

import numpy as np
import pandas as pd


def load_completion_module():
    here = Path(__file__).resolve().parent
    path = here / 'xau_wick_zone_completion_models.py'
    spec = importlib.util.spec_from_file_location('z4cm', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def finite_quantile(x, q):
    a = np.asarray(x, float)
    a = a[np.isfinite(a)]
    return None if len(a) == 0 else float(np.quantile(a, q))


def stability(D):
    D = D.copy()
    D['time'] = pd.to_datetime(D['time'], utc=True)
    if len(D) == 0:
        return {'rows': 0}

    zpl = D.groupby('landmark_i').size().to_numpy(int)
    lens = D.groupby('lineage_id').size().to_numpy(int)
    last_lm = int(D.landmark_i.max())

    # Each lineage of n snapshots contributes n-1 successful consecutive
    # continuations. The denominator is every zone snapshot with a later
    # represented landmark in the dataset. Z4 itself forbids gap bridging.
    denom = int((D.landmark_i < last_lm).sum())
    successful = int(np.maximum(lens - 1, 0).sum())
    continuation = None if denom <= 0 else float(successful / denom)

    out = {
        'zone_snapshots': int(len(D)),
        'represented_landmarks': int(D.landmark_i.nunique()),
        'lineages': int(D.lineage_id.nunique()),
        'zones_per_represented_landmark': {
            'mean': float(np.mean(zpl)),
            'median': float(np.median(zpl)),
            'p90': float(np.quantile(zpl, .90)),
            'p95': float(np.quantile(zpl, .95)),
            'max': int(np.max(zpl)),
        },
        'lineage_length_snapshots': {
            'mean': float(np.mean(lens)),
            'median': float(np.median(lens)),
            'p90': float(np.quantile(lens, .90)),
            'p95': float(np.quantile(lens, .95)),
            'max': int(np.max(lens)),
        },
        'lineage_share_ge_2': float(np.mean(lens >= 2)),
        'lineage_share_ge_4': float(np.mean(lens >= 4)),
        'lineage_share_ge_8': float(np.mean(lens >= 8)),
        'one_step_continuation_rate': continuation,
        'one_step_drop_churn_rate': None if continuation is None else float(1.0 - continuation),
    }

    if 'center_shift_vseg' in D.columns:
        x = np.abs(D['center_shift_vseg'].to_numpy(float))
        out['abs_center_shift_vseg'] = {
            'median': finite_quantile(x, .50),
            'p95': finite_quantile(x, .95),
        }
    if 'width_log_change' in D.columns:
        x = np.abs(D['width_log_change'].to_numpy(float))
        out['abs_width_log_change'] = {
            'median': finite_quantile(x, .50),
            'p95': finite_quantile(x, .95),
        }
    return out


def compact_feed(F):
    folds = {}
    for name in ['APR', 'MAY', 'JUN', 'JUL']:
        r = F['folds'][name]['revisit']['models']['M0GL']
        folds[name] = {
            'delta_brier': float(r['delta_brier']),
            'delta_logloss': float(r['delta_logloss']),
        }
    P = F['revisit_oof_pooled']
    W = F['revisit_weekly']
    return {
        'rows': int(F['rows']),
        'landmarks': int(F['landmarks']),
        'lineages': int(F['lineages']),
        'folds': folds,
        'pooled': {
            'M0_brier': float(P['M0_brier']),
            'M0GL_brier': float(P['M0GL_brier']),
            'delta_brier': float(P['delta_brier']),
            'M0_logloss': float(P['M0_logloss']),
            'M0GL_logloss': float(P['M0GL_logloss']),
            'delta_logloss': float(P['delta_logloss']),
        },
        'weekly': {
            'n_weeks': int(W['n_weeks']),
            'positive_weeks': int(W['positive_weeks']),
            'mean_delta_brier': float(W['mean_delta_brier']),
            'bootstrap_95': [float(W['bootstrap_95'][0]), float(W['bootstrap_95'][1])],
        },
        'dev_sign_checks': F['dev_sign_checks'],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bid-pkl', required=True)
    p.add_argument('--ask-pkl', required=True)
    p.add_argument('--lookback', type=int, required=True)
    p.add_argument('--engine-patch-json', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()

    if a.lookback not in {240, 360, 600, 900, 1440}:
        raise RuntimeError('lookback not preregistered')

    cm = load_completion_module()
    bid = pd.read_pickle(a.bid_pkl)
    ask = pd.read_pickle(a.ask_pkl)

    print('MEMORY', a.lookback, 'BID evaluation', flush=True)
    BF = cm.feed_eval(bid, f'BID_L{a.lookback}')
    print('MEMORY', a.lookback, 'ASK evaluation', flush=True)
    AF = cm.feed_eval(ask, f'ASK_L{a.lookback}')

    bc = compact_feed(BF)
    ac = compact_feed(AF)

    bid_robust = bool(
        all(bc['folds'][x]['delta_brier'] > 0 for x in ['APR','MAY','JUN','JUL'])
        and bc['pooled']['delta_brier'] > 0
        and bc['weekly']['bootstrap_95'][0] > 0
    )
    dual_strong = bool(
        bid_robust
        and all(ac['folds'][x]['delta_brier'] > 0 for x in ['APR','MAY','JUN','JUL'])
        and ac['pooled']['delta_brier'] > 0
        and ac['weekly']['bootstrap_95'][0] > 0
    )

    out = {
        'status': 'DEV_MEMORY_SENSITIVITY_CANDIDATE_COMPLETE_NO_PROMOTION',
        'lookback_active_m1': int(a.lookback),
        'incumbent_control': bool(a.lookback == 1440),
        'scientific_endpoint': 'REVISIT_240',
        'landmark_cadence': '15-minute UTC',
        'frozen_reference_engine_git_blob': 'a8a147615c3fd366c49e93b340fd2018b5b66e9e',
        'engine_patch_attestation': json.load(open(a.engine_patch_json)),
        'BID': bc,
        'ASK': ac,
        'geometry_stability': {
            'BID': stability(bid),
            'ASK': stability(ask),
        },
        'preregistered_flags': {
            'BID_ROBUST_PASS': bid_robust,
            'DUAL_FEED_STRONG_PASS': dual_strong,
        },
        'limits': [
            'DEV Jan-Jul 2024 only.',
            'No candidate is promoted by this file.',
            'Raw Brier across different zone populations is not a standalone winner criterion.',
            'No Validation/OOS data used.',
        ],
    }
    Path(a.output).write_text(json.dumps(out, indent=2, allow_nan=False))
    print(json.dumps({
        'lookback': a.lookback,
        'BID_delta_brier': bc['pooled']['delta_brier'],
        'ASK_delta_brier': ac['pooled']['delta_brier'],
        'BID_weekly_ci': bc['weekly']['bootstrap_95'],
        'ASK_weekly_ci': ac['weekly']['bootstrap_95'],
        'BID_ROBUST_PASS': bid_robust,
        'DUAL_FEED_STRONG_PASS': dual_strong,
        'BID_churn': out['geometry_stability']['BID']['one_step_drop_churn_rate'],
    }, indent=2), flush=True)


if __name__ == '__main__':
    main()
