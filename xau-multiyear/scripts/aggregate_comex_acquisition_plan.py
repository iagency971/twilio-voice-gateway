#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

NY=ZoneInfo('America/New_York')
FVG_TIERS=(1,2,4)
SESSION_TIERS=(2,3,4)
GAP_MINUTES=(0,5,15,30,60)
FVG_SEED='COMEX_FVG_SAMPLE_V1_SEED_971'


def h(*parts): return hashlib.sha256('|'.join(str(x) for x in parts).encode()).hexdigest()

def qband(s,q=4):
    s=pd.to_numeric(s,errors='coerce'); out=pd.Series(-1,index=s.index,dtype='int16'); good=s.notna()
    if good.sum()<q: out.loc[good]=0; return out
    out.loc[good]=pd.qcut(s.loc[good].rank(method='first'),q,labels=False,duplicates='drop').astype('int16')
    return out

def merge_windows(df,gap_min=0):
    if df.empty:return pd.DataFrame(columns=['start','end'])
    x=df[['start','end']].copy(); x['start']=pd.to_datetime(x.start,utc=True); x['end']=pd.to_datetime(x.end,utc=True)
    x=x.sort_values(['start','end']).reset_index(drop=True); gap=pd.Timedelta(minutes=gap_min)
    out=[]; s=x.iloc[0].start; e=x.iloc[0].end
    for r in x.iloc[1:].itertuples():
        if r.start<=e+gap: e=max(e,r.end)
        else: out.append((s,e)); s=r.start; e=r.end
    out.append((s,e)); return pd.DataFrame(out,columns=['start','end'])

def session_envelope(date_str):
    d=pd.Timestamp(date_str); prev=(d-pd.Timedelta(days=1)).date(); cur=d.date()
    # Deliberately wider than any expected standard-GC maintenance boundary.
    # Actual session is trimmed after trade data are available, from the observed exchange break.
    return (pd.Timestamp(f'{prev} 17:00:00',tz=NY).tz_convert('UTC'),pd.Timestamp(f'{cur} 18:00:00',tz=NY).tz_convert('UTC'))

def mins(df):
    if df.empty:return 0.0
    return float(((pd.to_datetime(df.end,utc=True)-pd.to_datetime(df.start,utc=True)).dt.total_seconds()/60).sum())

