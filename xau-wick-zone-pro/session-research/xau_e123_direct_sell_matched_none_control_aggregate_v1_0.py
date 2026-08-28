#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

WINDOWS={
 'H1':(pd.Timestamp('2024-08-01T00:00:00Z'),pd.Timestamp('2025-08-01T00:00:00Z')),
 'H2':(pd.Timestamp('2025-08-01T00:00:00Z'),pd.Timestamp('2026-08-01T00:00:00Z')),
 'POOLED':(pd.Timestamp('2024-08-01T00:00:00Z'),pd.Timestamp('2026-08-01T00:00:00Z')),
}

def parse_args():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);return p.parse_args()

def cr(o,rr):
 if o=='TP_FIRST':return float(rr)
 if o=='INVALIDATION_FIRST':return -1.0
 if o=='NEITHER':return 0.0
 return np.nan

def metrics(d):
 q=d[(d.e_outcome!='AMBIGUOUS')&(d.c_outcome!='AMBIGUOUS')].copy()
 if len(q)==0:return {'n_pairs':0}
 er=np.array([cr(o,r) for o,r in zip(q.e_outcome,q.e_nominal_rr)],float); crv=np.array([cr(o,r) for o,r in zip(q.c_outcome,q.c_nominal_rr)],float)
 et=(q.e_outcome=='TP_FIRST').astype(float).to_numpy();ct=(q.c_outcome=='TP_FIRST').astype(float).to_numpy()
 return {'n_pairs':int(len(q)),'mean_R_E':float(np.nanmean(er)),'mean_R_control':float(np.nanmean(crv)),'mean_delta_R':float(np.nanmean(er-crv)),'tp_probability_E':float(et.mean()),'tp_probability_control':float(ct.mean()),'mean_delta_TP_probability':float(np.mean(et-ct)),'median_time_diff_min':float(q.time_diff_min.median()),'median_abs_target_distance_v_diff':float((q.e_target_distance_v-q.c_target_distance_v).abs().median()),'median_abs_down_close_position_diff':float((q.e_down_close_position-q.c_down_close_position).abs().median())}

def boot(d,n=2000,seed=20260828):
 q=d[(d.e_outcome!='AMBIGUOUS')&(d.c_outcome!='AMBIGUOUS')].copy()
 if len(q)==0:return {'n_clusters':0,'delta_R_ci95':[None,None],'delta_TP_ci95':[None,None]}
 q['cluster']=q.session.astype(str)+'|'+q.session_id.astype(str); clusters=sorted(q.cluster.unique()); rng=np.random.default_rng(seed); dr=[];dt=[]
 for _ in range(n):
  draw=rng.choice(clusters,size=len(clusters),replace=True); parts=[q[q.cluster==c] for c in draw]; b=pd.concat(parts,ignore_index=True)
  er=np.array([cr(o,r) for o,r in zip(b.e_outcome,b.e_nominal_rr)],float);cv=np.array([cr(o,r) for o,r in zip(b.c_outcome,b.c_nominal_rr)],float)
  dr.append(float(np.nanmean(er-cv)));dt.append(float(np.mean((b.e_outcome=='TP_FIRST').astype(float)-(b.c_outcome=='TP_FIRST').astype(float))))
 return {'n_clusters':len(clusters),'delta_R_ci95':[float(np.quantile(dr,.025)),float(np.quantile(dr,.975))],'delta_TP_ci95':[float(np.quantile(dt,.025)),float(np.quantile(dt,.975))]}

def main():
 a=parse_args();root=Path(a.root);pairs=[];session_results={};treated_counts={}
 for p in sorted(root.glob('*_PAIRS.csv.gz')):
  s=p.name.replace('_PAIRS.csv.gz','');d=pd.read_csv(p,compression='gzip');d['session']=s;d['e_trigger_time']=pd.to_datetime(d.e_trigger_time,utc=True);pairs.append(d)
 for p in sorted(root.glob('*_CONTROL_RESULT.json')):
  r=json.load(open(p));s=r['session'];session_results[s]=r
  for w in ['H1','H2']:
   treated_counts[(s,w,'BETWEEN_Z4_STRICT')]=r['results'][w]['BETWEEN_Z4_STRICT']['treated_n'];treated_counts[(s,w,'ABOVE_HIGHEST_Z4_STRICT')]=r['results'][w]['ABOVE_HIGHEST_Z4_STRICT']['treated_n']
 allp=pd.concat(pairs,ignore_index=True) if pairs else pd.DataFrame()
 out={'status':'DIRECT_ESELL_MATCHED_NONE_CONTROL_AGGREGATE_COMPLETE','primary_geometry':'BETWEEN_Z4_STRICT','session_results':session_results,'aggregate':{},'production_authorization':'NONE_CONTROL_STUDY_ONLY'}
 for geom in ['BETWEEN_Z4_STRICT','ABOVE_HIGHEST_Z4_STRICT']:
  out['aggregate'][geom]={}
  for w,(lo,hi) in WINDOWS.items():
   d=allp[(allp.geometry==geom)&(allp.e_trigger_time>=lo)&(allp.e_trigger_time<hi)].copy()
   m=metrics(d);m['bootstrap']=boot(d)
   if w!='POOLED':
    denom=sum(treated_counts.get((s,w,geom),0) for s in session_results);m['treated_n']=int(denom);m['matched_n']=int(len(d));m['matching_coverage']=float(len(d)/denom) if denom else None
   out['aggregate'][geom][w]=m
  ranks={}
  for rank in ['E1','E2','E3']:
   ranks[rank]={}
   for w,(lo,hi) in WINDOWS.items():
    d=allp[(allp.geometry==geom)&(allp.e_entry_label==rank)&(allp.e_trigger_time>=lo)&(allp.e_trigger_time<hi)].copy();ranks[rank][w]=metrics(d)
  out['aggregate'][geom]['by_E_rank_descriptive']=ranks
 b=out['aggregate']['BETWEEN_Z4_STRICT'];h1=b['H1'];h2=b['H2'];pool=b['POOLED']
 gate={'H1_coverage_ge_50pct':bool(h1.get('matching_coverage') is not None and h1['matching_coverage']>=.50),'H2_coverage_ge_50pct':bool(h2.get('matching_coverage') is not None and h2['matching_coverage']>=.50),'H1_delta_R_positive':bool(h1.get('mean_delta_R') is not None and h1['mean_delta_R']>0),'H2_delta_R_positive':bool(h2.get('mean_delta_R') is not None and h2['mean_delta_R']>0),'pooled_delta_R_ci_low_positive':bool(pool['bootstrap']['delta_R_ci95'][0] is not None and pool['bootstrap']['delta_R_ci95'][0]>0),'H1_delta_TP_nonnegative':bool(h1.get('mean_delta_TP_probability') is not None and h1['mean_delta_TP_probability']>=0),'H2_delta_TP_nonnegative':bool(h2.get('mean_delta_TP_probability') is not None and h2['mean_delta_TP_probability']>=0)}
 gate['pass']=all(gate.values());out['primary_incremental_gate']=gate;out['interpretation_status']='HISTORICAL_INCREMENTAL_E_CONTACT_SUPPORTED_PENDING_FUTURE_CONFIRMATION' if gate['pass'] else 'INCREMENTAL_E_CONTACT_NOT_ESTABLISHED_CONTROL_EXPLAINS_OR_INCONCLUSIVE'
 Path(a.output).write_text(json.dumps(out,indent=2,default=str,allow_nan=False));print(json.dumps(out,indent=2,default=str,allow_nan=False))
if __name__=='__main__':main()
