#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, sys
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
from rzr.entries_v1 import simulate_one, TARGET_RS
from rzr.entries_s1 import apply_volatility_floor
from rzr.vantage_overlay import apply_fixed_spread_overlay
import build_comex_dev_rank1_event_features as feat

STRUCTURAL_MODELS = ['PASSIVE_TOUCH','CLEAN_REJECTION','FAILED_AUCTION','ACCEPTANCE_RETEST','RECLAIM_PULLBACK']
TNO_K = (0.25,0.50,0.75,1.00)
SCENARIOS = {
    'S10_C6': {'spread_usd':0.10,'commission_rt_usd':6.0,'role':'sensitivity'},
    'S11_C6_PRIMARY': {'spread_usd':0.11,'commission_rt_usd':6.0,'role':'primary'},
    'S12_C6': {'spread_usd':0.12,'commission_rt_usd':6.0,'role':'sensitivity'},
    'S18_C9_STRESS': {'spread_usd':0.18,'commission_rt_usd':9.0,'role':'stress'},
}

def stable_hash(*parts):return hashlib.sha256('|'.join(str(x) for x in parts).encode('utf-8')).hexdigest()
def utc(x):
    z=pd.Timestamp(x);return z.tz_localize('UTC') if z.tzinfo is None else z.tz_convert('UTC')
def family_fields(s):
    sig=feat.family_signature(s);return sig,feat.family_stack(sig)

def attach_identity(events,year):
    e=events.copy().reset_index(drop=True);e['year']=int(year)
    e['event_uid']=[stable_hash(year,r.stack_id,r.contact_time,r.lower,r.upper,r.constituent_families) for r in e.itertuples()]
    e['research_trading_date']=feat.xau_day_key(pd.to_datetime(e.contact_time,utc=True));ff=[family_fields(x) for x in e.constituent_families];e['signature']=[x[0] for x in ff];e['family_stack']=[x[1] for x in ff];return e

def parity_gate(events,canonical,sessions,year):
    dates=set(sessions.loc[sessions.acquisition_stage.eq('DEV_RANK1'),'research_trading_date'].astype(str));c=canonical[canonical.year.eq(int(year))].copy();c['research_trading_date']=feat.xau_day_key(pd.to_datetime(c.contact_time,utc=True));c=c[c.research_trading_date.isin(dates)].copy();e=events[events.research_trading_date.isin(dates)].copy();a=set(e.event_uid.astype(str));b=set(c.event_uid.astype(str))
    if a!=b:raise SystemExit(json.dumps({'error':'EVENT_UID_PARITY_FAIL','year':int(year),'generated':len(a),'canonical':len(b),'generated_only':sorted(a-b)[:5],'canonical_only':sorted(b-a)[:5]},indent=2))
    chk=e[['event_uid','contact_time','stack_id','constituent_families']].merge(c[['event_uid','contact_time','stack_id','constituent_families']],on='event_uid',suffixes=('_gen','_canon'),validate='one_to_one')
    if not (pd.to_datetime(chk.contact_time_gen,utc=True)==pd.to_datetime(chk.contact_time_canon,utc=True)).all():raise SystemExit('contact_time parity fail')
    if not (chk.stack_id_gen.astype(str)==chk.stack_id_canon.astype(str)).all():raise SystemExit('stack_id parity fail')
    if not (chk.constituent_families_gen.astype(str)==chk.constituent_families_canon.astype(str)).all():raise SystemExit('constituent_families parity fail')
    return e.sort_values(['research_trading_date','contact_time','event_uid']).reset_index(drop=True),c

