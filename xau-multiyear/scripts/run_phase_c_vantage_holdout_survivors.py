#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, os, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from rzr.config import ResearchConfig
from rzr.io import load_ohlc_csv
from rzr.features import quote_activity_mask, robust_sigma60
from rzr.zones import generate_baseline_zones
from rzr.contacts import find_first_contacts
from rzr.stacking import collapse_contact_events
from rzr.labels import label_contacts
from rzr.behavior_v2 import classify_behavior_v2
from rzr.entries_v2 import build_entry
from rzr.entries_v1 import simulate_one
from rzr.entries_s1 import apply_volatility_floor
from rzr.vantage_overlay import apply_fixed_spread_overlay

SCENARIOS = {
    'S10_C6': {'spread_usd': 0.10, 'commission_rt_usd': 6.0, 'role': 'sensitivity'},
    'S11_C6_PRIMARY': {'spread_usd': 0.11, 'commission_rt_usd': 6.0, 'role': 'primary'},
    'S12_C6': {'spread_usd': 0.12, 'commission_rt_usd': 6.0, 'role': 'sensitivity'},
    'S18_C9_STRESS': {'spread_usd': 0.18, 'commission_rt_usd': 9.0, 'role': 'stress'},
}
CLEAN_RR = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
TNO_CELLS = ((0.50, 2.5), (0.75, 3.0))


def pf(x: pd.Series) -> float:
    a = pd.to_numeric(x, errors='coerce').dropna()
    pos = float(a[a > 0].sum()); neg = float(-a[a < 0].sum())
    if neg <= 0:
        return np.inf if pos > 0 else np.nan
    return pos / neg


def _zero_summary_row(scenario: str, sc: dict, model: str, risk_rule: str,
                      vol_floor_k: float, target_r: float) -> dict:
    """Represent a frozen cell with no executable trades without dropping the cell."""
    return {
        'scenario': scenario, 'scenario_role': sc['role'], 'spread_usd': float(sc['spread_usd']),
        'commission_rt_usd': float(sc['commission_rt_usd']), 'sample': 'DOZ_OBJECTIVE_ONLY',
        'entry_model': model, 'risk_rule': risk_rule, 'vol_floor_k': vol_floor_k,
        'target_r': float(target_r), 'trades': 0, 'tp_pct': np.nan, 'sl_pct': np.nan,
        'time_pct': np.nan, 'ambiguous_same_bar_pct': np.nan, 'avg_gross_R': np.nan,
        'pf_gross': np.nan, 'avg_net_R': np.nan, 'pf_net': np.nan,
        'median_risk_price': np.nan, 'min_risk_price': np.nan,
        'median_entry_delay_minutes': np.nan, 'sum_net_R': 0.0,
    }


