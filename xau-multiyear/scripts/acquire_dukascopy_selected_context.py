#!/usr/bin/env python3
from __future__ import annotations
import argparse,io,time
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import requests

NY=ZoneInfo('America/New_York')
RAW='https://raw.githubusercontent.com/kevingtlin/dukascopy_XAUUSD_1m_Data/main/xauusd/{side}/m1/xauusd_{side}_m1_{year:04d}_{month:02d}.csv'

def get_csv(url,retries=4):
    err=None
    for k in range(retries):
        try:
            r=requests.get(url,timeout=90);r.raise_for_status();return pd.read_csv(io.BytesIO(r.content))
        except Exception as e:err=e;time.sleep(2*(k+1))
    raise RuntimeError(f'download failed {url}: {err}')

def bounds(date):
    d=pd.Timestamp(date);prev=(d-pd.Timedelta(days=1)).date();cur=d.date()
    s=pd.Timestamp(f'{prev} 17:00:00',tz=NY).tz_convert('UTC')-pd.Timedelta(minutes=90)
    e=pd.Timestamp(f'{cur} 18:00:00',tz=NY).tz_convert('UTC')+pd.Timedelta(minutes=30)
    return s,e

def month_iter(a,b):
    p=pd.Timestamp(a).to_period('M');q=pd.Timestamp(b).to_period('M')
    while p<=q:
        yield p.year,p.month;p+=1

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sessions',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    s=pd.read_csv(a.sessions);s=s[s.acquisition_stage.eq('DEV_RANK1')].copy();assert len(s)==96
    months=set();windows=[]
    for d in s.research_trading_date.astype(str):
        lo,hi=bounds(d);windows.append((lo,hi));months.update(month_iter(lo,hi))
    pieces=[]
    for y,m in sorted(months):
        bid=get_csv(RAW.format(side='bid',year=y,month=m));ask=get_csv(RAW.format(side='ask',year=y,month=m));x=bid[['timestamp','close']].merge(ask[['timestamp','close']],on='timestamp',how='inner',suffixes=('_bid','_ask'));x['timestamp']=pd.to_datetime(x.timestamp,unit='ms',utc=True);x['xau_close']=(pd.to_numeric(x.close_bid)+pd.to_numeric(x.close_ask))/2.0;pieces.append(x[['timestamp','xau_close']]);print(f'{y}-{m:02d} rows={len(x)}',flush=True)
    x=pd.concat(pieces,ignore_index=True).drop_duplicates('timestamp').sort_values('timestamp');mask=pd.Series(False,index=x.index)
    for lo,hi in windows:mask |= (x.timestamp>=lo)&(x.timestamp<hi)
    x=x.loc[mask].copy();x.to_parquet(out,index=False,compression='zstd');print(f'DONE months={len(months)} rows={len(x)} out={out}',flush=True)
if __name__=='__main__':main()