def simulate_record(base,entry,bars_exec,target_r,commission,scenario,sc,risk_rule,vol_floor_k):
    sim=simulate_one(entry,bars_exec,float(target_r),horizon_minutes=120,commission_rt_per_lot=float(commission))
    return {'event_uid':base['event_uid'],'year':int(base['year']),'research_trading_date':base['research_trading_date'],'contact_time':base['contact_time'],'family_stack':base['family_stack'],'signature':base['signature'],'side':base.get('side'),'session':base.get('session'),'behavior_v2':base.get('behavior_v2'),'scenario':scenario,'scenario_role':sc['role'],'spread_usd':float(sc['spread_usd']),'commission_rt_usd':float(commission),'entry_model':base['_entry_model'],'risk_rule':risk_rule,'vol_floor_k':vol_floor_k,'target_r':float(target_r),'gross_R':float(sim['gross_R']),'net_R':float(sim['net_R_legacy22']),'result':sim['result'],'ambiguous_same_bar':bool(sim['ambiguous_same_bar']),'risk_price':float(entry['risk_price']),'entry_delay_minutes':float(entry['entry_delay_minutes']),'entry_time':str(pd.Timestamp(bars_exec.index[int(entry['entry_idx'])]))}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('csv');ap.add_argument('--target-start',required=True);ap.add_argument('--target-end',required=True);ap.add_argument('--canonical-events',required=True);ap.add_argument('--sessions',required=True);ap.add_argument('--out',required=True);ap.add_argument('--parity-only',action='store_true');a=ap.parse_args();start=utc(a.target_start);end=utc(a.target_end);year=int(start.year);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if end.year not in {year,year+1}:raise SystemExit('unexpected target window')
    cfg=ResearchConfig();canonical=pd.read_csv(a.canonical_events,compression='gzip',low_memory=False);sessions=pd.read_csv(a.sessions);bars_mid=load_ohlc_csv(a.csv).sort_index().copy();bars_mid['quote_active']=quote_activity_mask(bars_mid);bars_mid['sigma60']=robust_sigma60(bars_mid);zones=generate_baseline_zones(bars_mid,cfg);events=find_first_contacts(bars_mid,zones,bars_mid['sigma60'],cfg);events=collapse_contact_events(events,cfg.stack_overlap_threshold);events=label_contacts(bars_mid,events,cfg);events=classify_behavior_v2(bars_mid,events,cfg)
    if not events.empty:
        ct=pd.to_datetime(events.contact_time,utc=True);events=events[(ct>=start)&(ct<end)].copy()
    events=attach_identity(events,year);events,canon_sel=parity_gate(events,canonical,sessions,year)
    parity={'version':'COMEX_DEV_RANK1_VANTAGE_EVENT_PARITY_V1','year':year,'market_data_api_calls':False,'canonical_selected_events':int(len(canon_sel)),'generated_selected_events':int(len(events)),'event_uid_parity':True,'selected_sessions':int(events.research_trading_date.nunique()),'outcomes_generated':False}
    (out/'parity_manifest.json').write_text(json.dumps(parity,indent=2))
    if a.parity_only:print(json.dumps(parity,indent=2));return

    records=[];entry_counts={}
    for scenario,sc in SCENARIOS.items():
        bars_exec=apply_fixed_spread_overlay(bars_mid,float(sc['spread_usd']));commission=float(sc['commission_rt_usd'])
        for model in STRUCTURAL_MODELS:
            built=0
            for rec in events.to_dict('records'):
                entry=build_entry(rec,bars_exec,model,acceptance_minutes=cfg.acceptance_minutes)
                if entry is None:continue
                built+=1;rec['_entry_model']=model
                for rr in TARGET_RS:records.append(simulate_record(rec,entry,bars_exec,rr,commission,scenario,sc,'STRUCTURAL',np.nan))
            entry_counts[f'{scenario}:{model}:STRUCTURAL']=int(built)
        for k in TNO_K:
            built=0
            for rec in events.to_dict('records'):
                raw=build_entry(rec,bars_exec,'TOUCH_NEXT_OPEN',acceptance_minutes=cfg.acceptance_minutes)
                if raw is None:continue
                entry=apply_volatility_floor(raw,float(k))
                if entry is None:continue
                built+=1;rec['_entry_model']='TOUCH_NEXT_OPEN'
                for rr in TARGET_RS:records.append(simulate_record(rec,entry,bars_exec,rr,commission,scenario,sc,f'VOL_FLOOR_{k:.2f}',float(k)))
            entry_counts[f'{scenario}:TOUCH_NEXT_OPEN:VOL_FLOOR_{k:.2f}']=int(built)
    r=pd.DataFrame(records);r.to_parquet(out/'event_outcomes.parquet',index=False,compression='zstd');r.head(200).to_csv(out/'event_outcomes_sample_200.csv',index=False);counts=[]
    if len(r):
        for key,g in r.groupby(['scenario','entry_model','risk_rule'],dropna=False):counts.append({'scenario':key[0],'entry_model':key[1],'risk_rule':key[2],'outcome_rows':int(len(g)),'unique_events':int(g.event_uid.nunique()),'rr_values':sorted(float(x) for x in g.target_r.unique())})
    manifest={'version':'COMEX_DEV_RANK1_VANTAGE_EVENT_OUTCOMES_V1','market_data_api_calls':False,'year':year,'canonical_selected_events':int(len(canon_sel)),'generated_selected_events':int(len(events)),'event_uid_parity':True,'selected_sessions':int(events.research_trading_date.nunique()),'outcome_rows':int(len(r)),'scenarios':SCENARIOS,'structural_models':STRUCTURAL_MODELS,'touch_next_open_vol_floor_k':list(TNO_K),'raw_touch_next_open_exported':False,'target_R_surface':[float(x) for x in TARGET_RS],'horizon_minutes':120,'engine':'unchanged rzr.build_entry + rzr.simulate_one + fixed Vantage overlay; event-level publication only','net_r_surface_freeze':'COMEX_DEV_RANK1_NET_R_SURFACE_FREEZE_v1.md','entry_counts':entry_counts,'counts':counts};(out/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
