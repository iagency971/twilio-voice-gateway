#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from rzr.config import ResearchConfig
from rzr.io import load_ohlc_csv
from rzr.features import quote_activity_mask, robust_sigma60, trading_day_key
from rzr.zones import generate_baseline_zones
from rzr.contacts import find_first_contacts
from rzr.stacking import collapse_contact_events
from rzr.labels import label_contacts
from rzr.behavior_v2 import classify_behavior_v2
from rzr.entries_v2 import build_entry

MODELS = [
    'PASSIVE_TOUCH','TOUCH_NEXT_OPEN','CLEAN_REJECTION',
    'FAILED_AUCTION','ACCEPTANCE_RETEST','RECLAIM_PULLBACK'
]
FAMILIES = ['DISPLACEMENT_ORIGIN','OBJECTIVE_LIQUIDITY','MEMORY','FVG']
SAMPLE_SEED = 'COMEX_FVG_SAMPLE_V1_SEED_971'
SESSION_SEED = 'COMEX_SESSION_PANEL_V1_SEED_971'


def utc(x):
    x = pd.Timestamp(x)
    return x.tz_localize('UTC') if x.tzinfo is None else x.tz_convert('UTC')


def split_for_year(y:int)->str:
    if y <= 2018: return 'DEV'
    if y <= 2022: return 'VALIDATION'
    if y <= 2025: return 'COMEX_FEATURE_HOLDOUT'
    return 'FORWARD_AUDIT'


def stable_hash(*parts)->str:
    s='|'.join(str(x) for x in parts)
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def known_close_time(bars, idx):
    if idx is None or idx < 0 or idx >= len(bars): return pd.NaT
    return pd.Timestamp(bars.index[int(idx)]) + pd.Timedelta(minutes=1)


def qband(series, q=4):
    s=pd.to_numeric(series, errors='coerce')
    out=pd.Series(-1,index=s.index,dtype='int16')
    good=s.notna()
    if good.sum() < q:
        out.loc[good]=0; return out
    try:
        out.loc[good]=pd.qcut(s.loc[good].rank(method='first'), q, labels=False, duplicates='drop').astype('int16')
    except Exception:
        out.loc[good]=0
    return out


def add_model_times(events, bars, cfg):
    for model in MODELS:
        elig=[]; decision=[]; order=[]; entry=[]; delay=[]
        for rec in events.to_dict('records'):
            t0=pd.Timestamp(rec['contact_time'])
            e=build_entry(rec,bars,model,acceptance_minutes=cfg.acceptance_minutes)
            elig.append(bool(e is not None))
            if model=='PASSIVE_TOUCH':
                # Predictor information for a truly standing passive order must stop before t0.
                d=t0
            elif model=='TOUCH_NEXT_OPEN':
                d=t0+pd.Timedelta(minutes=1)
            elif model=='ACCEPTANCE_RETEST':
                d=t0+pd.Timedelta(minutes=cfg.acceptance_minutes)
            elif model in {'CLEAN_REJECTION','FAILED_AUCTION','RECLAIM_PULLBACK'} and e is not None:
                d=known_close_time(bars,int(e['confirm_idx']))
            else:
                d=pd.NaT
            decision.append(d)
            order.append(d)
            if e is not None:
                entry.append(pd.Timestamp(bars.index[int(e['entry_idx'])]))
                delay.append(int(e['entry_delay_minutes']))
            else:
                entry.append(pd.NaT); delay.append(np.nan)
        p=model.lower()
        events[p+'_eligible']=elig
        events[p+'_decision_time']=decision
        events[p+'_order_time']=order
        events[p+'_entry_time']=entry
        events[p+'_entry_delay_min']=delay
    return events


