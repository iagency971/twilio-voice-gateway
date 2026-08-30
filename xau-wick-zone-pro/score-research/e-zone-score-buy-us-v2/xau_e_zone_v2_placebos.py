#!/usr/bin/env python3
from __future__ import annotations

import argparse, gzip, hashlib, json
from pathlib import Path

import numpy as np
import pandas as pd

SEED_TEXT='E_ZONE_SCORE_BUY_US_V2_20260829'
MATCH_VARS=['trend15_v','trend60_v','trend240_v','nearest_upper_z4_dist_v','log_v_snapshot']


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument('--features',required=True)
    p.add_argument('--full-pool',required=True)
    p.add_argument('--context',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--matching-table',required=True)
    p.add_argument('--manifest',required=True)
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


def tie_hash(donor,recipient):
    return hashlib.sha256(f'{SEED_TEXT}|{donor}|{recipient}'.encode()).hexdigest()


def placebo_id(donor,recipient,rank):
    return 'PLV2:'+hashlib.sha256(f'{donor}|{recipient}|{rank}|{SEED_TEXT}'.encode()).hexdigest()[:24]


def overlaps(zlo,zhi,g):
    if not len(g):return False
    lo=g.zlo.to_numpy(float); hi=g.zhi.to_numpy(float)
    return bool(np.any(np.minimum(float(zhi),hi)>=np.maximum(float(zlo),lo)))


def main():
    a=parse_args(); f=read(a.features); pool=read(a.full_pool); ctx=read(a.context)
    if not len(f) or not len(ctx):raise RuntimeError('empty features/context')
    f['log_v_snapshot']=np.log(f.v_snapshot.astype(float))
    ctx['log_v_snapshot']=np.log(ctx.v_snapshot.astype(float))
    ctx=ctx.sort_values(['session_date_ny','minute_of_session','time']).drop_duplicates(['session_date_ny','minute_of_session'],keep='last')
    sessions=sorted(ctx.session_date_ny.astype(str).unique()); sess_idx={s:i for i,s in enumerate(sessions)}
    ctx_key={(str(r.session_date_ny),int(r.minute_of_session)):r for _,r in ctx.iterrows()}
    pool_by={pd.Timestamp(t):g for t,g in pool.groupby('time',sort=False)}
    # Require that the original E display slot exists in the recipient context.
    slot_presence=set((str(r.session_date_ny),int(r.minute_of_session),int(r.display_slot_rank)) for _,r in f.iterrows())
    # Outcome-free normalization for nearest-neighbour distance.
    stats={}
    for c in MATCH_VARS:
        x=pd.to_numeric(ctx[c],errors='coerce').to_numpy(float); mu=float(np.nanmean(x)); sd=float(np.nanstd(x,ddof=0)); stats[c]=(mu,sd if np.isfinite(sd) and sd>0 else 1.0)

    start_rows=f.sort_values(['display_episode_id','snapshot_time_utc']).groupby('display_episode_id',sort=False).first().reset_index()
    paths={eid:g.sort_values('snapshot_time_utc').copy() for eid,g in f.groupby('display_episode_id',sort=False)}
    placebo_rows=[]; match_rows=[]; donor_summary=[]

    for _,d0 in start_rows.iterrows():
        eid=str(d0.display_episode_id); donor_session=str(d0.session_date_ny); dsi=sess_idx[donor_session]; minute=int(d0.minute_of_session); slot=int(d0.display_slot_rank)
        wd=str(d0.weekday_ny); ub=str(d0.upper_z4_count_bucket); lv=float(d0.log_v_snapshot); zd=float(d0.nearest_upper_z4_dist_v)
        candidates=[]
        for s in sessions:
            if s==donor_session or abs(sess_idx[s]-dsi)<10:continue
            r=ctx_key.get((s,minute));
            if r is None:continue
            if str(r.weekday_ny)!=wd or str(r.upper_z4_count_bucket)!=ub:continue
            if (s,minute,slot) not in slot_presence:continue
            if abs(float(r.log_v_snapshot)-lv)>.20:continue
            if abs(float(r.nearest_upper_z4_dist_v)-zd)>.25:continue
            dist=0.0
            for c in MATCH_VARS:
                mu,sd=stats[c]; dist+=((float(r[c])-float(d0[c]))/sd)**2
            candidates.append((float(dist),tie_hash(eid,s),s,r))
        candidates.sort(key=lambda x:(x[0],x[1]))
        selected=0; attempts=0
        donor_path=paths[eid]
        for md,_,recipient_session,r0 in candidates:
            if selected>=5:break
            attempts+=1; temp=[]; conflict_reason=None
            start_minute=int(r0.minute_of_session)
            donor_start_minute=int(d0.minute_of_session)
            for _,dr in donor_path.iterrows():
                off=int(round((pd.Timestamp(dr.snapshot_time_utc)-pd.Timestamp(d0.snapshot_time_utc)).total_seconds()/300.0))
                target_min=start_minute+off*5
                rr=ctx_key.get((recipient_session,target_min))
                if rr is None:
                    conflict_reason='RECIPIENT_SNAPSHOT_UNAVAILABLE'; break
                rv=float(rr.v_snapshot); center=float(rr.close)-float(dr.distance_v)*rv
                zlo=center-float((float(dr.center)-float(dr.zlo))/float(dr.v_snapshot))*rv
                zhi=center+float((float(dr.zhi)-float(dr.center))/float(dr.v_snapshot))*rv
                pg=pool_by.get(pd.Timestamp(rr.time),pd.DataFrame())
                if len(pg) and (overlaps(zlo,zhi,pg) or bool(np.any(np.abs(pg.center.to_numpy(float)-center)<=.20*rv))):
                    conflict_reason='REAL_POOL_NEUTRALITY_CONFLICT'; break
                temp.append({'recipient_ctx':rr,'donor_row':dr,'center':center,'zlo':zlo,'zhi':zhi,'off':off})
            if not temp:continue
            selected+=1; pid=placebo_id(eid,recipient_session,selected)
            # Truncation at first conflict is allowed; snapshots before it remain a valid placebo episode.
            for x in temp:
                rr=x['recipient_ctx']; dr=x['donor_row']
                placebo_rows.append({
                    'placebo_id':pid,'donor_episode_id':eid,'control_rank':selected,'donor_session_date_ny':donor_session,
                    'recipient_session_date_ny':recipient_session,'snapshot_time_utc':pd.Timestamp(rr.time),'feature_available_time_utc':pd.Timestamp(rr.time)+pd.Timedelta(minutes=1),
                    'family':str(dr.current_family),'current_family':str(dr.current_family),'display_slot_rank':slot,
                    'center':x['center'],'zlo':x['zlo'],'zhi':x['zhi'],'v_snapshot':float(rr.v_snapshot),'distance_v':float(dr.distance_v),
                    'zone_width_v':float((x['zhi']-x['zlo'])/float(rr.v_snapshot)),'donor_offset_c5':int(x['off']),
                })
            match_rows.append({
                'donor_episode_id':eid,'placebo_id':pid,'control_rank':selected,'donor_session_date_ny':donor_session,'recipient_session_date_ny':recipient_session,
                'match_distance':md,'donor_zone_width_v':float(d0.zone_width_v),'recipient_transplanted_zone_width_v':float((temp[0]['zhi']-temp[0]['zlo'])/float(temp[0]['recipient_ctx'].v_snapshot)),
                'donor_distance_v':float(d0.distance_v),'recipient_distance_v':float(d0.distance_v),
                'donor_log_v_snapshot':lv,'recipient_log_v_snapshot':float(r0.log_v_snapshot),
                'donor_minute_of_session':minute,'recipient_minute_of_session':int(r0.minute_of_session),
                'donor_nearest_upper_z4_dist_v':zd,'recipient_nearest_upper_z4_dist_v':float(r0.nearest_upper_z4_dist_v),
                'donor_trend15_v':float(d0.trend15_v),'recipient_trend15_v':float(r0.trend15_v),
                'donor_trend60_v':float(d0.trend60_v),'recipient_trend60_v':float(r0.trend60_v),
                'donor_trend240_v':float(d0.trend240_v),'recipient_trend240_v':float(r0.trend240_v),
                'path_snapshots':len(temp),'truncation_reason':conflict_reason or '',
            })
        donor_summary.append((eid,selected,len(candidates),attempts))

    p=pd.DataFrame(placebo_rows); m=pd.DataFrame(match_rows)
    if not len(p):raise RuntimeError('no valid placebos')
    write_gz(p,a.output); write_gz(m,a.matching_table)
    sm=pd.DataFrame(donor_summary,columns=['episode','selected','candidate_pool','attempted'])
    manifest={
        'status':'E_ZONE_V2_PLACEBO_GENERATION_OUTCOME_BLIND_PASS','future_price_outcomes_used':False,
        'donor_episodes':int(len(start_rows)),'donors_with_5_controls':int((sm.selected>=5).sum()),'donors_with_at_least_2_controls':int((sm.selected>=2).sum()),
        'fraction_donors_with_5_controls':float((sm.selected>=5).mean()),'fraction_donors_with_at_least_2_controls':float((sm.selected>=2).mean()),
        'placebo_episodes':int(p.placebo_id.nunique()),'placebo_snapshot_rows':int(len(p)),'matching_rows':int(len(m)),
        'matching_normalization':{c:{'mean':stats[c][0],'sd_ddof0':stats[c][1]} for c in MATCH_VARS},
        'selection_rule':'standardized Euclidean distance on frozen matching variables; SHA256 lexical tie break; first five valid neutral paths',
        'neutrality_rule':'truncate before first snapshot overlapping/within 0.20v of any causal real E/Z4 full-pool interval',
    }
    Path(a.manifest).write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n');print(json.dumps(manifest,indent=2,sort_keys=True))

if __name__=='__main__':main()
