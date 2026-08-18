#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd

NY=ZoneInfo('America/New_York');FAMS=['DISPLACEMENT_ORIGIN','OBJECTIVE_LIQUIDITY','MEMORY','FVG'];MODELS=['passive_touch','touch_next_open','clean_rejection','failed_auction','acceptance_retest','reclaim_pullback']

def research_date(s):return (pd.to_datetime(s,utc=True).dt.tz_convert(NY)-pd.Timedelta(hours=17)).dt.date.astype(str)
def sig(x):return '+'.join(f for f in FAMS if f in str(x)) or 'OTHER'
def stack(s):return {'DISPLACEMENT_ORIGIN':'DOZ_ONLY','OBJECTIVE_LIQUIDITY':'OBJECTIVE_ONLY','MEMORY':'MEMORY_ONLY','FVG':'FVG_ONLY'}.get(s,'CONFLUENCE' if '+' in s else 'OTHER')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--events',required=True);ap.add_argument('--sessions',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    sess=pd.read_csv(a.sessions);rank1=set(sess.loc[sess.acquisition_stage.eq('DEV_RANK1'),'research_trading_date'].astype(str));use=['event_uid','year','contact_time','constituent_families','behavior_v2','side']+[m+'_eligible' for m in MODELS];e=pd.read_csv(a.events,compression='gzip',usecols=use,low_memory=False);e['research_trading_date']=research_date(e.contact_time);e=e[e.research_trading_date.isin(rank1)].copy();e['signature']=e.constituent_families.fillna('').map(sig);e['family_stack']=e.signature.map(stack)
    for m in MODELS:e[m+'_eligible']=e[m+'_eligible'].astype(str).str.lower().eq('true')
    broad=e.groupby('family_stack').agg(events=('event_uid','size'),independent_sessions=('research_trading_date','nunique'),years=('year','nunique')).reset_index()
    em=[]
    for m in MODELS:
        q=e[e[m+'_eligible']]
        g=q.groupby('family_stack').agg(eligible_events=('event_uid','size'),independent_sessions=('research_trading_date','nunique'),years=('year','nunique')).reset_index();g['entry_model']=m.upper();em.append(g)
    em=pd.concat(em,ignore_index=True).sort_values(['family_stack','entry_model']);em.to_csv(out/'dev_rank1_entry_model_summary_corrected.csv',index=False)
    sm=[]
    for m in MODELS:
        q=e[e[m+'_eligible']]
        g=q.groupby('signature').agg(eligible_events=('event_uid','size'),independent_sessions=('research_trading_date','nunique'),years=('year','nunique')).reset_index();g['entry_model']=m.upper();sm.append(g)
    sm=pd.concat(sm,ignore_index=True).sort_values(['signature','entry_model']);sm.to_csv(out/'dev_rank1_signature_model_summary_corrected.csv',index=False)
    beh=e.groupby(['family_stack','behavior_v2']).agg(events=('event_uid','size'),independent_sessions=('research_trading_date','nunique'),years=('year','nunique')).reset_index();beh.to_csv(out/'dev_rank1_behavior_summary_corrected.csv',index=False)
    conf=e[e.signature.str.contains('+',regex=False)].groupby('signature').agg(events=('event_uid','size'),independent_sessions=('research_trading_date','nunique'),years=('year','nunique')).reset_index().sort_values('events',ascending=False);conf.to_csv(out/'dev_rank1_confluence_summary_corrected.csv',index=False)
    result={'version':'COMEX_DEV_RANK1_COVERAGE_SUMMARY_V2_TRUE_NUNIQUE','market_data_download_performed':False,'events':int(len(e)),'selected_rank1_sessions':len(rank1),'sessions_with_events':int(e.research_trading_date.nunique()),'broad_families':broad.to_dict('records'),'family_entry_models':em.to_dict('records'),'family_behaviors':beh.to_dict('records'),'confluence_signatures':conf.to_dict('records'),'note':'All independent-session counts are computed directly from canonical event rows using nunique(research_trading_date); no cross-signature summation.'}
    (out/'dev_rank1_coverage_summary_v2.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
