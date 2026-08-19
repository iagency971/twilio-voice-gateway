#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

import audit_comex_native_reaction_expanded_controls as base

TICK=.10
K=5


def pb(v):
    if isinstance(v,(bool,np.bool_)): return bool(v)
    return str(v).strip().lower()=='true'


def ratio_mask(s,b,lo=.5,hi=2.0):
    x=pd.to_numeric(s,errors='coerce'); b=float(b)
    return x.notna()&(x>0)&(b>0)&(x/b>=lo)&(x/b<=hi)


def load_n1_sessions(root:Path, manifest_path:str):
    man=pd.read_csv(manifest_path,dtype={'source_instrument_id':str,'symbols':str}); marks=base.read_n1_markers(root); out={}
    for r in man.itertuples(index=False):
        rid=str(r.market_request_id)
        if rid not in marks: raise SystemExit(f'N1 marker missing {rid}')
        mk,raw=marks[rid]; m=base.pre.prepare_m1(raw,r.start,r.end)
        out[str(r.source_research_date)]={'m1':m,'start':base.pre.to_utc(r.start),'end':base.pre.to_utc(r.end),'next_date':str(r.eligible_next_research_date),'iid':str(r.source_instrument_id),'rid':rid}
    if len(out)!=92: raise SystemExit(f'expected 92 N1 sessions, got {len(out)}')
    return out


