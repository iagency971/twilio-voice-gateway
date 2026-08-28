#!/usr/bin/env python3
from __future__ import annotations
import argparse, glob, json
from pathlib import Path
import numpy as np
import pandas as pd

COSTS=[0.00,0.05,0.10,0.15,0.20,0.25,0.30,0.40,0.50]
WINDOWS={
 'H1':(pd.Timestamp('2024-08-01T00:00:00Z'),pd.Timestamp('2025-08-01T00:00:00Z')),
 'H2':(pd.Timestamp('2025-08-01T00:00:00Z'),pd.Timestamp('2026-08-01T00:00:00Z')),
}
SESSIONS=['US','ASIA_BROAD','ASIA_CORE_STANDALONE','EUROPE']

def parse_args():
 p=argparse.ArgumentParser();p.add_argument('--files',nargs='+',required=True);p.add_argument('--evidence-root',required=True);p.add_argument('--output',required=True);p.add_argument('--realized-csv',required=True);return p.parse_args()

def load_raw(patterns):
 frames=[]
 for pat in patterns:
  for f in sorted(glob.glob(pat)):
   d=pd.read_csv(f,usecols=['timestamp','close']);d['time']=pd.to_datetime(d.timestamp,unit='ms',utc=True);frames.append(d[['time','close']])
 r=pd.concat(frames,ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True);r['close']=pd.to_numeric(r.close,errors='raise').astype(float);return r

def one_position(d):
 if len(d)==0:return d.copy()
 q=d.sort_values(['entry_time','trigger_time']).copy();keep=[];until=None
 for i,r in q.iterrows():
  et=pd.Timestamp(r.entry_time);ot=pd.Timestamp(r.outcome_time)
  if until is None or et>until:keep.append(i);until=ot
 return q.loc[keep].copy()

def stats(d):
 if len(d)==0:return {'n':0,'gross_realized_mean_R':None,'neither_n':0,'neither_realized_R':{'mean':None,'median':None,'p10':None,'p90':None},'break_even_cost_usd_per_oz':None,'net_mean_R_by_cost':{f'{c:.2f}':None for c in COSTS}}
 g=d.gross_realized_R.to_numpy(float);inv=1.0/d.stop_distance_usd.to_numpy(float);den=float(np.mean(inv));be=float(np.mean(g)/den) if den>0 else None;n=d[d.outcome=='NEITHER'].gross_realized_R.to_numpy(float)
 return {'n':int(len(d)),'gross_realized_mean_R':float(np.mean(g)),'neither_n':int(len(n)),'neither_realized_R':{'mean':float(np.mean(n)) if len(n) else None,'median':float(np.median(n)) if len(n) else None,'p10':float(np.quantile(n,.1)) if len(n) else None,'p90':float(np.quantile(n,.9)) if len(n) else None},'break_even_cost_usd_per_oz':be,'net_mean_R_by_cost':{f'{c:.2f}':float(np.mean(g-c*inv)) for c in COSTS},'stop_distance_usd':{'median':float(np.median(d.stop_distance_usd)),'p10':float(np.quantile(d.stop_distance_usd,.1)),'p90':float(np.quantile(d.stop_distance_usd,.9))}}

def main():
 a=parse_args();raw=load_raw(a.files);close_map=pd.Series(raw.close.values,index=raw.time).to_dict();root=Path(a.evidence_root);allrows=[];results={}
 for s in SESSIONS:
  fs=list(root.glob(f'{s}_Z4_GAP_TRADES.csv.gz'));assert len(fs)==1,(s,fs)
  d=pd.read_csv(fs[0],compression='gzip');
  for c in ['trigger_time','entry_time','outcome_time']:d[c]=pd.to_datetime(d[c],utc=True,errors='raise')
  d['session']=s;d['stop_distance_usd']=d.stop_price.astype(float)-d.entry_price.astype(float);assert (d.stop_distance_usd>0).all()
  endclose=[];gross=[]
  for _,r in d.iterrows():
   o=str(r.outcome)
   if o=='TP_FIRST':ec=np.nan;gr=float(r.nominal_rr)
   elif o=='INVALIDATION_FIRST':ec=np.nan;gr=-1.0
   elif o=='AMBIGUOUS':ec=np.nan;gr=-1.0
   elif o=='NEITHER':
    t=pd.Timestamp(r.outcome_time);assert t in close_map,t;ec=float(close_map[t]);gr=(float(r.entry_price)-ec)/float(r.stop_distance_usd)
   else:raise RuntimeError(o)
   endclose.append(ec);gross.append(gr)
  d['session_end_close_if_neither']=endclose;d['gross_realized_R']=gross;allrows.append(d)
  results[s]={}
  for w,(lo,hi) in WINDOWS.items():
   q=d[(d.trigger_time>=lo)&(d.trigger_time<hi)].copy();results[s][w]={'all':stats(q),'one_position_at_a_time':stats(one_position(q))}
 all_d=pd.concat(allrows,ignore_index=True);all_d.to_csv(a.realized_csv,index=False,compression='gzip')
 pooled={}
 for w,(lo,hi) in WINDOWS.items():
  q=all_d[(all_d.trigger_time>=lo)&(all_d.trigger_time<hi)].copy();parts=[]
  for s in SESSIONS:
   parts.append(one_position(q[q.session==s]))
  op=pd.concat(parts,ignore_index=True) if parts else q.iloc[0:0]
  pooled[w]={'all_cross_session_definitions':stats(q),'one_position_per_session_definition':stats(op)}
 out={'status':'Z4_GAP_BR70_EXECUTION_ROBUSTNESS_COMPLETE','effective_cost_grid_usd_per_oz':COSTS,'neither_rule':'liquidate at frozen session-end BID M1 close','ambiguous_rule':'conservative -1R before costs','sessions':results,'pooled_descriptive_cross_session_definitions':pooled,'production_authorization':'NONE_EXECUTION_ROBUSTNESS_ONLY'};Path(a.output).write_text(json.dumps(out,indent=2,allow_nan=False));print(json.dumps(out,indent=2,allow_nan=False))
if __name__=='__main__':main()
