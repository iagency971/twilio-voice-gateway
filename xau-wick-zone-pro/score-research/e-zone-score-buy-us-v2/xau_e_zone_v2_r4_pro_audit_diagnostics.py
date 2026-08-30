#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np, pandas as pd
import xau_e_zone_v2_r4_matching_ladder as r4

DESIGN = r4.DESIGNS[0]
Q = [0.0,.1,.25,.5,.75,.9,1.0]

def args():
 p=argparse.ArgumentParser();p.add_argument('--features',required=True);p.add_argument('--full-pool',required=True);p.add_argument('--context',required=True);p.add_argument('--output',required=True);return p.parse_args()

def wmean(x,w):
 x=np.asarray(x,float);w=np.asarray(w,float);return float(np.sum(x*w)/np.sum(w))

def wvar(x,w):
 m=wmean(x,w);return float(np.sum(w*(np.asarray(x,float)-m)**2)/np.sum(w))

def wsmd(a,b,w):
 den=np.sqrt((wvar(a,w)+wvar(b,w))/2);d=wmean(a,w)-wmean(b,w);return 0.0 if den<=0 and abs(d)<1e-15 else (float('inf') if den<=0 else float(d/den))

def weighted_cat(a,b,w):
 cats=sorted(set(map(str,a))|set(map(str,b)));pa={};pb={}
 sw=float(np.sum(w))
 for c in cats:
  pa[c]=float(np.sum(w[np.asarray(a,dtype=str)==c])/sw);pb[c]=float(np.sum(w[np.asarray(b,dtype=str)==c])/sw)
 dif={c:pa[c]-pb[c] for c in cats}
 return {'donor_proportions':pa,'recipient_proportions':pb,'differences':dif,'max_abs_proportion_difference':max(map(abs,dif.values()),default=0.0),'total_variation_distance':0.5*sum(abs(x) for x in dif.values())}

def weighted_ks(a,b,w):
 a=np.asarray(a,float);b=np.asarray(b,float);w=np.asarray(w,float);grid=np.unique(np.r_[a,b]);sw=float(w.sum())
 ca=np.array([w[a<=x].sum()/sw for x in grid]);cb=np.array([w[b<=x].sum()/sw for x in grid]);return float(np.max(np.abs(ca-cb)))

def summary(x):
 x=np.asarray(x,float);return {'n':int(len(x)),'quantiles':{str(q):float(np.quantile(x,q)) for q in Q}}

