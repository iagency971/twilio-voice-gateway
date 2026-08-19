#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from rzr.config import ResearchConfig
from rzr.io import load_ohlc_csv
from rzr.features import quote_activity_mask
from rzr.entries_v2 import build_entry
from rzr.entries_v1 import simulate_one, TARGET_RS
from rzr.entries_s1 import apply_volatility_floor
from rzr.vantage_overlay import apply_fixed_spread_overlay
import build_comex_dev_rank1_event_features as feat

STRUCTURAL_MODELS = [
    'PASSIVE_TOUCH', 'CLEAN_REJECTION', 'FAILED_AUCTION',
    'ACCEPTANCE_RETEST', 'RECLAIM_PULLBACK'
]
TNO_K = (0.25, 0.50, 0.75, 1.00)
SCENARIOS = {
    'S10_C6': {'spread_usd': 0.10, 'commission_rt_usd': 6.0, 'role': 'sensitivity'},
    'S11_C6_PRIMARY': {'spread_usd': 0.11, 'commission_rt_usd': 6.0, 'role': 'primary'},
    'S12_C6': {'spread_usd': 0.12, 'commission_rt_usd': 6.0, 'role': 'sensitivity'},
    'S18_C9_STRESS': {'spread_usd': 0.18, 'commission_rt_usd': 9.0, 'role': 'stress'},
}


def utc_series(s):
    return pd.to_datetime(s, utc=True)


def family_fields(v):
    sig = feat.family_signature(v)
    return sig, feat.family_stack(sig)


def selected_events(events_path: str, sessions_path: str, bars: pd.DataFrame, year: int) -> pd.DataFrame:
    sessions = pd.read_csv(sessions_path)
    sessions = sessions[sessions.acquisition_stage.eq('DEV_RANK1')].copy()
    assert len(sessions) == 96, len(sessions)
    dates = set(sessions.research_trading_date.astype(str))

    e = pd.read_csv(events_path, compression='gzip', low_memory=False)
    required = {
        'event_uid','year','contact_time','lower','upper','sigma60','side',
        'approach_direction','constituent_families','behavior_v2',
        'first_reclaim_minutes_v2','reclaim_after_breach_minutes_v2'
    }
    missing = sorted(required - set(e.columns))
    if missing:
        raise SystemExit(f'canonical event table missing required columns: {missing}')

    e = e[pd.to_numeric(e.year, errors='coerce').eq(int(year))].copy()
    e['contact_time'] = utc_series(e.contact_time)
    e['research_trading_date'] = feat.xau_day_key(e.contact_time)
    e = e[e.research_trading_date.isin(dates)].copy().reset_index(drop=True)
    if e.empty:
        raise SystemExit(f'no DEV_RANK1 canonical events for {year}')
    if e.event_uid.astype(str).duplicated().any():
        raise SystemExit('duplicate event_uid in selected canonical events')

    # The canonical event was originally built on the same Dukascopy M1 timeline,
    # but contact_idx referred to a much larger annual input. Re-anchor it exactly
    # to the frozen two-year XAU window used for this economic replay.
    loc = bars.index.get_indexer(pd.DatetimeIndex(e.contact_time))
    bad = np.flatnonzero(loc < 0)
    if len(bad):
        sample = e.iloc[bad[:10]][['event_uid','contact_time']].to_dict('records')
        raise SystemExit(f'contact_time absent from frozen XAU replay window: {sample}')
    e['contact_idx'] = loc.astype(int)

    ff = [family_fields(v) for v in e.constituent_families]
    e['signature'] = [x[0] for x in ff]
    e['family_stack'] = [x[1] for x in ff]
    return e


