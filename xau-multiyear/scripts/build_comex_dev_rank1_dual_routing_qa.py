#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import databento as db

NY=ZoneInfo('America/New_York')
MODELS=['passive_touch','touch_next_open','clean_rejection','failed_auction','acceptance_retest','reclaim_pullback']
BITS={2:'F_PUBLISHER_SPECIFIC',4:'F_MAYBE_BAD_BOOK',8:'F_BAD_TS_RECV',16:'F_MBP',32:'F_SNAPSHOT',64:'F_TOB',128:'F_LAST'}

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
    return h.hexdigest()

def session_bounds(date):
    d=pd.Timestamp(date);prev=(d-pd.Timedelta(days=1)).date();cur=d.date()
    start=pd.Timestamp(f'{prev} 18:00:00',tz=NY).tz_convert('UTC')
    close='17:15:00' if d.date()<pd.Timestamp('2015-09-21').date() else '17:00:00'
    end=pd.Timestamp(f'{cur} {close}',tz=NY).tz_convert('UTC')
    return start,end

def day_key(s:pd.Series)->pd.Series:
    z=pd.to_datetime(s,utc=True).dt.tz_convert(NY)
    base=z.dt.normalize().dt.tz_localize(None)
    return (base+pd.to_timedelta((z.dt.hour>=17).astype(int),unit='D')).dt.date.astype(str)

def load_dbn(path:Path)->pd.DataFrame:
    x=db.DBNStore.from_file(path).to_df().reset_index(drop=False)
    if 'ts_event' not in x.columns and x.columns[0] in {'ts_event','index'}:
        x=x.rename(columns={x.columns[0]:'ts_event'})
    x['ts_event']=pd.to_datetime(x['ts_event'],utc=True)
    return x

def marker_files(root:Path):
    out={}
    for p in root.rglob('*.json'):
        try:o=json.loads(p.read_text())
        except Exception:continue
        if o.get('version')=='COMEX_DEV_RANK1_DUAL_REQUEST_FILE_V1':out[str(o['request_id'])]=o
    return out

def find_one(root:Path,name:str)->Path|None:
    z=list(root.rglob(name));return z[0] if len(z)==1 else None

def prefix_volume(minute_idx:np.ndarray,minute_cum:np.ndarray,t:pd.Timestamp)->float:
    m=np.datetime64(t.floor('min').tz_convert('UTC').tz_localize(None),'ns')
    k=int(np.searchsorted(minute_idx,m,side='left'))-1
    return float(minute_cum[k]) if k>=0 else 0.0

