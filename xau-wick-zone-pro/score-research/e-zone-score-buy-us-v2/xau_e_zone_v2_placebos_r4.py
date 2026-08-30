#!/usr/bin/env python3
from __future__ import annotations

"""Exact outcome-blind R4_D5 neutral-control generator.

This materializes the design authorized by E_ZONE_SCORE_BUY_US_V2_R4_PRO_GATE.json.
It intentionally imports the frozen R4 ladder constants and uses only D5.
D6-D8 are never evaluated here.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import xau_e_zone_v2_r4_matching_ladder as r4

DESIGN = r4.DESIGNS[0]
SEED = r4.SEED
FORBIDDEN = ('w5','w15','w60','nrb','mfe','mae','outcome','reaction_label','target_hit','stop_hit')


def args():
    p=argparse.ArgumentParser()
    for x in ['features','full-pool','context','output','matching-table','manifest']:
        p.add_argument('--'+x,required=True)
    return p.parse_args()


def read(path):
    d=pd.read_csv(path,compression='infer',float_precision='round_trip')
    for c in ['time','snapshot_time_utc','feature_available_time_utc']:
        if c in d.columns:d[c]=pd.to_datetime(d[c],utc=True)
    return d


def write_gz(d,path):
    raw=d.to_csv(index=False,lineterminator='\n',float_format='%.17g',na_rep='').encode()
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with open(path,'wb') as fh:
        with gzip.GzipFile(fileobj=fh,mode='wb',mtime=0,filename='') as gz:gz.write(raw)


def placebo_id(eid,recipient,rank):
    return 'PLV2R4:'+hashlib.sha256(f'{SEED}|{DESIGN["id"]}|{eid}|{recipient}|{rank}'.encode()).hexdigest()[:24]


def selection_hash(m):
    cols=['donor_episode_id','control_rank','recipient_session_date_ny','match_distance','path_snapshots']
    x=m[cols].sort_values(['donor_episode_id','control_rank']).copy()
    rows=[]
    for _,z in x.iterrows():
        rows.append('|'.join([str(z.donor_episode_id),str(int(z.control_rank)),str(z.recipient_session_date_ny),format(float(z.match_distance),'.17g'),str(int(z.path_snapshots))]))
    return hashlib.sha256(('\n'.join(rows)+'\n').encode()).hexdigest()


def main():
    a=args();f=read(a.features);pool=read(a.full_pool);ctx=read(a.context)
    bad={c for c in list(f.columns)+list(pool.columns)+list(ctx.columns) if any(t in c.lower() for t in FORBIDDEN)}
    if bad:raise RuntimeError(f'R4_FORBIDDEN_OUTCOME_COLUMNS_PRESENT {sorted(bad)}')
    if not len(f) or not len(ctx):raise RuntimeError('R4_EMPTY_FEATURES_OR_CONTEXT')

    f['log_v_snapshot']=np.log(f.v_snapshot.astype(float));ctx['log_v_snapshot']=np.log(ctx.v_snapshot.astype(float))
    ctx=ctx.sort_values(['session_date_ny','minute_of_session','time']).drop_duplicates(['session_date_ny','minute_of_session'],keep='last').reset_index(drop=True)
    sessions=sorted(ctx.session_date_ny.astype(str).unique());si={s:i for i,s in enumerate(sessions)}
    ctx['_s']=ctx.session_date_ny.astype(str);ctx['_i']=ctx['_s'].map(si).astype(int)
    stats={}
    for c in r4.MATCH:
        x=ctx[c].to_numpy(float);mu=float(x.mean());sd=float(x.std(ddof=0));sd=sd if np.isfinite(sd) and sd>0 else 1.0
        stats[c]=(mu,sd);ctx['_z_'+c]=(x-mu)/sd
    by={}
    for minute,g in ctx.groupby('minute_of_session',sort=False):
        g=g.reset_index(drop=True)
        by[int(minute)]={'g':g,'s':g._s.to_numpy(object),'i':g._i.to_numpy(int),'wd':g.weekday_ny.astype(str).to_numpy(object),'bu':g.upper_z4_count_bucket.astype(str).to_numpy(object),'lv':g.log_v_snapshot.to_numpy(float),'z4':g.nearest_upper_z4_dist_v.to_numpy(float),'z':np.column_stack([g['_z_'+c].to_numpy(float) for c in r4.MATCH])}
    ck={(str(x.session_date_ny),int(x.minute_of_session)):x for _,x in ctx.iterrows()}
    pb={pd.Timestamp(t):(g.zlo.to_numpy(float),g.zhi.to_numpy(float),g.center.to_numpy(float)) for t,g in pool.groupby('time',sort=False)}
    starts=f.sort_values(['display_episode_id','snapshot_time_utc']).groupby('display_episode_id',sort=False).first().reset_index()
    paths={}
    for eid,g in f.groupby('display_episode_id',sort=False):
        g=g.sort_values('snapshot_time_utc');t0=pd.Timestamp(g.snapshot_time_utc.iloc[0])
        paths[str(eid)]=[(int(round((pd.Timestamp(x.snapshot_time_utc)-t0).total_seconds()/300.0)),x) for _,x in g.iterrows()]

    pr=[];mr=[];summary=[]
    for _,d in starts.iterrows():
        eid=str(d.display_episode_id);ds=str(d.session_date_ny);minute=int(d.minute_of_session);slot=int(d.display_slot_rank);base=by.get(minute);selected=0;attempts=0;candidate_n=0
        if base is not None:
            mask=(np.abs(base['i']-si[ds])>=r4.MIN_SESSION_GAP)&(base['s']!=ds)&(np.abs(base['lv']-float(d.log_v_snapshot))<=DESIGN['logv'])&(np.abs(base['z4']-float(d.nearest_upper_z4_dist_v))<=DESIGN['z4'])
            idx=np.flatnonzero(mask);candidate_n=int(len(idx))
            if len(idx):
                dz=np.asarray([(float(d[c])-stats[c][0])/stats[c][1] for c in r4.MATCH])
                dist=np.sum((base['z'][idx]-dz)**2,axis=1)+(base['bu'][idx]!=str(d.upper_z4_count_bucket))*r4.BUCKET_MISMATCH_PENALTY+(base['wd'][idx]!=str(d.weekday_ny))*r4.WEEKDAY_MISMATCH_PENALTY
                order=r4.exact_tie_order(dist,base['s'][idx],eid,DESIGN['id'])
                for q in order:
                    if selected>=r4.MAX_CONTROLS:break
                    attempts+=1;pos=int(q);j=int(idx[pos]);rs=str(base['s'][j]);r0=base['g'].iloc[j];temp=[];reason=''
                    for off,dr in paths[eid]:
                        rr=ck.get((rs,minute+off*5))
                        if rr is None:reason='RECIPIENT_SNAPSHOT_UNAVAILABLE';break
                        rv=float(rr.v_snapshot);center=float(rr.close)-float(dr.distance_v)*rv
                        lo=center-((float(dr.center)-float(dr.zlo))/float(dr.v_snapshot))*rv
                        hi=center+((float(dr.zhi)-float(dr.center))/float(dr.v_snapshot))*rv
                        pg=pb.get(pd.Timestamp(rr.time))
                        if pg is not None:
                            plo,phi,pc=pg
                            if np.any(np.minimum(hi,phi)>=np.maximum(lo,plo)) or np.any(np.abs(pc-center)<=.20*rv):reason='REAL_POOL_NEUTRALITY_CONFLICT';break
                        temp.append((off,dr,rr,center,lo,hi))
                    if not temp:continue
                    selected+=1;pid=placebo_id(eid,rs,selected)
                    for off,dr,rr,center,lo,hi in temp:
                        pr.append({'placebo_id':pid,'donor_episode_id':eid,'control_rank':selected,'donor_session_date_ny':ds,'recipient_session_date_ny':rs,'snapshot_time_utc':pd.Timestamp(rr.time),'feature_available_time_utc':pd.Timestamp(rr.time)+pd.Timedelta(minutes=1),'family':str(dr.current_family),'current_family':str(dr.current_family),'display_slot_rank':slot,'center':center,'zlo':lo,'zhi':hi,'v_snapshot':float(rr.v_snapshot),'distance_v':float(dr.distance_v),'zone_width_v':float((hi-lo)/float(rr.v_snapshot)),'donor_offset_c5':int(off)})
                    rr0=temp[0][2];dr0=temp[0][1]
                    mr.append({'donor_episode_id':eid,'placebo_id':pid,'control_rank':selected,'donor_session_date_ny':ds,'recipient_session_date_ny':rs,'donor_family':str(d.current_family),'display_slot_rank':slot,'match_distance':float(dist[pos]),'donor_zone_width_v':float(d.zone_width_v),'recipient_transplanted_zone_width_v':float((temp[0][5]-temp[0][4])/float(rr0.v_snapshot)),'donor_distance_v':float(d.distance_v),'recipient_distance_v':float(dr0.distance_v),'donor_log_v_snapshot':float(d.log_v_snapshot),'recipient_log_v_snapshot':float(r0.log_v_snapshot),'donor_minute_of_session':minute,'recipient_minute_of_session':int(r0.minute_of_session),'donor_nearest_upper_z4_dist_v':float(d.nearest_upper_z4_dist_v),'recipient_nearest_upper_z4_dist_v':float(r0.nearest_upper_z4_dist_v),'donor_trend15_v':float(d.trend15_v),'recipient_trend15_v':float(r0.trend15_v),'donor_trend60_v':float(d.trend60_v),'recipient_trend60_v':float(r0.trend60_v),'donor_trend240_v':float(d.trend240_v),'recipient_trend240_v':float(r0.trend240_v),'donor_weekday_ny':str(d.weekday_ny),'recipient_weekday_ny':str(r0.weekday_ny),'donor_upper_z4_count_bucket':str(d.upper_z4_count_bucket),'recipient_upper_z4_count_bucket':str(r0.upper_z4_count_bucket),'donor_session_index':int(si[ds]),'recipient_session_index':int(si[rs]),'session_index_gap':int(abs(si[rs]-si[ds])),'donor_path_snapshots':int(len(paths[eid])),'path_snapshots':int(len(temp)),'truncation_reason':reason})
        summary.append({'episode':eid,'slot':slot,'family':str(d.current_family),'selected':selected,'candidate_pool':candidate_n,'attempted':attempts})

    p=pd.DataFrame(pr);m=pd.DataFrame(mr);s=pd.DataFrame(summary)
    if not len(p) or not len(m):raise RuntimeError('R4_NO_VALID_PLACEBOS')
    write_gz(p,a.output);write_gz(m,a.matching_table)
    slot={str(int(k)):{'donors':int(len(g)),'donors_ge2':int((g.selected>=2).sum()),'fraction_ge2':float((g.selected>=2).mean())} for k,g in s.groupby('slot',sort=True)}
    fam={str(k):{'donors':int(len(g)),'donors_ge2':int((g.selected>=2).sum()),'fraction_ge2':float((g.selected>=2).mean())} for k,g in s.groupby('family',sort=True)}
    out={'status':'E_ZONE_V2_R4_PLACEBO_GENERATION_OUTCOME_BLIND_PASS','future_price_outcomes_used':False,'design':{**DESIGN,'weekday_exact':False,'bucket_exact':False,'weekday_mismatch_penalty':r4.WEEKDAY_MISMATCH_PENALTY,'bucket_mismatch_penalty':r4.BUCKET_MISMATCH_PENALTY,'min_session_gap':r4.MIN_SESSION_GAP,'max_controls':r4.MAX_CONTROLS},'donor_episodes':int(len(s)),'donors_with_at_least_2_controls':int((s.selected>=2).sum()),'fraction_donors_with_at_least_2_controls':float((s.selected>=2).mean()),'donors_with_5_controls':int((s.selected>=5).sum()),'fraction_donors_with_5_controls':float((s.selected>=5).mean()),'placebo_episodes':int(m.placebo_id.nunique()),'placebo_snapshot_rows':int(len(p)),'matching_rows':int(len(m)),'coverage_by_slot':slot,'coverage_by_family':fam,'selection_sha256':selection_hash(m),'matching_normalization':{c:{'mean':stats[c][0],'sd_ddof0':stats[c][1]} for c in r4.MATCH},'selection_rule':'R4_D5 standardized Euclidean distance plus frozen weekday/bucket mismatch penalties; exact SHA256 tie ordering; first five valid neutral paths','neutrality_rule':'truncate before first snapshot overlapping/within 0.20v of any causal real E/Z4 full-pool interval','D6_D7_D8_used':False}
    Path(a.manifest).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,indent=2,sort_keys=True))


if __name__=='__main__':main()