def record(base, entry, bars_exec, rr, scenario, sc, risk_rule, vol_floor_k):
    sim = simulate_one(
        entry, bars_exec, float(rr), horizon_minutes=120,
        commission_rt_per_lot=float(sc['commission_rt_usd'])
    )
    return {
        'event_uid': str(base['event_uid']),
        'year': int(base['year']),
        'research_trading_date': str(base['research_trading_date']),
        'contact_time': str(pd.Timestamp(base['contact_time'])),
        'family_stack': str(base['family_stack']),
        'signature': str(base['signature']),
        'side': str(base.get('side','')),
        'session': str(base.get('session','')),
        'behavior_v2': str(base.get('behavior_v2','')),
        'scenario': scenario,
        'scenario_role': sc['role'],
        'spread_usd': float(sc['spread_usd']),
        'commission_rt_usd': float(sc['commission_rt_usd']),
        'entry_model': str(base['_entry_model']),
        'risk_rule': risk_rule,
        'vol_floor_k': vol_floor_k,
        'target_r': float(rr),
        'gross_R': float(sim['gross_R']),
        'net_R': float(sim['net_R_legacy22']),
        'result': str(sim['result']),
        'ambiguous_same_bar': bool(sim['ambiguous_same_bar']),
        'risk_price': float(entry['risk_price']),
        'entry_delay_minutes': float(entry['entry_delay_minutes']),
        'entry_time': str(pd.Timestamp(bars_exec.index[int(entry['entry_idx'])])),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--year', type=int, required=True)
    ap.add_argument('--canonical-events', required=True)
    ap.add_argument('--sessions', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cfg = ResearchConfig()

    bars_mid = load_ohlc_csv(a.csv).sort_index().copy()
    bars_mid['quote_active'] = quote_activity_mask(bars_mid)
    events = selected_events(a.canonical_events, a.sessions, bars_mid, int(a.year))

    rows = []
    counts = []
    for scenario, sc in SCENARIOS.items():
        bars_exec = apply_fixed_spread_overlay(bars_mid, float(sc['spread_usd']))
        for model in STRUCTURAL_MODELS:
            built = 0
            for rec in events.to_dict('records'):
                ent = build_entry(rec, bars_exec, model, acceptance_minutes=cfg.acceptance_minutes)
                if ent is None:
                    continue
                built += 1
                rec['_entry_model'] = model
                for rr in TARGET_RS:
                    rows.append(record(rec, ent, bars_exec, rr, scenario, sc, 'STRUCTURAL', np.nan))
            counts.append({'scenario':scenario,'entry_model':model,'risk_rule':'STRUCTURAL','entered_events':built})

        for k in TNO_K:
            built = 0
            for rec in events.to_dict('records'):
                raw = build_entry(rec, bars_exec, 'TOUCH_NEXT_OPEN', acceptance_minutes=cfg.acceptance_minutes)
                if raw is None:
                    continue
                ent = apply_volatility_floor(raw, float(k))
                if ent is None:
                    continue
                built += 1
                rec['_entry_model'] = 'TOUCH_NEXT_OPEN'
                for rr in TARGET_RS:
                    rows.append(record(rec, ent, bars_exec, rr, scenario, sc, f'VOL_FLOOR_{k:.2f}', float(k)))
            counts.append({'scenario':scenario,'entry_model':'TOUCH_NEXT_OPEN','risk_rule':f'VOL_FLOOR_{k:.2f}','entered_events':built})

    r = pd.DataFrame(rows)
    if r.empty:
        raise SystemExit('no economic outcomes generated')
    r.to_parquet(out/'event_outcomes.parquet', index=False, compression='zstd')
    r.head(200).to_csv(out/'event_outcomes_sample_200.csv', index=False)
    c = pd.DataFrame(counts)
    c.to_csv(out/'coverage_by_model.csv', index=False)

    primary = r[r.scenario.eq('S11_C6_PRIMARY')]
    manifest = {
        'version':'COMEX_DEV_RANK1_VANTAGE_OUTCOMES_DIRECT_V1',
        'market_data_api_calls':False,
        'databento_calls':False,
        'year':int(a.year),
        'canonical_selected_events':int(len(events)),
        'selected_sessions':int(events.research_trading_date.nunique()),
        'outcome_rows':int(len(r)),
        'primary_outcome_rows':int(len(primary)),
        'primary_unique_entered_events':int(primary.event_uid.nunique()),
        'event_uid_unique_in_canonical_selection':int(events.event_uid.nunique()),
        'contact_time_exactly_reanchored_to_xau_m1':True,
        'canonical_behavior_and_zone_geometry_reused_without_relabeling':True,
        'execution_engine':'unchanged rzr.entries_v2.build_entry + rzr.entries_v1.simulate_one + fixed Vantage overlay',
        'source_xau_window':'same annual replay convention as frozen Phase-C Vantage: previous calendar year through following January',
        'scenarios':SCENARIOS,
        'target_R_surface':[float(x) for x in TARGET_RS],
        'structural_models':STRUCTURAL_MODELS,
        'touch_next_open_vol_floor_k':[float(x) for x in TNO_K],
        'horizon_minutes':120,
        'net_r_surface_freeze':'COMEX_DEV_RANK1_NET_R_SURFACE_FREEZE_v1.md',
        'decision_population_freeze':'COMEX_DEV_RANK1_ENTRY_DECISION_POPULATIONS_FREEZE_v1.md',
        'note':'Canonical raw eligibility is not used as the economic fill truth; entries are rebuilt on the frozen Vantage execution overlay.'
    }
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
