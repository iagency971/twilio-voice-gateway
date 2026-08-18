#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd

NY = ZoneInfo('America/New_York')
SEED = 'COMEX_SUPPLEMENT_V2_SEED_971'
SESSION_TIERS = (1, 2, 3, 4)
MERGE_GAPS = (0, 30, 60, 120, 180, 240, 360, 720)
ORDER = ['DISPLACEMENT_ORIGIN', 'OBJECTIVE_LIQUIDITY', 'MEMORY', 'FVG']
PURE = {'DISPLACEMENT_ORIGIN', 'OBJECTIVE_LIQUIDITY', 'MEMORY'}
ABUNDANT = {'DISPLACEMENT_ORIGIN+FVG', 'OBJECTIVE_LIQUIDITY+FVG', 'MEMORY+FVG'}
PURE_TARGETS = {'DEV': 2000, 'VALIDATION': 1000, 'COMEX_FEATURE_HOLDOUT': 1000}
ABUNDANT_TARGETS = {'DEV': 1500, 'VALIDATION': 750, 'COMEX_FEATURE_HOLDOUT': 750}
# Screening floors for ACCEPTANCE_RETEST. Targets above population availability are capped naturally.
ACCEPT_TARGETS = {
    'DEV': {'CONFLUENCE':150, 'DOZ_ONLY':150, 'FVG_ONLY':500, 'MEMORY_ONLY':150, 'OBJECTIVE_ONLY':150},
    'VALIDATION': {'CONFLUENCE':100, 'DOZ_ONLY':100, 'FVG_ONLY':250, 'MEMORY_ONLY':100, 'OBJECTIVE_ONLY':100},
    'COMEX_FEATURE_HOLDOUT': {'CONFLUENCE':100, 'DOZ_ONLY':100, 'FVG_ONLY':250, 'MEMORY_ONLY':100, 'OBJECTIVE_ONLY':100},
}
MODELS = ['passive_touch','touch_next_open','clean_rejection','failed_auction','acceptance_retest','reclaim_pullback']


def stable_hash(uid: str) -> str:
    return hashlib.sha256(f'{SEED}|{uid}'.encode()).hexdigest()


def signature(x: str) -> str:
    return '+'.join([z for z in ORDER if z in str(x)]) or 'OTHER'


def family_stack(sig: str) -> str:
    if sig == 'FVG': return 'FVG_ONLY'
    if sig == 'DISPLACEMENT_ORIGIN': return 'DOZ_ONLY'
    if sig == 'OBJECTIVE_LIQUIDITY': return 'OBJECTIVE_ONLY'
    if sig == 'MEMORY': return 'MEMORY_ONLY'
    return 'CONFLUENCE'


def is_rare(sig: str) -> bool:
    return sig not in PURE and sig not in ABUNDANT and sig not in {'FVG','OTHER'}


def research_date(ts: pd.Series) -> pd.Series:
    return (pd.to_datetime(ts, utc=True).dt.tz_convert(NY) - pd.Timedelta(hours=17)).dt.date.astype(str)


