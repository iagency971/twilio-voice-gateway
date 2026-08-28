#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import pandas as pd

EPS=1e-12
WINDOWS={
 'H1':(pd.Timestamp('2024-08-01T00:00:00Z'),pd.Timestamp('2025-08-01T00:00:00Z')),
 'H2':(pd.Timestamp('2025-08-01T00:00:00Z'),pd.Timestamp('2026-08-01T00:00:00Z')),
}

def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod

def parse_args():
 p=argparse.ArgumentParser();p.add_argument('--session',required=True);p.add_argument('--files',nargs='+',required=True);p.add_argument('--z4-pkl',required=True);p.add_argument('--output',required=True);p.add_argument('--trades-csv',required=True);p.add_argument('--triggers-csv',required=True);return p.parse_args()

def overlap(a,b):return min(float(a['zhi']),float(b['zhi']))>=max(float(a['zlo']),float(b['zlo']))-EPS

def zone_same(a,b,v1,v2):return overlap(a,b) or abs(float(a['center'])-float(b['center']))<=.25*max(float(v1),float(v2))+EPS

def gap_same(a,b):return zone_same(a['lower'],b['lower'],a['v'],b['v']) and zone_same(a['upper'],b['upper'],a['v'],b['v'])

def qpack(x):
 a=np.asarray([float(v) for v in x if v is not None and np.isfinite(float(v))],float)
 return {'n':int(len(a)),'p10':float(np.quantile(a,.1)) if len(a) else None,'median':float(np.median(a)) if len(a) else None,'p90':float(np.quantile(a,.9)) if len(a) else None}

def outcome_scan(raw,ex,end,target,stop):
 status='NEITHER';term=end
 for k in range(ex,end+1):
  tp=float(raw.at[k,'low'])<=target+EPS; inv=float(raw.at[k,'close'])>stop+EPS
  if tp and inv:status='AMBIGUOUS';term=k;break
  if tp:status='TP_FIRST';term=k;break
  if inv:status='INVALIDATION_FIRST';term=k;break
 return status,term

def diag(d):
 if len(d)==0:return {'executed':0,'terminal_n':0,'TP_FIRST':0,'INVALIDATION_FIRST':0,'NEITHER':0,'AMBIGUOUS':0,'terminal_tp_rate':None,'expectancy_R':None,'profit_factor_R':None}
 c=Counter(d.outcome.astype(str));tp=c['TP_FIRST'];sl=c['INVALIDATION_FIRST'];term=d[d.outcome.isin(['TP_FIRST','INVALIDATION_FIRST'])]
 vals=np.array([float(r.nominal_rr) if r.outcome=='TP_FIRST' else -1.0 for _,r in term.iterrows()],float)
 pos=float(vals[vals>0].sum()) if len(vals) else 0.;neg=float(-vals[vals<0].sum()) if len(vals) else 0.
 return {'executed':int(len(d)),'terminal_n':int(tp+sl),'TP_FIRST':int(tp),'INVALIDATION_FIRST':int(sl),'NEITHER':int(c['NEITHER']),'AMBIGUOUS':int(c['AMBIGUOUS']),'terminal_tp_rate':float(tp/(tp+sl)) if tp+sl else None,'expectancy_R':float(vals.mean()) if len(vals) else None,'profit_factor_R':float(pos/neg) if neg>0 else (float('inf') if pos>0 else None),'nominal_rr':qpack(d.nominal_rr),'stop_distance_v':qpack(d.stop_distance_v),'target_distance_v':qpack(d.target_distance_v)}

def one_position(d):
 if len(d)==0:return d.copy()
 q=d.sort_values(['entry_time','trigger_time']).copy();keep=[];until=None
 for i,r in q.iterrows():
  et=pd.Timestamp(r.entry_time);ot=pd.Timestamp(r.outcome_time)
  if until is None or et>until:
   keep.append(i);until=ot
 return q.loc[keep].copy()

