#!/usr/bin/env python3
from __future__ import annotations

import argparse, gzip, hashlib, importlib.util, json, sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
V1DIR = HERE.parent / 'e-display-episode-reaction-rank-v1'
ENTRY = HERE.parents[1] / 'entry-research'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod); return mod

prov = load_module('v2_prov', V1DIR / 'xau_ebuy_provenance_instrument_v1.py')
v01 = prov.v01; v02 = prov.v02
E_FAMILIES = {'ESM_BOTH_G120M','EPM_M1_R2_A8H','EWM_G60M','ES_M1_8H_R2_T0.50'}


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument('--files',nargs='+',required=True)
    p.add_argument('--z4-pkl',required=True)
    p.add_argument('--output-features',required=True)
    p.add_argument('--output-display-all',required=True)
    p.add_argument('--output-full-pool',required=True)
    p.add_argument('--output-context',required=True)
    p.add_argument('--manifest',required=True)
    p.add_argument('--target-start',required=True)
    p.add_argument('--target-end',required=True)
    p.add_argument('--reference-v04-csv')
    return p.parse_args()


def write_gz(df,path):
    raw=df.to_csv(index=False,lineterminator='\n',float_format='%.17g',na_rep='').encode()
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with open(path,'wb') as fh:
        with gzip.GzipFile(fileobj=fh,mode='wb',mtime=0,filename='') as gz: gz.write(raw)


def ts(x):
    t=pd.Timestamp(x); return t.tz_localize('UTC') if t.tzinfo is None else t.tz_convert('UTC')


def overlap(a,b): return min(float(a.zhi),float(b.zhi)) >= max(float(a.zlo),float(b.zlo))


def members(x):
    if x is None or pd.isna(x) or str(x)=='': return frozenset()
    return frozenset(z for z in str(x).split(';') if z)


def episode_id(session,seq,family,t,prov_id):
    s=f'{session}|{seq}|{family}|{ts(t).isoformat()}|{prov_id}'
    return 'EZV2:'+hashlib.sha256(s.encode()).hexdigest()[:24]


def candidate_edges(prev,cur):
    edges=[]
    for pi,p in enumerate(prev):
        for ci,c in enumerate(cur):
            if p['family']!=c['family']: continue
            fam=c['family']
            if fam in {'ESM_BOTH_G120M','EPM_M1_R2_A8H','EWM_G60M'}:
                if p['source_provenance_id']==c['source_provenance_id']:
                    edges.append((0,0.0,abs(p['center']-c['center']),p['display_episode_id'],c['source_provenance_id'],pi,ci))
            elif fam=='ES_M1_8H_R2_T0.50':
                a=p['_members']; b=c['_members']; inter=len(a&b)
                if inter:
                    union=len(a|b); jac=inter/union if union else 0.0
                    edges.append((-inter,-jac,abs(p['center']-c['center']),p['display_episode_id'],c['source_provenance_id'],pi,ci))
    return sorted(edges)


def assign_episode_identity(e_df):
    e=e_df.sort_values(['time','display_slot_rank','family','center']).copy()
    out=[]; prev=[]; prev_t=None; prev_session=None; seqs={}
    for t,g in e.groupby('time',sort=True):
        t=ts(t); session=t.tz_convert('America/New_York').date().isoformat()
        cur=[]
        for _,r in g.iterrows():
            cur.append({**r.to_dict(),'time':t,'session_date_ny':session,'_members':members(r.get('source_provenance_members',''))})
        assigned_prev=set(); assigned_cur=set()
        if prev_t is not None and t-prev_t==pd.Timedelta(minutes=5) and session==prev_session:
            for edge in candidate_edges(prev,cur):
                pi,ci=edge[-2],edge[-1]
                if pi in assigned_prev or ci in assigned_cur: continue
                p=prev[pi]; c=cur[ci]
                c['display_episode_id']=p['display_episode_id']; c['display_persistence_c5']=int(p['display_persistence_c5'])+1
                c['is_new_display_episode']=False; c['prior_snapshot_time_utc']=p['time']
                assigned_prev.add(pi); assigned_cur.add(ci)
        for ci,c in enumerate(cur):
            if ci not in assigned_cur:
                seq=seqs.get(session,0)+1; seqs[session]=seq
                c['display_episode_id']=episode_id(session,seq,c['family'],t,c['source_provenance_id'])
                c['display_persistence_c5']=1; c['is_new_display_episode']=True; c['prior_snapshot_time_utc']=pd.NaT
            out.append(c)
        prev=cur; prev_t=t; prev_session=session
    ans=pd.DataFrame(out)
    # Causal stability from up to the three previous contiguous episode transitions.
    st=np.zeros(len(ans),float)
    for _,idx in ans.groupby('display_episode_id',sort=False).groups.items():
        ids=list(idx); ids=sorted(ids,key=lambda i: ans.at[i,'time'])
        drifts=[]
        for j,i in enumerate(ids):
            if j==0: st[i]=0.0; continue
            ip=ids[j-1]
            drift=abs(float(ans.at[i,'center'])-float(ans.at[ip,'center']))/float(ans.at[i,'v_snapshot'])
            drifts.append(float(drift)); st[i]=float(np.exp(-np.median(drifts[max(0,len(drifts)-3):])))
    ans['center_stability_3_c5']=st
    return ans.drop(columns=['_members'],errors='ignore')


