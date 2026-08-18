#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, math
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd

NY=ZoneInfo('America/New_York')
FVG_TIERS=(1,2,4)
SESSION_TIERS=(2,3,4)
GAP_MINUTES=(0,5,15,30,60)


def merge_windows(df, gap_min=0):
    if df.empty:return df.copy()
    x=df[['start','end']].copy()
    x['start']=pd.to_datetime(x.start,utc=True); x['end']=pd.to_datetime(x.end,utc=True)
    x=x.sort_values(['start','end']).reset_index(drop=True)
    gap=pd.Timedelta(minutes=gap_min)
    out=[]; s=x.iloc[0].start; e=x.iloc[0].end
    for r in x.iloc[1:].itertuples():
        if r.start <= e+gap:
            if r.end>e:e=r.end
        else:
            out.append((s,e)); s=r.start; e=r.end
    out.append((s,e))
    return pd.DataFrame(out,columns=['start','end'])


def session_envelope(date_str):
    d=pd.Timestamp(date_str)
    # Wide envelope covering historical and current standard-GC daily sessions;
    # exact maintenance-gap trimming occurs only after data acquisition.
    prev=(d-pd.Timedelta(days=1)).date()
    cur=d.date()
    s=pd.Timestamp(f'{prev} 17:00:00',tz=NY).tz_convert('UTC')
    e=pd.Timestamp(f'{cur} 18:00:00',tz=NY).tz_convert('UTC')
    return s,e


def minutes(df):
    if df.empty:return 0.0
    return float(((pd.to_datetime(df.end,utc=True)-pd.to_datetime(df.start,utc=True)).dt.total_seconds()/60).sum())


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    root=Path(a.root); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    manifests=[]; event_files=[]; session_files=[]
    for p in root.rglob('manifest.json'):
        try:
            m=json.loads(p.read_text());
            if m.get('version')=='COMEX_EVENT_TIMING_V1': manifests.append(m)
        except Exception: pass
    for p in root.rglob('events.csv.gz'): event_files.append(p)
    for p in root.rglob('session_candidates.csv'): session_files.append(p)
    if not event_files: raise SystemExit('no annual event files')

    pd.DataFrame(manifests).sort_values('year').to_csv(out/'annual_manifest.csv',index=False)

    events=[]
    for p in event_files:
        x=pd.read_csv(p,compression='gzip',low_memory=False)
        events.append(x)
    ev=pd.concat(events,ignore_index=True)
    ev['contact_time']=pd.to_datetime(ev.contact_time,utc=True)
    ev['uniform_tick_start']=pd.to_datetime(ev.uniform_tick_start,utc=True)
    ev['uniform_tick_end']=pd.to_datetime(ev.uniform_tick_end,utc=True)
    ev['fvg_rank']=pd.to_numeric(ev.fvg_rank,errors='coerce')

    # Compact canonical audit table: all events, all decision/order/entry columns.
    ev.to_csv(out/'canonical_events_all.csv.gz',index=False,compression='gzip')

    # Split counts and entry eligibility.
    rows=[]
    model_prefixes=['passive_touch','touch_next_open','clean_rejection','failed_auction','acceptance_retest','reclaim_pullback']
    for (y,sp),g in ev.groupby(['year','temporal_split']):
        r={'year':int(y),'split':sp,'events':len(g),'fvg_only':int(g.fvg_only.astype(str).str.lower().eq('true').sum())}
        for m in model_prefixes:
            c=m+'_eligible'; r[m+'_eligible']=int(g[c].astype(str).str.lower().eq('true').sum()) if c in g else 0
        rows.append(r)
    pd.DataFrame(rows).sort_values('year').to_csv(out/'event_counts_by_year.csv',index=False)

    # FVG sample ranks are frozen; tier size can be chosen after power/cost review.
    fvg=ev[ev.fvg_only.astype(str).str.lower().eq('true')].copy()
    fvg_plan=[]
    for k in FVG_TIERS:
        sel=fvg[fvg.fvg_rank<=k]
        for sp,g in sel.groupby('temporal_split'):
            fvg_plan.append({'tier_rank_per_stratum':k,'split':sp,'events':len(g),'years':g.year.nunique()})
    pd.DataFrame(fvg_plan).to_csv(out/'fvg_sampling_tiers.csv',index=False)

    sess=[]
    for p in session_files:
        x=pd.read_csv(p)
        if len(x):sess.append(x)
    sessions=pd.concat(sess,ignore_index=True) if sess else pd.DataFrame()
    if len(sessions):
        sessions['panel_rank']=pd.to_numeric(sessions.panel_rank,errors='coerce')
        sessions.to_csv(out/'session_candidates_all.csv',index=False)

    # Window frontier: union non-FVG POIs + sampled FVG + session panel.
    frontier=[]
    for fk in FVG_TIERS:
        selected=(~ev.fvg_only.astype(str).str.lower().eq('true')) | (ev.fvg_rank<=fk)
        local=pd.DataFrame({'start':ev.loc[selected,'uniform_tick_start'],'end':ev.loc[selected,'uniform_tick_end']})
        for sk in SESSION_TIERS:
            sw=[]
            if len(sessions):
                for r in sessions[sessions.panel_rank<=sk].itertuples(): sw.append(session_envelope(r.research_trading_date))
            sessw=pd.DataFrame(sw,columns=['start','end']) if sw else pd.DataFrame(columns=['start','end'])
            union=pd.concat([local,sessw],ignore_index=True)
            for gap in GAP_MINUTES:
                mw=merge_windows(union,gap)
                name=f'windows_fvg{fk}_sess{sk}_gap{gap}m.csv'
                mw.to_csv(out/name,index=False)
                frontier.append({
                    'fvg_rank_per_stratum':fk,'session_rank_per_stratum':sk,'merge_gap_min':gap,
                    'selected_event_windows':int(selected.sum()),'session_windows':int(len(sessw)),
                    'merged_windows':int(len(mw)),'covered_minutes':minutes(mw),
                    'covered_days':minutes(mw)/1440.0,
                })
    pd.DataFrame(frontier).to_csv(out/'window_frontier.csv',index=False)

    # Session tier counts by temporal split using year mapping from canonical events.
    if len(sessions):
        ysplit=ev[['year','temporal_split']].drop_duplicates().set_index('year').temporal_split.to_dict()
        sessions['temporal_split']=sessions.year.map(ysplit)
        sr=[]
        for k in SESSION_TIERS:
            q=sessions[sessions.panel_rank<=k]
            for sp,g in q.groupby('temporal_split'):
                sr.append({'tier_rank_per_stratum':k,'split':sp,'sessions':len(g),'years':g.year.nunique()})
        pd.DataFrame(sr).to_csv(out/'session_sampling_tiers.csv',index=False)

    manifest={
        'version':'COMEX_ACQUISITION_PLAN_V1','annual_files':len(event_files),'events':int(len(ev)),
        'years':sorted(int(x) for x in ev.year.unique()),'fvg_tiers':FVG_TIERS,'session_tiers':SESSION_TIERS,
        'merge_gap_minutes':GAP_MINUTES,'market_data_download_performed':False,
        'note':'Sampling ranks and temporal splits frozen before any COMEX market-data download.'
    }
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