def main():
    ap=argparse.ArgumentParser();
    for a in ['new-root','pilot-root','requests','sessions','mapping','events','out']:ap.add_argument('--'+a,required=True)
    a=ap.parse_args();newroot=Path(a.new_root);pilotroot=Path(a.pilot_root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    req=pd.read_csv(a.requests,dtype={'symbols':str});sessions=pd.read_csv(a.sessions);sessions=sessions[sessions.acquisition_stage.eq('DEV_RANK1')].copy();mapping=pd.read_csv(a.mapping,dtype={'v0_start_iid':str,'n0_start_iid':str})
    assert len(sessions)==96 and len(mapping)==96
    selected=set(sessions.research_trading_date.astype(str));paid=set(sessions[sessions.already_paid].research_trading_date.astype(str))
    marks=marker_files(newroot)

    # Build logical candidate-file map. Same-contract sessions reuse the N0 file for V0 logically.
    candidates={}; marker_by_path={}; source_by_path={}
    for _,r in req[req.request_type.eq('RAW_TRADES')].iterrows():
        rid=str(r.request_id);date=str(r.research_trading_date);role=str(r.candidate_role);label='N0' if role=='N0_PRIMARY_CANDIDATE' else 'V0'
        o=marks.get(rid);p=find_one(newroot,f'{rid}.dbn.zst') if o and int(o.get('records_downloaded',0))>0 else None
        candidates[(date,label)]={'path':p,'iid':str(r.symbols),'source':'NEW','request_id':rid,'marker':o}
        if p is not None:marker_by_path[str(p)]=o;source_by_path[str(p)]='NEW'
    mp=mapping.set_index(mapping.research_trading_date.astype(str))
    # Reuse the four paid rank-1 pilot trades. Pilot was V0; if same mapping it is also N0.
    for date in sorted(paid):
        p=find_one(pilotroot,f'{date}__trades.dbn.zst')
        if p is None:raise SystemExit(f'paid pilot trades missing for {date}')
        r=mp.loc[date];candidates[(date,'V0')]={'path':p,'iid':str(r.v0_start_iid),'source':'PILOT','request_id':None,'marker':None}
        source_by_path[str(p)]='PILOT'
        if str(r.v0_start_iid)==str(r.n0_start_iid):candidates[(date,'N0')]={'path':p,'iid':str(r.n0_start_iid),'source':'PILOT','request_id':None,'marker':None}
    # Same mapping: one physical N0/raw tape represents both candidates.
    for date,r in mapping.set_index(mapping.research_trading_date.astype(str)).iterrows():
        if bool(r.same_start_contract):
            z=candidates.get((date,'N0')) or candidates.get((date,'V0'))
            if z is not None:
                candidates[(date,'N0')]=z;candidates[(date,'V0')]=z

    # Decode each distinct raw tape once and retain minute-volume index for causal routing.
    paths={str(v['path']):v['path'] for v in candidates.values() if v.get('path') is not None}
    tape={};qa=[]
    for ps,p in sorted(paths.items()):
        x=load_dbn(p);price=pd.to_numeric(x.get('price'),errors='coerce');size=pd.to_numeric(x.get('size'),errors='coerce');flags=pd.to_numeric(x.get('flags',pd.Series(0,index=x.index)),errors='coerce').fillna(0).astype('int64');side=x.get('side',pd.Series('',index=x.index)).astype(str);iid=sorted(str(int(v)) for v in pd.to_numeric(x.get('instrument_id'),errors='coerce').dropna().unique())
        minute=x.ts_event.dt.floor('min');mv=pd.DataFrame({'minute':minute,'size':size}).groupby('minute',sort=True)['size'].sum();mi=mv.index.tz_convert('UTC').tz_localize(None).to_numpy(dtype='datetime64[ns]');mc=mv.cumsum().to_numpy(float)
        tape[ps]={'minutes':mi,'cum':mc,'full_volume':float(size.sum()),'records':int(len(x)),'min_ts':str(x.ts_event.min()),'max_ts':str(x.ts_event.max())}
        marker=marker_by_path.get(ps);expected=int(marker['records_downloaded']) if marker else None;expected_sha=marker.get('sha256') if marker else None
        row={'file':p.name,'source':source_by_path.get(ps),'records':int(len(x)),'expected_records':expected,'record_match':None if expected is None else int(len(x))==expected,'sha256':sha256_file(p),'expected_sha256':expected_sha,'sha_match':None if not expected_sha else sha256_file(p)==expected_sha,'instrument_ids':'|'.join(iid),'price_grid_0_1_violations':int(((price*10-(price*10).round()).abs()>1e-6).fillna(True).sum()),'nonpositive_size':int((size<=0).fillna(True).sum()),'side_N_records':int(side.eq('N').sum()),'side_values':'|'.join(sorted(side.unique())),'sequence_backward_steps':int((pd.to_numeric(x.get('sequence'),errors='coerce').diff()<0).sum()) if 'sequence' in x else 0,'full_volume':float(size.sum())}
        for bit,name in BITS.items():row[name]=int(((flags&bit)!=0).sum())
        qa.append(row)
        del x
    q=pd.DataFrame(qa);q.to_csv(out/'raw_tape_qa.csv',index=False)

    # Candidate/session availability and terminal leader.
    sessrows=[]
    for date,r in mapping.set_index(mapping.research_trading_date.astype(str)).iterrows():
        v=candidates.get((date,'V0'));n=candidates.get((date,'N0'));vp=str(v['path']) if v and v.get('path') else None;npth=str(n['path']) if n and n.get('path') else None
        vv=tape[vp]['full_volume'] if vp in tape else np.nan;nv=tape[npth]['full_volume'] if npth in tape else np.nan
        if bool(r.same_start_contract):leader='SAME' if np.isfinite(nv) else 'MISSING'
        elif np.isfinite(vv) and np.isfinite(nv):leader='N0' if nv>=vv else 'V0'
        else:leader='MISSING'
        sessrows.append({'research_trading_date':date,'same_start_contract':bool(r.same_start_contract),'v0_iid':str(r.v0_start_iid),'n0_iid':str(r.n0_start_iid),'v0_tape_available':bool(vp in tape),'n0_tape_available':bool(npth in tape),'v0_full_volume':None if not np.isfinite(vv) else vv,'n0_full_volume':None if not np.isfinite(nv) else nv,'terminal_leader':leader})
    sq=pd.DataFrame(sessrows);sq.to_csv(out/'dual_session_routing_qa.csv',index=False)

    # Canonical selected events and causal per-model active-contract routing.
    cols=['event_uid','year','contact_time']
    for m in MODELS:cols += [m+'_eligible',m+'_decision_time']
    e=pd.read_csv(a.events,compression='gzip',usecols=cols,low_memory=False);e['research_trading_date']=day_key(e.contact_time);e=e[e.research_trading_date.isin(selected)].copy();assert len(e)==31710,len(e)
    routes=[]
    smap=mapping.set_index(mapping.research_trading_date.astype(str))
    for row in e.itertuples(index=False):
        date=str(row.research_trading_date);mr=smap.loc[date];start,end=session_bounds(date)
        for m in MODELS:
            if not str(getattr(row,m+'_eligible')).lower()=='true':continue
            d=pd.to_datetime(getattr(row,m+'_decision_time'),utc=True,errors='coerce')
            if pd.isna(d):continue
            in_session=bool(d>=start and d<end)
            active='OUTSIDE_GC_SESSION';vvol=nvol=np.nan;active_iid=None
            if in_session:
                v=candidates.get((date,'V0'));n=candidates.get((date,'N0'));vp=str(v['path']) if v and v.get('path') else None;npth=str(n['path']) if n and n.get('path') else None
                if bool(mr.same_start_contract):
                    if npth in tape:active='SAME';active_iid=str(mr.n0_start_iid)
                    else:active='TAPE_MISSING'
                elif vp in tape and npth in tape:
                    vvol=prefix_volume(tape[vp]['minutes'],tape[vp]['cum'],d);nvol=prefix_volume(tape[npth]['minutes'],tape[npth]['cum'],d)
                    active='N0' if nvol>=vvol else 'V0';active_iid=str(mr.n0_start_iid if active=='N0' else mr.v0_start_iid)
                else:active='TAPE_MISSING'
            routes.append({'event_uid':row.event_uid,'research_trading_date':date,'year':int(row.year),'entry_model':m.upper(),'decision_time':str(d),'in_canonical_gc_session':in_session,'active_contract':active,'active_instrument_id':active_iid,'v0_cum_volume_before_decision_minute':None if not np.isfinite(vvol) else vvol,'n0_cum_volume_before_decision_minute':None if not np.isfinite(nvol) else nvol})
    rr=pd.DataFrame(routes);rr.to_csv(out/'event_model_dual_routing.csv.gz',index=False,compression='gzip')
    rsum=rr.groupby(['entry_model','active_contract'],dropna=False).size().rename('decisions').reset_index();rsum.to_csv(out/'routing_by_model.csv',index=False)

    # Context QA.
    ctx=[o for o in marks.values() if o.get('request_type')=='CONTINUOUS_OHLCV_CONTEXT']
    context={'markers':len(ctx),'records_downloaded':sum(int(o.get('records_downloaded',0)) for o in ctx),'raw_bytes':sum(int(o.get('raw_file_bytes',0)) for o in ctx),'sha256':[o.get('sha256') for o in ctx]}
    bad_record=int((q.record_match==False).sum()) if 'record_match' in q else 0;bad_sha=int((q.sha_match==False).sum()) if 'sha_match' in q else 0
    result={'version':'COMEX_DEV_RANK1_DUAL_ROUTING_QA_V1','market_data_download_performed':False,'analytical_sessions':96,'canonical_events':31710,'distinct_raw_tapes_loaded':len(paths),'raw_records_loaded':int(q.records.sum()),'raw_qa':{'record_mismatches':bad_record,'sha_mismatches':bad_sha,'tick_grid_violations':int(q.price_grid_0_1_violations.sum()),'nonpositive_size':int(q.nonpositive_size.sum()),'sequence_backward_steps':int(q.sequence_backward_steps.sum())},'session_availability':{'n0_available':int(sq.n0_tape_available.sum()),'v0_available':int(sq.v0_tape_available.sum()),'both_or_same_available':int(((sq.n0_tape_available)&(sq.v0_tape_available)).sum()),'tape_missing_dates':sq[~sq.n0_tape_available].research_trading_date.tolist(),'terminal_N0':int((sq.terminal_leader=='N0').sum()),'terminal_V0':int((sq.terminal_leader=='V0').sum()),'terminal_same':int((sq.terminal_leader=='SAME').sum()),'terminal_missing':int((sq.terminal_leader=='MISSING').sum())},'routing':{'eligible_decisions':int(len(rr)),'in_gc_session':int(rr.in_canonical_gc_session.sum()),'outside_gc_session':int((~rr.in_canonical_gc_session).sum()),'active_counts':{str(k):int(v) for k,v in rr.active_contract.value_counts().to_dict().items()}},'continuous_n0_context':context,'note':'Routing uses cumulative traded size strictly before the minute containing each causal decision_time. No XAU outcome is used.'}
    (out/'dual_routing_qa_summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
