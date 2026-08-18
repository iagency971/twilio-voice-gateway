#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from rzr.config import ResearchConfig
from rzr.io import load_ohlc_csv
from rzr.features import quote_activity_mask,robust_sigma60
from rzr.zones import generate_baseline_zones
from rzr.contacts import find_first_contacts
from rzr.stacking import collapse_contact_events
from rzr.labels import label_contacts
from rzr.behavior_v2 import classify_behavior_v2
from rzr.entries_v1 import build_entry,simulate_one
from rzr.entries_s1 import apply_volatility_floor

TARGET_RS=(1.0,1.5,2.0)
VOL_FLOOR_K=1.0
SAMPLE='DISPLACEMENT_ORIGIN_ONLY'
MODEL='TOUCH_NEXT_OPEN'

def pf(x):
    a=pd.to_numeric(x,errors='coerce').dropna(); pos=float(a[a>0].sum()); neg=float(-a[a<0].sum())
    return pos/neg if neg>0 else (np.inf if pos>0 else np.nan)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('csv'); ap.add_argument('--target-start',required=True); ap.add_argument('--target-end',required=True); ap.add_argument('--out',required=True); ap.add_argument('--horizon-minutes',type=int,default=120); a=ap.parse_args()
    start=pd.Timestamp(a.target_start); start=start.tz_localize('UTC') if start.tzinfo is None else start.tz_convert('UTC')
    end=pd.Timestamp(a.target_end); end=end.tz_localize('UTC') if end.tzinfo is None else end.tz_convert('UTC')
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True); cfg=ResearchConfig()
    bars=load_ohlc_csv(a.csv).sort_index().copy(); req=['open_bid','high_bid','low_bid','close_bid','open_ask','high_ask','low_ask','close_ask','spread']; miss=[c for c in req if c not in bars.columns]
    if miss: raise ValueError(f'Missing BID/ASK execution columns: {miss}')
    for c in req: bars[c]=pd.to_numeric(bars[c],errors='raise')
    bars['quote_active']=quote_activity_mask(bars); bars['sigma60']=robust_sigma60(bars)
    zones=generate_baseline_zones(bars,cfg); contacts=find_first_contacts(bars,zones,bars['sigma60'],cfg); contacts=collapse_contact_events(contacts,cfg.stack_overlap_threshold); contacts=label_contacts(bars,contacts,cfg); contacts=classify_behavior_v2(bars,contacts,cfg)
    ct=pd.to_datetime(contacts['contact_time'],utc=True); contacts=contacts[(ct>=start)&(ct<end)].copy()
    sf=contacts['constituent_families'].fillna('')
    doz=sf.str.contains('"DISPLACEMENT_ORIGIN"',regex=False); obj=sf.str.contains('"OBJECTIVE_LIQUIDITY"',regex=False); mem=sf.str.contains('"MEMORY"',regex=False); fvg=sf.str.contains('"FVG"',regex=False)
    g=contacts[doz & ~obj & ~mem & ~fvg]
    recs=[]; built=0; widened=0
    for r in g.to_dict('records'):
        e0=build_entry(r,bars,MODEL,acceptance_minutes=cfg.acceptance_minutes)
        if not e0: continue
        e=apply_volatility_floor(e0,VOL_FLOOR_K)
        if not e: continue
        built+=1; widened+=int(bool(e['s1_widened']))
        base={'sample':SAMPLE,'entry_model':MODEL,'vol_floor_k':VOL_FLOOR_K,'contact_time':r.get('contact_time'),'direction':e['direction'],'entry_price':e['entry_price'],'stop_price':e['stop_price'],'risk_price':e['risk_price'],'structural_risk_price':e['structural_risk_price'],'s1_widened':e['s1_widened'],'sigma60':e['sigma60']}
        for tr in TARGET_RS:
            sim=simulate_one(e,bars,tr,horizon_minutes=a.horizon_minutes); recs.append({**base,**sim})
    t=pd.DataFrame(recs)
    if t.empty: raise SystemExit('No promoted S1 trades built')
    t['net_R_cost1_5x']=t['gross_R']-1.5*t['legacy_commission_R']
    rows=[]
    for tr,gx in t.groupby('target_r',sort=True):
        rows.append({'sample':SAMPLE,'entry_model':MODEL,'vol_floor_k':VOL_FLOOR_K,'target_r':float(tr),'trades':int(len(gx)),'widened_pct':100.0*float(gx.s1_widened.mean()),'avg_gross_R':float(gx.gross_R.mean()),'pf_gross':float(pf(gx.gross_R)),'avg_net_R_legacy22':float(gx.net_R_legacy22.mean()),'pf_net_legacy22':float(pf(gx.net_R_legacy22)),'avg_net_R_cost1_5x':float(gx.net_R_cost1_5x.mean()),'pf_net_cost1_5x':float(pf(gx.net_R_cost1_5x)),'median_risk_price':float(gx.risk_price.median()),'median_structural_risk_price':float(gx.structural_risk_price.median()),'median_commission_R':float(gx.legacy_commission_R.median()),'min_risk_price':float(gx.risk_price.min()),'min_structural_risk_price':float(gx.structural_risk_price.min()),'sum_net_R_legacy22':float(gx.net_R_legacy22.sum()),'sum_net_R_cost1_5x':float(gx.net_R_cost1_5x.sum())})
    s=pd.DataFrame(rows); s.to_csv(out/'summary.csv',index=False)
    json.dump({'version':'PHASE_C_S1_PROMOTED_MULTIYEAR_V1','source_commit':os.getenv('GITHUB_SHA','LOCAL'),'target_start':str(start),'target_end':str(end),'target_events':int(len(contacts)),'sample':SAMPLE,'entry_model':MODEL,'vol_floor_k':VOL_FLOOR_K,'target_R_surface':list(TARGET_RS),'built_trades':int(built),'widened_trades':int(widened),'rule':'risk=max(structural_risk,1.0*causal sigma60); never tightens structural stop','selection_source':'2025 preregistered S1 computational screen','decision_gate':'PHASE_C_S1_MULTIYEAR_GATE.md','costs':'$22 RT/100oz and 1.5x stress','horizon_minutes':int(a.horizon_minutes)},open(out/'manifest.json','w'),indent=2)
    print(s.to_string(index=False))
if __name__=='__main__': main()
