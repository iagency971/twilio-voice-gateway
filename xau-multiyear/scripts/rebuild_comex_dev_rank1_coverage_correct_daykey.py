#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd

NY=ZoneInfo('America/New_York')
FAMILIES=['DISPLACEMENT_ORIGIN','OBJECTIVE_LIQUIDITY','MEMORY','FVG']
MODELS=['passive_touch','touch_next_open','clean_rejection','failed_auction','acceptance_retest','reclaim_pullback']

def research_day_key(ts: pd.Series) -> pd.Series:
    # Exact vectorized equivalent of rzr.features.trading_day_key(..., boundary_hour=17):
    # local date, advanced by one calendar day when local hour >= 17.
    local=pd.to_datetime(ts,utc=True).dt.tz_convert(NY)
    return (local + pd.Timedelta(hours=7)).dt.date.astype(str)

def signature(s: pd.Series)->pd.Series:
    v=s.fillna('').astype(str)
    return v.map(lambda x: '+'.join(f for f in FAMILIES if f in x) or 'OTHER')

def family_stack(sig: str)->str:
    return {'DISPLACEMENT_ORIGIN':'DOZ_ONLY','OBJECTIVE_LIQUIDITY':'OBJECTIVE_ONLY','MEMORY':'MEMORY_ONLY','FVG':'FVG_ONLY'}.get(sig,'CONFLUENCE' if '+' in sig else 'OTHER')

def agg(df,keys):
    return df.groupby(keys,dropna=False).agg(events=('event_uid','size'),independent_sessions=('research_trading_date','nunique'),years=('year','nunique')).reset_index()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--events',required=True);ap.add_argument('--sessions',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    sess=pd.read_csv(a.sessions);rank1=sess[sess.acquisition_stage.eq('DEV_RANK1')].copy();dates=set(rank1.research_trading_date.astype(str))
    use=['event_uid','year','contact_time','constituent_families','behavior_v2','side']+[f'{m}_eligible' for m in MODELS]
    e=pd.read_csv(a.events,compression='gzip',usecols=use,low_memory=False)
    e['research_trading_date']=research_day_key(e.contact_time)
    e=e[e.research_trading_date.isin(dates)].copy()
    e['signature']=signature(e.constituent_families);e['family_stack']=e.signature.map(family_stack)
    for m in MODELS:e[f'{m}_eligible']=e[f'{m}_eligible'].astype(str).str.lower().eq('true')
    broad=agg(e,['family_stack']);broad.to_csv(out/'dev_rank1_coverage_broad_correct_daykey.csv',index=False)
    behaviors=agg(e,['family_stack','behavior_v2']);behaviors.to_csv(out/'dev_rank1_coverage_behaviors_correct_daykey.csv',index=False)
    conf=agg(e[e.signature.str.contains('+',regex=False)],['signature']);conf.to_csv(out/'dev_rank1_coverage_confluences_correct_daykey.csv',index=False)
    model_rows=[]
    for m in MODELS:
        q=e[e[f'{m}_eligible']]
        if q.empty:continue
        z=agg(q,['family_stack']);z['entry_model']=m.upper();model_rows.append(z)
    models=pd.concat(model_rows,ignore_index=True);models.to_csv(out/'dev_rank1_coverage_models_correct_daykey.csv',index=False)
    per_year=agg(e,['year','family_stack']);per_year.to_csv(out/'dev_rank1_coverage_year_family_correct_daykey.csv',index=False)
    result={
      'version':'COMEX_DEV_RANK1_COVERAGE_CORRECT_DAYKEY_V3',
      'market_data_download_performed':False,
      'day_key_definition':'America/New_York local date; +1 day if local hour >=17; vectorized as date(local+7h)',
      'selected_rank1_sessions':int(len(rank1)),
      'sessions_with_events':int(e.research_trading_date.nunique()),
      'events':int(len(e)),
      'years':sorted(int(x) for x in e.year.unique()),
      'broad_families':broad.to_dict('records'),
      'family_entry_models':models.to_dict('records'),
      'confluence_signatures':conf.to_dict('records'),
      'blocking':{'all_event_dates_subset_selected':bool(set(e.research_trading_date).issubset(dates)),'independent_sessions_le_96':bool(e.research_trading_date.nunique()<=96)},
      'note':'Supersedes earlier coverage summaries whose helper incorrectly used date(ts-17h). Session selection itself is unchanged.'
    }
    (out/'dev_rank1_coverage_correct_daykey.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
