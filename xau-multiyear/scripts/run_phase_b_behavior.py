#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, sys, time
from dataclasses import asdict
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

FAMILIES = ['DISPLACEMENT_ORIGIN', 'OBJECTIVE_LIQUIDITY', 'MEMORY', 'FVG']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--target-start', required=True)
    ap.add_argument('--target-end', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    start = pd.Timestamp(args.target_start)
    start = start.tz_localize('UTC') if start.tzinfo is None else start.tz_convert('UTC')
    end = pd.Timestamp(args.target_end)
    end = end.tz_localize('UTC') if end.tzinfo is None else end.tz_convert('UTC')
    cfg = ResearchConfig()
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)

    bars = load_ohlc_csv(args.csv).sort_index().copy()
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
    rows = []

    def summarize(name: str, mask: pd.Series):
        g = contacts[mask].copy()
        if g.empty:
            return
        vc = g['behavior_v2'].value_counts()
        row = {
            'sample': name,
            'events': int(len(g)),
            'clean_rejection_pct': 100.0 * vc.get('CLEAN_REJECTION', 0) / len(g),
            'failed_auction_pct': 100.0 * vc.get('FAILED_AUCTION', 0) / len(g),
            'accepted_break_pct': 100.0 * vc.get('ACCEPTED_BREAK', 0) / len(g),
            'unresolved_pct': 100.0 * vc.get('UNRESOLVED', 0) / len(g),
            'reaction_0_5sigma_pct': 100.0 * g['reaction_0_5sigma'].mean(),
            'median_mfe_sigma': float(g['mfe_sigma'].median()),
            'median_mae_sigma': float(g['mae_sigma'].median()),
            'median_distal_overshoot_sigma': float(g['max_distal_overshoot_sigma_v2'].median()),
        }
        fa = g[g.behavior_v2 == 'FAILED_AUCTION']
        if len(fa):
            row['failed_auction_reaction_0_5sigma_pct'] = 100.0 * fa['reaction_0_5sigma'].mean()
            row['failed_auction_median_reclaim_min'] = float(fa['reclaim_after_breach_minutes_v2'].median())
            row['failed_auction_median_overshoot_sigma'] = float(fa['max_distal_overshoot_sigma_v2'].median())
        else:
            row['failed_auction_reaction_0_5sigma_pct'] = np.nan
            row['failed_auction_median_reclaim_min'] = np.nan
            row['failed_auction_median_overshoot_sigma'] = np.nan
        ab = g[g.behavior_v2 == 'ACCEPTED_BREAK']
        row['accepted_break_reaction_0_5sigma_pct'] = 100.0 * ab['reaction_0_5sigma'].mean() if len(ab) else np.nan
        rows.append(row)

    # Pure families.
    for f in FAMILIES:
        other = pd.Series(False, index=contacts.index)
        for o in FAMILIES:
            if o != f:
                other |= masks[o]
        summarize(f + '_ONLY', masks[f] & ~other)

    # Locked secondary interactions discovered in 2011-2025.
    summarize('DOZ_OBJECTIVE_ONLY', masks['DISPLACEMENT_ORIGIN'] & masks['OBJECTIVE_LIQUIDITY'] & ~masks['FVG'] & ~masks['MEMORY'])
    summarize('DOZ_FVG_ONLY', masks['DISPLACEMENT_ORIGIN'] & masks['FVG'] & ~masks['OBJECTIVE_LIQUIDITY'] & ~masks['MEMORY'])

    summary = pd.DataFrame(rows)
    keep = [c for c in [
        'stack_id','zone_id','contact_time','family','variant','side','constituent_count',
        'constituent_families','constituent_variants','sigma60','approach_direction','approach_band',
        'mfe_sigma','mae_sigma','reaction_0_5sigma','behavior_v2','distal_breach_v2',
        'clean_rejection_v2','failed_auction_v2','accepted_break_v2','first_breach_minutes_v2',
        'first_reclaim_minutes_v2','reclaim_after_breach_minutes_v2','max_distal_overshoot_sigma_v2'
    ] if c in contacts.columns]
    contacts[keep].to_csv(outdir / 'phase_b_events.csv.gz', index=False, compression='gzip')
    summary.to_csv(outdir / 'behavior_summary.csv', index=False)
    manifest = {
        'target_start': str(start), 'target_end': str(end), 'bars': int(len(bars)),
        'zones_generated': int(len(zones)), 'target_events': int(len(contacts)),
        'classifier': 'behavior_v2: CLEAN_REJECTION / FAILED_AUCTION / ACCEPTED_BREAK / UNRESOLVED',
        'failed_auction_rule': 'distal breach followed by proximal reclaim within 15 minutes',
        'acceptance_rule': 'unchanged preregistered 5-minute acceptance rule',
    }
    (outdir / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    print(summary.to_string(index=False))


if __name__ == '__main__':
    main()
