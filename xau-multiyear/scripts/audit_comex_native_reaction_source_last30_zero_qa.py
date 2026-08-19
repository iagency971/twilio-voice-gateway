#!/usr/bin/env python3
from __future__ import annotations

import argparse, json
from pathlib import Path

import numpy as np
import pandas as pd

import build_comex_dev_rank1_event_features as feat

TICK = 0.10


def main() -> None:
    ap = argparse.ArgumentParser()
    for name in [
        'source-new-root','source-pilot-root','dual-requests','sessions','mapping','routing',
        'source-levels','events','out'
    ]:
        ap.add_argument('--'+name, required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    req = pd.read_csv(a.dual_requests, dtype={'symbols':str})
    sessions = pd.read_csv(a.sessions)
    sessions = sessions[sessions.acquisition_stage.eq('DEV_RANK1')].copy()
    mapping = pd.read_csv(a.mapping, dtype={'v0_start_iid':str,'n0_start_iid':str})
    routing = pd.read_csv(a.routing, dtype={'v0_iid':str,'n0_iid':str})
    levels = pd.read_csv(a.source_levels, dtype={'source_instrument_id':str})
    events = pd.read_csv(a.events, dtype={'source_instrument_id':str})

    if len(sessions) != 96 or len(mapping) != 96 or len(routing) != 96:
        raise SystemExit('DEV_RANK1 source routing cardinality mismatch')

    cand, _ = feat.build_candidate_map(Path(a.source_new_root), Path(a.source_pilot_root), req, sessions, mapping)
    rt = routing.set_index(routing.research_trading_date.astype(str))
    reg = levels.groupby('source_research_date', sort=True).first().reset_index()

    session_rows = []
    for r in reg.itertuples(index=False):
        d = str(r.source_research_date)
        rr = rt.loc[d]
        label = str(r.source_candidate_key)
        z = cand.get((d,label)) or cand.get((d,'N0')) or cand.get((d,'V0'))
        p = Path(z['path']) if z and z.get('path') else None
        if p is None:
            raise SystemExit(f'source raw missing for {d}')
        t = feat.prep_tape(p, d)
        if t is None or len(t['price']) == 0:
            raise SystemExit(f'empty source raw tape for {d}')
        s,e = feat.session_bounds(d)
        # prep_tape already clips to [s,e); recover exact raw timestamps/prices from arrays.
        ts = pd.to_datetime(t['ts'], utc=True)
        price = np.asarray(t['price'], dtype=float)
        mask = ts >= (e - pd.Timedelta(minutes=30))
        p30 = price[mask]
        finite = p30[np.isfinite(p30)]
        n = int(len(finite))
        uniq = int(len(np.unique(finite))) if n else 0
        pmin = float(np.min(finite)) if n else np.nan
        pmax = float(np.max(finite)) if n else np.nan
        rng = (pmax-pmin)/TICK if n else np.nan
        session_rows.append({
            'source_research_date': d,
            'source_year': pd.Timestamp(d).year,
            'source_instrument_id': str(r.source_instrument_id),
            'source_candidate_key': label,
            'terminal_leader': str(rr.terminal_leader),
            'source_session_start_utc': s.isoformat(),
            'source_session_end_utc': e.isoformat(),
            'last30_start_utc': (e-pd.Timedelta(minutes=30)).isoformat(),
            'last30_trade_records': n,
            'last30_unique_prices': uniq,
            'last30_min_price': pmin,
            'last30_max_price': pmax,
            'source_last30_range_ticks': float(rng) if np.isfinite(rng) else np.nan,
            'source_last30_positive': bool(np.isfinite(rng) and rng > 0),
            'source_last30_missing': bool(n == 0),
            'source_last30_flat': bool(n > 0 and np.isfinite(rng) and rng == 0),
            'source_raw_file': p.name,
        })

    sf = pd.DataFrame(session_rows).sort_values('source_research_date').reset_index(drop=True)
    if len(sf) != 92:
        raise SystemExit(f'expected 92 source sessions, got {len(sf)}')

    bad = sf[~sf.source_last30_positive].copy()
    ev = events.copy()
    ev['source_research_date'] = ev.source_research_date.astype(str)
    affected = ev[ev.source_research_date.isin(set(bad.source_research_date.astype(str)))].copy()
    keep = [c for c in [
        'level_id','source_research_date','eligible_next_research_date','source_instrument_id','level_type',
        't0_utc','m0_utc','anchor_minute_of_session','approach','away_sign','approach_defined','w15_complete'
    ] if c in affected.columns]
    affected = affected[keep].sort_values(['source_research_date','level_id']).reset_index(drop=True)

    sf.to_csv(out/'source_last30_all_sessions.csv', index=False)
    bad.to_csv(out/'source_last30_nonpositive_sessions.csv', index=False)
    affected.to_csv(out/'source_last30_nonpositive_affected_contacts.csv', index=False)

    result = {
        'version':'COMEX_DEV_RANK1_NATIVE_REACTION_SOURCE_LAST30_ZERO_QA_V1',
        'post_contact_values_used_for_matching':False,
        'post_anchor_outcomes_read':False,
        'reaction_outcomes_computed':False,
        'mfe_mae_computed':False,
        'market_data_api_called':False,
        'market_data_download_performed':False,
        'source_sessions_total':92,
        'source_last30_positive_sessions':int(sf.source_last30_positive.sum()),
        'source_last30_nonpositive_sessions':int(len(bad)),
        'source_last30_missing_sessions':int(sf.source_last30_missing.sum()),
        'source_last30_flat_sessions':int(sf.source_last30_flat.sum()),
        'affected_contact_events':int(len(affected)),
        'affected_defined_approach_events':int(pd.to_numeric(affected.get('away_sign',pd.Series(dtype=float)),errors='coerce').isin([-1,1]).sum()) if len(affected) else 0,
        'affected_source_years':sorted(set(pd.to_datetime(bad.source_research_date).dt.year.astype(int).tolist())),
        'nonpositive_source_dates':bad.source_research_date.astype(str).tolist(),
        'notes':[
            'This QA reads only the already-owned source-session raw tape and frozen event timestamps/context.',
            'It does not read or compute any post-contact reaction endpoint.',
            'A zero range with positive trade count is a genuinely flat final-30-minute executed-price window, not missing data.',
            'A missing final-30-minute window is reported separately and must not be treated as a zero volatility observation.'
        ]
    }
    (out/'source_last30_zero_qa.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
