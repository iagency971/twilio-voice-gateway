#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

import audit_comex_native_reaction_expanded_controls as base

TICK=0.10
K=5


def parse_bool(v):
    if isinstance(v,(bool,np.bool_)): return bool(v)
    return str(v).strip().lower()=='true'


def session_features(g:pd.DataFrame, source_date:str, next_date:str, iid:str, source_range:float, s:pd.Timestamp, e:pd.Timestamp, known_contacts:list[pd.Timestamp]):
    z=g.sort_values('ts_event').copy().reset_index(drop=True)
    z['anchor_time_utc']=z.ts_event+pd.Timedelta(minutes=1)
    z['anchor_minute_of_session']=((z.ts_event-s).dt.total_seconds()//60).astype(int)
    z['anchor_30m_bin']=(z.anchor_minute_of_session//30).astype(int)
    # Previous different completed close within 30 wall-clock minutes, vectorized by flat-price runs.
    run=(z.close.astype(float).ne(z.close.astype(float).shift())).cumsum()
    tmp=pd.DataFrame({'run':run,'close':z.close.astype(float),'bar_end':z.anchor_time_utc}).groupby('run',sort=True).agg(run_close=('close','first'),run_last_end=('bar_end','last'))
    tmp['prev_close']=tmp.run_close.shift(1); tmp['prev_end']=tmp.run_last_end.shift(1)
    z['approach_prior_price']=run.map(tmp.prev_close)
    z['approach_prior_end']=run.map(tmp.prev_end)
    age=(z.anchor_time_utc-z.approach_prior_end).dt.total_seconds()/60.0
    valid=z.approach_prior_price.notna() & age.le(30.0)
    z['away_sign']=0
    z.loc[valid & (z.approach_prior_price.astype(float)<z.close.astype(float)),'away_sign']=-1
    z.loc[valid & (z.approach_prior_price.astype(float)>z.close.astype(float)),'away_sign']=1
    # Rolling 30-minute executed-price range, including the anchor minute bar.
    ri=z.set_index('ts_event')
    z['pre30_range_ticks']=((ri.high.astype(float).rolling('30min').max()-ri.low.astype(float).rolling('30min').min())/TICK).to_numpy()
    z['pre30_complete']=(z.anchor_time_utc-pd.Timedelta(minutes=30)>=s)
    # Last executed close at or before 5 minutes before the anchor, matching the frozen pre5 definition.
    ts=z.ts_event.to_numpy(dtype='datetime64[ns]'); target=(z.ts_event-pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]')
    idx=np.searchsorted(ts,target,side='right')-1
    p5=np.full(len(z),np.nan); ok=idx>=0; p5[ok]=z.close.astype(float).to_numpy()[idx[ok]]
    z['pre5_signed_move_ticks']=z.away_sign.astype(float)*(z.close.astype(float).to_numpy()-p5)/TICK
    z['pre5_signed_move_norm']=z.pre5_signed_move_ticks/source_range
    z['w15_complete']=(z.anchor_time_utc+pd.Timedelta(minutes=15)<=e)
    excluded=np.zeros(len(z),dtype=bool)
    for t in known_contacts:
        excluded |= (np.abs((z.anchor_time_utc-t).dt.total_seconds().to_numpy())<=3600)
    z['excluded_native_contact_pm60']=excluded
    q=z[(z.away_sign!=0)&z.w15_complete&(~z.excluded_native_contact_pm60)&(z.anchor_minute_of_session>=0)].copy()
    q['control_source_research_date']=source_date; q['control_eligible_next_research_date']=next_date; q['year']=pd.Timestamp(source_date).year; q['source_instrument_id']=iid; q['source_range_ticks']=source_range
    q['approach']=np.where(q.away_sign.eq(-1),'APPROACH_FROM_BELOW','APPROACH_FROM_ABOVE'); q['approach_source']='M1_PRIOR_DIFFERENT_CLOSE'; q['anchor_price']=q.close.astype(float); q['anchor_bar_start_utc']=q.ts_event.astype(str)
    q['control_candidate_id']=[hashlib.sha256(f'CTXCTRL|{source_date}|{next_date}|{t.isoformat()}|{iid}'.encode()).hexdigest()[:24] for t in q.ts_event]
    q['post_anchor_reaction_values_read']=False; q['control_origin']='OWNED_GC_N0_CONTINUOUS_UNADJUSTED_STABLE_IID'
    cols=['control_candidate_id','control_source_research_date','control_eligible_next_research_date','year','source_instrument_id','anchor_bar_start_utc','anchor_time_utc','anchor_price','approach','away_sign','approach_prior_price','approach_source','anchor_minute_of_session','anchor_30m_bin','source_range_ticks','pre30_range_ticks','pre5_signed_move_ticks','pre5_signed_move_norm','excluded_native_contact_pm60','pre30_complete','w15_complete','post_anchor_reaction_values_read','control_origin']
    return q[cols]


def build_generic(ctx,events,sessions_path,original_dates):
    sess=pd.read_csv(sessions_path); sess['research_trading_date']=sess.research_trading_date.astype(str)
    stages=sess.acquisition_stage.astype(str).value_counts().to_dict(); reserved=set(sess.loc[~sess.acquisition_stage.astype(str).eq('DEV_RANK1'),'research_trading_date'])
    groups={d:g.copy().sort_values('ts_event') for d,g in ctx.groupby(ctx.gc_trade_date.astype(str),sort=True)}; dates=sorted(groups)
    ev=events.copy(); ev['t0']=pd.to_datetime(ev.t0_utc,utc=True); known={str(k):list(g.t0) for k,g in ev.groupby(ev.eligible_next_research_date.astype(str))}
    controls=[]; blocks=[]
    for i,d in enumerate(dates[:-1]):
        y=pd.Timestamp(d).year
        if y<2011 or y>2018: continue
        nd=dates[i+1]
        if d in reserved or nd in reserved or d in original_dates: continue
        a,b=groups[d],groups[nd]; ia=sorted(a.instrument_id.astype(str).unique()); ib=sorted(b.instrument_id.astype(str).unique())
        if len(ia)!=1 or len(ib)!=1 or ia[0]!=ib[0]: continue
        iid=ia[0]; sr=(float(a.high.max())-float(a.low.min()))/TICK
        if not np.isfinite(sr) or sr<=0: continue
        s,e=base.session_bounds(nd); b=b[(b.ts_event>=s)&(b.ts_event<e)].copy()
        if b.empty: continue
        q=session_features(b,d,nd,iid,sr,s,e,known.get(nd,[]))
        controls.append(q); blocks.append({'control_source_research_date':d,'control_eligible_next_research_date':nd,'source_year':y,'source_instrument_id':iid,'source_range_ticks':sr,'source_rows':len(a),'next_rows':len(b),'candidate_rows':len(q),'same_iid_source_and_next':True})
    C=pd.concat(controls,ignore_index=True) if controls else pd.DataFrame(); B=pd.DataFrame(blocks)
    return C,B,reserved,stages


def ratio_mask(series,b,lo=.5,hi=2.0):
    x=pd.to_numeric(series,errors='coerce'); return x.notna()&(x>0)&(float(b)>0)&(x/float(b)>=lo)&(x/float(b)<=hi)


def support(events,controls,early_fallback):
    E=events.copy(); E['source_year']=pd.to_datetime(E.source_research_date).dt.year
    C=controls.copy(); C['source_year']=pd.to_datetime(C.control_source_research_date).dt.year
    C['anchor_30m_bin']=pd.to_numeric(C.anchor_30m_bin,errors='coerce').astype('Int64'); C['away_sign']=pd.to_numeric(C.away_sign,errors='coerce').astype('Int64')
    grouped={(int(y),int(b),int(s)):g.copy() for (y,b,s),g in C.groupby(['source_year','anchor_30m_bin','away_sign'],sort=False) if pd.notna(y) and pd.notna(b) and pd.notna(s)}
    rr=[]
    for e in E.to_dict('records'):
        sign=int(float(e['away_sign'])); defined=sign in (-1,1); minute=int(e['anchor_minute_of_session']); early=minute<30
        strict=parse_bool(e['pre30_complete']) and np.isfinite(float(e['pre30_range_ticks'])) and float(e['pre30_range_ticks'])>0 and np.isfinite(float(e['pre5_signed_move_norm']))
        eligible=defined and parse_bool(e['w15_complete']) and float(e['source_range_ticks'])>0 and (strict or (early_fallback and early))
        q=C.iloc[0:0]
        if eligible:
            q=grouped.get((int(e['source_year']),minute//30,sign),C.iloc[0:0]).copy(); q=q[q.control_source_research_date.astype(str)!=str(e['source_research_date'])]
            if len(q): q=q[ratio_mask(q.source_range_ticks,e['source_range_ticks'])]
            if len(q) and not (early_fallback and early):
                q=q[q.pre30_complete.map(parse_bool)&q.pre30_range_ticks.notna()&q.pre5_signed_move_norm.notna()]
                q=q[ratio_mask(q.pre30_range_ticks,e['pre30_range_ticks'])]
            if len(q):
                q['d_source_log']=np.abs(np.log(q.source_range_ticks.astype(float)/float(e['source_range_ticks']))); q['d_minute']=np.abs(q.anchor_minute_of_session.astype(int)-minute); q['anchor_ts_sort']=pd.to_datetime(q.anchor_time_utc,utc=True)
                if early_fallback and early: q['d_pre30_log']=0.0; q['d_pre5_norm']=0.0
                else:
                    q['d_pre30_log']=np.abs(np.log(q.pre30_range_ticks.astype(float)/float(e['pre30_range_ticks']))); q['d_pre5_norm']=np.abs(q.pre5_signed_move_norm.astype(float)-float(e['pre5_signed_move_norm']))
                sort=['d_pre30_log','d_source_log','d_pre5_norm','d_minute','anchor_ts_sort','control_source_research_date','source_instrument_id','control_candidate_id']
                q=q.sort_values(sort,kind='mergesort').groupby('control_source_research_date',sort=False,as_index=False).head(1).sort_values(sort,kind='mergesort').head(K)
        n=int(q.control_source_research_date.nunique()) if len(q) else 0
        rr.append({'level_id':str(e['level_id']),'source_research_date':str(e['source_research_date']),'source_year':int(e['source_year']),'approach_defined':defined,'event_eligible':eligible,'eligible_control_dates':n,'full_k5_match':n==K})
    R=pd.DataFrame(rr); D=R[R.approach_defined]; M=D[D.full_k5_match]; ys=[]
    for y in range(2011,2019):
        g=D[D.source_year==y]; m=g[g.full_k5_match]; ys.append({'source_year':y,'defined_events':len(g),'matched_events':len(m),'match_rate':len(m)/len(g) if len(g) else 0,'matched_dates':m.source_research_date.nunique()})
    Y=pd.DataFrame(ys); rate=len(M)/len(D) if len(D) else 0
    crit={'matched_events_ge_160':len(M)>=160,'matched_dates_ge_60':M.source_research_date.nunique()>=60,'every_source_year_matched_dates_ge_5':bool((Y.matched_dates>=5).all()),'defined_contact_full_match_rate_ge_0_85':rate>=.85,'every_source_year_full_match_rate_ge_0_75':bool((Y.match_rate>=.75).all())}
    return R,Y,{'defined_events':len(D),'event_eligible':int(D.event_eligible.sum()),'full_k5_matched_events':len(M),'full_k5_matched_dates':int(M.source_research_date.nunique()),'full_match_rate':rate,'criteria':crit,'support_gate_pass':all(crit.values())}


def main():
    ap=argparse.ArgumentParser()
    for x in ['context-root','n1-root','n1-market-manifest','events','existing-controls','sessions','out']:ap.add_argument('--'+x,required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    marker,ctx_path=base.find_context(Path(a.context_root));ctx=base.load_context(ctx_path);parity,ps=base.parity_audit(ctx,Path(a.n1_root),a.n1_market_manifest)
    events=pd.read_csv(a.events); existing=pd.read_csv(a.existing_controls,compression='gzip'); existing['control_origin']='CANONICAL_92_RAW_N1'; existing['year']=pd.to_datetime(existing.control_source_research_date).dt.year
    generic,blocks,reserved,stages=build_generic(ctx,events,a.sessions,set(events.source_research_date.astype(str)))
    combined=pd.concat([existing,generic],ignore_index=True,sort=False); r0,y0,s0=support(events,combined,False);r1,y1,s1=support(events,combined,True)
    parity.to_csv(out/'continuous_vs_raw_n1_parity.csv',index=False);blocks.to_csv(out/'expanded_control_blocks.csv',index=False);r0.to_csv(out/'support_strict_pro.csv',index=False);y0.to_csv(out/'support_strict_pro_by_year.csv',index=False);r1.to_csv(out/'support_early_fallback.csv',index=False);y1.to_csv(out/'support_early_fallback_by_year.csv',index=False)
    manifest={'version':'COMEX_DEV_RANK1_NATIVE_REACTION_EXPANDED_CONTROL_FEASIBILITY_V2','post_anchor_outcomes_read':False,'reaction_outcomes_computed':False,'mfe_mae_computed':False,'market_data_api_called':False,'market_data_download_performed':False,'continuous_context_request_id':marker.get('request_id'),'continuous_context_raw_sha256':base.sha256_file(ctx_path),'continuous_context_records':len(ctx),'continuous_context_unique_instrument_ids':int(ctx.instrument_id.nunique()),'parity_summary':ps,'session_stage_counts':{str(k):int(v) for k,v in stages.items()},'reserved_non_dev_rank1_dates':len(reserved),'generic_stable_same_iid_blocks':len(blocks),'generic_control_candidates':len(generic),'existing_control_candidates':len(existing),'combined_control_candidates':len(combined),'strict_pro_support':s0,'early_fallback_support':s1,'expanded_blocks_sha256':base.sha256_file(out/'expanded_control_blocks.csv'),'notes':['Vendor continuous-contract prices are original and unadjusted; this audit additionally requires a constant underlying instrument_id across source J and J+1 and raw-N1 parity where directly testable.','Any source or next date explicitly reserved for non-DEV_RANK1 is excluded.','No post-anchor reaction outcome is read or computed.','Strict support preserves original Pro K5/exact-source-year/30-minute-bin/approach/0.5-2 calipers.','Early fallback is a sensitivity only and requires Pro approval before freezing.']}
    (out/'expanded_control_feasibility.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