def canonical_hash(row):
    d={}
    for k,v in sorted(row.items()):
        if k=='row_sha256': continue
        if pd.isna(v): d[k]=None
        elif isinstance(v,(pd.Timestamp,)): d[k]=ts(v).isoformat()
        elif isinstance(v,(np.integer,int)): d[k]=int(v)
        elif isinstance(v,(np.floating,float)): d[k]=format(float(v),'.17g')
        elif isinstance(v,(np.bool_,bool)): d[k]=int(bool(v))
        else: d[k]=str(v)
    return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def exact_parity(reference_path,got,target_start,target_end):
    ref=pd.read_csv(reference_path,compression='infer',float_precision='round_trip'); ref['time']=pd.to_datetime(ref.time,utc=True)
    ref=ref[(ref.time>=target_start)&(ref.time<target_end)].copy().sort_values(['time','entry_rank']).reset_index(drop=True)
    g=got.copy().sort_values(['time','entry_rank']).reset_index(drop=True)
    cols=['time','entry_rank','family','center','zlo','zhi']
    if len(ref)!=len(g): return {'pass':False,'reason':'row_count','reference_rows':int(len(ref)),'instrumented_rows':int(len(g))}
    bad={}
    for c in cols:
        if c=='time': neq=ref[c].to_numpy()!=g[c].to_numpy()
        elif c in {'entry_rank','family'}: neq=ref[c].astype(str).to_numpy()!=g[c].astype(str).to_numpy()
        else:
            # Exact float64 equality after round-trip CSV parsing.
            neq=ref[c].to_numpy(float)!=g[c].to_numpy(float)
        n=int(np.sum(neq));
        if n: bad[c]=n
    return {'pass':not bad,'reference_rows':int(len(ref)),'instrumented_rows':int(len(g)),'mismatch_counts':bad}


