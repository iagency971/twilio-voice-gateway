#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

HERE=Path(__file__).resolve().parent
EPS=1e-12
WINDOWS={
 'H1':(pd.Timestamp('2024-08-01T00:00:00Z'),pd.Timestamp('2025-08-01T00:00:00Z')),
 'H2':(pd.Timestamp('2025-08-01T00:00:00Z'),pd.Timestamp('2026-08-01T00:00:00Z')),
}

def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def parse_args():
 p=argparse.ArgumentParser(); p.add_argument('--session',required=True); p.add_argument('--files',nargs='+',required=True); p.add_argument('--z4-pkl',required=True); p.add_argument('--treated-csv',required=True); p.add_argument('--pairs-csv',required=True); p.add_argument('--controls-csv',required=True); p.add_argument('--output',required=True); return p.parse_args()

def target_same(t,c):
 ov=min(float(t.target_zhi),float(c.target_zhi))>=max(float(t.target_zlo),float(c.target_zlo))-EPS
 tol=.25*max(float(t.v_entry_context),float(c.v_entry_context))
 return ov or abs(float(t.target_center)-float(c.target_center))<=tol+EPS

def classify_anchor(anchor,z4s):
 if not z4s:return None
 top=max(z4s,key=lambda x:(x['zhi'],x['center']))
 if anchor>top['zhi']+EPS:return {'geometry':'ABOVE_HIGHEST_Z4_STRICT','target':top,'upper_neighbor':None}
 zs=sorted(z4s,key=lambda x:(x['center'],x['zlo'],x['zhi']))
 for lo,hi in zip(zs[:-1],zs[1:]):
  if anchor>lo['zhi']+EPS and anchor<hi['zlo']-EPS:return {'geometry':'BETWEEN_Z4_STRICT','target':lo,'upper_neighbor':hi}
 return None

def conservative_r(outcome,rr):
 if outcome=='TP_FIRST':return float(rr)
 if outcome=='INVALIDATION_FIRST':return -1.0
 if outcome=='NEITHER':return 0.0
 return np.nan

def arm_metrics(df,prefix):
 out=df[f'{prefix}_outcome'].astype(str); rr=pd.to_numeric(df[f'{prefix}_nominal_rr'],errors='coerce')
 r=np.array([conservative_r(o,q) for o,q in zip(out,rr)],float); ok=np.isfinite(r); r=r[ok]
 tp=(out=='TP_FIRST').to_numpy(); amb=(out=='AMBIGUOUS').to_numpy(); nonamb=~amb
 terminal=(out.isin(['TP_FIRST','INVALIDATION_FIRST'])).to_numpy()
 tr=[]
 for o,q in zip(out[terminal],rr[terminal]): tr.append(float(q) if o=='TP_FIRST' else -1.0)
 pos=sum(x for x in tr if x>0); neg=-sum(x for x in tr if x<0)
 return {'n_pairs_nonambiguous':int(nonamb.sum()),'tp_probability_all_nonambiguous':float(tp[nonamb].mean()) if nonamb.any() else None,'conservative_mean_R':float(r.mean()) if len(r) else None,'terminal_n':int(terminal.sum()),'terminal_tp_rate':float(tp[terminal].mean()) if terminal.any() else None,'terminal_expectancy_R':float(np.mean(tr)) if tr else None,'terminal_pf_R':float(pos/neg) if neg>0 else (float('inf') if pos>0 else None)}

def pair_metrics(df):
 d=df[(df.e_outcome!='AMBIGUOUS')&(df.c_outcome!='AMBIGUOUS')].copy()
 if len(d)==0:return {'n_pairs':0}
 er=np.array([conservative_r(o,q) for o,q in zip(d.e_outcome,d.e_nominal_rr)],float)
 cr=np.array([conservative_r(o,q) for o,q in zip(d.c_outcome,d.c_nominal_rr)],float)
 etp=(d.e_outcome=='TP_FIRST').astype(float).to_numpy(); ctp=(d.c_outcome=='TP_FIRST').astype(float).to_numpy()
 return {'n_pairs':int(len(d)),'mean_delta_R':float(np.mean(er-cr)),'mean_delta_TP_probability':float(np.mean(etp-ctp)),'treated':arm_metrics(d,'e'),'control':arm_metrics(d,'c')}

