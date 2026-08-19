#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from rzr.config import ResearchConfig
from rzr.io import load_ohlc_csv
from rzr.features import quote_activity_mask, robust_sigma60
from rzr.zones import generate_baseline_zones
from rzr.contacts import find_first_contacts
from rzr.stacking import collapse_contact_events
from rzr.labels import label_contacts
from rzr.behavior_v2 import classify_behavior_v2
from rzr.entries_v2 import build_entry
from rzr.vantage_overlay import apply_fixed_spread_overlay

from run_xau_core_audit_annual_v1 import (
    FAMILIES,
    collapse_with_membership,
    assert_stack_parity,
    stable_event_id,
)


def _iso(ts):
    return pd.Timestamp(ts).isoformat()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--year', type=int, required=True)
    ap.add_argument('--canonical-ledger', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    year = int(args.year)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = ResearchConfig()
    start = pd.Timestamp(f'{year}-01-01', tz='UTC')
    end = pd.Timestamp(f'{year+1}-01-01', tz='UTC')

    bars = load_ohlc_csv(args.csv).sort_index().copy()
    bars['quote_active'] = quote_activity_mask(bars)
    bars['sigma60'] = robust_sigma60(bars)

    zones = generate_baseline_zones(bars, cfg)
    zdf = pd.DataFrame([{
        'zone_id': z.zone_id,
        'family': z.family.value,
        'variant': z.variant,
        'origin_time': z.origin_time,
        'known_time': z.known_time,
        'source_tf': z.source_tf,
        'lower': z.lower,
        'upper': z.upper,
    } for z in zones])

    raw = find_first_contacts(bars, zones, bars['sigma60'], cfg)
    canonical = collapse_contact_events(raw, cfg.stack_overlap_threshold)
    audit_stacks, membership = collapse_with_membership(raw, cfg.stack_overlap_threshold)
    stack_parity = assert_stack_parity(canonical, audit_stacks)
    if not stack_parity['pass']:
        raise RuntimeError(f'stack parity failure {year}: {stack_parity}')

    # Each zone has exactly one first-contact row. Join the raw member contact time/index
    # back to the exact stack membership without changing canonical grouping semantics.
    raw_meta = raw[['zone_id','contact_idx','contact_time']].copy()
    raw_meta = raw_meta.rename(columns={'contact_idx':'member_contact_idx','contact_time':'member_contact_time'})
    if raw_meta['zone_id'].duplicated().any():
        raise RuntimeError('raw first-contact zone IDs are not unique')
    member_meta = membership.merge(zdf, left_on='member_zone_id', right_on='zone_id', how='left', validate='many_to_one')
    member_meta = member_meta.merge(raw_meta, on='zone_id', how='left', validate='many_to_one')
    if member_meta[['family','known_time','member_contact_idx','member_contact_time']].isna().any().any():
        raise RuntimeError('untraceable member metadata')
    by_stack = {sid: g.copy() for sid,g in member_meta.groupby('stack_id', sort=False)}

    contacts = label_contacts(bars, canonical, cfg)
    contacts = classify_behavior_v2(bars, contacts, cfg)
    ct = pd.to_datetime(contacts['contact_time'], utc=True)
    contacts = contacts[(ct >= start) & (ct < end)].copy()
    sf = contacts.get('constituent_families', pd.Series('', index=contacts.index)).fillna('')
    masks = {f: sf.str.contains(f'"{f}"', regex=False) for f in FAMILIES}
    core = contacts[masks['DISPLACEMENT_ORIGIN'] & masks['OBJECTIVE_LIQUIDITY'] & ~masks['MEMORY'] & ~masks['FVG']].copy()

    # Entry/confirmation indices must be the same as the historical core; primary overlay
    # is used only because spread participates in the structural buffer/entry object.
    exec_bars = apply_fixed_spread_overlay(bars, 0.11)
    rows = []
    actual_event_ids = []
    future_member_rows = []

    for _, rec in core.iterrows():
        entry = build_entry(rec.to_dict(), exec_bars, 'CLEAN_REJECTION', acceptance_minutes=cfg.acceptance_minutes)
        if entry is None:
            continue
        eid = stable_event_id(year, rec)
        actual_event_ids.append(eid)
        confirm_idx = int(entry['confirm_idx'])
        entry_idx = int(entry['entry_idx'])
        confirm_time = bars.index[confirm_idx]
        entry_time = bars.index[entry_idx]
        sid = str(rec['stack_id'])
        m = by_stack.get(sid)
        if m is None or m.empty:
            raise RuntimeError(f'missing membership for {sid}')
        m = m.copy()
        m['known_time'] = pd.to_datetime(m['known_time'], utc=True)
        m['member_contact_time'] = pd.to_datetime(m['member_contact_time'], utc=True)
        m['member_contact_idx'] = pd.to_numeric(m['member_contact_idx']).astype(int)
        # Strict causal availability at the confirmation boundary. An entry occurs at a
        # later bar open, so contact on the entry bar itself cannot establish confluence.
        m['available_by_confirmation'] = (m['known_time'] <= confirm_time) & (m['member_contact_idx'] <= confirm_idx)
        m['future_after_confirmation'] = ~m['available_by_confirmation']
        doz_avail = m[(m.family == 'DISPLACEMENT_ORIGIN') & m.available_by_confirmation]
        obj_avail = m[(m.family == 'OBJECTIVE_LIQUIDITY') & m.available_by_confirmation]
        missing_doz = len(doz_avail) == 0
        missing_obj = len(obj_avail) == 0
        violation = bool(missing_doz or missing_obj)
        future = m[m.future_after_confirmation]
        for _, fm in future.iterrows():
            future_member_rows.append({
                'source_year': year,
                'event_id': eid,
                'stack_id': sid,
                'representative_contact_time': _iso(rec['contact_time']),
                'confirmation_time': _iso(confirm_time),
                'entry_time': _iso(entry_time),
                'member_zone_id': str(fm['zone_id']),
                'member_family': str(fm['family']),
                'member_variant': str(fm['variant']),
                'member_known_time': _iso(fm['known_time']),
                'member_contact_time': _iso(fm['member_contact_time']),
                'member_contact_idx': int(fm['member_contact_idx']),
                'confirm_idx': confirm_idx,
                'entry_idx': entry_idx,
                'core_classification_violation': violation,
            })
        rows.append({
            'source_year': year,
            'event_id': eid,
            'stack_id': sid,
            'zone_id': str(rec['zone_id']),
            'representative_contact_time': _iso(rec['contact_time']),
            'confirmation_time': _iso(confirm_time),
            'entry_time': _iso(entry_time),
            'confirm_idx': confirm_idx,
            'entry_idx': entry_idx,
            'constituent_count': int(len(m)),
            'available_doz_members_by_confirmation': int(len(doz_avail)),
            'available_objective_members_by_confirmation': int(len(obj_avail)),
            'future_members_after_confirmation': int(len(future)),
            'future_doz_members_after_confirmation': int(((future.family == 'DISPLACEMENT_ORIGIN')).sum()),
            'future_objective_members_after_confirmation': int(((future.family == 'OBJECTIVE_LIQUIDITY')).sum()),
            'missing_causal_doz_by_confirmation': bool(missing_doz),
            'missing_causal_objective_by_confirmation': bool(missing_obj),
            'core_classification_violation': violation,
        })

    events = pd.DataFrame(rows)
    future_df = pd.DataFrame(future_member_rows)

    # Exact event-set binding to the already-published 304-event ledger.
    can = pd.read_csv(args.canonical_ledger)
    can = can[(can['source_year'].astype(int) == year) &
              (can['scenario'] == 'S11_C6_PRIMARY') &
              np.isclose(can['target_r'].astype(float), 1.5)]
    expected_ids = sorted(can['event_id'].astype(str).unique())
    actual_ids = sorted(set(actual_event_ids))
    event_set_pass = expected_ids == actual_ids
    if not event_set_pass:
        raise RuntimeError(f'core event-set mismatch {year}: expected {len(expected_ids)} actual {len(actual_ids)}')

    violations = events[events['core_classification_violation']].copy()
    events.to_csv(out / f'temporal_stack_events_{year}.csv', index=False)
    violations.to_csv(out / f'temporal_stack_violations_{year}.csv', index=False)
    future_df.to_csv(out / f'temporal_stack_future_members_{year}.csv', index=False)

    summary = {
        'version': 'XAU_CORE_TEMPORAL_STACK_INTEGRITY_V1_ANNUAL',
        'year': year,
        'stack_parity_pass': True,
        'canonical_core_event_set_pass': True,
        'core_events': int(len(events)),
        'core_classification_violations': int(len(violations)),
        'missing_causal_doz_events': int(events['missing_causal_doz_by_confirmation'].sum()),
        'missing_causal_objective_events': int(events['missing_causal_objective_by_confirmation'].sum()),
        'events_with_any_future_member_after_confirmation': int((events['future_members_after_confirmation'] > 0).sum()),
        'future_member_rows': int(len(future_df)),
        'future_doz_member_rows': int((future_df['member_family'] == 'DISPLACEMENT_ORIGIN').sum()) if len(future_df) else 0,
        'future_objective_member_rows': int((future_df['member_family'] == 'OBJECTIVE_LIQUIDITY').sum()) if len(future_df) else 0,
        'temporal_stack_integrity_pass': bool(len(violations) == 0),
        'new_market_data_spend': 0,
        'pnl_inspected_or_used': False,
    }
    (out / f'temporal_stack_summary_{year}.json').write_text(json.dumps(summary, indent=2, allow_nan=False))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
