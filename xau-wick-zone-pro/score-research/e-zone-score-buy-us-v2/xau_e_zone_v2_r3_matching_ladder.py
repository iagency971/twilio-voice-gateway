#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd

SEED='E_ZONE_SCORE_BUY_US_V2_R3_20260830'
MATCH=['trend15_v','trend60_v','trend240_v','nearest_upper_z4_dist_v','log_v_snapshot']
DESIGNS=[
 {'id':'D0_FROZEN_R2','weekday_exact':True,'bucket_exact':True,'logv':.20,'z4':.25},
 {'id':'D1_WIDER_CALIPERS','weekday_exact':True,'bucket_exact':True,'logv':.35,'z4':.50},
 {'id':'D2_NO_WEEKDAY_EXACT','weekday_exact':False,'bucket_exact':True,'logv':.35,'z4':.50},
 {'id':'D3_CONTEXT_WIDE','weekday_exact':False,'bucket_exact':True,'logv':.50,'z4':1.00},
 {'id':'D4_BUCKET_AS_DISTANCE','weekday_exact':False,'bucket_exact':False,'logv':.50,'z4':1.00},
]
BAL=[('log_v_snapshot','log_v_snapshot'),('nearest_upper_z4_dist_v','nearest_upper_z4_dist_v'),('trend15_v','trend15_v'),('trend60_v','trend60_v'),('trend240_v','trend240_v')]

def args():
 p=argparse.ArgumentParser();p.add_argument('--features',required=True);p.add_argument('--full-pool',required=True);p.add_argument('--context',required=True);p.add_argument('--output',required=True);return p.parse_args()
def read(p):
 d=pd.read_csv(p,compression='infer',float_precision='round_trip')
 for c in ['time','snapshot_time_utc','feature_available_time_utc']:
  if c in d:d[c]=pd.to_datetime(d[c],utc=True)
 return d
def smd(a,b):
 a=np.asarray(a,float);b=np.asarray(b,float);den=np.sqrt((np.var(a)+np.var(b))/2)
 return 0.0 if den<=0 and abs(np.mean(a)-np.mean(b))<1e-15 else (float('inf') if den<=0 else float((np.mean(a)-np.mean(b))/den))
def overlaps(lo,hi,g):
 if not len(g):return False
 return bool(np.any(np.minimum(float(hi),g.zhi.to_numpy(float))>=np.maximum(float(lo),g.zlo.to_numpy(float))))
