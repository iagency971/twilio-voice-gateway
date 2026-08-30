#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import xau_e_zone_v2_r4_matching_ladder as r4

DESIGN=r4.DESIGNS[0]


def args():
    p=argparse.ArgumentParser()
    for x in ['features','full-pool','context','matching','canonical-r4-json','output']:p.add_argument('--'+x,required=True)
    return p.parse_args()


def main():
    a=args();f=r4.read(a.features);pool=r4.read(a.full_pool);ctx=r4.read(a.context);got=pd.read_csv(a.matching,compression='infer',float_precision='round_trip');canon=json.load(open(a.canonical_r4_json))
    f['log_v_snapshot']=np.log(f.v_snapshot.astype(float));ctx['log_v_snapshot']=np.log(ctx.v_snapshot.astype(float));ctx=ctx.sort_values(['session_date_ny','minute_of_session','time']).drop_duplicates(['session_date_ny','minute_of_session'],keep='last').reset_index(drop=True)
    sessions=sorted(ctx.session_date_ny.astype(str).unique());si={s:i for i,s in enumerate(sessions)};ctx['_s']=ctx.session_date_ny.astype(str);ctx['_i']=ctx['_s'].map(si).astype(int)
    stats={}
    for c in r4.MATCH:
        x=ctx[c].to_numpy(float);mu=float(x.mean());sd=float(x.std(ddof=0));sd=sd if np.isfinite(sd) and sd>0 else 1.0;stats[c]=(mu,sd);ctx['_z_'+c]=(x-mu)/sd
    by={}
    for minute,g in ctx.groupby('minute_of_session',sort=False):
        g=g.reset_index(drop=True);by[int(minute)]={'g':g,'s':g._s.to_numpy(object),'i':g._i.to_numpy(int),'wd':g.weekday_ny.astype(str).to_numpy(object),'bu':g.upper_z4_count_bucket.astype(str).to_numpy(object),'lv':g.log_v_snapshot.to_numpy(float),'z4':g.nearest_upper_z4_dist_v.to_numpy(float),'z':np.column_stack([g['_z_'+c].to_numpy(float) for c in r4.MATCH])}
    ck={(str(x.session_date_ny),int(x.minute_of_session)):x for _,x in ctx.iterrows()};pb={pd.Timestamp(t):(g.zlo.to_numpy(float),g.zhi.to_numpy(float),g.center.to_numpy(float)) for t,g in pool.groupby('time',sort=False)}
    starts=f.sort_values(['display_episode_id','snapshot_time_utc']).groupby('display_episode_id',sort=False).first().reset_index();paths={}
    for eid,g in f.groupby('display_episode_id',sort=False):
        g=g.sort_values('snapshot_time_utc');t0=pd.Timestamp(g.snapshot_time_utc.iloc[0]);paths[str(eid)]=[(int(round((pd.Timestamp(x.snapshot_time_utc)-t0).total_seconds()/300.0)),float(x.distance_v),float(x.center),float(x.zlo),float(x.zhi),float(x.v_snapshot)) for _,x in g.iterrows()]
    rows=[];counts=[]
    for _,d in starts.iterrows():
        eid=str(d.display_episode_id);ds=str(d.session_date_ny);minute=int(d.minute_of_session);b=by.get(minute);selected=[]
        if b is not None:
            mask=(np.abs(b['i']-si[ds])>=r4.MIN_SESSION_GAP)&(b['s']!=ds)&(np.abs(b['lv']-float(d.log_v_snapshot))<=DESIGN['logv'])&(np.abs(b['z4']-float(d.nearest_upper_z4_dist_v))<=DESIGN['z4']);idx=np.flatnonzero(mask)
            if len(idx):
                dz=np.asarray([(float(d[c])-stats[c][0])/stats[c][1] for c in r4.MATCH]);dist=np.sum((b['z'][idx]-dz)**2,axis=1)+(b['bu'][idx]!=str(d.upper_z4_count_bucket))*r4.BUCKET_MISMATCH_PENALTY+(b['wd'][idx]!=str(d.weekday_ny))*r4.WEEKDAY_MISMATCH_PENALTY;order=r4.exact_tie_order(dist,b['s'][idx],eid,DESIGN['id'])
                for q in order:
                    if len(selected)>=r4.MAX_CONTROLS:break
                    pos=int(q);j=int(idx[pos]);rs=str(b['s'][j]);ret=0
                    for off,dv,c0,l0,h0,v0 in paths[eid]:
                        rr=ck.get((rs,minute+off*5))
                        if rr is None:break
                        rv=float(rr.v_snapshot);c=float(rr.close)-dv*rv;lo=c-((c0-l0)/v0)*rv;hi=c+((h0-c0)/v0)*rv;pg=pb.get(pd.Timestamp(rr.time))
                        if pg is not None:
                            plo,phi,pc=pg
                            if np.any(np.minimum(hi,phi)>=np.maximum(lo,plo)) or np.any(np.abs(pc-c)<=.20*rv):break
                        ret+=1
                    if ret:selected.append((rs,float(dist[pos]),ret))
        counts.append(len(selected))
        for rank,(rs,md,ret) in enumerate(selected,1):rows.append({'donor_episode_id':eid,'control_rank':rank,'recipient_session_date_ny':rs,'match_distance':md,'path_snapshots':ret})
    ref=pd.DataFrame(rows).sort_values(['donor_episode_id','control_rank']).reset_index(drop=True);g=got[['donor_episode_id','control_rank','recipient_session_date_ny','match_distance','path_snapshots']].copy().sort_values(['donor_episode_id','control_rank']).reset_index(drop=True)
    mism={};same_len=len(ref)==len(g)
    if not same_len:mism['row_count']=[int(len(ref)),int(len(g))]
    else:
        for c in ['donor_episode_id','recipient_session_date_ny']:
            n=int(np.sum(ref[c].astype(str).to_numpy()!=g[c].astype(str).to_numpy()));
            if n:mism[c]=n
        for c in ['control_rank','path_snapshots']:
            n=int(np.sum(ref[c].astype(int).to_numpy()!=g[c].astype(int).to_numpy()));
            if n:mism[c]=n
        n=int(np.sum(ref.match_distance.to_numpy(float)!=g.match_distance.to_numpy(float)))
        if n:mism['match_distance_exact_float64']=n
    sc=np.asarray(counts,int);d0=canon['designs_evaluated'][0]
    aggregates={'donor_episodes':int(len(sc)),'controls':int(sc.sum()),'donors_ge2':int((sc>=2).sum()),'fraction_ge2':float((sc>=2).mean()),'donors_with_5':int((sc>=5).sum()),'fraction_with_5':float((sc>=5).mean())}
    agg_ok=aggregates['donor_episodes']==int(d0['donor_episodes']) and aggregates['controls']==int(d0['controls']) and aggregates['donors_ge2']==int(d0['donors_ge2']) and aggregates['donors_with_5']==int(d0['donors_with_5']) and aggregates['fraction_ge2']==float(d0['fraction_ge2']) and aggregates['fraction_with_5']==float(d0['fraction_with_5'])
    out={'status':'R4_CANONICAL_SELECTION_EXACT_PASS' if not mism and agg_ok else 'R4_CANONICAL_SELECTION_EXACT_FAIL','future_price_outcomes_used':False,'design':'R4_D5_MINIMAL_DENSE','row_level_mismatches':mism,'aggregate_recomputed':aggregates,'aggregate_matches_frozen_r4_json':agg_ok,'checked_fields':['donor_episode_id','control_rank','recipient_session_date_ny','match_distance exact float64','path_snapshots']}
    Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,indent=2,sort_keys=True))
    if out['status'].endswith('FAIL'):raise RuntimeError('R4_CANONICAL_SELECTION_VERIFY_FAIL')


if __name__=='__main__':main()