def main():
 a=parse_args();direct=load_module('gap_direct_helpers',Path('xau-wick-zone-pro/session-research/xau_e123_direct_sell_between_above_z4_v1_0.py'));v01=direct.v01
 raw=v01.load_raw(a.files);active=v01.active_m1(raw);vmap={pd.Timestamp(r.time):float(r.v60) for _,r in active.iterrows() if np.isfinite(r.v60)}
 z4=pd.read_pickle(a.z4_pkl).copy();z4['time']=pd.to_datetime(z4.time,utc=True);bad=sorted(v01.FORBIDDEN & set(z4.columns));
 if bad:raise RuntimeError(f'future columns in Z4: {bad}')
 states=[];state_for={}
 for t,g in z4.groupby('time',sort=True):
  t=pd.Timestamp(t);k=len(states);rows=[{'zlo':float(r.zlo),'center':float(r.center),'zhi':float(r.zhi),'side':int(r.side)} for _,r in g.sort_values('center').iterrows()];states.append({'time':t,'z4':rows})
  i0=direct.raw_index(raw,t,'right')+1;i1=direct.raw_index(raw,t+pd.Timedelta(minutes=5),'right')
  for j in range(max(0,i0),min(len(raw)-1,i1)+1):
   tj=pd.Timestamp(raw.at[j,'time'])
   if direct.in_session(tj,a.session) and tj>t and tj<=t+pd.Timedelta(minutes=5):state_for[j]=k
 sessions=defaultdict(list)
 for j,t in enumerate(raw.time):
  sid=direct.session_id(t,a.session)
  if sid is not None:sessions[sid].append(j)
 triggers=[];trades=[]
 for sid in sorted(sessions):
  idxs=sessions[sid];idxset=set(idxs);end=idxs[-1];consumed=[]
  for j in idxs:
   if j not in state_for:continue
   row=raw.loc[j];t=pd.Timestamp(row.time);v=vmap.get(t,np.nan)
   if not np.isfinite(v) or v<=0:continue
   br,cp=direct.bearish_rejection(row)
   if not br:continue
   zs=states[state_for[j]]['z4'];h=float(row.high);found=[]
   for lo,hi in zip(zs[:-1],zs[1:]):
    if float(lo['zhi'])<float(hi['zlo'])-EPS and h>float(lo['zhi'])+EPS and h<float(hi['zlo'])-EPS:found.append((lo,hi))
   if not found:continue
   lo,hi=found[0];ident={'lower':lo,'upper':hi,'v':v}
   if any(gap_same(ident,q) for q in consumed):continue
   consumed.append(ident)
   rec={'session_id':sid,'trigger_time':t,'down_close_position':cp,'lower_zlo':lo['zlo'],'lower_center':lo['center'],'lower_zhi':lo['zhi'],'upper_zlo':hi['zlo'],'upper_center':hi['center'],'upper_zhi':hi['zhi'],'v':v}
   triggers.append(rec)
   target=float(lo['zhi']);stop=float(hi['zlo'])
   if float(row.low)<=target+EPS:continue
   ex=j+1
   if ex not in idxset:continue
   entry=float(raw.at[ex,'open']);et=pd.Timestamp(raw.at[ex,'time'])
   if not (target+EPS<entry<stop-EPS):continue
   sd=stop-entry;td=entry-target
   if sd<=EPS or td<=EPS:continue
   rr=td/sd;out,term=outcome_scan(raw,ex,end,target,stop)
   trades.append({**rec,'entry_time':et,'entry_price':entry,'target_price':target,'stop_price':stop,'stop_distance_v':sd/v,'target_distance_v':td/v,'nominal_rr':rr,'outcome':out,'outcome_time':pd.Timestamp(raw.at[term,'time']),'minutes_entry_to_outcome':float((pd.Timestamp(raw.at[term,'time'])-et).total_seconds()/60)})
 tdf=pd.DataFrame(trades);gdf=pd.DataFrame(triggers);tdf.to_csv(a.trades_csv,index=False,compression='gzip');gdf.to_csv(a.triggers_csv,index=False,compression='gzip')
 if len(tdf):
  for c in ['trigger_time','entry_time','outcome_time']:tdf[c]=pd.to_datetime(tdf[c],utc=True)
 out={'status':'Z4_GAP_BR70_DIRECT_SELL_RETROSPECTIVE_EXPLORATORY_COMPLETE','session':a.session,'results':{}}
 for w,(lo,hi) in WINDOWS.items():
  q=tdf[(tdf.trigger_time>=lo)&(tdf.trigger_time<hi)] if len(tdf) else tdf
  op=one_position(q)
  counts=q.groupby('session_id').size().to_numpy(float) if len(q) else np.array([])
  out['results'][w]={'all':diag(q),'one_position_at_a_time':diag(op),'signal_frequency':{'sessions_with_trade':int(len(counts)),'median':float(np.median(counts)) if len(counts) else None,'p90':float(np.quantile(counts,.9)) if len(counts) else None}}
 Path(a.output).write_text(json.dumps(out,indent=2,default=str,allow_nan=False));print(json.dumps(out,indent=2,default=str,allow_nan=False))
if __name__=='__main__':main()
