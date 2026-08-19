#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import databento as db

import build_comex_native_reaction_v1_preoutcome_manifests as pre
import build_comex_dev_rank1_event_features as feat

NY = ZoneInfo('America/New_York')
K = 5
TICK = 0.10


def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()


def parse_bool(v) -> bool:
    if isinstance(v,(bool,np.bool_)): return bool(v)
    return str(v).strip().lower()=='true'


def find_context(root: Path):
    found=[]
    for p in root.rglob('*.json'):
        try: z=json.loads(p.read_text())
        except Exception: continue
        if z.get('request_type')=='CONTINUOUS_OHLCV_CONTEXT':
            raw=z.get('raw_file'); qs=list(root.rglob(str(raw))) if raw else []
            if len(qs)==1: found.append((z,qs[0]))
    if len(found)!=1: raise SystemExit(f'expected one continuous context marker, got {len(found)}')
    z,p=found[0]
    if z.get('sha256') and sha256_file(p)!=z['sha256']: raise SystemExit('continuous context raw SHA mismatch')
    return z,p


def load_context(path: Path) -> pd.DataFrame:
    x=db.DBNStore.from_file(path).to_df().reset_index(drop=False)
    if 'ts_event' not in x.columns: x=x.rename(columns={x.columns[0]:'ts_event'})
    x['ts_event']=pd.to_datetime(x.ts_event,utc=True)
    need=['open','high','low','close','volume','instrument_id']
    miss=[c for c in need if c not in x.columns]
    if miss: raise SystemExit(f'context missing {miss}')
    for c in ['open','high','low','close','volume']: x[c]=pd.to_numeric(x[c],errors='coerce')
    x=x[x[['open','high','low','close']].notna().all(axis=1)].copy()
    x['instrument_id']=x.instrument_id.astype(str)
    feat.assign_gc_session(x)
    x=x[x.gc_session_valid].copy()
    x['bar_end']=x.ts_event+pd.Timedelta(minutes=1)
    return x.sort_values('ts_event').reset_index(drop=True)


def read_n1_markers(root: Path):
    out={}
    for p in root.rglob('*.json'):
        try:z=json.loads(p.read_text())
        except Exception:continue
        rid=z.get('market_request_id'); raw=z.get('raw_file')
        if rid and raw:
            qs=list(root.rglob(str(raw)))
            if len(qs)==1: out[str(rid)]=(z,qs[0])
    return out


def parity_audit(ctx: pd.DataFrame, n1_root: Path, n1_manifest_path: str):
    man=pd.read_csv(n1_manifest_path,dtype={'symbols':str,'source_instrument_id':str})
    marks=read_n1_markers(n1_root)
    rows=[]
    for r in man.itertuples(index=False):
        rid=str(r.market_request_id); iid=str(r.source_instrument_id)
        if rid not in marks: raise SystemExit(f'N1 marker missing {rid}')
        mk,raw=marks[rid]
        m=pre.prepare_m1(raw,r.start,r.end)
        s,e=pre.to_utc(r.start),pre.to_utc(r.end)
        q=ctx[(ctx.ts_event>=s)&(ctx.ts_event<e)].copy()
        iids=sorted(q.instrument_id.unique().tolist())
        stable=(len(iids)==1 and iids[0]==iid)
        exact=False; common=0; n1_rows=len(m); ctx_rows=len(q)
        if stable:
            a=m[['ts_event','open','high','low','close','volume']].copy() if 'volume' in m.columns else m[['ts_event','open','high','low','close']].copy()
            b=q[['ts_event','open','high','low','close','volume']].copy()
            common=len(set(a.ts_event).intersection(set(b.ts_event)))
            z=a.merge(b,on='ts_event',how='outer',suffixes=('_n1','_ctx'),indicator=True)
            exact=bool((z['_merge']=='both').all())
            for c in ['open','high','low','close']:
                exact=exact and bool(np.allclose(z[f'{c}_n1'],z[f'{c}_ctx'],rtol=0,atol=1e-9,equal_nan=True))
            if 'volume_n1' in z.columns:
                exact=exact and bool(np.allclose(z['volume_n1'],z['volume_ctx'],rtol=0,atol=1e-9,equal_nan=True))
        rows.append({'source_research_date':str(r.source_research_date),'eligible_next_research_date':str(r.eligible_next_research_date),'source_instrument_id':iid,'context_iids':'+'.join(iids),'context_same_single_iid':stable,'n1_rows':n1_rows,'context_rows':ctx_rows,'common_rows':common,'exact_ohlcv_parity_if_stable':exact})
    d=pd.DataFrame(rows)
    stable=d[d.context_same_single_iid]
    return d, {'n1_blocks':len(d),'stable_same_iid_blocks':len(stable),'stable_blocks_exact_parity':int(stable.exact_ohlcv_parity_if_stable.sum()),'stable_parity_all_pass':bool(len(stable)>0 and stable.exact_ohlcv_parity_if_stable.all())}