def make_session_candidates(bars, start, end, year):
    active=bars.loc[quote_activity_mask(bars)].copy()
    if active.empty: return pd.DataFrame()
    active=active[(active.index>=start-pd.Timedelta(days=2))&(active.index<end+pd.Timedelta(days=1))]
    keys=pd.Series([trading_day_key(ts,'America/New_York',17) for ts in active.index],index=active.index)
    rows=[]
    for d,idxs in keys.groupby(keys,sort=True).groups.items():
        if pd.Timestamp(d).year != year: continue
        g=active.loc[list(idxs)]
        if g.empty: continue
        local_date=pd.Timestamp(d)
        rows.append({
            'research_trading_date':str(d),
            'year':year,
            'quarter':int(local_date.quarter),
            'xau_range':float(g.high.max()-g.low.min()),
            'xau_close_abs_move':float(g.close.diff().abs().sum()),
            'first_ts':str(g.index.min()),'last_ts':str(g.index.max()),
        })
    x=pd.DataFrame(rows)
    if x.empty:return x
    x['vol_band']=qband(x['xau_range'],3)
    x['panel_hash']=[stable_hash(SESSION_SEED,r.year,r.quarter,r.vol_band,r.research_trading_date) for r in x.itertuples()]
    x['panel_rank']=x.groupby(['year','quarter','vol_band'])['panel_hash'].rank(method='first').astype(int)
    return x


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--target-start',required=True)
    ap.add_argument('--target-end',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    start=utc(args.target_start); end=utc(args.target_end); year=int(start.year)
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    cfg=ResearchConfig()

    bars=load_ohlc_csv(args.csv).sort_index().copy()
    bars['quote_active']=quote_activity_mask(bars)
    bars['sigma60']=robust_sigma60(bars)
    zones=generate_baseline_zones(bars,cfg)
    events=find_first_contacts(bars,zones,bars['sigma60'],cfg)
    events=collapse_contact_events(events,cfg.stack_overlap_threshold)
    events=label_contacts(bars,events,cfg)
    events=classify_behavior_v2(bars,events,cfg)
    if not events.empty:
        ct=pd.to_datetime(events.contact_time,utc=True)
        events=events[(ct>=start)&(ct<end)].copy().reset_index(drop=True)

    events['year']=year
    events['temporal_split']=split_for_year(year)
    events['event_uid']=[stable_hash(year,r.stack_id,r.contact_time,r.lower,r.upper,r.constituent_families) for r in events.itertuples()]
    events['zone_width_sigma']=(pd.to_numeric(events.upper)-pd.to_numeric(events.lower))/pd.to_numeric(events.sigma60)
    fam=events.constituent_families.fillna('')
    for f in FAMILIES: events['has_'+f.lower()]=fam.str.contains('"'+f+'"',regex=False)
    events['fvg_only']=events['has_fvg'] & ~events['has_displacement_origin'] & ~events['has_objective_liquidity'] & ~events['has_memory']
    events['uniform_tick_start']=pd.to_datetime(events.contact_time,utc=True)-pd.Timedelta(minutes=30)
    events['uniform_tick_end']=pd.to_datetime(events.contact_time,utc=True)+pd.Timedelta(minutes=16)
    events=add_model_times(events,bars,cfg)

    fvg=events.fvg_only
    events['sigma_q']=qband(events.sigma60,4)
    events['width_q']=qband(events.zone_width_sigma,4)
    events['fvg_sample_hash']=''
    events.loc[fvg,'fvg_sample_hash']=[stable_hash(SAMPLE_SEED,*vals) for vals in zip(events.loc[fvg,'year'],events.loc[fvg,'session'],events.loc[fvg,'side'],events.loc[fvg,'sigma_q'],events.loc[fvg,'width_q'],events.loc[fvg,'event_uid'])]
    events['fvg_rank']=np.nan
    if fvg.any():
        strata=['year','session','side','sigma_q','width_q']
        events.loc[fvg,'fvg_rank']=events.loc[fvg].groupby(strata)['fvg_sample_hash'].rank(method='first')

    keep=['event_uid','year','temporal_split','stack_id','zone_id','contact_time','zone_known_time','family','variant','side','lower','upper','center','sigma60','zone_width_sigma','session','local_hour','approach_direction','approach_band','constituent_count','constituent_families','constituent_variants','behavior_v2','reaction_0_5sigma','first_reclaim_minutes_v2','reclaim_after_breach_minutes_v2','uniform_tick_start','uniform_tick_end','fvg_only','sigma_q','width_q','fvg_sample_hash','fvg_rank']
    for m in MODELS:
        p=m.lower(); keep += [p+'_eligible',p+'_decision_time',p+'_order_time',p+'_entry_time',p+'_entry_delay_min']
    keep=[c for c in keep if c in events.columns]
    events[keep].to_csv(out/'events.csv.gz',index=False,compression='gzip')

    sess=make_session_candidates(bars,start,end,year)
    sess.to_csv(out/'session_candidates.csv',index=False)
    manifest={
        'version':'COMEX_EVENT_TIMING_V1','year':year,'target_start':str(start),'target_end':str(end),
        'events':int(len(events)),'fvg_only_events':int(events.fvg_only.sum()),
        'non_fvg_only_events':int((~events.fvg_only).sum()),'session_candidates':int(len(sess)),
        'temporal_split':split_for_year(year),'fvg_seed':SAMPLE_SEED,'session_seed':SESSION_SEED,
        'uniform_tick_window':'contact -30m through contact +16m; end is exclusive in acquisition plan',
        'models':MODELS,
    }
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__': main()
