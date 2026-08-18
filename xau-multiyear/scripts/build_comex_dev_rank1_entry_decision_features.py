#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
import build_comex_dev_rank1_event_features as feat

MODELS=['PASSIVE_TOUCH','TOUCH_NEXT_OPEN','CLEAN_REJECTION','FAILED_AUCTION','ACCEPTANCE_RETEST','RECLAIM_PULLBACK']

def decision_rows(e):
    rows=[]
    for r in e.itertuples(index=False):
        t0=pd.Timestamp(r.contact_time);b=str(r.behavior_v2)
        specs=[]
        specs.append(('PASSIVE_TOUCH',t0,True,'ALL_CONTACTS'))
        specs.append(('TOUCH_NEXT_OPEN',t0+pd.Timedelta(minutes=1),True,'ALL_CONTACTS'))
        m=getattr(r,'first_reclaim_minutes_v2',np.nan)
        if b=='CLEAN_REJECTION' and np.isfinite(m):
            specs.append(('CLEAN_REJECTION',t0+pd.Timedelta(minutes=float(m)+1),True,'CLEAN_REJECTION_CONFIRMED'))
            specs.append(('RECLAIM_PULLBACK',t0+pd.Timedelta(minutes=float(m)+1),True,'RECLAIM_CONFIRMED'))
        m2=getattr(r,'reclaim_after_breach_minutes_v2',np.nan)
        if b=='FAILED_AUCTION' and np.isfinite(m2):
            specs.append(('FAILED_AUCTION',t0+pd.Timedelta(minutes=float(m2)+1),True,'FAILED_AUCTION_RECLAIM_CONFIRMED'))
            specs.append(('RECLAIM_PULLBACK',t0+pd.Timedelta(minutes=float(m2)+1),True,'RECLAIM_CONFIRMED'))
        if b=='ACCEPTED_BREAK':specs.append(('ACCEPTANCE_RETEST',t0+pd.Timedelta(minutes=5),True,'ACCEPTED_BREAK_CONFIRMED'))
        for model,d,_,pop in specs:
            p=model.lower();fill=bool(getattr(r,p+'_eligible'))
            ent=getattr(r,p+'_entry_time',pd.NaT);delay=getattr(r,p+'_entry_delay_min',np.nan)
            if model in {'CLEAN_REJECTION','FAILED_AUCTION','RECLAIM_PULLBACK'}:
                lag=(d-t0).total_seconds()/60.0
                if lag>16.000001:raise SystemExit(f'causal reclaim cutoff >16m {r.event_uid} {model} {lag}')
            rows.append({'event_uid':str(r.event_uid),'year':int(r.year),'research_trading_date':str(r.research_trading_date),'contact_time':t0,'entry_model':model,'decision_time':d,'decision_population':pop,'fill_or_entry':fill,'entry_time':pd.Timestamp(ent) if pd.notna(ent) else pd.NaT,'entry_delay_min':float(delay) if pd.notna(delay) else np.nan,'family_stack':r.family_stack,'signature':r.signature,'side':r.side,'session':r.session,'local_hour':r.local_hour,'sigma60':r.sigma60,'zone_width_sigma':r.zone_width_sigma,'approach_direction':r.approach_direction,'approach_band':r.approach_band,'constituent_count':r.constituent_count,'quarter':r.quarter,'vol_band':r.vol_band,'poststrat_weight':r.poststrat_weight,'behavior_v2':b})
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser()
    for x in ['new-root','pilot-root','requests','sessions','mapping','events','xau-context','out']:ap.add_argument('--'+x,required=True)
    ap.add_argument('--model',choices=MODELS,required=False,default=None)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);newroot=Path(a.new_root);pilotroot=Path(a.pilot_root)
    req=pd.read_csv(a.requests,dtype={'symbols':str});sessions=pd.read_csv(a.sessions);sessions=sessions[sessions.acquisition_stage.eq('DEV_RANK1')].copy();mapping=pd.read_csv(a.mapping,dtype={'v0_start_iid':str,'n0_start_iid':str});assert len(sessions)==96 and len(mapping)==96
    cand,mk=feat.build_candidate_map(newroot,pilotroot,req,sessions,mapping);ctxm=[o for o in mk.values() if o.get('request_type')=='CONTINUOUS_OHLCV_CONTEXT'];assert len(ctxm)==1;ctxfile=feat.find_one(newroot,f"{ctxm[0]['request_id']}.dbn.zst");assert ctxfile is not None;ctx=feat.prepare_context(ctxfile,a.xau_context)
    use=['event_uid','year','contact_time','constituent_families','side','session','local_hour','sigma60','zone_width_sigma','approach_direction','approach_band','constituent_count','behavior_v2','first_reclaim_minutes_v2','reclaim_after_breach_minutes_v2']
    for m in MODELS:
        p=m.lower();use += [p+'_eligible',p+'_entry_time',p+'_entry_delay_min']
    e=pd.read_csv(a.events,compression='gzip',usecols=lambda c:c in set(use),low_memory=False);e['contact_time']=pd.to_datetime(e.contact_time,utc=True);e['research_trading_date']=feat.xau_day_key(e.contact_time);selected=set(sessions.research_trading_date.astype(str));e=e[e.research_trading_date.isin(selected)].copy();assert len(e)==31710
    e['signature']=e.constituent_families.map(feat.family_signature);e['family_stack']=e.signature.map(feat.family_stack);sw=sessions[['research_trading_date','quarter','vol_band','poststrat_weight']].copy();sw.research_trading_date=sw.research_trading_date.astype(str);e=e.merge(sw,on='research_trading_date',how='left',validate='many_to_one')
    d=decision_rows(e);assert set(d.entry_model.unique())==set(MODELS)
    if a.model is not None:
        d=d[d.entry_model.eq(a.model)].copy().reset_index(drop=True)
        if d.empty:raise SystemExit(f'no decision rows for {a.model}')
    mp=mapping.set_index(mapping.research_trading_date.astype(str));rows=[]
    grouped=list(d.groupby('research_trading_date',sort=True))
    for k,(date,g) in enumerate(grouped,1):
        print(f'session {k}/{len(grouped)} {date} decisions={len(g)} model={a.model or "ALL"}',flush=True);mr=mp.loc[date];s0,s1=feat.session_bounds(date);paths={}
        for lab in ['V0','N0']:
            z=cand.get((date,lab));p=z.get('path') if z else None
            if p is not None and str(p) not in paths:paths[str(p)]=feat.prep_tape(p,date)
        assignments=[]
        for idx,r in g.iterrows():
            cutoff=pd.Timestamp(r.decision_time);active='OUTSIDE_GC_SESSION';path=None;iid=''
            if cutoff>=s0 and cutoff<s1:
                vz=cand.get((date,'V0'));nz=cand.get((date,'N0'));vp=str(vz['path']) if vz and vz.get('path') else None;npth=str(nz['path']) if nz and nz.get('path') else None
                if bool(mr.same_start_contract):
                    if npth in paths and paths[npth] is not None:active='SAME';path=npth;iid=str(nz.get('iid',''))
                    else:active='TAPE_MISSING'
                elif vp in paths and npth in paths and paths[vp] is not None and paths[npth] is not None:
                    vt=paths[vp];nt=paths[npth];vj=feat.end_index(vt,cutoff);nj=feat.end_index(nt,cutoff);vv=feat.cumulative(vt['cum_size'],vj);nv=feat.cumulative(nt['cum_size'],nj);active='N0' if nv>=vv else 'V0';path=npth if active=='N0' else vp;iid=str((nz if active=='N0' else vz).get('iid',''))
                else:active='TAPE_MISSING'
            assignments.append((idx,cutoff,active,path,iid))
        bypath={}
        for z in assignments:
            if z[3] is not None:bypath.setdefault(z[3],[]).append(z)
        b2rows={}
        for ps,items in bypath.items():
            t=paths[ps];items=sorted(items,key=lambda z:z[1]);hist=np.zeros(t['tickmax']-t['tick0']+1,dtype=float);prev=0
            for idx,cutoff,active,_,iid in items:
                j=feat.end_index(t,cutoff)
                if j>prev:
                    hist += np.bincount(t['ticks'][prev:j]-t['tick0'],weights=t['size'][prev:j],minlength=len(hist));prev=j
                ref=float(t['price'][j-1]) if j>0 else np.nan;o={'b2_available':bool(j>0),'b2_active_contract':active,'b2_active_instrument_id':iid}
                if j>0:
                    tv=feat.cumulative(t['cum_size'],j);bv=feat.cumulative(t['cum_b'],j);av=feat.cumulative(t['cum_a'],j);nv=feat.cumulative(t['cum_n'],j);delta=bv-av;vwap=feat.cumulative(t['cum_ps'],j)/tv if tv else np.nan;poc,vah,val=feat.profile_hist(hist,t['tick0'],vwap);o.update({'b2_p_ref':ref,'b2_session_volume':tv,'b2_session_trade_count':j,'b2_session_bvol':bv,'b2_session_avol':av,'b2_session_nvol':nv,'b2_session_bshare':bv/tv if tv else np.nan,'b2_session_ashare':av/tv if tv else np.nan,'b2_session_nshare_secondary':nv/tv if tv else np.nan,'b2_session_native_delta':delta,'b2_session_normalized_delta':delta/tv if tv else np.nan,'b2_session_delta_lower':delta-nv,'b2_session_delta_upper':delta+nv,'b2_session_delta_sign_robust':1 if delta-nv>0 else (-1 if delta+nv<0 else 0),'b2_session_vwap_dist_bps':feat.dist_bps(ref,vwap),'b2_session_poc_dist_bps':feat.dist_bps(ref,poc),'b2_session_vah_dist_bps':feat.dist_bps(ref,vah),'b2_session_val_dist_bps':feat.dist_bps(ref,val),'b2_session_elapsed_min':float((cutoff-s0).total_seconds()/60.0)})
                    for h in feat.HORIZONS:o.update(feat.local_features(t,cutoff,j,h,ref))
                b2rows[idx]=o
        amap={z[0]:z for z in assignments}
        for idx,r in g.iterrows():
            base=r.to_dict();base.update(feat.context_features(ctx,pd.Timestamp(r.decision_time)));z=amap[idx];base.update(b2rows.get(idx,{'b2_available':False,'b2_active_contract':z[2],'b2_active_instrument_id':z[4]}));rows.append(base)
    f=pd.DataFrame(rows);f.to_parquet(out/'dev_rank1_entry_decision_features.parquet',index=False,compression='zstd')
    counts=[]
    for model,g in f.groupby('entry_model'):
        counts.append({'entry_model':model,'decision_events':len(g),'filled_or_entered':int(g.fill_or_entry.sum()),'fill_rate':float(g.fill_or_entry.mean()),'sessions':int(g.research_trading_date.nunique()),'years':int(g.year.nunique()),'b2_available':int(g.b2_available.fillna(False).sum())})
    meta={'version':'COMEX_DEV_RANK1_ENTRY_DECISION_FEATURES_V1_1','market_data_api_calls':False,'rows':len(f),'sessions':int(f.research_trading_date.nunique()),'models':sorted(f.entry_model.unique().tolist()),'requested_model':a.model,'counts':counts,'decision_population_freeze':'COMEX_DEV_RANK1_ENTRY_DECISION_POPULATIONS_FREEZE_v1.md','net_r_not_computed':True,'rr_not_selected':True,'scientific_change_from_v1':'none; optional model filter applied before session feature loop for orchestration only'}
    (out/'entry_decision_feature_manifest.json').write_text(json.dumps(meta,indent=2));f.head(200).to_csv(out/'entry_decision_sample_200.csv',index=False);print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
