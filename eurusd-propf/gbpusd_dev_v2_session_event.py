#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures as cf, importlib.util
from pathlib import Path
import pandas as pd
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v2',ROOT/'dev_research_v2.py')
v2=importlib.util.module_from_spec(spec); spec.loader.exec_module(v2)


def load_gbp(_start,_end,workers,out):
    items=[]
    for y in range(2012,2019):
        for w in range(1,54): items.append((y,w,f'https://candledata.fxcorporate.com/m1/GBPUSD/{y}/{w}.csv.gz'))
    frames=[]; cov=[]
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for fut in cf.as_completed([ex.submit(v2.v1.fetch_week,it) for it in items]):
            y,w,df,status=fut.result(); cov.append({'year':y,'week':w,'status':status})
            if df is not None:
                try: frames.append(v2.v1.normalize_week(df))
                except Exception as e: cov[-1]['status']=f'parse:{e}'
    pd.DataFrame(cov).sort_values(['year','week']).to_csv(out/'fxcm_coverage.csv',index=False)
    d=pd.concat(frames,ignore_index=True).sort_values('utc').drop_duplicates('utc',keep='last')
    d=d[(d.utc>=pd.Timestamp('2012-01-01',tz='UTC'))&(d.utc<pd.Timestamp('2019-01-01',tz='UTC'))].copy()
    d['mid_open']=(d.BidOpen+d.AskOpen)/2; d['mid_close']=(d.BidClose+d.AskClose)/2
    d['ny']=d.utc.dt.tz_convert(ZoneInfo('America/New_York')); d['lon']=d.utc.dt.tz_convert(ZoneInfo('Europe/London'))
    # Preserve all UTC 06:00-18:05 plus relevant early NY window. Avoid the EURUSD V2 summer truncation issue.
    um=d.utc.dt.hour*60+d.utc.dt.minute; nm=d.ny.dt.hour*60+d.ny.dt.minute
    d=d[((um>=6*60)&(um<=18*60+5))|((nm>=2*60)&(nm<=11*60))].copy()
    return d,pd.DataFrame(cov)

v2.v1.load_fxcm=load_gbp
if __name__=='__main__': v2.main()
