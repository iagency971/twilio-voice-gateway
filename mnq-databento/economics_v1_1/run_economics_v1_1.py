#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path('mnq-databento')
RAW = ROOT / 'results/cme_validation_v1/databento_nq_1m.csv.gz'
ROLL_DIAG = ROOT / 'roll_diag/results/RESULT.json'
OUT = ROOT / 'results/cme_validation_v1_1'
OUT.mkdir(parents=True, exist_ok=True)

# Reuse the already-frozen execution/statistics implementation. Importing does not run its paid main().
sys.path.insert(0, str(ROOT.resolve()))
import run_cme_validation_v1 as base  # noqa: E402

base.OUTDIR = OUT
EVAL_START = pd.Timestamp('2026-08-03 00:00:00')
EVAL_END = pd.Timestamp('2026-08-19 23:59:59')
HALF_SPLIT = pd.Timestamp('2026-08-12 00:00:00')
EXPECTED = [d.date() for d in pd.bdate_range('2026-08-03', '2026-08-19')]
EST_COST = 0.294231325388


def dump(obj, name):
    (OUT / name).write_text(json.dumps(obj, indent=2, allow_nan=False, default=str))


def roll_aware_qa(d: pd.DataFrame, roll_diag: dict) -> dict:
    d = d.sort_values('datetime').reset_index(drop=True).copy()
    dup = int(d.duplicated('datetime').sum())
    bad_ohlc = int(((d.low > d.high) | (d.open < d.low) | (d.open > d.high) |
                    (d.close < d.low) | (d.close > d.high)).sum())
    t = d.datetime.dt.time
    rth = d[(t >= pd.Timestamp('09:30').time()) & (t < pd.Timestamp('16:00').time())].copy()
    rth['date'] = rth.datetime.dt.date
    counts = rth.groupby('date').size()
    aug_counts = counts[counts.index.isin(EXPECTED)]
    missing = [str(x) for x in EXPECTED if x not in set(aug_counts.index)]

    prices = d[['open','high','low','close']].to_numpy(dtype=float)
    plausible = bool(np.isfinite(prices).all() and np.nanmin(prices) > 10000 and np.nanmax(prices) < 50000)

    delta = d.datetime.diff().dt.total_seconds().div(60)
    jumps = d.index[(delta <= 2.0) & (d.close.diff().abs() > 250.0)].tolist()
    actual_jump_times = [str(pd.Timestamp(d.iloc[i].datetime)) for i in jumps]
    diag_jumps = roll_diag.get('large_intraday_jumps', [])
    diag_times = [str(pd.Timestamp(x['datetime_et'])) for x in diag_jumps]
    roll_exemptions_exact = (
        len(jumps) == len(diag_jumps) and
        sorted(actual_jump_times) == sorted(diag_times) and
        bool(roll_diag.get('all_large_jumps_coincide_with_mapping_change'))
    )

    aug = d[(d.datetime >= EVAL_START) & (d.datetime <= EVAL_END)].copy()
    aug_delta = aug.datetime.diff().dt.total_seconds().div(60)
    aug_large = int(((aug_delta <= 2.0) & (aug.close.diff().abs() > 250.0)).sum())

    qa = {
        'estimated_original_download_cost_usd': EST_COST,
        'additional_paid_data_request_for_v1_1': False,
        'rows': int(len(d)),
        'min_datetime_et': str(d.datetime.min()),
        'max_datetime_et': str(d.datetime.max()),
        'duplicate_timestamps': dup,
        'ohlc_consistency_violations': bad_ohlc,
        'expected_aug_rth_dates': len(EXPECTED),
        'observed_aug_rth_dates': int(len(aug_counts)),
        'missing_aug_rth_dates': missing,
        'median_aug_rth_bars': float(aug_counts.median()) if len(aug_counts) else None,
        'min_aug_rth_bars': int(aug_counts.min()) if len(aug_counts) else None,
        'price_min': float(np.nanmin(prices)),
        'price_max': float(np.nanmax(prices)),
        'plausible_nq_scale': plausible,
        'adjacent_minute_jump_gt250_count': int(len(jumps)),
        'adjacent_minute_jump_times_et': actual_jump_times,
        'roll_mapping_intervals': roll_diag.get('continuous_mapping_intervals', []),
        'roll_raw_symbols': roll_diag.get('instrument_id_to_raw_symbol', {}),
        'all_large_jumps_exactly_verified_roll_boundaries': bool(roll_exemptions_exact),
        'confirmatory_aug3_19_large_jump_count': aug_large,
    }
    qa['pass'] = bool(
        len(d) > 0 and dup == 0 and bad_ohlc == 0 and not missing and
        qa['median_aug_rth_bars'] is not None and qa['median_aug_rth_bars'] >= 380 and
        plausible and roll_exemptions_exact and aug_large == 0
    )
    return qa


def grouped(df, value_col, group_col):
    return {str(k): base.stats(g[value_col].to_numpy()) for k, g in df.groupby(group_col)}


