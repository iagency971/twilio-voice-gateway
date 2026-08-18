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
from rzr.entries_v1 import build_entry,simulate_surface,TARGET_RS
from rzr.entries_s1 import apply_volatility_floor,VOL_FLOOR_K
FAMILIES=['DISPLACEMENT_ORIGIN','OBJECTIVE_LIQUIDITY','MEMORY','FVG']
MODELS=['PASSIVE_TOUCH','TOUCH_NEXT_OPEN','CLEAN_REJECTION','FAILED_AUCTION','ACCEPTANCE_RETEST']
def pf(x):
 a=pd.to_numeric(x,errors='coerce').dropna(); pos=float(a[a>0].sum()); neg=float(-a[a<0].sum()); return pos/neg if neg>0 else (np.inf if pos>0 else np.nan)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('csv'); ap.add_argument('--target-start',required=True); ap.add_argument('--target-end',required=True); ap.add_argument('--out',required=True); ap.add_argument('--horizon-minutes',type=int,default=120); a=ap.parse_args()
 start=pd.Timestamp(a.target_start); start=start.tz_localize('UTC') if start.tzinfo is None else start.tz_convert('UTC'); end=pd.Timestamp(a.target_end); end=end.tz_localize('UTC') if end.tzinfo is None else end.tz_convert('UTC'); out=Path(a.out); out.mkdir(parents=True,exist_ok=True); cfg=ResearchConfig()
 bars=load_ohlc_csv(a.csv).sort_index().copy(); req=['open_bid','high_bid','low_bid','close_bid','open_ask','high_ask','low_ask','close_ask','spread']; miss=[c for c in req if c not in bars.columns]
 if miss: raise ValueError(miss)
 for c in req: bars[c]=pd.to_numeric(bars[c],errors='raise')
 bars['quote_active']=quote_activity_mask(bars); bars['sigma60']=robust_sigma60(bars); zones=generate_baseline_zones(bars,cfg); contacts=find_first_contacts(bars,zones,bars.sigma60,cfg); contacts=collapse_contact_events(contacts,cfg.stack_overlap_threshold); contacts=label_contacts(bars,contacts,cfg); contacts=classify_behavior_v2(bars,contacts,cfg)
 ct=pd.to_datetime(contacts.contact_time,utc=True); contacts=contacts[(ct>=start)&(ct<end)].copy(); sf=contacts.constituent_families.fillna(''); masks={f:sf.str.contains(f'"{f}"',regex=False) for f in FAMILIES}
 samples={'DISPLACEMENT_ORIGIN_ONLY':masks['DISPLACEMENT_ORIGIN']&~masks['OBJECTIVE_LIQUIDITY']&~masks['MEMORY']&~masks['FVG'],'OBJECTIVE_LIQUIDITY_ONLY':masks['OBJECTIVE_LIQUIDITY']&~masks['DISPLACEMENT_ORIGIN']&~masks['MEMORY']&~masks['FVG'],'MEMORY_ONLY':masks['MEMORY']&~masks['DISPLACEMENT_ORIGIN']&~masks['OBJECTIVE_LIQUIDITY']&~masks['FVG'],'DOZ_OBJECTIVE_ONLY':masks['DISPLACEMENT_ORIGIN']&masks['OBJECTIVE_LIQUIDITY']&~masks['MEMORY']&~masks['FVG']}
 recs=[]; counts={}
 for sample,mask in samples.items():
  g=contacts[mask]
  for model in MODELS:
   built=0
   for r in g.to_dict('records'):
    e0=build_entry(r,bars,model,acceptance_minutes=cfg.acceptance_minutes)
    if not e0: continue
    built+=1
    for k in VOL_FLOOR_K:
     e=apply_volatility_floor(e0,k)
     if not e: continue
     base={'sample':sample,'entry_model':model,'vol_floor_k':k,'contact_time':r.get('contact_time'),'direction':e['direction'],'entry_price':e['entry_price'],'stop_price':e['stop_price'],'risk_price':e['risk_price'],'structural_risk_price':e['structural_risk_price'],'s1_widened':e['s1_widened'],'sigma60':e['sigma60']}
     for sim in simulate_surface(e,bars,TARGET_RS,horizon_minutes=a.horizon_minutes): recs.append({**base,**sim})
   counts[f'{sample}:{model}']=built
 t=pd.DataFrame(recs); t['net_R_cost1_5x']=t.gross_R-1.5*t.legacy_commission_R; rows=[]
 for (sample,model,k,tr),g in t.groupby(['sample','entry_model','vol_floor_k','target_r'],sort=True):
  rows.append({'sample':sample,'entry_model':model,'vol_floor_k':float(k),'target_r':float(tr),'trades':len(g),'widened_pct':100*g.s1_widened.mean(),'avg_gross_R':g.gross_R.mean(),'pf_gross':pf(g.gross_R),'avg_net_R_legacy22':g.net_R_legacy22.mean(),'pf_net_legacy22':pf(g.net_R_legacy22),'avg_net_R_cost1_5x':g.net_R_cost1_5x.mean(),'pf_net_cost1_5x':pf(g.net_R_cost1_5x),'median_risk_price':g.risk_price.median(),'median_structural_risk_price':g.structural_risk_price.median(),'median_commission_R':g.legacy_commission_R.median()})
 s=pd.DataFrame(rows); s.to_csv(out/'summary.csv',index=False); t.to_csv(out/'trade_surface.csv.gz',index=False,compression='gzip'); json.dump({'version':'PHASE_C_S1_VOLATILITY_FLOOR_V1','scientific_status':'exploratory sensitivity; exact k grid frozen before S1 run','target_start':str(start),'target_end':str(end),'target_events':len(contacts),'vol_floor_k':list(VOL_FLOOR_K),'target_R_surface':list(TARGET_RS),'entry_models':MODELS,'rule':'risk=max(structural_risk,k*sigma60); never tightens structural stop','costs':'$22 RT/100oz and 1.5x stress','entry_counts':counts},open(out/'manifest.json','w'),indent=2); print(s.sort_values('avg_net_R_legacy22',ascending=False).head(50).to_string(index=False))
if __name__=='__main__':main()
