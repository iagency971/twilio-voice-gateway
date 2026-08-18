#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd

NY = ZoneInfo('America/New_York')
SEED = 'COMEX_SUPPLEMENT_V3_SEED_971'
ORDER = ['DISPLACEMENT_ORIGIN','OBJECTIVE_LIQUIDITY','MEMORY','FVG']
MODELS = ['passive_touch','touch_next_open','clean_rejection','failed_auction','acceptance_retest','reclaim_pullback']
TIER = 2
# Screening floors. These are not claims of universal statistical power; they prevent obviously thin cells.
FAMILY_TARGETS = {
    'DEV': {'CONFLUENCE':1000,'DOZ_ONLY':1000,'MEMORY_ONLY':1000,'OBJECTIVE_ONLY':1000},
    'VALIDATION': {'CONFLUENCE':600,'DOZ_ONLY':600,'MEMORY_ONLY':600,'OBJECTIVE_ONLY':600},
    'COMEX_FEATURE_HOLDOUT': {'CONFLUENCE':600,'DOZ_ONLY':600,'MEMORY_ONLY':600,'OBJECTIVE_ONLY':600},
}
# Ensure exact confluence types are not silently absent. Population shortages remain explicitly underpowered.
CONFLUENCE_SIGNATURE_MIN = {'DEV':100,'VALIDATION':50,'COMEX_FEATURE_HOLDOUT':50}
ACCEPT_TARGETS = {
    'DEV': {'CONFLUENCE':150,'DOZ_ONLY':150,'FVG_ONLY':500,'MEMORY_ONLY':150,'OBJECTIVE_ONLY':150},
    'VALIDATION': {'CONFLUENCE':100,'DOZ_ONLY':100,'FVG_ONLY':250,'MEMORY_ONLY':100,'OBJECTIVE_ONLY':100},
    'COMEX_FEATURE_HOLDOUT': {'CONFLUENCE':100,'DOZ_ONLY':100,'FVG_ONLY':250,'MEMORY_ONLY':100,'OBJECTIVE_ONLY':100},
}

def h(uid): return hashlib.sha256(f'{SEED}|{uid}'.encode()).hexdigest()
def sig(x): return '+'.join(z for z in ORDER if z in str(x)) or 'OTHER'
def fam(s):
    return {'FVG':'FVG_ONLY','DISPLACEMENT_ORIGIN':'DOZ_ONLY','OBJECTIVE_LIQUIDITY':'OBJECTIVE_ONLY','MEMORY':'MEMORY_ONLY'}.get(s,'CONFLUENCE')
