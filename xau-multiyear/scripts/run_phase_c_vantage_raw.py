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
from rzr.entries_v1 import simulate_one, TARGET_RS
from rzr.entries_s1 import apply_volatility_floor
from rzr.vantage_overlay import apply_fixed_spread_overlay

FAMILIES = ['DISPLACEMENT_ORIGIN', 'OBJECTIVE_LIQUIDITY', 'MEMORY', 'FVG']
STRUCTURAL_MODELS = ['PASSIVE_TOUCH', 'CLEAN_REJECTION', 'FAILED_AUCTION', 'ACCEPTANCE_RETEST', 'RECLAIM_PULLBACK']
TNO_K = (0.25, 0.50, 0.75, 1.00)
SCENARIOS = {
    'S10_C6': {'spread_usd': 0.10, 'commission_rt_usd': 6.0, 'role': 'sensitivity'},
    'S11_C6_PRIMARY': {'spread_usd': 0.11, 'commission_rt_usd': 6.0, 'role': 'primary'},
    'S12_C6': {'spread_usd': 0.12, 'commission_rt_usd': 6.0, 'role': 'sensitivity'},
    'S18_C9_STRESS': {'spread_usd': 0.18, 'commission_rt_usd': 9.0, 'role': 'stress'},
}


def pf(x: pd.Series) -> float:
    a = pd.to_numeric(x, errors='coerce').dropna()
    pos = float(a[a > 0].sum()); neg = float(-a[a < 0].sum())
    if neg <= 0: return np.inf if pos > 0 else np.nan
    return pos / neg