def dump_frontier(out,kind,tier_a,tier_b,base):
    rows=[]
    for gap in GAP_MINUTES:
        mw=merge_windows(base,gap); mw.to_csv(out/f'{kind}_a{tier_a}_b{tier_b}_gap{gap}m.csv',index=False)
        rows.append({'kind':kind,'tier_a':tier_a,'tier_b':tier_b,'merge_gap_min':gap,'raw_windows':len(base),'merged_windows':len(mw),'covered_minutes':mins(mw),'covered_days':mins(mw)/1440})
    return rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    root=Path(a.root); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    manifests=[]; event_files=list(root.rglob('events.csv.gz')); session_files=list(root.rglob('session_candidates.csv'))
    for p in root.rglob('manifest.json'):
        try:
            m=json.loads(p.read_text());
            if m.get('version')=='COMEX_EVENT_TIMING_V1':manifests.append(m)
        except Exception:pass
    if not event_files:raise SystemExit('no annual event files')
    pd.DataFrame(manifests).sort_values('year').to_csv(out/'annual_manifest.csv',index=False)

    ev=pd.concat([pd.read_csv(p,compression='gzip',low_memory=False) for p in event_files],ignore_index=True)
    for c in ['contact_time','uniform_tick_start','uniform_tick_end']:ev[c]=pd.to_datetime(ev[c],utc=True)
    isf=ev.fvg_only.astype(str).str.lower().eq('true')
    # Recompute FVG-only quartiles inside each year before hashing. This is outcome-blind and supersedes annual provisional ranks.
    ev['fvg_sigma_q']=-1; ev['fvg_width_q']=-1; ev['fvg_rank_frozen']=np.nan; ev['fvg_hash_frozen']=''
    for y,idx in ev[isf].groupby('year').groups.items():
        ev.loc[idx,'fvg_sigma_q']=qband(ev.loc[idx,'sigma60'],4).astype(int)
        ev.loc[idx,'fvg_width_q']=qband(ev.loc[idx,'zone_width_sigma'],4).astype(int)
    idxs=ev.index[isf]
    ev.loc[idxs,'fvg_hash_frozen']=[h(FVG_SEED,r.year,r.session,r.side,r.fvg_sigma_q,r.fvg_width_q,r.event_uid) for r in ev.loc[idxs].itertuples()]
    strata=['year','session','side','fvg_sigma_q','fvg_width_q']
    ev.loc[idxs,'fvg_rank_frozen']=ev.loc[idxs].groupby(strata)['fvg_hash_frozen'].rank(method='first')
    ev.to_csv(out/'canonical_events_all.csv.gz',index=False,compression='gzip')

    model_prefixes=['passive_touch','touch_next_open','clean_rejection','failed_auction','acceptance_retest','reclaim_pullback']
    counts=[]
    for (y,sp),g in ev.groupby(['year','temporal_split']):
        r={'year':int(y),'split':sp,'events':len(g),'fvg_only':int(g.fvg_only.astype(str).str.lower().eq('true').sum())}
        for m in model_prefixes:r[m+'_eligible']=int(g[m+'_eligible'].astype(str).str.lower().eq('true').sum())
        counts.append(r)
    pd.DataFrame(counts).sort_values('year').to_csv(out/'event_counts_by_year.csv',index=False)

    fvg_plan=[]
    for k in FVG_TIERS:
        q=ev[isf&(ev.fvg_rank_frozen<=k)]
        for sp,g in q.groupby('temporal_split'):fvg_plan.append({'tier_rank_per_stratum':k,'split':sp,'events':len(g),'years':g.year.nunique()})
    pd.DataFrame(fvg_plan).to_csv(out/'fvg_sampling_tiers.csv',index=False)

    sessions=pd.concat([pd.read_csv(p) for p in session_files if p.stat().st_size>0],ignore_index=True) if session_files else pd.DataFrame()
    if len(sessions):
        sessions['panel_rank']=pd.to_numeric(sessions.panel_rank,errors='coerce')
        ysplit=ev[['year','temporal_split']].drop_duplicates().set_index('year').temporal_split.to_dict(); sessions['temporal_split']=sessions.year.map(ysplit)
        sessions.to_csv(out/'session_candidates_all.csv',index=False)
        sr=[]
        for k in SESSION_TIERS:
            q=sessions[sessions.panel_rank<=k]
            for sp,g in q.groupby('temporal_split'):sr.append({'tier_rank_per_stratum':k,'split':sp,'sessions':len(g),'years':g.year.nunique()})
        pd.DataFrame(sr).to_csv(out/'session_sampling_tiers.csv',index=False)

    frontier=[]
    # Local-only, session-only, and combined frontiers are stored separately so cost attribution is possible.
    local_by_fvg={}
    for fk in FVG_TIERS:
        sel=(~isf)|(ev.fvg_rank_frozen<=fk)
        local=pd.DataFrame({'start':ev.loc[sel,'uniform_tick_start'],'end':ev.loc[sel,'uniform_tick_end']}); local_by_fvg[fk]=local
        frontier+=dump_frontier(out,'local',fk,0,local)
    session_by_tier={}
    for sk in SESSION_TIERS:
        sw=[]
        if len(sessions):
            for r in sessions[sessions.panel_rank<=sk].itertuples():sw.append(session_envelope(r.research_trading_date))
        sessw=pd.DataFrame(sw,columns=['start','end']); session_by_tier[sk]=sessw
        frontier+=dump_frontier(out,'session',sk,0,sessw)
    for fk in FVG_TIERS:
        for sk in SESSION_TIERS:
            union=pd.concat([local_by_fvg[fk],session_by_tier[sk]],ignore_index=True)
            frontier+=dump_frontier(out,'union',fk,sk,union)
    pd.DataFrame(frontier).to_csv(out/'window_frontier.csv',index=False)

    manifest={'version':'COMEX_ACQUISITION_PLAN_V1_1','annual_files':len(event_files),'events':int(len(ev)),'years':sorted(int(x) for x in ev.year.unique()),'fvg_tiers':FVG_TIERS,'session_tiers':SESSION_TIERS,'merge_gap_minutes':GAP_MINUTES,'fvg_seed':FVG_SEED,'market_data_download_performed':False,'note':'FVG ranks recomputed within FVG-only yearly population; local/session/union frontiers frozen before COMEX download.'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8'); print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
