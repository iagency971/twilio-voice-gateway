#!/usr/bin/env python3
from __future__ import annotations
import json, os
from pathlib import Path
import pandas as pd
import databento as db

ROOT = Path('mnq-databento')
RAW = ROOT / 'results/cme_validation_v1/databento_nq_1m.csv.gz'
OUT = ROOT / 'roll_diag/results'
OUT.mkdir(parents=True, exist_ok=True)

key = os.environ['DATABENTO_API_KEY']
client = db.Historical(key)

d = pd.read_csv(RAW, compression='gzip')
d['datetime'] = pd.to_datetime(d['datetime'])
d = d.sort_values('datetime').reset_index(drop=True)
d['delta_min'] = d['datetime'].diff().dt.total_seconds().div(60)
d['close_jump'] = d['close'].diff().abs()
jidx = d.index[(d.delta_min <= 2.0) & (d.close_jump > 250.0)].tolist()

mapping = client.symbology.resolve(
    dataset='GLBX.MDP3',
    symbols=['NQ.v.0'],
    stype_in='continuous',
    stype_out='instrument_id',
    start_date='2026-06-13',
    end_date='2026-06-21',
)
intervals = mapping.get('result', {}).get('NQ.v.0', [])

id_to_raw = {}
for item in intervals:
    sid = str(item['s'])
    if sid in id_to_raw:
        continue
    try:
        r = client.symbology.resolve(
            dataset='GLBX.MDP3',
            symbols=[sid],
            stype_in='instrument_id',
            stype_out='raw_symbol',
            start_date=item['d0'],
            end_date=item['d1'],
        )
        vals = r.get('result', {}).get(sid, [])
        id_to_raw[sid] = vals
    except Exception as exc:
        id_to_raw[sid] = {'error': type(exc).__name__, 'message': str(exc)}

jumps = []
roll_start_dates = {str(x['d0']) for x in intervals[1:]}
for i in jidx:
    prev = d.iloc[i-1]
    cur = d.iloc[i]
    local = pd.Timestamp(cur.datetime).tz_localize('America/New_York')
    utc = local.tz_convert('UTC')
    jumps.append({
        'prev_datetime_et': str(prev.datetime),
        'datetime_et': str(cur.datetime),
        'datetime_utc': str(utc),
        'utc_date': str(utc.date()),
        'prev_close': float(prev.close),
        'current_open': float(cur.open),
        'current_close': float(cur.close),
        'prevclose_to_open_gap_points': float(cur.open - prev.close),
        'prevclose_to_close_gap_points': float(cur.close - prev.close),
        'coincides_with_mapping_start_date': str(utc.date()) in roll_start_dates,
    })

aug = d[(d.datetime >= pd.Timestamp('2026-08-03')) & (d.datetime <= pd.Timestamp('2026-08-19 23:59:59'))].copy()
aug['delta_min'] = aug.datetime.diff().dt.total_seconds().div(60)
aug['close_jump'] = aug.close.diff().abs()
aug_big = int(((aug.delta_min <= 2.0) & (aug.close_jump > 250.0)).sum())

result = {
    'status': 'FREE_SYMBOLOGY_ROLL_DIAGNOSTIC',
    'data_timeseries_requested': False,
    'additional_paid_data_cost_usd': 0.0,
    'continuous_mapping_status': mapping.get('status'),
    'continuous_mapping_message': mapping.get('message'),
    'continuous_mapping_intervals': intervals,
    'instrument_id_to_raw_symbol': id_to_raw,
    'large_intraday_jumps': jumps,
    'large_jump_count': len(jumps),
    'all_large_jumps_coincide_with_mapping_change': bool(jumps) and all(x['coincides_with_mapping_start_date'] for x in jumps),
    'confirmatory_aug3_19_large_jump_count': aug_big,
}
(OUT/'RESULT.json').write_text(json.dumps(result, indent=2, default=str))
print(json.dumps(result, indent=2, default=str))