def main():
    d = pd.read_csv(RAW, compression='gzip')
    d['datetime'] = pd.to_datetime(d['datetime'], errors='coerce')
    for c in ['open','high','low','close','volume']:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    d = d.dropna(subset=['datetime','open','high','low','close']).sort_values('datetime').reset_index(drop=True)
    roll_diag = json.loads(ROLL_DIAG.read_text())
    qa = roll_aware_qa(d, roll_diag)
    dump(qa, 'data_qa_v1_1.json')
    if not qa['pass']:
        dump({'status':'CME_DATA_QA_V1_1_FAIL_NO_ECONOMIC_INTERPRETATION','data_qa':qa}, 'RESULT.json')
        return

    ext = base.ensure_external()
    cme_csv = ext / 'data' / 'databento_nq_1m.csv'
    d.to_csv(cme_csv, index=False)
    daily_csv = base.build_daily_context(ext, d)
    trades = base.run_external(ext, cme_csv, daily_csv)
    trades['entry_time'] = pd.to_datetime(trades.entry_time, errors='coerce')
    trades = trades.dropna(subset=['entry_time']).sort_values('entry_time').reset_index(drop=True)

    ev = trades[(trades.entry_time >= EVAL_START) & (trades.entry_time <= EVAL_END)].copy().reset_index(drop=True)
    if ev.empty:
        raise RuntimeError('Pinned external engine generated no confirmatory August trades')
    ev['primary_r'] = base.rescore(ev, 1.0)
    ev['stress_r'] = base.rescore(ev, 2.0)
    ev['half'] = np.where(ev.entry_time < HALF_SPLIT, 'Aug03_11', 'Aug12_19')
    ev['date'] = ev.entry_time.dt.date.astype(str)
    ev.to_csv(OUT / 'august_trades_rescored.csv', index=False)

    diag = trades[(trades.entry_time >= pd.Timestamp('2026-06-01')) &
                  (trades.entry_time < pd.Timestamp('2026-08-01'))].copy().reset_index(drop=True)
    if len(diag):
        diag['primary_r'] = base.rescore(diag, 1.0)
        diag['stress_r'] = base.rescore(diag, 2.0)
        diag['month'] = diag.entry_time.dt.to_period('M').astype(str)
        diag.to_csv(OUT / 'jun_jul_trades_diagnostic.csv', index=False)

    prim = base.stats(ev.primary_r.to_numpy())
    stress = base.stats(ev.stress_r.to_numpy())
    rb10, rb_n = base.remove_best_mean(ev.primary_r.to_numpy(), 0.10)
    halves_p = grouped(ev, 'primary_r', 'half')
    halves_s = grouped(ev, 'stress_r', 'half')
    observed_days = qa['observed_aug_rth_dates']
    tpd = float(len(ev) / observed_days) if observed_days else 0.0

    gates = {
        'data_qa_pass': bool(qa['pass']),
        'n_ge_25': len(ev) >= 25,
        'trades_per_day_ge_1_5': tpd >= 1.5,
        'primary_mean_ge_0_10R': prim['mean'] is not None and prim['mean'] >= 0.10,
        'primary_pf_ge_1_25': prim['pf'] is not None and prim['pf'] >= 1.25,
        'aug03_11_positive': halves_p.get('Aug03_11',{}).get('sum',0.0) > 0,
        'aug12_19_positive': halves_p.get('Aug12_19',{}).get('sum',0.0) > 0,
        'primary_max_dd_le_7R': prim['max_dd'] is not None and prim['max_dd'] <= 7.0,
        'remove_best_10pct_mean_nonnegative': rb10 is not None and rb10 >= 0.0,
        'stress_mean_positive': stress['mean'] is not None and stress['mean'] > 0.0,
        'stress_pf_ge_1_10': stress['pf'] is not None and stress['pf'] >= 1.10,
    }
    verdict = 'CME_AUGUST_CONFIRMATORY_PASS_FOR_PROPFIRM_SIMULATION' if all(gates.values()) else 'CME_AUGUST_CONFIRMATORY_NO_GO'

    result = {
        'status': verdict,
        'protocol': 'PROTOCOL_CME_VALIDATION_V1_1_ROLL_QA_AMENDMENT',
        'external_repo': base.EXT_REPO,
        'external_commit': base.EXT_SHA,
        'official_data': 'Databento GLBX.MDP3 NQ.v.0 ohlcv-1m',
        'original_download_estimated_cost_usd': EST_COST,
        'additional_paid_cost_v1_1_usd': 0.0,
        'data_qa': qa,
        'evaluation_start': str(EVAL_START),
        'evaluation_end': str(EVAL_END),
        'observed_august_rth_days': observed_days,
        'trades_per_day': tpd,
        'scenarios': {
            'PRIMARY': {
                'full': prim,
                'by_half': halves_p,
                'by_model': grouped(ev,'primary_r','model'),
                'by_direction': grouped(ev,'primary_r','direction'),
                'remove_best_10pct_mean': rb10,
                'removed_best_n': rb_n,
            },
            'STRESS': {
                'full': stress,
                'by_half': halves_s,
                'by_model': grouped(ev,'stress_r','model'),
                'by_direction': grouped(ev,'stress_r','direction'),
            },
        },
        'jun_jul_diagnostic_only': {
            'n': int(len(diag)),
            'PRIMARY': base.stats(diag.primary_r.to_numpy()) if len(diag) else base.stats([]),
            'STRESS': base.stats(diag.stress_r.to_numpy()) if len(diag) else base.stats([]),
            'by_month_primary': grouped(diag,'primary_r','month') if len(diag) else {},
        },
        'gates': gates,
        'notes': [
            'Official Databento CME data is authoritative for the verdict.',
            'The single Jun16 20:00 ET discontinuity is the verified NQM6->NQU6 unadjusted continuous roll.',
            'No comparable discontinuity exists in Aug3-Aug19.',
            'The pinned May31 external strategy is unchanged.',
            'No model/direction/date rescue is permitted after this result.',
        ],
    }
    dump(result, 'RESULT.json')
    print(json.dumps(result, indent=2, allow_nan=False, default=str))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        dump({'status':'CME_VALIDATION_V1_1_INVALID_ABORT','error_type':type(exc).__name__,'error':str(exc)}, 'RESULT.json')
        raise