def vector_control_features(m1:pd.DataFrame, source_date:str, next_date:str, iid:str, sr:float, s:pd.Timestamp, e:pd.Timestamp, contacts:list[pd.Timestamp], origin:str):
    z=m1.sort_values('ts_event').copy().reset_index(drop=True)
    if z.empty: return pd.DataFrame()
    z['bar_end']=z.ts_event+pd.Timedelta(minutes=1)
    z['minute']=((z.ts_event-s).dt.total_seconds()//60).astype(int); z['bin30']=(z.minute//30).astype(int)
    # Pseudo-approach uses the pseudo contact minute close vs the most recent different completed close in prior 30m.
    run=z.close.astype(float).ne(z.close.astype(float).shift()).cumsum()
    info=pd.DataFrame({'run':run,'v':z.close.astype(float),'end':z.bar_end}).groupby('run',sort=True).agg(v=('v','first'),last_end=('end','last'))
    info['pv']=info.v.shift(1);info['pe']=info.last_end.shift(1)
    z['prior']=run.map(info.pv);z['prior_end']=run.map(info.pe);age=(z.bar_end-z.prior_end).dt.total_seconds()/60
    valid=z.prior.notna()&age.le(30);z['sign']=0;z.loc[valid&(z.prior<z.close.astype(float)),'sign']=-1;z.loc[valid&(z.prior>z.close.astype(float)),'sign']=1
    # STRICTLY PRE-PSEUDO-CONTACT local covariates: exclude current pseudo contact minute bar.
    ri=z.set_index('ts_event')
    z['pre30']=((ri.high.astype(float).rolling('30min',closed='left').max()-ri.low.astype(float).rolling('30min',closed='left').min())/TICK).to_numpy()
    z['pre30_complete']=(z.ts_event-pd.Timedelta(minutes=30)>=s)
    hi=z.high.astype(float).cummax().shift(1);lo=z.low.astype(float).cummin().shift(1);z['preavail']=(hi-lo)/TICK;z['prehistory']=z.index.to_numpy()>0
    ends=z.bar_end.to_numpy(dtype='datetime64[ns]'); ts=z.ts_event
    last_idx=np.arange(len(z))-1; last=np.full(len(z),np.nan); ok=last_idx>=0; last[ok]=z.close.astype(float).to_numpy()[last_idx[ok]]
    bound=(ts-pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]'); i5=np.searchsorted(ends,bound,side='right')-1;p5=np.full(len(z),np.nan);ok5=i5>=0;p5[ok5]=z.close.astype(float).to_numpy()[i5[ok5]]
    z['pre5']=z.sign.astype(float)*(last-p5)/TICK;z['pre5norm']=z.pre5/sr
    z['w15']=(z.bar_end+pd.Timedelta(minutes=15)<=e)
    ex=np.zeros(len(z),dtype=bool)
    for t in contacts: ex|=(np.abs((z.bar_end-t).dt.total_seconds().to_numpy())<=3600)
    z['excluded']=ex
    q=z[(z.sign!=0)&z.w15&(~z.excluded)&(z.minute>=0)].copy()
    q['control_candidate_id']=[hashlib.sha256(f'PRECTRL|{origin}|{source_date}|{t.isoformat()}|{iid}'.encode()).hexdigest()[:24] for t in q.ts_event]
    q['control_source_research_date']=source_date;q['control_eligible_next_research_date']=next_date;q['source_year']=pd.Timestamp(source_date).year;q['source_instrument_id']=iid;q['anchor_time_utc']=q.bar_end.astype(str);q['anchor_minute_of_session']=q.minute;q['anchor_30m_bin']=q.bin30;q['away_sign']=q.sign;q['source_range_ticks']=sr;q['pre30_range_precontact_ticks']=q.pre30;q['pre5_signed_move_precontact_norm']=q.pre5norm;q['preavailable_range_precontact_ticks']=q.preavail;q['prehistory_present']=q.prehistory;q['pre30_complete_precontact']=q.pre30_complete;q['control_origin']=origin;q['post_contact_values_used_for_matching']=False
    return q[['control_candidate_id','control_source_research_date','control_eligible_next_research_date','source_year','source_instrument_id','anchor_time_utc','anchor_minute_of_session','anchor_30m_bin','away_sign','source_range_ticks','pre30_range_precontact_ticks','pre5_signed_move_precontact_norm','preavailable_range_precontact_ticks','prehistory_present','pre30_complete_precontact','control_origin','post_contact_values_used_for_matching']]


def event_precontact(events:pd.DataFrame,n1:dict):
    rows=[]
    for e in events.to_dict('records'):
        d=str(e['source_research_date']);ss=n1[d];m=ss['m1'];m0=pd.Timestamp(e['m0_utc']);m0=m0.tz_localize('UTC') if m0.tzinfo is None else m0.tz_convert('UTC'); sign=int(float(e['away_sign']));
        pre=m[m.ts_event<m0].copy(); w30=pre[pre.ts_event>=m0-pd.Timedelta(minutes=30)]
        p30=(float(w30.high.max())-float(w30.low.min()))/TICK if len(w30) else np.nan
        pav=(float(pre.high.max())-float(pre.low.min()))/TICK if len(pre) else np.nan
        last=float(pre.iloc[-1].close) if len(pre) else np.nan
        z5=pre[pre.bar_end<=m0-pd.Timedelta(minutes=5)];p5=float(z5.iloc[-1].close) if len(z5) else np.nan
        mv=sign*(last-p5)/TICK if sign in (-1,1) and np.isfinite(last) and np.isfinite(p5) else np.nan
        sr=float(e['source_range_ticks']); rows.append({'level_id':str(e['level_id']),'source_research_date':d,'source_year':pd.Timestamp(d).year,'level_type':str(e['level_type']),'away_sign':sign,'m0_utc':m0.isoformat(),'anchor_minute_of_session':int(e['anchor_minute_of_session']),'anchor_30m_bin':int(e['anchor_minute_of_session'])//30,'source_range_ticks':sr,'pre30_range_precontact_ticks':p30,'pre5_signed_move_precontact_norm':mv/sr if np.isfinite(mv) and sr>0 else np.nan,'preavailable_range_precontact_ticks':pav,'prehistory_present':bool(len(pre)),'pre30_complete_precontact':bool(m0-pd.Timedelta(minutes=30)>=ss['start']),'w15_complete':pb(e['w15_complete']),'approach_defined':sign in (-1,1),'post_contact_values_used_for_matching':False})
    return pd.DataFrame(rows)


def build_controls(ctx,events,n1,source_ranges,sessions_path):
    contacts={};ev=events.copy();ev['t0']=pd.to_datetime(ev.t0_utc,utc=True)
    for nd,g in ev.groupby(ev.eligible_next_research_date.astype(str)):contacts[str(nd)]=list(g.t0)
    # Canonical 92 raw-N1 blocks rebuilt with strictly pre-pseudo-contact covariates.
    parts=[];blocks=[]
    for d,ss in n1.items():
        sr=float(source_ranges[d]);q=vector_control_features(ss['m1'],d,ss['next_date'],ss['iid'],sr,ss['start'],ss['end'],contacts.get(ss['next_date'],[]),'CANONICAL_RAW_N1_PRECONTACT');parts.append(q);blocks.append({'source_date':d,'next_date':ss['next_date'],'origin':'CANONICAL_RAW_N1_PRECONTACT','iid':ss['iid'],'source_range_ticks':sr,'candidate_rows':len(q)})
    # Expanded generic N0 blocks: same underlying iid on source and J+1, excluding every reserved non-RANK1 source/next date.
    sess=pd.read_csv(sessions_path);sess['research_trading_date']=sess.research_trading_date.astype(str);reserved=set(sess.loc[~sess.acquisition_stage.astype(str).eq('DEV_RANK1'),'research_trading_date']);original=set(n1)
    groups={d:g.copy().sort_values('ts_event') for d,g in ctx.groupby(ctx.gc_trade_date.astype(str),sort=True)};dates=sorted(groups)
    for i,d in enumerate(dates[:-1]):
        y=pd.Timestamp(d).year
        if y<2011 or y>2018:continue
        nd=dates[i+1]
        if d in reserved or nd in reserved or d in original:continue
        a,b=groups[d],groups[nd];ia=sorted(a.instrument_id.astype(str).unique());ib=sorted(b.instrument_id.astype(str).unique())
        if len(ia)!=1 or len(ib)!=1 or ia[0]!=ib[0]:continue
        iid=ia[0];sr=(float(a.high.max())-float(a.low.min()))/TICK
        if not np.isfinite(sr) or sr<=0:continue
        s,e=base.session_bounds(nd);b=b[(b.ts_event>=s)&(b.ts_event<e)].copy();
        if b.empty:continue
        q=vector_control_features(b,d,nd,iid,sr,s,e,contacts.get(nd,[]),'EXPANDED_N0_STABLE_IID_PRECONTACT');parts.append(q);blocks.append({'source_date':d,'next_date':nd,'origin':'EXPANDED_N0_STABLE_IID_PRECONTACT','iid':iid,'source_range_ticks':sr,'candidate_rows':len(q)})
    C=pd.concat(parts,ignore_index=True);return C,pd.DataFrame(blocks),reserved


def support(E,C,mode):
    grouped={(int(y),int(b),int(s)):g.copy() for (y,b,s),g in C.groupby(['source_year','anchor_30m_bin','away_sign'],sort=False)};rr=[]
    for e in E.to_dict('records'):
        sign=int(e['away_sign']);defined=bool(e['approach_defined']);minute=int(e['anchor_minute_of_session']);early=minute<30
        strict=pb(e['pre30_complete_precontact']) and np.isfinite(e['pre30_range_precontact_ticks']) and e['pre30_range_precontact_ticks']>0 and np.isfinite(e['pre5_signed_move_precontact_norm'])
        if mode=='STRICT':eligible=defined and pb(e['w15_complete']) and strict
        elif mode=='EARLY_AVAILABLE':eligible=defined and pb(e['w15_complete']) and (strict or (early and pb(e['prehistory_present']) and np.isfinite(e['preavailable_range_precontact_ticks']) and e['preavailable_range_precontact_ticks']>0))
        elif mode=='EARLY_SOURCE_ONLY':eligible=defined and pb(e['w15_complete']) and (strict or early)
        else:raise ValueError(mode)
        q=C.iloc[0:0]
        if eligible:
            q=grouped.get((int(e['source_year']),minute//30,sign),C.iloc[0:0]).copy();q=q[q.control_source_research_date.astype(str)!=str(e['source_research_date'])];q=q[ratio_mask(q.source_range_ticks,e['source_range_ticks'])]
            if len(q):
                if strict:
                    q=q[q.pre30_complete_precontact.map(pb)&q.pre30_range_precontact_ticks.notna()&q.pre5_signed_move_precontact_norm.notna()];q=q[ratio_mask(q.pre30_range_precontact_ticks,e['pre30_range_precontact_ticks'])]
                    q['d_local']=np.abs(np.log(q.pre30_range_precontact_ticks.astype(float)/float(e['pre30_range_precontact_ticks'])));q['d_move']=np.abs(q.pre5_signed_move_precontact_norm.astype(float)-float(e['pre5_signed_move_precontact_norm']))
                elif mode=='EARLY_AVAILABLE':
                    q=q[q.prehistory_present.map(pb)&q.preavailable_range_precontact_ticks.notna()];q=q[ratio_mask(q.preavailable_range_precontact_ticks,e['preavailable_range_precontact_ticks'])];q['d_local']=np.abs(np.log(q.preavailable_range_precontact_ticks.astype(float)/float(e['preavailable_range_precontact_ticks'])));q['d_move']=0.0
                else:q['d_local']=0.0;q['d_move']=0.0
            if len(q):
                q['d_source']=np.abs(np.log(q.source_range_ticks.astype(float)/float(e['source_range_ticks'])));q['d_minute']=np.abs(q.anchor_minute_of_session.astype(int)-minute);q['ts']=pd.to_datetime(q.anchor_time_utc,utc=True);sort=['d_local','d_source','d_move','d_minute','ts','control_source_research_date','source_instrument_id','control_candidate_id'];q=q.sort_values(sort,kind='mergesort').groupby('control_source_research_date',sort=False,as_index=False).head(1).sort_values(sort,kind='mergesort').head(K)
        n=int(q.control_source_research_date.nunique()) if len(q) else 0;rr.append({'level_id':e['level_id'],'source_research_date':e['source_research_date'],'source_year':int(e['source_year']),'approach_defined':defined,'eligible':eligible,'full_k5_match':n==5,'controls':n,'minute':minute})
    R=pd.DataFrame(rr);D=R[R.approach_defined];M=D[D.full_k5_match];ys=[]
    for y in range(2011,2019):g=D[D.source_year==y];m=g[g.full_k5_match];ys.append({'source_year':y,'defined_events':len(g),'matched_events':len(m),'match_rate':len(m)/len(g) if len(g) else 0,'matched_dates':m.source_research_date.nunique()})
    Y=pd.DataFrame(ys);rate=len(M)/len(D) if len(D) else 0;crit={'matched_events_ge_160':len(M)>=160,'matched_dates_ge_60':M.source_research_date.nunique()>=60,'every_source_year_matched_dates_ge_5':bool((Y.matched_dates>=5).all()),'defined_contact_full_match_rate_ge_0_85':rate>=.85,'every_source_year_full_match_rate_ge_0_75':bool((Y.match_rate>=.75).all())};return R,Y,{'mode':mode,'defined_events':len(D),'eligible_events':int(D.eligible.sum()),'matched_events':len(M),'matched_dates':int(M.source_research_date.nunique()),'match_rate':rate,'criteria':crit,'support_gate_pass':all(crit.values())}


def main():
    ap=argparse.ArgumentParser()
    for x in ['context-root','n1-root','n1-market-manifest','events','source-ranges','sessions','out']:ap.add_argument('--'+x,required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    marker,ctxp=base.find_context(Path(a.context_root));ctx=base.load_context(ctxp);parity,ps=base.parity_audit(ctx,Path(a.n1_root),a.n1_market_manifest);n1=load_n1_sessions(Path(a.n1_root),a.n1_market_manifest);events0=pd.read_csv(a.events);ranges=pd.read_csv(a.source_ranges);rm=ranges.set_index(ranges.source_research_date.astype(str)).source_range_ticks.astype(float).to_dict();E=event_precontact(events0,n1);C,B,res=build_controls(ctx,events0,n1,rm,a.sessions)
    results={};
    for mode in ['STRICT','EARLY_AVAILABLE','EARLY_SOURCE_ONLY']:
        r,y,s=support(E,C,mode);r.to_csv(out/f'support_{mode.lower()}.csv',index=False);y.to_csv(out/f'support_{mode.lower()}_by_year.csv',index=False);results[mode]=s
    parity.to_csv(out/'continuous_vs_raw_n1_parity.csv',index=False);E.to_csv(out/'treated_event_strict_precontact_context.csv',index=False);B.to_csv(out/'control_block_manifest.csv',index=False)
    z={'version':'COMEX_DEV_RANK1_NATIVE_REACTION_PRECONTACT_CONTROL_REPAIR_V1','post_contact_values_used_for_matching':False,'post_anchor_outcomes_read':False,'reaction_outcomes_computed':False,'market_data_api_called':False,'market_data_download_performed':False,'parity_summary':ps,'controls_total':len(C),'control_blocks':len(B),'reserved_non_dev_rank1_dates':len(res),'event_context_rows':len(E),'minute0_defined_events':int(((E.anchor_minute_of_session==0)&E.approach_defined).sum()),'early_defined_events':int(((E.anchor_minute_of_session<30)&E.approach_defined).sum()),'support':results,'event_context_sha256':base.sha256_file(out/'treated_event_strict_precontact_context.csv'),'control_blocks_sha256':base.sha256_file(out/'control_block_manifest.csv'),'notes':['The prior PREOUTCOME v1 matching covariates are superseded for execution because they could include the contact-minute bar after t0.','All local matching covariates in this audit end strictly before m0, the contact-minute start.','EARLY_AVAILABLE uses only session-open-to-m0 executed-price range when a treated event lacks 30 full pre-contact minutes; minute-0 events with no prehistory are not made eligible by that mode.','EARLY_SOURCE_ONLY is diagnostic only.','No reaction endpoint or post-contact price is used.']};(out/'precontact_control_repair.json').write_text(json.dumps(z,indent=2));print(json.dumps(z,indent=2))

if __name__=='__main__':main()