def main():
    ap = argparse.ArgumentParser(description='Frozen eight-cell Vantage holdout runner; no cell discovery.')
    ap.add_argument('csv')
    ap.add_argument('--target-start', required=True)
    ap.add_argument('--target-end', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--horizon-minutes', type=int, default=120)
    args = ap.parse_args()

    start = pd.Timestamp(args.target_start); start = start.tz_localize('UTC') if start.tzinfo is None else start.tz_convert('UTC')
    end = pd.Timestamp(args.target_end); end = end.tz_localize('UTC') if end.tzinfo is None else end.tz_convert('UTC')
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    cfg = ResearchConfig()

    # Research path is exactly the same unchanged mid-price path as the full corrected Vantage run.
    bars_mid = load_ohlc_csv(args.csv).sort_index().copy()
    bars_mid['quote_active'] = quote_activity_mask(bars_mid)
    bars_mid['sigma60'] = robust_sigma60(bars_mid)
    zones = generate_baseline_zones(bars_mid, cfg)
    contacts = find_first_contacts(bars_mid, zones, bars_mid['sigma60'], cfg)
    contacts = collapse_contact_events(contacts, cfg.stack_overlap_threshold)
    contacts = label_contacts(bars_mid, contacts, cfg)
    contacts = classify_behavior_v2(bars_mid, contacts, cfg)
    if not contacts.empty:
        ct = pd.to_datetime(contacts['contact_time'], utc=True)
        contacts = contacts[(ct >= start) & (ct < end)].copy()

    sf = contacts.get('constituent_families', pd.Series('', index=contacts.index)).fillna('')
    doz = sf.str.contains('"DISPLACEMENT_ORIGIN"', regex=False)
    obj = sf.str.contains('"OBJECTIVE_LIQUIDITY"', regex=False)
    mem = sf.str.contains('"MEMORY"', regex=False)
    fvg = sf.str.contains('"FVG"', regex=False)
    sample = contacts[doz & obj & ~mem & ~fvg].copy()
    recs = sample.to_dict('records')

    rows = []
    counts = {}
    for scenario, sc in SCENARIOS.items():
        bars_exec = apply_fixed_spread_overlay(bars_mid, sc['spread_usd'])
        commission = float(sc['commission_rt_usd'])

        clean_entries = []
        for rec in recs:
            e = build_entry(rec, bars_exec, 'CLEAN_REJECTION', acceptance_minutes=cfg.acceptance_minutes)
            if e is not None:
                clean_entries.append(e)
        counts[f'{scenario}:CLEAN_REJECTION'] = len(clean_entries)
        for tr in CLEAN_RR:
            sims = [simulate_one(e, bars_exec, tr, horizon_minutes=args.horizon_minutes, commission_rt_per_lot=commission) for e in clean_entries]
            for e, sim in zip(clean_entries, sims):
                rows.append({
                    'scenario': scenario, 'scenario_role': sc['role'], 'spread_usd': sc['spread_usd'],
                    'commission_rt_usd': commission, 'sample': 'DOZ_OBJECTIVE_ONLY',
                    'entry_model': 'CLEAN_REJECTION', 'risk_rule': 'STRUCTURAL', 'vol_floor_k': np.nan,
                    'target_r': float(tr), 'gross_R': sim['gross_R'], 'net_R': sim['net_R_legacy22'],
                    'result': sim['result'], 'ambiguous_same_bar': bool(sim['ambiguous_same_bar']),
                    'risk_price': e['risk_price'], 'entry_delay_minutes': e['entry_delay_minutes'],
                })

        tno_base = []
        for rec in recs:
            e = build_entry(rec, bars_exec, 'TOUCH_NEXT_OPEN', acceptance_minutes=cfg.acceptance_minutes)
            if e is not None:
                tno_base.append(e)
        for k, tr in TNO_CELLS:
            entries = [apply_volatility_floor(e, k) for e in tno_base]
            entries = [e for e in entries if e is not None]
            counts[f'{scenario}:TOUCH_NEXT_OPEN:VOL_FLOOR_{k:.2f}:RR{tr:.1f}'] = len(entries)
            sims = [simulate_one(e, bars_exec, tr, horizon_minutes=args.horizon_minutes, commission_rt_per_lot=commission) for e in entries]
            for e, sim in zip(entries, sims):
                rows.append({
                    'scenario': scenario, 'scenario_role': sc['role'], 'spread_usd': sc['spread_usd'],
                    'commission_rt_usd': commission, 'sample': 'DOZ_OBJECTIVE_ONLY',
                    'entry_model': 'TOUCH_NEXT_OPEN', 'risk_rule': f'VOL_FLOOR_{k:.2f}', 'vol_floor_k': float(k),
                    'target_r': float(tr), 'gross_R': sim['gross_R'], 'net_R': sim['net_R_legacy22'],
                    'result': sim['result'], 'ambiguous_same_bar': bool(sim['ambiguous_same_bar']),
                    'risk_price': e['risk_price'], 'entry_delay_minutes': e['entry_delay_minutes'],
                })

    trades = pd.DataFrame(rows)
    summaries = []
    group_cols = ['scenario','scenario_role','spread_usd','commission_rt_usd','sample','entry_model','risk_rule','vol_floor_k','target_r']
    if not trades.empty:
        for key, g in trades.groupby(group_cols, sort=True, dropna=False):
            scenario, role, spread, comm, sample_name, model, risk_rule, k, tr = key
            summaries.append({
                'scenario':scenario,'scenario_role':role,'spread_usd':float(spread),'commission_rt_usd':float(comm),
                'sample':sample_name,'entry_model':model,'risk_rule':risk_rule,
                'vol_floor_k':float(k) if pd.notna(k) else np.nan,'target_r':float(tr),'trades':int(len(g)),
                'tp_pct':100.0*float((g.result=='TP').mean()),'sl_pct':100.0*float((g.result=='SL').mean()),
                'time_pct':100.0*float((g.result=='TIME').mean()),'ambiguous_same_bar_pct':100.0*float(g.ambiguous_same_bar.mean()),
                'avg_gross_R':float(g.gross_R.mean()),'pf_gross':float(pf(g.gross_R)),
                'avg_net_R':float(g.net_R.mean()),'pf_net':float(pf(g.net_R)),
                'median_risk_price':float(g.risk_price.median()),'min_risk_price':float(g.risk_price.min()),
                'median_entry_delay_minutes':float(g.entry_delay_minutes.median()),'sum_net_R':float(g.net_R.sum()),
            })

    # A frozen cell with zero executable trades is evidence too. Keep it in the table instead of
    # letting pandas groupby silently omit it and turning a low-N holdout into a workflow failure.
    def cell_key(r):
        return (str(r['scenario']), str(r['entry_model']), str(r['risk_rule']), round(float(r['target_r']), 6))
    present = {cell_key(r) for r in summaries}
    for scenario, sc in SCENARIOS.items():
        for tr in CLEAN_RR:
            row = _zero_summary_row(scenario, sc, 'CLEAN_REJECTION', 'STRUCTURAL', np.nan, tr)
            if cell_key(row) not in present:
                summaries.append(row); present.add(cell_key(row))
        for k, tr in TNO_CELLS:
            row = _zero_summary_row(scenario, sc, 'TOUCH_NEXT_OPEN', f'VOL_FLOOR_{k:.2f}', float(k), tr)
            if cell_key(row) not in present:
                summaries.append(row); present.add(cell_key(row))

    summary = pd.DataFrame(summaries).sort_values(['scenario','entry_model','target_r']).reset_index(drop=True)
    assert len(summary) == 32, len(summary)
    summary.to_csv(outdir/'survivors_holdout.csv', index=False)
    manifest = {
        'source_commit':os.getenv('GITHUB_SHA','LOCAL'),'version':'PHASE_C_VANTAGE_HOLDOUT_SURVIVORS_V1_ZERO_CELL_REPORTING_FIX',
        'target_start':str(start),'target_end':str(end),'bars':int(len(bars_mid)),'zones_generated':int(len(zones)),
        'target_events':int(len(contacts)),'doz_objective_only_events':int(len(sample)),
        'frozen_clean_rejection_rr':list(CLEAN_RR),'frozen_tno_cells':[{'k':k,'target_r':tr} for k,tr in TNO_CELLS],
        'scenarios':SCENARIOS,'horizon_minutes':int(args.horizon_minutes),'entry_counts':counts,
        'scientific_rule':'Exactly the eight 2011-2025 survivors; no holdout cell discovery.',
        'reporting_fix':'Frozen zero-trade cells are explicitly retained with trades=0 and NaN performance instead of failing publication.'
    }
    (outdir/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2)); print(summary.to_string(index=False))

if __name__ == '__main__':
    main()
