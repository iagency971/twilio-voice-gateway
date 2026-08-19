#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
import databento as db

import build_comex_dev_rank1_event_features as feat
import audit_comex_native_reaction_expanded_controls as expanded

TICK=.10
K=5


def pb(v):
    if isinstance(v,(bool,np.bool_)): return bool(v)
    return str(v).strip().lower()=='true'


def sha256_file(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
    return h.hexdigest()


def load_dbn(path:Path):
    x=db.DBNStore.from_file(path).to_df().reset_index(drop=False)
    if 'ts_event' not in x.columns:x=x.rename(columns={x.columns[0]:'ts_event'})
    x['ts_event']=pd.to_datetime(x.ts_event,utc=True)
    return x.sort_values('ts_event').reset_index(drop=True)


def source_features(args, source_levels:pd.DataFrame, provenance:pd.DataFrame):
    req=pd.read_csv(args.dual_requests,dtype={'symbols':str});sessions=pd.read_csv(args.sessions);sessions=sessions[sessions.acquisition_stage.eq('DEV_RANK1')].copy();mapping=pd.read_csv(args.mapping,dtype={'v0_start_iid':str,'n0_start_iid':str});routing=pd.read_csv(args.routing,dtype={'v0_iid':str,'n0_iid':str})
    cand,_=feat.build_candidate_map(Path(args.source_new_root),Path(args.source_pilot_root),req,sessions,mapping);rt=routing.set_index(routing.research_trading_date.astype(str));reg=source_levels.groupby('source_research_date',sort=True).first().reset_index();prov=provenance.set_index(provenance.source_research_date.astype(str));rows=[]
    for r in reg.itertuples(index=False):
        d=str(r.source_research_date);rr=rt.loc[d];label=str(r.source_candidate_key);z=cand.get((d,label)) or cand.get((d,'N0')) or cand.get((d,'V0'));p=Path(z['path']) if z and z.get('path') else None
        if p is None:raise SystemExit(f'source raw missing {d}')
        x=load_dbn(p);s,e=feat.session_bounds(d);x=x[(x.ts_event>=s)&(x.ts_event<e)].copy();x['price']=pd.to_numeric(x.price,errors='coerce');x=x[x.price.notna()]
        if x.empty:raise SystemExit(f'empty source raw {d}')
        full=(float(x.price.max())-float(x.price.min()))/TICK;last=x[x.ts_event>=e-pd.Timedelta(minutes=30)];l30=(float(last.price.max())-float(last.price.min()))/TICK if len(last) else np.nan;iid=str(r.source_instrument_id)
        q=prov.loc[d]
        if str(q.source_instrument_id)!=iid or not np.isclose(full,float(q.source_range_ticks),rtol=0,atol=1e-8):raise SystemExit(f'source provenance parity fail {d}')
        rows.append({'source_research_date':d,'source_year':pd.Timestamp(d).year,'source_instrument_id':iid,'source_range_ticks':full,'source_last30_range_ticks':l30,'source_raw_file':p.name,'source_raw_sha256':sha256_file(p),'source_last30_known_before_j1':True,'same_raw_as_level_creation':True})
    return pd.DataFrame(rows)


def load_n1(root:Path,manifest_path:str):
    man=pd.read_csv(manifest_path,dtype={'source_instrument_id':str,'symbols':str});marks=expanded.read_n1_markers(root);out={}
    for r in man.itertuples(index=False):
        rid=str(r.market_request_id);mk,p=marks[rid];m=expanded.pre.prepare_m1(p,r.start,r.end);out[str(r.source_research_date)]={'m1':m,'start':expanded.pre.to_utc(r.start),'end':expanded.pre.to_utc(r.end),'next_date':str(r.eligible_next_research_date),'iid':str(r.source_instrument_id)}
    return out


def event_context(events:pd.DataFrame,n1:dict,sf:dict):
    rows=[]
    for e in events.to_dict('records'):
        d=str(e['source_research_date']);ss=n1[d];m=ss['m1'];m0=pd.Timestamp(e['m0_utc']);m0=m0.tz_localize('UTC') if m0.tzinfo is None else m0.tz_convert('UTC');sign=int(float(e['away_sign']));pre=m[m.ts_event<m0].copy();w30=pre[pre.ts_event>=m0-pd.Timedelta(minutes=30)];p30=(float(w30.high.max())-float(w30.low.min()))/TICK if len(w30) else np.nan;last=float(pre.iloc[-1].close) if len(pre) else np.nan;z5=pre[pre.bar_end<=m0-pd.Timedelta(minutes=5)];p5=float(z5.iloc[-1].close) if len(z5) else np.nan;mv=sign*(last-p5)/TICK if sign in (-1,1) and np.isfinite(last) and np.isfinite(p5) else np.nan;f=sf[d]
        rows.append({'level_id':str(e['level_id']),'source_research_date':d,'source_year':pd.Timestamp(d).year,'away_sign':sign,'approach_defined':sign in (-1,1),'anchor_minute_of_session':int(e['anchor_minute_of_session']),'anchor_30m_bin':int(e['anchor_minute_of_session'])//30,'source_range_ticks':float(f['source_range_ticks']),'source_last30_range_ticks':float(f['source_last30_range_ticks']),'pre30_range_precontact_ticks':p30,'pre5_signed_move_precontact_norm':mv/float(f['source_range_ticks']) if np.isfinite(mv) else np.nan,'pre30_complete_precontact':bool(m0-pd.Timedelta(minutes=30)>=ss['start']),'w15_complete':pb(e['w15_complete']),'post_contact_values_used_for_matching':False})
    return pd.DataFrame(rows)


def control_candidates_one(m1:pd.DataFrame,source_date:str,next_date:str,iid:str,sr:float,sl30:float,s:pd.Timestamp,e:pd.Timestamp,contacts:list[pd.Timestamp],origin:str,bar_open_fallback:bool):
    z=m1.sort_values('ts_event').copy().reset_index(drop=True)
    if 'open' not in z.columns:raise SystemExit('M1 open required for control fallback audit')
    z['bar_end']=z.ts_event+pd.Timedelta(minutes=1);z['minute']=((z.ts_event-s).dt.total_seconds()//60).astype(int);z['bin30']=(z.minute//30).astype(int)
    run=z.close.astype(float).ne(z.close.astype(float).shift()).cumsum();info=pd.DataFrame({'run':run,'v':z.close.astype(float),'end':z.bar_end}).groupby('run',sort=True).agg(v=('v','first'),last_end=('end','last'));info['pv']=info.v.shift(1);info['pe']=info.last_end.shift(1);z['prior']=run.map(info.pv);z['prior_end']=run.map(info.pe);age=(z.bar_end-z.prior_end).dt.total_seconds()/60;valid=z.prior.notna()&age.le(30);z['sign']=0;z.loc[valid&(z.prior<z.close.astype(float)),'sign']=-1;z.loc[valid&(z.prior>z.close.astype(float)),'sign']=1;z['sign_source']='PRIOR_DIFFERENT_M1_CLOSE'
    if bar_open_fallback:
        fb=z.sign.eq(0)&(np.abs(z.open.astype(float)-z.close.astype(float))>1e-9);z.loc[fb&(z.open.astype(float)<z.close.astype(float)),'sign']=-1;z.loc[fb&(z.open.astype(float)>z.close.astype(float)),'sign']=1;z.loc[fb,'sign_source']='CURRENT_CONTROL_MINUTE_OPEN'
    ri=z.set_index('ts_event');z['pre30']=((ri.high.astype(float).rolling('30min',closed='left').max()-ri.low.astype(float).rolling('30min',closed='left').min())/TICK).to_numpy();z['pre30_complete']=(z.ts_event-pd.Timedelta(minutes=30)>=s)
    ends=z.bar_end.to_numpy(dtype='datetime64[ns]');target=(z.ts_event-pd.Timedelta(minutes=5)).to_numpy(dtype='datetime64[ns]');i5=np.searchsorted(ends,target,side='right')-1;p5=np.full(len(z),np.nan);ok=i5>=0;p5[ok]=z.close.astype(float).to_numpy()[i5[ok]];lastidx=np.arange(len(z))-1;last=np.full(len(z),np.nan);ok2=lastidx>=0;last[ok2]=z.close.astype(float).to_numpy()[lastidx[ok2]];z['pre5']=z.sign.astype(float)*(last-p5)/TICK;z['pre5norm']=z.pre5/sr;z['w15']=(z.bar_end+pd.Timedelta(minutes=15)<=e);ex=np.zeros(len(z),bool)
    for t in contacts:ex|=(np.abs((z.bar_end-t).dt.total_seconds().to_numpy())<=3600)
    q=z[(z.sign!=0)&z.w15&(~ex)&(z.minute>=0)].copy();q['control_candidate_id']=[hashlib.sha256(f'SL30|{bar_open_fallback}|{source_date}|{t.isoformat()}|{iid}'.encode()).hexdigest()[:24] for t in q.ts_event];q['control_source_research_date']=source_date;q['source_year']=pd.Timestamp(source_date).year;q['source_instrument_id']=iid;q['anchor_time_utc']=q.bar_end.astype(str);q['anchor_minute_of_session']=q.minute;q['anchor_30m_bin']=q.bin30;q['away_sign']=q.sign;q['source_range_ticks']=sr;q['source_last30_range_ticks']=sl30;q['pre30_range_precontact_ticks']=q.pre30;q['pre5_signed_move_precontact_norm']=q.pre5norm;q['pre30_complete_precontact']=q.pre30_complete;q['control_origin']=origin;q['post_contact_values_used_for_matching']=False
    return q[['control_candidate_id','control_source_research_date','source_year','source_instrument_id','anchor_time_utc','anchor_minute_of_session','anchor_30m_bin','away_sign','sign_source','source_range_ticks','source_last30_range_ticks','pre30_range_precontact_ticks','pre5_signed_move_precontact_norm','pre30_complete_precontact','control_origin','post_contact_values_used_for_matching']]


def build_controls(ctx:pd.DataFrame,n1:dict,sf:dict,events_raw:pd.DataFrame,sessions_path:str,bar_open_fallback:bool):
    ev=events_raw.copy();ev['t0']=pd.to_datetime(ev.t0_utc,utc=True);known={str(k):list(g.t0) for k,g in ev.groupby(ev.eligible_next_research_date.astype(str))};parts=[];blocks=[]
    for d,ss in n1.items():
        f=sf[d];q=control_candidates_one(ss['m1'],d,ss['next_date'],ss['iid'],float(f['source_range_ticks']),float(f['source_last30_range_ticks']),ss['start'],ss['end'],known.get(ss['next_date'],[]),'CANONICAL_RAW_N1',bar_open_fallback);parts.append(q);blocks.append({'source_date':d,'origin':'CANONICAL_RAW_N1','candidate_rows':len(q)})
    sess=pd.read_csv(sessions_path);sess['research_trading_date']=sess.research_trading_date.astype(str);reserved=set(sess.loc[~sess.acquisition_stage.astype(str).eq('DEV_RANK1'),'research_trading_date']);original=set(n1);groups={d:g.copy().sort_values('ts_event') for d,g in ctx.groupby(ctx.gc_trade_date.astype(str),sort=True)};dates=sorted(groups)
    for i,d in enumerate(dates[:-1]):
        y=pd.Timestamp(d).year
        if y<2011 or y>2018:continue
        nd=dates[i+1]
        if d in reserved or nd in reserved or d in original:continue
        a,b=groups[d],groups[nd];ia=sorted(a.instrument_id.astype(str).unique());ib=sorted(b.instrument_id.astype(str).unique())
        if len(ia)!=1 or len(ib)!=1 or ia[0]!=ib[0]:continue
        iid=ia[0];sr=(float(a.high.max())-float(a.low.min()))/TICK;s,e=feat.session_bounds(d);al=a[(a.ts_event>=e-pd.Timedelta(minutes=30))&(a.ts_event<e)];sl30=(float(al.high.max())-float(al.low.min()))/TICK if len(al) else np.nan
        if not (np.isfinite(sr) and sr>0 and np.isfinite(sl30) and sl30>0):continue
        ns,ne=feat.session_bounds(nd);b=b[(b.ts_event>=ns)&(b.ts_event<ne)].copy();
        if b.empty:continue
        q=control_candidates_one(b,d,nd,iid,sr,sl30,ns,ne,known.get(nd,[]),'EXPANDED_N0_STABLE_IID',bar_open_fallback);parts.append(q);blocks.append({'source_date':d,'origin':'EXPANDED_N0_STABLE_IID','candidate_rows':len(q)})
    return pd.concat(parts,ignore_index=True),pd.DataFrame(blocks),reserved


def rmask(s,b):
    x=pd.to_numeric(s,errors='coerce');b=float(b);return x.notna()&(x>0)&(b>0)&(x/b>=.5)&(x/b<=2.0)


def support(E,C):
    grouped={(int(y),int(b),int(s)):g.copy() for (y,b,s),g in C.groupby(['source_year','anchor_30m_bin','away_sign'],sort=False)};rr=[]
    for e in E.to_dict('records'):
        sign=int(e['away_sign']);defined=pb(e['approach_defined']);minute=int(e['anchor_minute_of_session']);early=minute<30;strict=pb(e['pre30_complete_precontact']) and np.isfinite(e['pre30_range_precontact_ticks']) and e['pre30_range_precontact_ticks']>0 and np.isfinite(e['pre5_signed_move_precontact_norm']);eligible=defined and pb(e['w15_complete']) and (strict or early);q=C.iloc[0:0]
        if eligible:
            q=grouped.get((int(e['source_year']),minute//30,sign),C.iloc[0:0]).copy();q=q[q.control_source_research_date.astype(str)!=str(e['source_research_date'])];q=q[rmask(q.source_range_ticks,e['source_range_ticks'])]
            if len(q) and strict:
                q=q[q.pre30_complete_precontact.map(pb)&q.pre30_range_precontact_ticks.notna()&q.pre5_signed_move_precontact_norm.notna()];q=q[rmask(q.pre30_range_precontact_ticks,e['pre30_range_precontact_ticks'])];q['d_local']=np.abs(np.log(q.pre30_range_precontact_ticks.astype(float)/float(e['pre30_range_precontact_ticks'])));q['d_move']=np.abs(q.pre5_signed_move_precontact_norm.astype(float)-float(e['pre5_signed_move_precontact_norm']))
            elif len(q):
                q=q[q.source_last30_range_ticks.notna()];q=q[rmask(q.source_last30_range_ticks,e['source_last30_range_ticks'])];q['d_local']=np.abs(np.log(q.source_last30_range_ticks.astype(float)/float(e['source_last30_range_ticks'])));q['d_move']=0.0
            if len(q):
                q['d_source']=np.abs(np.log(q.source_range_ticks.astype(float)/float(e['source_range_ticks'])));q['d_minute']=np.abs(q.anchor_minute_of_session.astype(int)-minute);q['ts']=pd.to_datetime(q.anchor_time_utc,utc=True);sort=['d_local','d_source','d_move','d_minute','ts','control_source_research_date','source_instrument_id','control_candidate_id'];q=q.sort_values(sort,kind='mergesort').groupby('control_source_research_date',sort=False,as_index=False).head(1).sort_values(sort,kind='mergesort').head(K)
        n=int(q.control_source_research_date.nunique()) if len(q) else 0;rr.append({'level_id':e['level_id'],'source_research_date':e['source_research_date'],'source_year':int(e['source_year']),'minute':minute,'defined':defined,'eligible':eligible,'controls':n,'full_k5':n==5})
    R=pd.DataFrame(rr);D=R[R.defined];M=D[D.full_k5];ys=[]
    for y in range(2011,2019):g=D[D.source_year==y];m=g[g.full_k5];ys.append({'source_year':y,'defined_events':len(g),'matched_events':len(m),'match_rate':len(m)/len(g) if len(g) else 0,'matched_dates':m.source_research_date.nunique()})
    Y=pd.DataFrame(ys);rate=len(M)/len(D) if len(D) else 0;crit={'matched_events_ge_160':len(M)>=160,'matched_dates_ge_60':M.source_research_date.nunique()>=60,'every_source_year_matched_dates_ge_5':bool((Y.matched_dates>=5).all()),'defined_contact_full_match_rate_ge_0_85':rate>=.85,'every_source_year_full_match_rate_ge_0_75':bool((Y.match_rate>=.75).all())};return R,Y,{'defined_events':len(D),'eligible_events':int(D.eligible.sum()),'matched_events':len(M),'matched_dates':int(M.source_research_date.nunique()),'match_rate':rate,'criteria':crit,'support_gate_pass':all(crit.values())}


def main():
    ap=argparse.ArgumentParser();
    for x in ['source-new-root','source-pilot-root','dual-requests','sessions','mapping','routing','source-levels','source-provenance','context-root','n1-root','n1-market-manifest','events','out']:ap.add_argument('--'+x,required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);levels=pd.read_csv(a.source_levels,dtype={'source_instrument_id':str});prov=pd.read_csv(a.source_provenance,dtype={'source_instrument_id':str});SF=source_features(a,levels,prov);sf=SF.set_index(SF.source_research_date.astype(str)).to_dict('index');n1=load_n1(Path(a.n1_root),a.n1_market_manifest);events0=pd.read_csv(a.events);E=event_context(events0,n1,sf);marker,ctxp=expanded.find_context(Path(a.context_root));ctx=expanded.load_context(ctxp);parity,ps=expanded.parity_audit(ctx,Path(a.n1_root),a.n1_market_manifest)
    results={};block_info={}
    for name,fb in [('PRIOR_CLOSE_ONLY',False),('BAR_OPEN_FALLBACK',True)]:
        C,B,res=build_controls(ctx,n1,sf,events0,a.sessions,fb);R,Y,S=support(E,C);R.to_csv(out/f'support_{name.lower()}.csv',index=False);Y.to_csv(out/f'support_{name.lower()}_by_year.csv',index=False);B.to_csv(out/f'blocks_{name.lower()}.csv',index=False);results[name]=S;block_info[name]={'control_rows':len(C),'blocks':len(B),'reserved_non_dev_rank1_dates':len(res),'bar_open_fallback':fb}
    SF.to_csv(out/'source_last30_provenance.csv',index=False);E.to_csv(out/'event_source_last30_context.csv',index=False);parity.to_csv(out/'continuous_vs_raw_n1_parity.csv',index=False)
    z={'version':'COMEX_DEV_RANK1_NATIVE_REACTION_SOURCE_LAST30_FALLBACK_V1','post_contact_values_used_for_matching':False,'post_anchor_outcomes_read':False,'reaction_outcomes_computed':False,'market_data_api_called':False,'market_data_download_performed':False,'source_sessions':len(SF),'source_last30_all_positive':bool((SF.source_last30_range_ticks>0).all()),'parity_summary':ps,'support':results,'control_structure':block_info,'source_last30_sha256':sha256_file(out/'source_last30_provenance.csv'),'event_context_sha256':sha256_file(out/'event_source_last30_context.csv'),'notes':['Mature contacts use J+1 local 30m range ending strictly before contact-minute start m0.','Early contacts use source-session final-30m range, fully known before J+1, plus full source-session range.','PRIOR_CLOSE_ONLY retains the Pro pseudo-approach control rule exactly.','BAR_OPEN_FALLBACK changes only control pseudo-approach when no prior different M1 close exists; it uses the already-completed control minute open relative to its close before the post-anchor W15 outcome and requires Pro approval if adopted.','No contact-minute value from the treated event is used in matching.','No W15 reaction outcome is read or computed.']};(out/'source_last30_fallback.json').write_text(json.dumps(z,indent=2));print(json.dumps(z,indent=2))
if __name__=='__main__':main()