def main():
 a=args();f=r4.read(a.features);pool=r4.read(a.full_pool);ctx=r4.read(a.context)
 forbidden={c for c in list(f)+list(pool)+list(ctx) if any(x in c.lower() for x in ['w5','w15','w60','nrb','mfe','mae','outcome','reaction_label','win','loss','target_hit','stop_hit'])}
 if forbidden:raise RuntimeError(f'FORBIDDEN_OUTCOME_COLUMNS {sorted(forbidden)}')
 f['log_v_snapshot']=np.log(f.v_snapshot.astype(float));ctx['log_v_snapshot']=np.log(ctx.v_snapshot.astype(float))
 ctx=ctx.sort_values(['session_date_ny','minute_of_session','time']).drop_duplicates(['session_date_ny','minute_of_session'],keep='last').reset_index(drop=True)
 sessions=sorted(ctx.session_date_ny.astype(str).unique());si={s:i for i,s in enumerate(sessions)};ctx['_s']=ctx.session_date_ny.astype(str);ctx['_i']=ctx['_s'].map(si).astype(int)
 stats={}
 for c in r4.MATCH:
  x=ctx[c].to_numpy(float);mu=float(x.mean());sd=float(x.std(ddof=0)) or 1.0;stats[c]=(mu,sd);ctx['_z_'+c]=(x-mu)/sd
 by={}
 for minute,g in ctx.groupby('minute_of_session',sort=False):
  g=g.reset_index(drop=True);by[int(minute)]={'g':g,'s':g._s.to_numpy(object),'i':g._i.to_numpy(int),'wd':g.weekday_ny.astype(str).to_numpy(object),'bu':g.upper_z4_count_bucket.astype(str).to_numpy(object),'lv':g.log_v_snapshot.to_numpy(float),'z4':g.nearest_upper_z4_dist_v.to_numpy(float),'z':np.column_stack([g['_z_'+c].to_numpy(float) for c in r4.MATCH])}
 ck={(str(x.session_date_ny),int(x.minute_of_session)):x for _,x in ctx.iterrows()};pb={pd.Timestamp(t):(g.zlo.to_numpy(float),g.zhi.to_numpy(float),g.center.to_numpy(float)) for t,g in pool.groupby('time',sort=False)}
 starts=f.sort_values(['display_episode_id','snapshot_time_utc']).groupby('display_episode_id',sort=False).first().reset_index()
 paths={}
 for eid,g in f.groupby('display_episode_id',sort=False):
  g=g.sort_values('snapshot_time_utc');t0=pd.Timestamp(g.snapshot_time_utc.iloc[0]);paths[str(eid)]=[(int(round((pd.Timestamp(x.snapshot_time_utc)-t0).total_seconds()/300)),float(x.distance_v),float(x.center),float(x.zlo),float(x.zhi),float(x.v_snapshot)) for _,x in g.iterrows()]
 rows=[];don=[]
 for _,d in starts.iterrows():
  eid=str(d.display_episode_id);ds=str(d.session_date_ny);minute=int(d.minute_of_session);b=by.get(minute);selected=[]
  if b is not None:
   mask=(np.abs(b['i']-si[ds])>=r4.MIN_SESSION_GAP)&(b['s']!=ds)&(np.abs(b['lv']-float(d.log_v_snapshot))<=DESIGN['logv'])&(np.abs(b['z4']-float(d.nearest_upper_z4_dist_v))<=DESIGN['z4'])
   idx=np.flatnonzero(mask)
   if len(idx):
    dz=np.asarray([(float(d[c])-stats[c][0])/stats[c][1] for c in r4.MATCH]);dist=np.sum((b['z'][idx]-dz)**2,axis=1)+(b['bu'][idx]!=str(d.upper_z4_count_bucket))*r4.BUCKET_MISMATCH_PENALTY+(b['wd'][idx]!=str(d.weekday_ny))*r4.WEEKDAY_MISMATCH_PENALTY
    order=r4.exact_tie_order(dist,b['s'][idx],eid,DESIGN['id'])
    for q in order:
     if len(selected)>=r4.MAX_CONTROLS:break
     j=int(idx[int(q)]);rs=str(b['s'][j]);ret=0;first=None
     for off,dv,c0,l0,h0,v0 in paths[eid]:
      rr=ck.get((rs,minute+off*5))
      if rr is None:break
      rv=float(rr.v_snapshot);c=float(rr.close)-dv*rv;lo=c-((c0-l0)/v0)*rv;hi=c+((h0-c0)/v0)*rv;pg=pb.get(pd.Timestamp(rr.time))
      if pg is not None:
       plo,phi,pc=pg
       if np.any(np.minimum(hi,phi)>=np.maximum(lo,plo)) or np.any(np.abs(pc-c)<=.20*rv):break
      if first is None:first=rr
      ret+=1
     if ret:selected.append((rs,first,ret,float(dist[int(q)])))
  n=len(selected);dl=len(paths[eid]);don.append({'eid':eid,'slot':int(d.display_slot_rank),'family':str(d.current_family),'controls':n,'donor_path':dl,'two_full':sum(x[2]>=dl for x in selected)>=2,'two_half':sum(x[2]>=max(1,int(np.ceil(dl/2))) for x in selected)>=2,'two_min2':sum(x[2]>=min(2,dl) for x in selected)>=2})
  for rs,rr,ret,md in selected:
   z={c:float(d[c]) for c in r4.MATCH};z.update({'eid':eid,'slot':int(d.display_slot_rank),'family':str(d.current_family),'n_controls':n,'weight':1.0/n,'donor_weekday':str(d.weekday_ny),'recipient_weekday':str(rr.weekday_ny),'donor_bucket':str(d.upper_z4_count_bucket),'recipient_bucket':str(rr.upper_z4_count_bucket),'donor_path':dl,'retained_path':ret,'retention_ratio':ret/dl,'match_distance':md,'delta_logv':abs(float(rr.log_v_snapshot)-float(d.log_v_snapshot)),'delta_z4':abs(float(rr.nearest_upper_z4_dist_v)-float(d.nearest_upper_z4_dist_v))})
   for c in r4.MATCH:z['recipient_'+c]=float(rr[c])
   rows.append(z)
 m=pd.DataFrame(rows);d=pd.DataFrame(don);eligible=d[d.controls>=2];me=m[m.eid.isin(set(eligible.eid))].copy();w=me.weight.to_numpy(float)
 numeric={}
 for c in r4.MATCH:numeric[c]={'donor_equal_smd':wsmd(me[c],me['recipient_'+c],w),'donor_equal_weighted_ks':weighted_ks(me[c],me['recipient_'+c],w)}
 cats={'weekday':weighted_cat(me.donor_weekday,me.recipient_weekday,w),'upper_z4_count_bucket':weighted_cat(me.donor_bucket,me.recipient_bucket,w)}
 def group(col):
  out={}
  for k,g in d.groupby(col,sort=True):out[str(k)]={'donors':int(len(g)),'donors_ge2':int((g.controls>=2).sum()),'fraction_ge2':float((g.controls>=2).mean()),'median_controls':float(g.controls.median()),'fraction_two_full_paths':float(g.two_full.mean()),'fraction_two_half_paths':float(g.two_half.mean()),'fraction_two_min2_paths':float(g.two_min2.mean())}
  return out
 out={'status':'V2_R4_PRO_AUDIT_DISTRIBUTIONAL_DIAGNOSTIC_COMPLETE','future_price_outcomes_used':False,'design':{**DESIGN,'weekday_mismatch_penalty':r4.WEEKDAY_MISMATCH_PENALTY,'bucket_mismatch_penalty':r4.BUCKET_MISMATCH_PENALTY,'min_session_gap':r4.MIN_SESSION_GAP,'max_controls':r4.MAX_CONTROLS},'overall':{'donors':int(len(d)),'controls':int(len(m)),'donors_ge2':int(len(eligible)),'fraction_ge2':float(len(eligible)/len(d)),'donor_path_length':summary(d.donor_path),'retained_path_length':summary(m.retained_path),'retention_ratio':summary(m.retention_ratio),'fraction_selected_controls_full_path':float((m.retained_path>=m.donor_path).mean()),'fraction_eligible_donors_two_full_paths':float(eligible.two_full.mean()),'fraction_eligible_donors_two_half_paths':float(eligible.two_half.mean()),'fraction_eligible_donors_two_min2_paths':float(eligible.two_min2.mean())},'estimand_weighted_numeric_balance':numeric,'estimand_weighted_categorical_balance':cats,'coverage_by_slot':group('slot'),'coverage_by_family':group('family'),'selected_match_distance':summary(m.match_distance),'selected_abs_delta_logv':summary(m.delta_logv),'selected_abs_delta_z4':summary(m.delta_z4)}
 Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