def main():
    ap = argparse.ArgumentParser()
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

    # Mid-price research path. Existing source BID/ASK is intentionally ignored by the Vantage overlay.
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
    masks = {f: sf.str.contains(f'\"{f}\"', regex=False) for f in FAMILIES}
    pure_doz = masks['DISPLACEMENT_ORIGIN'] & ~masks['OBJECTIVE_LIQUIDITY'] & ~masks['MEMORY'] & ~masks['FVG']
    pure_obj = masks['OBJECTIVE_LIQUIDITY'] & ~masks['DISPLACEMENT_ORIGIN'] & ~masks['MEMORY'] & ~masks['FVG']
    pure_mem = masks['MEMORY'] & ~masks['DISPLACEMENT_ORIGIN'] & ~masks['OBJECTIVE_LIQUIDITY'] & ~masks['FVG']
    doz_obj = masks['DISPLACEMENT_ORIGIN'] & masks['OBJECTIVE_LIQUIDITY'] & ~masks['MEMORY'] & ~masks['FVG']
    samples = {
        'DISPLACEMENT_ORIGIN_ONLY': pure_doz,
        'OBJECTIVE_LIQUIDITY_ONLY': pure_obj,
        'MEMORY_ONLY': pure_mem,
        'DOZ_OBJECTIVE_ONLY': doz_obj,
    }

    records = []
    entry_counts = {}
    for scenario, sc in SCENARIOS.items():
        bars_exec = apply_fixed_spread_overlay(bars_mid, sc['spread_usd'])
        commission = float(sc['commission_rt_usd'])
        for sample, mask in samples.items():
            g = contacts[mask]
            rows = g.to_dict('records')

            for model in STRUCTURAL_MODELS:
                built = 0
                for rec in rows:
                    entry = build_entry(rec, bars_exec, model, acceptance_minutes=cfg.acceptance_minutes)
                    if entry is None: continue
                    built += 1
                    for tr in TARGET_RS:
                        sim = simulate_one(entry, bars_exec, tr, horizon_minutes=args.horizon_minutes, commission_rt_per_lot=commission)
                        records.append({
                            'scenario': scenario, 'scenario_role': sc['role'], 'spread_usd': sc['spread_usd'],
                            'commission_rt_usd': commission, 'sample': sample, 'entry_model': model,
                            'risk_rule': 'STRUCTURAL', 'vol_floor_k': np.nan, 'target_r': float(tr),
                            'gross_R': sim['gross_R'], 'net_R': sim['net_R_legacy22'], 'result': sim['result'],
                            'ambiguous_same_bar': bool(sim['ambiguous_same_bar']), 'risk_price': entry['risk_price'],
                            'entry_delay_minutes': entry['entry_delay_minutes'],
                        })
                entry_counts[f'{scenario}:{sample}:{model}:STRUCTURAL'] = int(built)

            # Raw TOUCH_NEXT_OPEN is audit-only. Recalculate the complete previously-frozen risk-floor grid.
            for k in TNO_K:
                built = 0
                for rec in rows:
                    e0 = build_entry(rec, bars_exec, 'TOUCH_NEXT_OPEN', acceptance_minutes=cfg.acceptance_minutes)
                    if e0 is None: continue
                    entry = apply_volatility_floor(e0, k)
                    if entry is None: continue
                    built += 1
                    for tr in TARGET_RS:
                        sim = simulate_one(entry, bars_exec, tr, horizon_minutes=args.horizon_minutes, commission_rt_per_lot=commission)
                        records.append({
                            'scenario': scenario, 'scenario_role': sc['role'], 'spread_usd': sc['spread_usd'],
                            'commission_rt_usd': commission, 'sample': sample, 'entry_model': 'TOUCH_NEXT_OPEN',
                            'risk_rule': f'VOL_FLOOR_{k:.2f}', 'vol_floor_k': float(k), 'target_r': float(tr),
                            'gross_R': sim['gross_R'], 'net_R': sim['net_R_legacy22'], 'result': sim['result'],
                            'ambiguous_same_bar': bool(sim['ambiguous_same_bar']), 'risk_price': entry['risk_price'],
                            'entry_delay_minutes': entry['entry_delay_minutes'],
                        })
                entry_counts[f'{scenario}:{sample}:TOUCH_NEXT_OPEN:VOL_FLOOR_{k:.2f}'] = int(built)

    trades = pd.DataFrame(records)
    rows = []
    if not trades.empty:
        keys = ['scenario','scenario_role','spread_usd','commission_rt_usd','sample','entry_model','risk_rule','vol_floor_k','target_r']
        # dropna=False keeps structural cells whose vol_floor_k is NA.
        for key, g in trades.groupby(keys, sort=True, dropna=False):
            scenario, role, spread, comm, sample, model, risk_rule, k, tr = key
            rows.append({
                'scenario': scenario, 'scenario_role': role, 'spread_usd': float(spread), 'commission_rt_usd': float(comm),
                'sample': sample, 'entry_model': model, 'risk_rule': risk_rule,
                'vol_floor_k': float(k) if pd.notna(k) else np.nan, 'target_r': float(tr), 'trades': int(len(g)),
                'tp_pct': 100.0 * float((g.result == 'TP').mean()), 'sl_pct': 100.0 * float((g.result == 'SL').mean()),
                'time_pct': 100.0 * float((g.result == 'TIME').mean()),
                'ambiguous_same_bar_pct': 100.0 * float(g.ambiguous_same_bar.mean()),
                'avg_gross_R': float(g.gross_R.mean()), 'pf_gross': float(pf(g.gross_R)),
                'avg_net_R': float(g.net_R.mean()), 'pf_net': float(pf(g.net_R)),
                'median_risk_price': float(g.risk_price.median()), 'min_risk_price': float(g.risk_price.min()),
                'median_entry_delay_minutes': float(g.entry_delay_minutes.median()), 'sum_net_R': float(g.net_R.sum()),
            })
    summary = pd.DataFrame(rows)
    summary.to_csv(outdir / 'summary.csv', index=False)
    manifest = {
        'source_commit': os.getenv('GITHUB_SHA','LOCAL'),
        'version': 'PHASE_C_VANTAGE_RAW_RECALC_V1',
        'spec': 'PHASE_C_VANTAGE_RAW_RECALC_SPEC.md',
        'target_start': str(start), 'target_end': str(end), 'bars': int(len(bars_mid)),
        'zones_generated': int(len(zones)), 'target_events': int(len(contacts)),
        'scenarios': SCENARIOS, 'structural_models': STRUCTURAL_MODELS,
        'touch_next_open_vol_floor_k': list(TNO_K), 'target_R_surface': list(TARGET_RS),
        'horizon_minutes': int(args.horizon_minutes),
        'execution_overlay': 'fixed symmetric Vantage-like BID/ASK around unchanged Dukascopy mid OHLC',
        'entry_counts': entry_counts,
    }
    (outdir / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    if len(summary):
        primary = summary[summary.scenario == 'S11_C6_PRIMARY'].sort_values('avg_net_R', ascending=False)
        print('PRIMARY_TOP')
        print(primary.head(30).to_string(index=False))

if __name__ == '__main__':
    main()