def rdate(s): return (pd.to_datetime(s,utc=True).dt.tz_convert(NY)-pd.Timedelta(hours=17)).dt.date.astype(str)
def snap10(t,ceil=False):
    t=pd.Timestamp(t); t=t.tz_convert('UTC') if t.tzinfo else t.tz_localize('UTC'); ns=600*10**9; v=t.value
    return pd.Timestamp(((v+ns-1)//ns*ns if ceil else v//ns*ns),tz='UTC')
def merge(iv,gap=30):
    if not iv:return []
    a=sorted(iv); out=[]; s,e=a[0]; g=pd.Timedelta(minutes=gap)
    for x,y in a[1:]:
        if x<=e+g:e=max(e,y)
        else:out.append((s,e));s,e=x,y
    out.append((s,e)); return out
def session_bounds(d):
    d=pd.Timestamp(d); prev=(d-pd.Timedelta(days=1)).date(); cur=d.date()
    return pd.Timestamp(f'{prev} 17:00:00',tz=NY).tz_convert('UTC'),pd.Timestamp(f'{cur} 18:00:00',tz=NY).tz_convert('UTC')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--events',required=True); ap.add_argument('--sessions',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    use=['event_uid','year','temporal_split','contact_time','constituent_families']+[m+'_eligible' for m in MODELS]
    e=pd.read_csv(a.events,compression='gzip',usecols=use,low_memory=False); assert len(e)==1274307,len(e)
    s=pd.read_csv(a.sessions); s['panel_rank']=pd.to_numeric(s.panel_rank,errors='coerce')
    e['research_trading_date']=rdate(e.contact_time); e['signature']=e.constituent_families.fillna('').map(sig); e['family_stack']=e.signature.map(fam); e['hash']=e.event_uid.astype(str).map(h)
    for m in MODELS:e[m+'_eligible']=e[m+'_eligible'].astype(str).str.lower().eq('true')
    base_dates=set(s.loc[s.panel_rank<=TIER,'research_trading_date'].astype(str)); base_mask=e.research_trading_date.isin(base_dates)
    selected=set(); reasons={}
    def add(q,reason):
        for uid in q.event_uid.astype(str):selected.add(uid);reasons.setdefault(uid,set()).add(reason)
    def union_mask(): return base_mask | e.event_uid.astype(str).isin(selected)

    # 1) family-stack floors, excluding generic FVG because full sessions already supply tens of thousands.
    for sp,targets in FAMILY_TARGETS.items():
        for fs,target in targets.items():
            cur=int((union_mask()&(e.temporal_split==sp)&(e.family_stack==fs)).sum()); need=max(0,target-cur)
            if need:
                q=e.loc[(~base_mask)&(~e.event_uid.astype(str).isin(selected))&(e.temporal_split==sp)&(e.family_stack==fs)].sort_values('hash').head(need); add(q,'family_floor')

    # 2) exact confluence minimums to preserve every confluence type when population permits.
    con_sigs=sorted(x for x in e.signature.unique() if fam(x)=='CONFLUENCE' and x!='OTHER')
    for sp,target in CONFLUENCE_SIGNATURE_MIN.items():
        for sg in con_sigs:
            cur=int((union_mask()&(e.temporal_split==sp)&(e.signature==sg)).sum()); need=max(0,target-cur)
            if need:
                q=e.loc[(~base_mask)&(~e.event_uid.astype(str).isin(selected))&(e.temporal_split==sp)&(e.signature==sg)].sort_values('hash').head(need); add(q,'confluence_signature_floor')

    # 3) entry-model floor for Acceptance Retest, the only clearly sparse current model.
    for sp,targets in ACCEPT_TARGETS.items():
        for fs,target in targets.items():
            cur=int((union_mask()&(e.temporal_split==sp)&(e.family_stack==fs)&e.acceptance_retest_eligible).sum()); need=max(0,target-cur)
            if need:
                q=e.loc[(~base_mask)&(~e.event_uid.astype(str).isin(selected))&(e.temporal_split==sp)&(e.family_stack==fs)&e.acceptance_retest_eligible].sort_values('hash').head(need); add(q,'acceptance_floor')

    sm=e.event_uid.astype(str).isin(selected); u=base_mask|sm; sup=e.loc[sm].copy(); union=e.loc[u].copy()
    counts=[]
    for (sp,fs),g in union.groupby(['temporal_split','family_stack'],sort=True):
        row={'split':sp,'family_stack':fs,'events':len(g)}
        for m in MODELS:row[m+'_eligible']=int(g[m+'_eligible'].sum())
        counts.append(row)
    sigs=[{'split':sp,'signature':sg,'events':len(g)} for (sp,sg),g in union.groupby(['temporal_split','signature'],sort=True)]
    raw=[(snap10(pd.Timestamp(t)-pd.Timedelta(minutes=30)),snap10(pd.Timestamp(t)+pd.Timedelta(minutes=16),True)) for t in pd.to_datetime(sup.contact_time,utc=True)]
    local=merge(raw,30); sess=merge([session_bounds(d) for d in sorted(base_dates)],0); package=merge(raw+[session_bounds(d) for d in sorted(base_dates)],30)
    pd.DataFrame(local,columns=['start','end']).to_csv(out/'tier2_local_gap30.csv',index=False); pd.DataFrame(sess,columns=['start','end']).to_csv(out/'tier2_sessions_gap0.csv',index=False); pd.DataFrame(package,columns=['start','end']).to_csv(out/'tier2_package_gap30.csv',index=False)
    sup[['event_uid','year','temporal_split','contact_time','research_trading_date','signature','family_stack','hash']].to_csv(out/'supplement_events.csv.gz',index=False,compression='gzip')
    pd.DataFrame(counts).to_csv(out/'counts_by_family.csv',index=False); pd.DataFrame(sigs).to_csv(out/'counts_by_signature.csv',index=False)
    reason_counts={r:sum(r in v for v in reasons.values()) for r in ['family_floor','confluence_signature_floor','acceptance_floor']}
    manifest={'version':'COMEX_SCREENING_PACKAGE_V3_LEAN','canonical_events':len(e),'session_tier':TIER,'base_session_dates':len(base_dates),'base_events':int(base_mask.sum()),'supplement_events':len(sup),'union_events':len(union),'reason_counts':reason_counts,'local_windows_gap30':len(local),'local_minutes_gap30':sum((b-a).total_seconds()/60 for a,b in local),'package_windows_gap30':len(package),'package_minutes_gap30':sum((b-a).total_seconds()/60 for a,b in package),'family_targets':FAMILY_TARGETS,'confluence_signature_min':CONFLUENCE_SIGNATURE_MIN,'acceptance_targets':ACCEPT_TARGETS,'selection_seed':SEED,'selection_uses_comex_data':False,'market_data_download_performed':False,'warning':'Lean screening design. Underpopulated cells remain inconclusive; no strategy validation claim.'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)); print(json.dumps(manifest,indent=2)); print(pd.DataFrame(counts).to_string(index=False))
if __name__=='__main__':main()