def session_bounds(date: str):
    return feat.session_bounds(date)


def pseudo_approach(m1: pd.DataFrame, anchor: pd.Timestamp, anchor_price: float):
    return pre.pseudo_approach(m1,anchor,anchor_price)


def pre_features(m1: pd.DataFrame, anchor: pd.Timestamp, sign: int, anchor_price: float):
    return pre.pre_anchor_features(m1,anchor,sign,anchor_price)


def build_generic_controls(ctx: pd.DataFrame, events: pd.DataFrame, sessions_path: str, original_source_dates: set[str]):
    sess=pd.read_csv(sessions_path)
    sess['research_trading_date']=sess.research_trading_date.astype(str)
    stage_counts=sess.acquisition_stage.astype(str).value_counts().to_dict()
    reserved=set(sess.loc[~sess.acquisition_stage.astype(str).eq('DEV_RANK1'),'research_trading_date'])
    # Build stable N0 session map from the already-owned continuous context.
    groups={d:g.copy().sort_values('ts_event') for d,g in ctx.groupby(ctx.gc_trade_date.astype(str),sort=True)}
    dates=sorted(groups)
    known_by_next={}
    ev=events.copy(); ev['t0']=pd.to_datetime(ev.t0_utc,utc=True)
    for nd,g in ev.groupby(ev.eligible_next_research_date.astype(str)):
        known_by_next[str(nd)]=list(g.t0)
    rows=[]; blocks=[]
    for i,d in enumerate(dates[:-1]):
        y=pd.Timestamp(d).year
        if y<2011 or y>2018: continue
        nd=dates[i+1]
        # Strictly avoid any source/next date explicitly reserved for a non-RANK1 block.
        if d in reserved or nd in reserved: continue
        # Existing native source dates stay on their canonical raw-control implementation.
        if d in original_source_dates: continue
        a,b=groups[d],groups[nd]
        ia=sorted(a.instrument_id.unique().tolist()); ib=sorted(b.instrument_id.unique().tolist())
        stable=(len(ia)==1 and len(ib)==1 and ia[0]==ib[0])
        if not stable: continue
        iid=ia[0]
        sr=(float(a.high.max())-float(a.low.min()))/TICK
        if not np.isfinite(sr) or sr<=0: continue
        s,e=session_bounds(nd)
        b=b[(b.ts_event>=s)&(b.ts_event<e)].copy()
        if b.empty: continue
        blocks.append({'control_source_research_date':d,'control_eligible_next_research_date':nd,'source_year':y,'source_instrument_id':iid,'source_range_ticks':sr,'source_rows':len(a),'next_rows':len(b),'same_iid_source_and_next':True,'reserved_date_excluded':False})
        contacts=known_by_next.get(nd,[])
        for r in b.itertuples(index=False):
            bar_start=r.ts_event; anchor=r.bar_end
            if anchor+pd.Timedelta(minutes=15)>e: continue
            if any(abs((anchor-t).total_seconds())<=60*60 for t in contacts): continue
            price=float(r.close)
            approach,sign,prior,src=pseudo_approach(b,anchor,price)
            if sign==0: continue
            minute=int((bar_start-s).total_seconds()//60)
            if minute<0: continue
            pre30_complete=bool(anchor-pd.Timedelta(minutes=30)>=s)
            pf=pre_features(b,anchor,sign,price)
            p30=float(pf.get('pre30_range_ticks',np.nan)) if pre30_complete else np.nan
            mv=float(pf.get('pre5_signed_move_ticks',np.nan))
            mvn=mv/sr if np.isfinite(mv) else np.nan
            cid=hashlib.sha256(f'CTXCTRL|{d}|{nd}|{bar_start.isoformat()}|{iid}'.encode()).hexdigest()[:24]
            rows.append({'control_candidate_id':cid,'control_source_research_date':d,'control_eligible_next_research_date':nd,'year':y,'source_instrument_id':iid,'anchor_bar_start_utc':bar_start.isoformat(),'anchor_time_utc':anchor.isoformat(),'anchor_price':price,'approach':approach,'away_sign':int(sign),'approach_prior_price':prior,'approach_source':src,'anchor_minute_of_session':minute,'anchor_30m_bin':minute//30,'source_range_ticks':sr,'pre30_range_ticks':p30,'pre5_signed_move_ticks':mv,'pre5_signed_move_norm':mvn,'excluded_native_contact_pm60':False,'pre30_complete':pre30_complete,'w15_complete':True,'post_anchor_reaction_values_read':False,'control_origin':'OWNED_GC_N0_CONTINUOUS_UNADJUSTED_STABLE_IID'})
    return pd.DataFrame(rows),pd.DataFrame(blocks),reserved,stage_counts


def ratio_ok(a,b,lo=.5,hi=2.0):
    return bool(np.isfinite(a) and np.isfinite(b) and a>0 and b>0 and lo<=a/b<=hi)


def support(events: pd.DataFrame, controls: pd.DataFrame, early_fallback: bool):
    E=events.copy(); E['source_year']=pd.to_datetime(E.source_research_date).dt.year
    C=controls.copy(); C['source_year']=pd.to_datetime(C.control_source_research_date).dt.year
    rr=[]
    for e in E.to_dict('records'):
        sign=int(float(e['away_sign'])); defined=sign in (-1,1); minute=int(e['anchor_minute_of_session']); early=minute<30
        strict_cov=parse_bool(e['pre30_complete']) and np.isfinite(float(e['pre30_range_ticks'])) and float(e['pre30_range_ticks'])>0 and np.isfinite(float(e['pre5_signed_move_norm']))
        eligible=defined and parse_bool(e['w15_complete']) and float(e['source_range_ticks'])>0 and (strict_cov or (early_fallback and early))
        q=C.iloc[0:0].copy()
        if eligible:
            q=C[(C.source_year==int(e['source_year']))&(C.anchor_30m_bin.astype(int)==minute//30)&(C.away_sign.astype(int)==sign)&(C.control_source_research_date.astype(str)!=str(e['source_research_date']))].copy()
            if len(q): q=q[q.source_range_ticks.map(lambda v:ratio_ok(float(v),float(e['source_range_ticks'])))].copy()
            if len(q) and not (early_fallback and early):
                q=q[q.pre30_complete.map(parse_bool)&q.pre30_range_ticks.notna()&q.pre5_signed_move_norm.notna()].copy()
                q=q[q.pre30_range_ticks.map(lambda v:ratio_ok(float(v),float(e['pre30_range_ticks'])))].copy()
            if len(q):
                if early_fallback and early:
                    q['d_pre30_log']=0.0; q['d_pre5_norm']=0.0
                else:
                    q['d_pre30_log']=np.abs(np.log(q.pre30_range_ticks.astype(float)/float(e['pre30_range_ticks'])))
                    q['d_pre5_norm']=np.abs(q.pre5_signed_move_norm.astype(float)-float(e['pre5_signed_move_norm']))
                q['d_source_log']=np.abs(np.log(q.source_range_ticks.astype(float)/float(e['source_range_ticks'])))
                q['d_minute']=np.abs(q.anchor_minute_of_session.astype(int)-minute)
                q['anchor_ts_sort']=pd.to_datetime(q.anchor_time_utc,utc=True)
                sort=['d_pre30_log','d_source_log','d_pre5_norm','d_minute','anchor_ts_sort','control_source_research_date','source_instrument_id','control_candidate_id']
                q=q.sort_values(sort,kind='mergesort').groupby('control_source_research_date',sort=False,as_index=False).head(1).sort_values(sort,kind='mergesort').head(K)
        n=int(q.control_source_research_date.nunique()) if len(q) else 0
        rr.append({'level_id':str(e['level_id']),'source_research_date':str(e['source_research_date']),'source_year':int(e['source_year']),'approach_defined':defined,'event_eligible':eligible,'eligible_control_dates':n,'full_k5_match':n==K})
    R=pd.DataFrame(rr); D=R[R.approach_defined]; M=D[D.full_k5_match]
    ys=[]
    for y in range(2011,2019):
        g=D[D.source_year==y]; m=g[g.full_k5_match]
        ys.append({'source_year':y,'defined_events':len(g),'matched_events':len(m),'match_rate':len(m)/len(g) if len(g) else 0,'matched_dates':m.source_research_date.nunique()})
    Y=pd.DataFrame(ys)
    rate=len(M)/len(D) if len(D) else 0
    crit={'matched_events_ge_160':len(M)>=160,'matched_dates_ge_60':M.source_research_date.nunique()>=60,'every_source_year_matched_dates_ge_5':bool((Y.matched_dates>=5).all()),'defined_contact_full_match_rate_ge_0_85':rate>=.85,'every_source_year_full_match_rate_ge_0_75':bool((Y.match_rate>=.75).all())}
    return R,Y,{'defined_events':len(D),'event_eligible':int(D.event_eligible.sum()),'full_k5_matched_events':len(M),'full_k5_matched_dates':int(M.source_research_date.nunique()),'full_match_rate':rate,'criteria':crit,'support_gate_pass':all(crit.values())}


def main():
    ap=argparse.ArgumentParser()
    for x in ['context-root','n1-root','n1-market-manifest','events','existing-controls','sessions','out']: ap.add_argument('--'+x,required=True)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    marker,ctx_path=find_context(Path(a.context_root)); ctx=load_context(ctx_path)
    parity,parity_summary=parity_audit(ctx,Path(a.n1_root),a.n1_market_manifest)
    events=pd.read_csv(a.events); existing=pd.read_csv(a.existing_controls,compression='gzip')
    existing['control_origin']='CANONICAL_92_RAW_N1'
    original=set(events.source_research_date.astype(str))
    generic,blocks,reserved,stages=build_generic_controls(ctx,events,a.sessions,original)
    combined=pd.concat([existing,generic],ignore_index=True,sort=False)
    if combined.control_candidate_id.duplicated().any(): raise SystemExit('combined control IDs duplicated')
    r0,y0,s0=support(events,combined,False); r1,y1,s1=support(events,combined,True)
    parity.to_csv(out/'continuous_vs_raw_n1_parity.csv',index=False); blocks.to_csv(out/'expanded_control_blocks.csv',index=False)
    r0.to_csv(out/'support_strict_pro.csv',index=False); y0.to_csv(out/'support_strict_pro_by_year.csv',index=False)
    r1.to_csv(out/'support_early_fallback.csv',index=False); y1.to_csv(out/'support_early_fallback_by_year.csv',index=False)
    # Do not publish the full expanded candidate table; only its SHA and structural counts are needed for this feasibility gate.
    generic.to_csv(out/'expanded_generic_control_candidates.csv.gz',index=False,compression='gzip')
    manifest={'version':'COMEX_DEV_RANK1_NATIVE_REACTION_EXPANDED_CONTROL_FEASIBILITY_V1','post_anchor_outcomes_read':False,'reaction_outcomes_computed':False,'mfe_mae_computed':False,'market_data_api_called':False,'market_data_download_performed':False,'continuous_context_request_id':marker.get('request_id'),'continuous_context_raw_sha256':sha256_file(ctx_path),'continuous_context_prices_vendor_semantics':'original unadjusted prices; record instrument_id identifies actual mapped tradable instrument','continuous_context_records':len(ctx),'continuous_context_unique_instrument_ids':int(ctx.instrument_id.nunique()),'parity_summary':parity_summary,'session_stage_counts':{str(k):int(v) for k,v in stages.items()},'reserved_non_dev_rank1_dates':len(reserved),'generic_stable_same_iid_blocks':len(blocks),'generic_control_candidates':len(generic),'existing_control_candidates':len(existing),'combined_control_candidates':len(combined),'strict_pro_support':s0,'early_fallback_support':s1,'generic_candidates_sha256':sha256_file(out/'expanded_generic_control_candidates.csv.gz'),'blocks_sha256':sha256_file(out/'expanded_control_blocks.csv'),'notes':['Generic blocks use only already-owned GC.n.0 M1 records whose Databento instrument_id is constant across source session J and next session J+1.','Any source or next date explicitly assigned to a non-DEV_RANK1 acquisition stage is excluded.','Original 92 native source dates remain on their canonical raw N1 control implementation and are not duplicated by the generic pool.','No post-anchor reaction value is read or computed.','Strict-Pro support preserves K=5, exact source year, 30-minute bin, approach sign, 0.5-2 source-range and pre30-range calipers.','Early-fallback sensitivity changes only the pre30/pre5 requirement for treated events in the first 30 minutes and their early controls; it is not frozen without Pro review.']}
    (out/'expanded_control_feasibility.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2))

if __name__=='__main__': main()
