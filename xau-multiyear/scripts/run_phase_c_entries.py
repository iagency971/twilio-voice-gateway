#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, sys
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
from rzr.entries_v1 import build_entry, simulate_surface, TARGET_RS

FAMILIES = ['DISPLACEMENT_ORIGIN', 'OBJECTIVE_LIQUIDITY', 'MEMORY', 'FVG']
ENTRY_MODELS = ['TOUCH_NEXT_OPEN', 'CLEAN_REJECTION', 'FAILED_AUCTION', 'ACCEPTANCE_RETEST']


def pf(x: pd.Series) -> float:
    a = pd.to_numeric(x, errors='coerce').dropna()
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg <= 0:
        return np.inf if pos > 0 else np.nan
    return pos / neg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--target-start', required=True)
    ap.add_argument('--target-end', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--horizon-minutes', type=int, default=120)
    args = ap.parse_args()

    start = pd.Timestamp(args.target_start)
    start = start.tz_localize('UTC') if start.tzinfo is None else start.tz_convert('UTC')
    end = pd.Timestamp(args.target_end)
    end = end.tz_localize('UTC') if end.tzinfo is None else end.tz_convert('UTC')
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    cfg = ResearchConfig()

    bars = load_ohlc_csv(args.csv).sort_index().copy()
    required_exec = ['open_bid','high_bid','low_bid','close_bid','open_ask','high_ask','low_ask','close_ask','spread']
    missing = [c for c in required_exec if c not in bars.columns]
    if missing:
        raise ValueError(f'Missing BID/ASK execution columns: {missing}')
    bars['quote_active'] = quote_activity_mask(bars)
    bars['sigma60'] = robust_sigma60(bars)

    zones = generate_baseline_zones(bars, cfg)
    contacts = find_first_contacts(bars, zones, bars['sigma60'], cfg)
    contacts = collapse_contact_events(contacts, cfg.stack_overlap_threshold)
    contacts = label_contacts(bars, contacts, cfg)
    contacts = classify_behavior_v2(bars, contacts, cfg)
    if not contacts.empty:
        ct = pd.to_datetime(contacts['contact_time'], utc=True)
        contacts = contacts[(ct >= start) & (ct < end)].copy()

    sf = contacts.get('constituent_families', pd.Series('', index=contacts.index)).fillna('')
    masks = {f: sf.str.contains(f'"{f}"', regex=False) for f in FAMILIES}
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
    for sample, mask in samples.items():
        g = contacts[mask]
        for model in ENTRY_MODELS:
            built = 0
            for rec in g.to_dict('records'):
                entry = build_entry(rec, bars, model, acceptance_minutes=cfg.acceptance_minutes)
                if entry is None:
                    continue
                built += 1
                base = {
                    'sample': sample,
                    'entry_model': model,
                    'stack_id': rec.get('stack_id'),
                    'zone_id': rec.get('zone_id'),
                    'contact_time': rec.get('contact_time'),
                    'behavior_v2': rec.get('behavior_v2'),
                    'direction': entry['direction'],
                    'entry_idx': entry['entry_idx'],
                    'entry_price': entry['entry_price'],
                    'stop_price': entry['stop_price'],
                    'risk_price': entry['risk_price'],
                    'buffer_price': entry['buffer_price'],
                    'entry_delay_minutes': entry['entry_delay_minutes'],
                    'sigma60': entry['sigma60'],
                }
                for sim in simulate_surface(entry, bars, TARGET_RS, horizon_minutes=args.horizon_minutes):
                    records.append({**base, **sim})
            entry_counts[f'{sample}:{model}'] = int(built)

    trades = pd.DataFrame(records)
    rows = []
    if not trades.empty:
        for (sample, model, tr), g in trades.groupby(['sample','entry_model','target_r'], sort=True):
            rows.append({
                'sample': sample,
                'entry_model': model,
                'target_r': float(tr),
                'trades': int(len(g)),
                'tp_pct': 100.0 * float((g.result == 'TP').mean()),
                'sl_pct': 100.0 * float((g.result == 'SL').mean()),
                'time_pct': 100.0 * float((g.result == 'TIME').mean()),
                'ambiguous_same_bar_pct': 100.0 * float(g.ambiguous_same_bar.mean()),
                'avg_gross_R': float(g.gross_R.mean()),
                'pf_gross': float(pf(g.gross_R)),
                'avg_net_R_legacy22': float(g.net_R_legacy22.mean()),
                'pf_net_legacy22': float(pf(g.net_R_legacy22)),
                'median_risk_price': float(g.risk_price.median()),
                'median_entry_delay_minutes': float(g.entry_delay_minutes.median()),
                'median_legacy_commission_R': float(g.legacy_commission_R.median()),
            })
    summary = pd.DataFrame(rows)
    trades.to_csv(outdir / 'trade_surface.csv.gz', index=False, compression='gzip')
    summary.to_csv(outdir / 'summary.csv', index=False)
    manifest = {
        'target_start': str(start),
        'target_end': str(end),
        'bars': int(len(bars)),
        'zones_generated': int(len(zones)),
        'target_events': int(len(contacts)),
        'entry_models': ENTRY_MODELS,
        'target_R_surface': list(TARGET_RS),
        'horizon_minutes': int(args.horizon_minutes),
        'stop_buffer_rule': 'max(2 x contemporaneous spread, 0.10 x causal sigma60)',
        'same_bar_tp_sl_rule': 'SL / adverse resolution',
        'execution': 'market longs ASK / shorts BID; exits executable opposite side; stop gaps worsened',
        'commission_sensitivity': '$22 round-turn per 100oz broker lot, inherited legacy Vantage model; reported separately',
        'overlap_policy': 'signal-level study; overlapping candidate trades allowed; portfolio constraints deferred',
        'entry_counts': entry_counts,
    }
    (outdir / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    if len(summary): print(summary.to_string(index=False))


if __name__ == '__main__':
    main()