def tie(eid,s,did):return hashlib.sha256(f'{SEED}|{did}|{eid}|{s}'.encode()).hexdigest()
def main():
 a=args();f=read(a.features);pool=read(a.full_pool);ctx=read(a.context)
 f['log_v_snapshot']=np.log(f.v_snapshot.astype(float));ctx['log_v_snapshot']=np.log(ctx.v_snapshot.astype(float))
 ctx=ctx.sort_values(['session_date_ny','minute_of_session','time']).drop_duplicates(['session_date_ny','minute_of_session'],keep='last')
 sessions=sorted(ctx.session_date_ny.astype(str).unique());si={s:i for i,s in enumerate(sessions)}
 by_min={int(m):g for m,g in ctx.groupby('minute_of_session',sort=False)}; pool_by={pd.Timestamp(t):g for t,g in pool.groupby('time',sort=False)}
 starts=f.sort_values(['display_episode_id','snapshot_time_utc']).groupby('display_episode_id',sort=False).first().reset_index()
 paths={str(k):g.sort_values('snapshot_time_utc') for k,g in f.groupby('display_episode_id',sort=False)}
 stats={c:(float(ctx[c].mean()),float(ctx[c].std(ddof=0)) or 1.0) for c in MATCH}
 reports=[]
 for des in DESIGNS:
  selected_counts=[];matches=[];path_lengths=[]
  for _,d0 in starts.iterrows():
   eid=str(d0.display_episode_id);ds=str(d0.session_date_ny);di=si[ds];minute=int(d0.minute_of_session);base=by_min.get(minute)
   cand=[]
   if base is not None:
    for _,r in base.iterrows():
     s=str(r.session_date_ny)
     if s==ds or abs(si[s]-di)<10:continue
     if des['weekday_exact'] and str(r.weekday_ny)!=str(d0.weekday_ny):continue
     if des['bucket_exact'] and str(r.upper_z4_count_bucket)!=str(d0.upper_z4_count_bucket):continue
     if abs(float(r.log_v_snapshot)-float(d0.log_v_snapshot))>des['logv']:continue
     if abs(float(r.nearest_upper_z4_dist_v)-float(d0.nearest_upper_z4_dist_v))>des['z4']:continue
     dist=0.0
     for c in MATCH:
      mu,sd=stats[c];dist+=((float(r[c])-float(d0[c]))/sd)**2
     if not des['bucket_exact'] and str(r.upper_z4_count_bucket)!=str(d0.upper_z4_count_bucket):dist+=.25
     if not des['weekday_exact'] and str(r.weekday_ny)!=str(d0.weekday_ny):dist+=.10
     cand.append((dist,tie(eid,s,des['id']),s,r))
   cand.sort(key=lambda z:(z[0],z[1]));sel=0
   donor=paths[eid]
   for md,_,rs,r0 in cand:
    if sel>=5:break
    temp=[]
    for _,dr in donor.iterrows():
     off=int(round((pd.Timestamp(dr.snapshot_time_utc)-pd.Timestamp(d0.snapshot_time_utc)).total_seconds()/300.0));target=minute+off*5
     rrctx=ctx[(ctx.session_date_ny.astype(str)==rs)&(ctx.minute_of_session.astype(int)==target)]
     if not len(rrctx):break
     rr=rrctx.iloc[-1];rv=float(rr.v_snapshot);center=float(rr.close)-float(dr.distance_v)*rv
     lo=center-float((float(dr.center)-float(dr.zlo))/float(dr.v_snapshot))*rv;hi=center+float((float(dr.zhi)-float(dr.center))/float(dr.v_snapshot))*rv
     pg=pool_by.get(pd.Timestamp(rr.time),pd.DataFrame())
     if len(pg) and (overlaps(lo,hi,pg) or bool(np.any(np.abs(pg.center.to_numpy(float)-center)<=.20*rv))):break
     temp.append((rr,dr,center,lo,hi))
    if not temp:continue
    sel+=1;path_lengths.append(len(temp));rr=temp[0][0]
    matches.append({'donor_episode_id':eid,'donor_session':ds,'recipient_session':rs,'match_distance':md,
      'donor_log_v_snapshot':float(d0.log_v_snapshot),'recipient_log_v_snapshot':float(rr.log_v_snapshot),
      'donor_nearest_upper_z4_dist_v':float(d0.nearest_upper_z4_dist_v),'recipient_nearest_upper_z4_dist_v':float(rr.nearest_upper_z4_dist_v),
      'donor_trend15_v':float(d0.trend15_v),'recipient_trend15_v':float(rr.trend15_v),
      'donor_trend60_v':float(d0.trend60_v),'recipient_trend60_v':float(rr.trend60_v),
      'donor_trend240_v':float(d0.trend240_v),'recipient_trend240_v':float(rr.trend240_v)})
   selected_counts.append(sel)
  sc=np.asarray(selected_counts,int);m=pd.DataFrame(matches);balance={}
  if len(m):
   for c in MATCH:
    dc='donor_'+c;rc='recipient_'+c;balance[c]=smd(m[dc],m[rc])
  frac2=float((sc>=2).mean());frac5=float((sc>=5).mean());maxs=max([abs(x) for x in balance.values()],default=float('inf'))
  feasible=bool(frac2>=.80 and maxs<=.10)
  reports.append({'design':des,'donor_episodes':int(len(sc)),'controls':int(sc.sum()),'donors_ge2':int((sc>=2).sum()),'fraction_ge2':frac2,'donors_with_5':int((sc>=5).sum()),'fraction_with_5':frac5,'median_controls':float(np.median(sc)),'median_retained_path_snapshots':float(np.median(path_lengths)) if path_lengths else None,'balance_smd':balance,'max_abs_smd':maxs,'preoutcome_feasibility_pass':feasible})
  print(json.dumps(reports[-1],sort_keys=True))
 chosen=next((r['design']['id'] for r in reports if r['preoutcome_feasibility_pass']),None)
 out={'status':'V2_R3_MATCHING_LADDER_OUTCOME_BLIND_COMPLETE','future_price_outcomes_used':False,'selection_rule':'first frozen ladder design with fraction donors >=2 controls >=0.80 and max absolute numeric context SMD <=0.10','chosen_design':chosen,'designs':reports}
 Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