def main():
    a=parse_args(); start=pd.Timestamp(a.target_start); end=pd.Timestamp(a.target_end)
    if start.tzinfo is None:start=start.tz_localize('UTC')
    if end.tzinfo is None:end=end.tz_localize('UTC')
    raw=v01.load_raw(a.files); active=v01.active_m1(raw)
    z4=pd.read_pickle(a.z4_pkl).copy(); z4['time']=pd.to_datetime(z4.time,utc=True)
    forbidden=sorted(v01.FORBIDDEN & set(z4.columns))
    if forbidden: raise RuntimeError(f'forbidden Z4 outcome columns: {forbidden}')

    snaps=v01.make_eval_times(active,z4); all_c5=v02.all_c5_snapshots(active)
    z4_lists=prov.z4_provenance_lists(snaps,z4)
    esm_map=prov.esm_outputs_with_ids(raw,active,all_c5); esm=[esm_map.get(s['time'],[]) for s in snaps]
    epm=prov.epm_lists_with_ids(snaps,prov.epm_base_events_with_ids(raw,active))
    ewm_map=prov.ewm_outputs_with_ids(raw,all_c5); ewm=[ewm_map.get(s['time'],[]) for s in snaps]
    es=prov.es_lists_with_ids(raw,snaps)
    raw_fams=[esm,epm,ewm,es]
    pools=[prov.dedup_full_pool(s,z4_lists[i],[esm[i],epm[i],ewm[i],es[i]]) for i,s in enumerate(snaps)]
    displays=prov.sticky_display(raw,snaps,pools)

    context=[]; full=[]; dall=[]; erows=[]
    for i,(s,zs) in enumerate(zip(snaps,displays)):
        t=ts(s['time']); ai=int(s['active_i']); close=float(s['close']); v=float(s['v']); ny=t.tz_convert('America/New_York')
        trend=lambda n:(close-float(active.at[max(0,ai-n),'close']))/v
        ctx={
            'time':t,'close':close,'v_snapshot':v,'upper_z4_count':int(s['upper_z4_count']),
            'upper_z4_count_bucket':str(min(3,int(s['upper_z4_count']))) if int(s['upper_z4_count'])<3 else '3+',
            'nearest_upper_z4_dist_v':float(s['nearest_upper_z4_dist_v']),
            'trend15_v':float(trend(15)),'trend60_v':float(trend(60)),'trend240_v':float(trend(240)),
            'minute_of_session':int((ny.hour-8)*60+ny.minute),'minute_bin_30m':str(int(((ny.hour-8)*60+ny.minute)//30)),
            'weekday_ny':str(ny.weekday()),'session_date_ny':ny.date().isoformat(),
        }
        context.append(ctx)
        # Full causal pool before cross-family dedup: local lower Z4 plus each family's current candidates.
        candidates=[]
        for z in z4_lists[i]: candidates.append(z)
        for L in raw_fams:
            for z in L[i]: candidates.append(z)
        for z in candidates:
            full.append({'time':t,'family':z.family,'center':float(z.center),'zlo':float(z.zlo),'zhi':float(z.zhi),'v_snapshot':v})
        for rank,z in enumerate(zs,1):
            d=(close-float(z.center))/v
            base={**ctx,'display_slot_rank':int(rank),'entry_rank':int(rank),'family':z.family,'current_family':z.family,
                  'center':float(z.center),'zlo':float(z.zlo),'zhi':float(z.zhi),'distance_v':float(d),
                  'source_provenance_id':z.source_provenance_id,'source_provenance_members':';'.join(z.source_provenance_members)}
            dall.append(base)
            if z.family not in E_FAMILIES: continue
            confluence=set()
            for L in raw_fams:
                for q in L[i]:
                    if q.family in E_FAMILIES and (overlap(z,q) or abs(float(z.center)-float(q.center))<=.20*v): confluence.add(q.family)
            native=1.0 if z.family=='ESM_BOTH_G120M' else float(z.rank)*(1.0+float(d))
            erows.append({**base,'native_evidence_raw':float(native),'confluence_count_e_families':int(max(1,len(confluence))),
                          'zone_width_v':float((float(z.zhi)-float(z.zlo))/v)})

    ctxdf=pd.DataFrame(context); fulldf=pd.DataFrame(full); alldf=pd.DataFrame(dall); edf=pd.DataFrame(erows)
    if not len(edf): raise RuntimeError('no E rows')
    edf=assign_episode_identity(edf)
    edf['snapshot_time_utc']=pd.to_datetime(edf.time,utc=True); edf['bar_open_time_utc']=edf.snapshot_time_utc
    edf['bar_close_time_utc']=edf.snapshot_time_utc+pd.Timedelta(minutes=1); edf['feature_available_time_utc']=edf.snapshot_time_utc+pd.Timedelta(minutes=1)
    edf['log1p_zone_width_v']=np.log1p(edf.zone_width_v.astype(float)); edf['log1p_zone_width_v_squared']=edf.log1p_zone_width_v**2
    edf['distance_v_squared']=edf.distance_v.astype(float)**2; edf['log_v_snapshot']=np.log(edf.v_snapshot.astype(float))
    # Keep original slot; never renumber after Z4 exclusion.
    edf['row_sha256']=[canonical_hash(r) for r in edf.drop(columns=['row_sha256'],errors='ignore').to_dict('records')]

    mask=lambda d:(pd.to_datetime(d.time,utc=True)>=start)&(pd.to_datetime(d.time,utc=True)<end)
    ctxdf=ctxdf[mask(ctxdf)].copy(); fulldf=fulldf[mask(fulldf)].copy(); alldf=alldf[mask(alldf)].copy(); edf=edf[mask(edf)].copy()
    pq=exact_parity(a.reference_v04_csv,alldf,start,end) if a.reference_v04_csv else None
    if pq is not None and not pq['pass']: raise RuntimeError(f'V04_EXACT_PARITY_FAIL {pq}')

    write_gz(edf,a.output_features); write_gz(alldf,a.output_display_all); write_gz(fulldf,a.output_full_pool); write_gz(ctxdf,a.output_context)
    m={'status':'E_ZONE_V2_INSTRUMENT_OUTCOME_BLIND_PASS','future_price_outcomes_used':False,'target_start':start.isoformat(),'target_end':end.isoformat(),
       'feature_rows':int(len(edf)),'episodes':int(edf.display_episode_id.nunique()),'sessions':int(edf.session_date_ny.nunique()),
       'display_all_rows':int(len(alldf)),'full_pool_rows':int(len(fulldf)),'context_rows':int(len(ctxdf)),'geometry_parity':pq,
       'family_counts':{str(k):int(v) for k,v in edf.current_family.value_counts().sort_index().items()},
       'slot_counts':{str(k):int(v) for k,v in edf.display_slot_rank.value_counts().sort_index().items()},
       'forbidden_outcome_columns_present':False}
    Path(a.manifest).write_text(json.dumps(m,indent=2,sort_keys=True)+'\n'); print(json.dumps(m,indent=2,sort_keys=True))

if __name__=='__main__':main()
