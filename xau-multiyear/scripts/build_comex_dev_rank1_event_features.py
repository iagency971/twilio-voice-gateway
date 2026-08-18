#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import databento as db

NY=ZoneInfo('America/New_York')
FAMILIES=['DISPLACEMENT_ORIGIN','OBJECTIVE_LIQUIDITY','MEMORY','FVG']
HORIZONS=[1,5,15,30]

def sha256_file(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
    return h.hexdigest()

def session_bounds(date):
    d=pd.Timestamp(date);prev=(d-pd.Timedelta(days=1)).date();cur=d.date();start=pd.Timestamp(f'{prev} 18:00:00',tz=NY).tz_convert('UTC');close='17:15:00' if d.date()<pd.Timestamp('2015-09-21').date() else '17:00:00';end=pd.Timestamp(f'{cur} {close}',tz=NY).tz_convert('UTC');return start,end

def xau_day_key(s):
    z=pd.to_datetime(s,utc=True).dt.tz_convert(NY);base=z.dt.normalize().dt.tz_localize(None);return (base+pd.to_timedelta((z.dt.hour>=17).astype(int),unit='D')).dt.date.astype(str)

def family_signature(s):
    v=str(s) if pd.notna(s) else ''
    return '+'.join(f for f in FAMILIES if f in v) or 'OTHER'

def family_stack(sig):
    return {'DISPLACEMENT_ORIGIN':'DOZ_ONLY','OBJECTIVE_LIQUIDITY':'OBJECTIVE_ONLY','MEMORY':'MEMORY_ONLY','FVG':'FVG_ONLY'}.get(sig,'CONFLUENCE' if '+' in sig else 'OTHER')

def load_dbn(path):
    x=db.DBNStore.from_file(path).to_df().reset_index(drop=False)
    if 'ts_event' not in x.columns:x=x.rename(columns={x.columns[0]:'ts_event'})
    x['ts_event']=pd.to_datetime(x.ts_event,utc=True);return x.sort_values('ts_event').reset_index(drop=True)

def markers(root):
    z={}
    for p in root.rglob('*.json'):
        try:o=json.loads(p.read_text())
        except Exception:continue
        if o.get('version')=='COMEX_DEV_RANK1_DUAL_REQUEST_FILE_V1':z[str(o['request_id'])]=o
    return z

def find_one(root,name):
    z=list(root.rglob(name));return z[0] if len(z)==1 else None

def profile_hist(hist,tick0,vwap):
    total=float(hist.sum())
    if total<=0:return (np.nan,np.nan,np.nan)
    mx=float(hist.max());cand=np.flatnonzero(hist==mx);vp=vwap*10.0;dist=np.abs((tick0+cand)-vp);mind=float(dist.min());cand2=cand[dist==mind];pidx=int(cand2.min());poc=(tick0+pidx)/10.0
    target=.70*total;sel=float(hist[pidx]);lo=hi=pidx
    while sel<target and (lo>0 or hi<len(hist)-1):
        lv=float(hist[lo-1]) if lo>0 else -1.0;uv=float(hist[hi+1]) if hi<len(hist)-1 else -1.0
        if lv==uv and lv>=0:
            lo-=1;sel+=float(hist[lo])
            if hi<len(hist)-1:hi+=1;sel+=float(hist[hi])
        elif lv>uv:
            lo-=1;sel+=float(hist[lo])
        else:
            hi+=1;sel+=float(hist[hi])
    return poc,(tick0+hi)/10.0,(tick0+lo)/10.0

def profile_slice(price,size):
    if len(price)==0:return (np.nan,np.nan,np.nan,np.nan)
    good=np.isfinite(price)&np.isfinite(size)&(size>0)
    if not good.any():return (np.nan,np.nan,np.nan,np.nan)
    p=price[good];s=size[good];tv=float(s.sum());vwap=float(np.sum(p*s)/tv);ticks=np.rint(p*10).astype(int);t0=int(ticks.min());hist=np.bincount(ticks-t0,weights=s,minlength=int(ticks.max()-t0+1));poc,vah,val=profile_hist(hist,t0,vwap);return vwap,poc,vah,val

def dist_bps(ref,level):
    return 10000.0*(ref-level)/ref if np.isfinite(ref) and ref!=0 and np.isfinite(level) else np.nan

def assign_gc_session(ctx):
    local=ctx.ts_event.dt.tz_convert(NY);mod=local.dt.hour*60+local.dt.minute;base=local.dt.normalize().dt.tz_localize(None);trade=base+pd.to_timedelta((mod>=1080).astype(int),unit='D');pre=trade<pd.Timestamp('2015-09-21');close=np.where(pre,1035,1020);valid=(mod>=1080)|(mod<close);off=np.where(mod>=1080,mod-1080,360+mod);ctx['gc_trade_date']=trade.dt.date.astype(str);ctx['gc_offset']=off.astype(int);ctx['gc_session_valid']=valid;ctx.loc[~valid,'gc_trade_date']='';ctx.loc[~valid,'gc_offset']=-1

def prepare_context(path,xau_path):
    c=load_dbn(path);need=['open','high','low','close','volume','instrument_id'];miss=[x for x in need if x not in c.columns]
    if miss:raise SystemExit(f'context missing columns {miss}')
    for col in ['open','high','low','close','volume']:c[col]=pd.to_numeric(c[col],errors='coerce')
    x=pd.read_parquet(xau_path);x['timestamp']=pd.to_datetime(x.timestamp,utc=True);c=c.merge(x.rename(columns={'timestamp':'ts_event'}),on='ts_event',how='left');c['basis']=c['close']-c['xau_close'];assign_gc_session(c)
    c=c.sort_values('ts_event').reset_index(drop=True)
    for h in HORIZONS:
        c[f'volsum_{h}']=np.nan;c[f'relvol_{h}']=np.nan
        idx=c.index[c.gc_session_valid]
        tmp=c.loc[idx,['gc_trade_date','gc_offset','volume']].copy();tmp[f'volsum_{h}']=tmp.groupby('gc_trade_date',sort=False)['volume'].transform(lambda s:s.rolling(h,min_periods=h).sum());tmp[f'baseline_{h}']=tmp.groupby('gc_offset',sort=False)[f'volsum_{h}'].transform(lambda s:s.shift(1).rolling(20,min_periods=10).median());tmp[f'relvol_{h}']=tmp[f'volsum_{h}']/tmp[f'baseline_{h}'].clip(lower=1.0);c.loc[idx,f'volsum_{h}']=tmp[f'volsum_{h}'];c.loc[idx,f'relvol_{h}']=tmp[f'relvol_{h}']
    return c

def context_features(c,cutoff):
    ts=c.ts_event.values.astype('datetime64[ns]');t=np.datetime64(pd.Timestamp(cutoff).tz_convert('UTC').tz_localize(None),'ns');j=int(np.searchsorted(ts,t,side='left'))-1;out={'b1_available':False,'b1_exact_prev_minute':False}
    if j<0:return out
    row=c.iloc[j];out['b1_available']=True;expected=pd.Timestamp(cutoff).floor('min')-pd.Timedelta(minutes=1);out['b1_exact_prev_minute']=bool(row.ts_event==expected);out['b1_last_bar_age_min']=float((pd.Timestamp(cutoff)-row.ts_event).total_seconds()/60.0);iid=row.instrument_id
    for h in HORIZONS:
        if j-h>=0:
            seg=c.iloc[j-h:j+1]
            if (seg.instrument_id==iid).all():
                out[f'b1_gc_ret_{h}_bps']=float(10000*np.log(seg.close.iloc[-1]/seg.close.iloc[0])) if seg.close.iloc[0]>0 and seg.close.iloc[-1]>0 else np.nan
                if seg.basis.notna().all():out[f'b1_basis_change_{h}']=float(seg.basis.iloc[-1]-seg.basis.iloc[0])
        if j-h+1>=0:
            seg2=c.iloc[j-h+1:j+1]
            if (seg2.instrument_id==iid).all():out[f'b1_gc_range_{h}_bps']=float(10000*(seg2.high.max()-seg2.low.min())/seg2.close.iloc[-1]) if seg2.close.iloc[-1]>0 else np.nan
        out[f'b1_gc_m1_volume_{h}']=float(row.get(f'volsum_{h}',np.nan));out[f'b1_relvol_{h}']=float(row.get(f'relvol_{h}',np.nan))
    for h in [15,60]:
        if j-h>=0:
            seg=c.iloc[j-h:j+1]
            if (seg.instrument_id==iid).all() and (seg.close>0).all():
                r=np.diff(np.log(seg.close.to_numpy(float)));out[f'b1_gc_rv_{h}']=float(np.sqrt(np.sum(r*r))*10000)
    if out['b1_exact_prev_minute'] and pd.notna(row.basis):out['b1_basis']=float(row.basis)
    out['b1_context_instrument_id']=str(int(iid)) if pd.notna(iid) else ''
    return out

def prep_tape(path,date):
    x=load_dbn(path);s,e=session_bounds(date);x=x[(x.ts_event>=s)&(x.ts_event<e)].copy().reset_index(drop=True)
    if x.empty:return None
    price=pd.to_numeric(x.price,errors='coerce').to_numpy(float);size=pd.to_numeric(x['size'],errors='coerce').to_numpy(float);side=x.side.astype(str).to_numpy();ts=x.ts_event.values.astype('datetime64[ns]');ticks=np.rint(price*10).astype(int);cum_size=np.cumsum(size);cum_ps=np.cumsum(price*size);cum_b=np.cumsum(np.where(side=='B',size,0.0));cum_a=np.cumsum(np.where(side=='A',size,0.0));cum_n=np.cumsum(np.where(side=='N',size,0.0));return {'price':price,'size':size,'side':side,'ts':ts,'ticks':ticks,'cum_size':cum_size,'cum_ps':cum_ps,'cum_b':cum_b,'cum_a':cum_a,'cum_n':cum_n,'tick0':int(ticks.min()),'tickmax':int(ticks.max())}

def end_index(tape,cutoff):
    t=np.datetime64(pd.Timestamp(cutoff).floor('min').tz_convert('UTC').tz_localize(None),'ns');return int(np.searchsorted(tape['ts'],t,side='left'))

def cumulative(a,j):return float(a[j-1]) if j>0 else 0.0

def local_features(tape,cutoff,j,h,ref):
    start=np.datetime64((pd.Timestamp(cutoff).floor('min')-pd.Timedelta(minutes=h)).tz_convert('UTC').tz_localize(None),'ns');i=int(np.searchsorted(tape['ts'],start,side='left'));p=tape['price'][i:j];s=tape['size'][i:j];side=tape['side'][i:j];o={};prefix=f'b2_{h}m_';n=len(p);tv=float(s.sum()) if n else 0.0;o[prefix+'volume']=tv;o[prefix+'trade_count']=int(n)
    if n:
        mins=np.unique(tape['ts'][i:j].astype('datetime64[m]')).size;o[prefix+'active_minutes']=int(mins);o[prefix+'trade_rate']=float(n/mins) if mins else np.nan;o[prefix+'volume_rate']=float(tv/mins) if mins else np.nan;o[prefix+'mean_size']=float(np.mean(s));o[prefix+'median_size']=float(np.median(s));o[prefix+'max_size']=float(np.max(s));b=float(s[side=='B'].sum());a=float(s[side=='A'].sum());nv=float(s[side=='N'].sum());d=b-a;o[prefix+'bvol']=b;o[prefix+'avol']=a;o[prefix+'nvol']=nv;o[prefix+'bshare']=b/tv if tv else np.nan;o[prefix+'ashare']=a/tv if tv else np.nan;o[prefix+'nshare_secondary']=nv/tv if tv else np.nan;o[prefix+'native_delta']=d;o[prefix+'normalized_delta']=d/tv if tv else np.nan;o[prefix+'delta_lower']=d-nv;o[prefix+'delta_upper']=d+nv;o[prefix+'delta_sign_robust']=1 if d-nv>0 else (-1 if d+nv<0 else 0);vwap=float(np.sum(p*s)/tv) if tv else np.nan;o[prefix+'vwap_dist_bps']=dist_bps(ref,vwap);chg=float(p[-1]-p[0]);o[prefix+'price_impact_per_volume']=chg/tv if tv else np.nan;o[prefix+'price_impact_per_abs_delta']=chg/abs(d) if abs(d)>0 else np.nan
        if h==30:
            _,poc,vah,val=profile_slice(p,s);o['b2_local30_poc_dist_bps']=dist_bps(ref,poc);o['b2_local30_vah_dist_bps']=dist_bps(ref,vah);o['b2_local30_val_dist_bps']=dist_bps(ref,val)
    else:
        o[prefix+'active_minutes']=0;o[prefix+'trade_rate']=np.nan;o[prefix+'volume_rate']=np.nan;o[prefix+'native_delta']=0.0;o[prefix+'normalized_delta']=np.nan;o[prefix+'delta_lower']=0.0;o[prefix+'delta_upper']=0.0;o[prefix+'delta_sign_robust']=0
    return o

def build_candidate_map(newroot,pilotroot,req,sessions,mapping):
    mk=markers(newroot);cand={};paid=set(sessions[sessions.already_paid].research_trading_date.astype(str));mp=mapping.set_index(mapping.research_trading_date.astype(str))
    for _,r in req[req.request_type.eq('RAW_TRADES')].iterrows():
        rid=str(r.request_id);date=str(r.research_trading_date);lab='N0' if r.candidate_role=='N0_PRIMARY_CANDIDATE' else 'V0';o=mk.get(rid);p=find_one(newroot,f'{rid}.dbn.zst') if o and int(o.get('records_downloaded',0))>0 else None;cand[(date,lab)]={'path':p,'iid':str(r.symbols)}
    for date in paid:
        p=find_one(pilotroot,f'{date}__trades.dbn.zst');r=mp.loc[date]
        if p is None:raise SystemExit(f'pilot tape missing {date}')
        cand[(date,'V0')]={'path':p,'iid':str(r.v0_start_iid)}
        if str(r.v0_start_iid)==str(r.n0_start_iid):cand[(date,'N0')]={'path':p,'iid':str(r.n0_start_iid)}
    for date,r in mp.iterrows():
        if bool(r.same_start_contract):
            z=cand.get((date,'N0')) or cand.get((date,'V0'))
            if z:cand[(date,'N0')]=z;cand[(date,'V0')]=z
    return cand,mk

def main():
    ap=argparse.ArgumentParser();
    for a in ['new-root','pilot-root','requests','sessions','mapping','events','xau-context','out']:ap.add_argument('--'+a,required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);newroot=Path(a.new_root);pilotroot=Path(a.pilot_root);req=pd.read_csv(a.requests,dtype={'symbols':str});sessions=pd.read_csv(a.sessions);sessions=sessions[sessions.acquisition_stage.eq('DEV_RANK1')].copy();mapping=pd.read_csv(a.mapping,dtype={'v0_start_iid':str,'n0_start_iid':str});assert len(sessions)==96 and len(mapping)==96
    cand,mk=build_candidate_map(newroot,pilotroot,req,sessions,mapping);ctxm=[o for o in mk.values() if o.get('request_type')=='CONTINUOUS_OHLCV_CONTEXT'];assert len(ctxm)==1;ctxfile=find_one(newroot,f"{ctxm[0]['request_id']}.dbn.zst");assert ctxfile is not None
    print('prepare context',flush=True);ctx=prepare_context(ctxfile,a.xau_context);ctx_ts=ctx.ts_event
    use=['event_uid','year','contact_time','constituent_families','side','session','local_hour','sigma60','zone_width_sigma','approach_direction','approach_band','constituent_count','reaction_0_5sigma','behavior_v2']
    e=pd.read_csv(a.events,compression='gzip',usecols=use,low_memory=False);e['research_trading_date']=xau_day_key(e.contact_time);selected=set(sessions.research_trading_date.astype(str));e=e[e.research_trading_date.isin(selected)].copy();assert len(e)==31710,len(e);e['signature']=e.constituent_families.map(family_signature);e['family_stack']=e.signature.map(family_stack);e['contact_time']=pd.to_datetime(e.contact_time,utc=True)
    sw=sessions[['research_trading_date','year','quarter','vol_band','poststrat_weight']].copy();sw.research_trading_date=sw.research_trading_date.astype(str);e=e.merge(sw.drop(columns=['year']),on='research_trading_date',how='left',validate='many_to_one')
    rows=[];mp=mapping.set_index(mapping.research_trading_date.astype(str))
    for k,(date,g) in enumerate(e.groupby('research_trading_date',sort=True),1):
        print(f'session {k}/96 {date} events={len(g)}',flush=True);mr=mp.loc[date];s0,s1=session_bounds(date);paths={}
        for lab in ['V0','N0']:
            z=cand.get((date,lab));p=z.get('path') if z else None
            if p is not None and str(p) not in paths:paths[str(p)]=prep_tape(p,date)
        # Assign active physical tape for each event at pre-contact cutoff.
        assignments=[]
        for idx,r in g.iterrows():
            cutoff=r.contact_time.floor('min');active='OUTSIDE_GC_SESSION';path=None
            if cutoff>=s0 and cutoff<s1:
                vz=cand.get((date,'V0'));nz=cand.get((date,'N0'));vp=str(vz['path']) if vz and vz.get('path') else None;npth=str(nz['path']) if nz and nz.get('path') else None
                if bool(mr.same_start_contract):
                    if npth in paths and paths[npth] is not None:active='SAME';path=npth
                    else:active='TAPE_MISSING'
                elif vp in paths and npth in paths and paths[vp] is not None and paths[npth] is not None:
                    vt=paths[vp];nt=paths[npth];vj=end_index(vt,cutoff);nj=end_index(nt,cutoff);vv=cumulative(vt['cum_size'],vj);nv=cumulative(nt['cum_size'],nj);active='N0' if nv>=vv else 'V0';path=npth if active=='N0' else vp
                else:active='TAPE_MISSING'
            assignments.append((idx,cutoff,active,path))
        # Profile/session processing per active physical path in chronological order.
        bypath={}
        for z in assignments:
            if z[3] is not None:bypath.setdefault(z[3],[]).append(z)
        b2rows={}
        for ps,items in bypath.items():
            t=paths[ps];items=sorted(items,key=lambda z:z[1]);hist=np.zeros(t['tickmax']-t['tick0']+1,dtype=float);prev=0
            for idx,cutoff,active,_ in items:
                j=end_index(t,cutoff)
                if j>prev:
                    add=np.bincount(t['ticks'][prev:j]-t['tick0'],weights=t['size'][prev:j],minlength=len(hist));hist+=add;prev=j
                ref=float(t['price'][j-1]) if j>0 else np.nan;o={'b2_available':bool(j>0),'b2_active_contract':active,'b2_active_instrument_id':str(int(e.loc[idx,'year'])) if False else ''}
                if j>0:
                    tv=cumulative(t['cum_size'],j);b=cumulative(t['cum_b'],j);av=cumulative(t['cum_a'],j);nv=cumulative(t['cum_n'],j);d=b-av;vwap=cumulative(t['cum_ps'],j)/tv if tv else np.nan;poc,vah,val=profile_hist(hist,t['tick0'],vwap);o.update({'b2_p_ref':ref,'b2_session_volume':tv,'b2_session_trade_count':j,'b2_session_bvol':b,'b2_session_avol':av,'b2_session_nvol':nv,'b2_session_bshare':b/tv if tv else np.nan,'b2_session_ashare':av/tv if tv else np.nan,'b2_session_nshare_secondary':nv/tv if tv else np.nan,'b2_session_native_delta':d,'b2_session_normalized_delta':d/tv if tv else np.nan,'b2_session_delta_lower':d-nv,'b2_session_delta_upper':d+nv,'b2_session_delta_sign_robust':1 if d-nv>0 else (-1 if d+nv<0 else 0),'b2_session_vwap_dist_bps':dist_bps(ref,vwap),'b2_session_poc_dist_bps':dist_bps(ref,poc),'b2_session_vah_dist_bps':dist_bps(ref,vah),'b2_session_val_dist_bps':dist_bps(ref,val),'b2_session_elapsed_min':float((cutoff-s0).total_seconds()/60.0)})
                    for h in HORIZONS:o.update(local_features(t,cutoff,j,h,ref))
                b2rows[idx]=o
        for idx,r in g.iterrows():
            base={c:r[c] for c in ['event_uid','year','research_trading_date','contact_time','family_stack','signature','side','session','local_hour','sigma60','zone_width_sigma','approach_direction','approach_band','constituent_count','reaction_0_5sigma','behavior_v2','quarter','vol_band','poststrat_weight']};base.update(context_features(ctx,r.contact_time.floor('min')));b2=b2rows.get(idx,{'b2_available':False,'b2_active_contract':next((z[2] for z in assignments if z[0]==idx),'TAPE_MISSING')});base.update(b2);rows.append(base)
    f=pd.DataFrame(rows);assert len(f)==31710;f.to_parquet(out/'dev_rank1_event_features.parquet',index=False,compression='zstd')
    b0=['family_stack','signature','side','session','local_hour','sigma60','zone_width_sigma','approach_direction','approach_band','constituent_count']
    b1=[c for c in f.columns if c.startswith('b1_') and c not in {'b1_available','b1_context_instrument_id'}]
    # N-share variables are retained but secondary because year is not an allowed B0 nuisance covariate.
    b2=[c for c in f.columns if c.startswith('b2_') and c not in {'b2_available','b2_active_contract','b2_active_instrument_id','b2_p_ref'} and 'nshare_secondary' not in c and not c.endswith('_nvol')]
    meta={'version':'COMEX_DEV_RANK1_EVENT_FEATURES_V1','events':len(f),'sessions':int(f.research_trading_date.nunique()),'b0_features':b0,'b1_primary_features':b1,'b2_primary_features':b2,'b2_secondary_n_features':[c for c in f.columns if 'nshare_secondary' in c or c.endswith('_nvol')],'availability':{'b1_available_events':int(f.b1_available.fillna(False).sum()),'b2_available_events':int(f.b2_available.fillna(False).sum()),'b2_active_contract_counts':{str(k):int(v) for k,v in f.b2_active_contract.fillna('MISSING').value_counts().to_dict().items()}},'outcomes':{'reaction_0_5sigma':{str(k):int(v) for k,v in f.reaction_0_5sigma.astype(str).value_counts().to_dict().items()},'behavior_v2':{str(k):int(v) for k,v in f.behavior_v2.astype(str).value_counts().to_dict().items()}},'cutoff':'strictly before contact minute start','basis_source':'same canonical Dukascopy bid/ask midpoint loader, selected months only','no_databento_api_calls_in_feature_job':True}
    (out/'feature_manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf-8');f.head(200).to_csv(out/'feature_sample_200.csv',index=False);print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