def main():
 a=parse_args()
 direct=load_module('direct_frozen',Path('xau-wick-zone-pro/session-research/xau_e123_direct_sell_between_above_z4_v1_0.py'))
 v04=direct.v04; v01=direct.v01
 raw_o=v01.load_raw(a.files); raw_r=direct.reflect_raw(raw_o); active_r=v01.active_m1(raw_r)
 z4_o=pd.read_pickle(a.z4_pkl).copy(); z4_o['time']=pd.to_datetime(z4_o.time,utc=True); z4_r=direct.reflect_z4(z4_o)
 pred=lambda t: direct.in_session(t,a.session); v04.v01.ny_us=pred
 snaps,pools=v04.build_fixed_pools(raw_r,active_r,z4_r); displays=v04.sticky_display(raw_r,snaps,pools)
 state_for_raw,states=direct.build_state_map(raw_r,z4_r,snaps,displays,a.session)
 sessions=defaultdict(list)
 for j,t in enumerate(raw_o.time):
  sid=direct.session_id(t,a.session)
  if sid is not None:sessions[sid].append(j)
 controls=[]
 for sid in sorted(sessions):
  idxs=sessions[sid]; idxset=set(idxs); end_idx=idxs[-1]
  for j in idxs:
   st=states[state_for_raw[j]] if j in state_for_raw else None
   if st is None:continue
   row=raw_o.loc[j]; t=pd.Timestamp(row.time); v=float(st['snap']['v'])
   if not np.isfinite(v) or v<=0:continue
   br,cp=direct.bearish_rejection(row)
   if not br:continue
   ez=[direct.orig_zone_from_reflected(z) for z in st['display']]
   if any(float(row.high)>=z['zlo']-EPS and float(row.low)<=z['zhi']+EPS for z in ez):continue
   z4s=direct.orig_z4s_from_reflected(st['z4']); geo=classify_anchor(float(row.high),z4s)
   if geo is None:continue
   tz=float(geo['target']['zhi'])
   if float(row.low)<=tz+EPS:continue
   ex=j+1
   if ex not in idxset:continue
   entry=float(raw_o.at[ex,'open']); entry_time=pd.Timestamp(raw_o.at[ex,'time'])
   if entry<=tz+EPS:continue
   td=entry-tz
   controls.append({'session_id':sid,'trigger_time':t,'entry_time':entry_time,'entry_price':entry,'geometry':geo['geometry'],'target_zlo':geo['target']['zlo'],'target_center':geo['target']['center'],'target_zhi':tz,'upper_neighbor_zlo':geo['upper_neighbor']['zlo'] if geo['upper_neighbor'] else None,'upper_neighbor_zhi':geo['upper_neighbor']['zhi'] if geo['upper_neighbor'] else None,'v_entry_context':v,'target_distance_v':td/v,'down_close_position':cp,'entry_idx':ex,'end_idx':end_idx})
 cdf=pd.DataFrame(controls); cdf.to_csv(a.controls_csv,index=False,compression='gzip')
 tr=pd.read_csv(a.treated_csv,compression='gzip');
 for c in ['trigger_time','entry_time','outcome_time']: tr[c]=pd.to_datetime(tr[c],utc=True,errors='coerce')
 tr=tr.sort_values(['session_id','trigger_time','entry_label']).reset_index(drop=True); cdf=cdf.sort_values(['session_id','trigger_time']).reset_index(drop=True)
 pairs=[]
 for sid,tg in tr.groupby('session_id',sort=True):
  cg=cdf[cdf.session_id.astype(str)==str(sid)]
  if len(cg)==0:continue
  for geom in ['BETWEEN_Z4_STRICT','ABOVE_HIGHEST_Z4_STRICT']:
   tt=tg[tg.geometry==geom].copy(); cc=cg[cg.geometry==geom].copy()
   if len(tt)==0 or len(cc)==0:continue
   M=np.full((len(tt),len(cc)),1e9,float)
   for ii,(_,te) in enumerate(tt.iterrows()):
    for jj,(_,co) in enumerate(cc.iterrows()):
     dt=abs((pd.Timestamp(te.trigger_time)-pd.Timestamp(co.trigger_time)).total_seconds()/60.0)
     if dt>180+EPS or not target_same(te,co):continue
     cost=.50*abs(float(te.target_distance_v)-float(co.target_distance_v))+.30*abs(float(te.down_close_position)-float(co.down_close_position))+.20*dt/180.0+1e-9*(ii*len(cc)+jj)
     M[ii,jj]=cost
   ri,ci=linear_sum_assignment(M)
   for ii,jj in zip(ri,ci):
    if M[ii,jj]>=1e8:continue
    te=tt.iloc[ii]; co=cc.iloc[jj]
    stopdv=float(te.stop_distance_v); stop=float(co.entry_price)+stopdv*float(co.v_entry_context)
    rr=(float(co.entry_price)-float(co.target_zhi))/(stop-float(co.entry_price))
    out,term,mfe,mae=direct.outcome_scan(raw_o,int(co.entry_idx),int(co.end_idx),float(co.entry_price),float(co.target_zhi),stop,float(co.v_entry_context))
    pairs.append({'session_id':sid,'geometry':geom,'e_trigger_time':te.trigger_time,'c_trigger_time':co.trigger_time,'match_cost':float(M[ii,jj]),'time_diff_min':abs((pd.Timestamp(te.trigger_time)-pd.Timestamp(co.trigger_time)).total_seconds()/60.0),'e_entry_label':te.entry_label,'e_outcome':te.outcome,'e_nominal_rr':float(te.nominal_rr),'e_stop_distance_v':float(te.stop_distance_v),'e_target_distance_v':float(te.target_distance_v),'e_down_close_position':float(te.down_close_position),'c_outcome':out,'c_nominal_rr':float(rr),'c_stop_distance_v':stopdv,'c_target_distance_v':float(co.target_distance_v),'c_down_close_position':float(co.down_close_position),'c_stop_price':stop,'c_entry_price':float(co.entry_price),'c_outcome_time':pd.Timestamp(raw_o.at[term,'time']),'c_mfe_v':mfe,'c_mae_v':mae})
 pdf=pd.DataFrame(pairs); pdf.to_csv(a.pairs_csv,index=False,compression='gzip')
 summary={'status':'DIRECT_ESELL_MATCHED_NONE_CONTROL_COMPLETE','session':a.session,'treated_rows':int(len(tr)),'control_candidates':int(len(cdf)),'pairs':int(len(pdf)),'results':{}}
 for w,(lo,hi) in WINDOWS.items():
  tx=tr[(tr.trigger_time>=lo)&(tr.trigger_time<hi)]
  px=pdf[(pd.to_datetime(pdf.e_trigger_time,utc=True)>=lo)&(pd.to_datetime(pdf.e_trigger_time,utc=True)<hi)] if len(pdf) else pdf
  s={'treated_n':int(len(tx)),'matched_n':int(len(px)),'matching_coverage':float(len(px)/len(tx)) if len(tx) else None,'all':pair_metrics(px)}
  for g in ['BETWEEN_Z4_STRICT','ABOVE_HIGHEST_Z4_STRICT']:
   tgg=tx[tx.geometry==g]; pgg=px[px.geometry==g] if len(px) else px
   s[g]={'treated_n':int(len(tgg)),'matched_n':int(len(pgg)),'matching_coverage':float(len(pgg)/len(tgg)) if len(tgg) else None,'paired':pair_metrics(pgg)}
  summary['results'][w]=s
 Path(a.output).write_text(json.dumps(summary,indent=2,default=str,allow_nan=False)); print(json.dumps(summary,indent=2,default=str,allow_nan=False))
if __name__=='__main__':main()