def snap10(t, ceil=False):
    t = pd.Timestamp(t)
    t = t.tz_convert('UTC') if t.tzinfo else t.tz_localize('UTC')
    ns = 10 * 60 * 10**9
    v = t.value
    w = ((v + ns - 1)//ns*ns) if ceil else (v//ns*ns)
    return pd.Timestamp(w, tz='UTC')


def merge_windows(intervals, gap_min=0):
    if not intervals: return []
    a = sorted(intervals)
    out=[]; s0,e0=a[0]; gap=pd.Timedelta(minutes=gap_min)
    for s1,e1 in a[1:]:
        if s1 <= e0 + gap:
            e0=max(e0,e1)
        else:
            out.append((s0,e0)); s0,e0=s1,e1
    out.append((s0,e0))
    return out


def session_bounds(d):
    d=pd.Timestamp(d); prev=(d-pd.Timedelta(days=1)).date(); cur=d.date()
    return (pd.Timestamp(f'{prev} 17:00:00',tz=NY).tz_convert('UTC'),
            pd.Timestamp(f'{cur} 18:00:00',tz=NY).tz_convert('UTC'))


def total_minutes(iv):
    return float(sum((b-a).total_seconds()/60.0 for a,b in iv))


def write_windows(path: Path, iv):
    pd.DataFrame(iv, columns=['start','end']).to_csv(path,index=False)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--events',required=True)
    ap.add_argument('--sessions',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)

    use=['event_uid','year','temporal_split','contact_time','constituent_families'] + [m+'_eligible' for m in MODELS]
    e=pd.read_csv(a.events,compression='gzip',usecols=use,low_memory=False)
    s=pd.read_csv(a.sessions)
    assert len(e)==1274307, len(e)
    s['panel_rank']=pd.to_numeric(s.panel_rank,errors='coerce')
    e['research_trading_date']=research_date(e.contact_time)
    e['signature']=e.constituent_families.fillna('').map(signature)
    e['family_stack']=e.signature.map(family_stack)
    e['selection_hash']=e.event_uid.astype(str).map(stable_hash)
    for m in MODELS:
        e[m+'_eligible']=e[m+'_eligible'].astype(str).str.lower().eq('true')

    summary=[]; count_rows=[]; sig_rows=[]; acc_rows=[]; frontier=[]
    package_artifacts={}

    for tier in SESSION_TIERS:
        base_dates=set(s.loc[s.panel_rank<=tier,'research_trading_date'].astype(str))
        base_mask=e.research_trading_date.isin(base_dates)
        outside=e.loc[~base_mask].copy()
        base=e.loc[base_mask]

        selected_ids=set()
        reason={}
        # Signature screening supplements.
        for (sp,sig),g in outside.groupby(['temporal_split','signature'],sort=True):
            already=int(((base.temporal_split==sp)&(base.signature==sig)).sum())
            if sig in PURE:
                n=max(0,PURE_TARGETS.get(sp,0)-already)
            elif sig in ABUNDANT:
                n=max(0,ABUNDANT_TARGETS.get(sp,0)-already)
            elif is_rare(sig):
                n=len(g)
            else:
                n=0
            if n:
                q=g.sort_values('selection_hash').head(n)
                for uid in q.event_uid.astype(str): selected_ids.add(uid); reason.setdefault(uid,set()).add('signature_screen')

        sig_mask=e.event_uid.astype(str).isin(selected_ids)
        union_mask=base_mask | sig_mask

        # Acceptance supplements after signature selection.
        for sp,targets in ACCEPT_TARGETS.items():
            for fs,target in targets.items():
                cur=int((union_mask & (e.temporal_split==sp) & (e.family_stack==fs) & e.acceptance_retest_eligible).sum())
                need=max(0,target-cur)
                if not need: continue
                q=e.loc[(~base_mask) & (~sig_mask) & (e.temporal_split==sp) & (e.family_stack==fs) & e.acceptance_retest_eligible].sort_values('selection_hash').head(need)
                for uid in q.event_uid.astype(str): selected_ids.add(uid); reason.setdefault(uid,set()).add('acceptance_floor')
                sig_mask=e.event_uid.astype(str).isin(selected_ids)
                union_mask=base_mask | sig_mask

        supplement=e.loc[e.event_uid.astype(str).isin(selected_ids)].copy()
        union=e.loc[union_mask].copy()

        # Counts by family stack and exact signature.
        for (sp,fs),g in union.groupby(['temporal_split','family_stack'],sort=True):
            r={'session_tier':tier,'split':sp,'family_stack':fs,'events':int(len(g))}
            for m in MODELS:r[m+'_eligible']=int(g[m+'_eligible'].sum())
            count_rows.append(r)
            acc_rows.append({'session_tier':tier,'split':sp,'family_stack':fs,'acceptance_retest_eligible':int(g.acceptance_retest_eligible.sum())})
        for (sp,sig),g in union.groupby(['temporal_split','signature'],sort=True):
            sig_rows.append({'session_tier':tier,'split':sp,'signature':sig,'events':int(len(g))})

        # Local scientific windows only for supplement events outside base full sessions.
        local_raw=[(snap10(pd.Timestamp(t)-pd.Timedelta(minutes=30)), snap10(pd.Timestamp(t)+pd.Timedelta(minutes=16),True)) for t in pd.to_datetime(supplement.contact_time,utc=True)]
        session_raw=[session_bounds(d) for d in sorted(base_dates)]
        sessions_merged=merge_windows(session_raw,0)
        write_windows(out/f'tier{tier}_sessions_gap0.csv',sessions_merged)

        for gap in MERGE_GAPS:
            local=merge_windows(local_raw,gap)
            package=merge_windows(session_raw+local_raw,gap)
            write_windows(out/f'tier{tier}_local_gap{gap}.csv',local)
            write_windows(out/f'tier{tier}_package_gap{gap}.csv',package)
            frontier.append({
                'session_tier':tier,'merge_gap_min':gap,'base_session_dates':len(base_dates),
                'supplement_events':int(len(supplement)),'union_events':int(len(union)),
                'local_windows':len(local),'local_minutes':total_minutes(local),
                'package_windows':len(package),'package_minutes':total_minutes(package),
                'session_windows_gap0':len(sessions_merged),'session_minutes_gap0':total_minutes(sessions_merged),
            })

        summary.append({
            'session_tier':tier,'base_session_dates':len(base_dates),'base_events':int(base_mask.sum()),
            'supplement_events':int(len(supplement)),'union_events':int(len(union)),
            'supplement_unique_dates':int(supplement.research_trading_date.nunique()),
            'signature_screen_events':sum('signature_screen' in v for v in reason.values()),
            'acceptance_floor_events':sum('acceptance_floor' in v for v in reason.values()),
            'both_reasons_events':sum(len(v)>1 for v in reason.values()),
        })
        # Compact supplement manifest for reproducibility; no outcomes other than eligibility used in selection.
        supplement[['event_uid','year','temporal_split','contact_time','research_trading_date','signature','family_stack','selection_hash']].to_csv(out/f'tier{tier}_supplement_events.csv.gz',index=False,compression='gzip')

    pd.DataFrame(summary).to_csv(out/'package_v2_summary.csv',index=False)
    pd.DataFrame(count_rows).to_csv(out/'package_v2_counts_by_family.csv',index=False)
    pd.DataFrame(sig_rows).to_csv(out/'package_v2_counts_by_signature.csv',index=False)
    pd.DataFrame(acc_rows).to_csv(out/'package_v2_acceptance_counts.csv',index=False)
    pd.DataFrame(frontier).to_csv(out/'package_v2_window_frontier.csv',index=False)
    manifest={
        'version':'COMEX_SCREENING_PACKAGE_V2','canonical_events':int(len(e)),
        'session_tiers':list(SESSION_TIERS),'merge_gaps_min':list(MERGE_GAPS),
        'selection_seed':SEED,'pure_targets':PURE_TARGETS,'abundant_fvg_confluence_targets':ABUNDANT_TARGETS,
        'acceptance_retest_screening_floors':ACCEPT_TARGETS,
        'rare_confluences':'all outside base session panel retained',
        'fvg_only':'no generic local supplement; full-session panel supplies FVG-only tick sample; acceptance floor may add FVG-only events',
        'local_scientific_window':'contact -30m / +16m; request bounds snapped outward to 10m',
        'selection_uses_comex_outcomes':False,'market_data_download_performed':False,
        'warning':'Screening package, not a virgin strategy validation. Cells below population/power requirements remain inconclusive rather than rejected.'
    }
    (out/'package_v2_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2)); print(pd.DataFrame(summary).to_string(index=False)); print(pd.DataFrame(frontier).to_string(index=False))

if __name__=='__main__': main()
