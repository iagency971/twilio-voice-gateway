#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures as cf, importlib.util
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v3',ROOT/'dev_research_v3_asian_london.py')
v3=importlib.util.module_from_spec(spec); spec.loader.exec_module(v3)


def load_gbpusd_dev(workers,out):
    items=[]
    for y in range(2012,2019):
        for w in range(1,54):
            items.append((y,w,f'https://candledata.fxcorporate.com/m1/GBPUSD/{y}/{w}.csv.gz'))
    frames=[]; cov=[]
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs=[ex.submit(v3.v1.fetch_week,it) for it in items]
        for fut in cf.as_completed(futs):
            y,w,df,status=fut.result(); cov.append({'year':y,'week':w,'status':status})
            if df is not None:
                try: frames.append(v3.v1.normalize_week(df))
                except Exception as e: cov[-1]['status']=f'parse:{e}'
    pd.DataFrame(cov).sort_values(['year','week']).to_csv(out/'coverage.csv',index=False)
    if not frames: raise RuntimeError('no GBPUSD data')
    d=pd.concat(frames,ignore_index=True).sort_values('utc').drop_duplicates('utc',keep='last')
    d=d[(d.utc>=pd.Timestamp('2012-01-01',tz='UTC'))&(d.utc<pd.Timestamp('2019-01-01',tz='UTC'))].copy()
    mins=d.utc.dt.hour*60+d.utc.dt.minute; d=d[(mins>=0)&(mins<=11*60+5)].copy()
    d['mid_open']=(d.BidOpen+d.AskOpen)/2; d['mid_close']=(d.BidClose+d.AskClose)/2
    d['date']=d.utc.dt.tz_convert(None).dt.normalize()
    return d

# Important: architecture, thresholds, stop, RR grid, train/validation split and
# quality gates are IDENTICAL to EURUSD DEV V3. Only the asset/data URL changes.
v3.load_dev=load_gbpusd_dev

if __name__=='__main__':
    v3.main()
# retrigger after GBPUSD DEV V2 completion; no trading logic changed
