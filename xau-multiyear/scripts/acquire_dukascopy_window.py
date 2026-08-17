#!/usr/bin/env python3
from __future__ import annotations
import argparse,io,time
from pathlib import Path
import pandas as pd
import requests

RAW='https://raw.githubusercontent.com/kevingtlin/dukascopy_XAUUSD_1m_Data/main/xauusd/{side}/m1/xauusd_{side}_m1_{year:04d}_{month:02d}.csv'

def months(start_ym,end_ym):
    y,m=map(int,start_ym.split('-')); ey,em=map(int,end_ym.split('-'))
    while (y,m)<=(ey,em):
        yield y,m
        m+=1
        if m==13:y+=1;m=1

def get_csv(url,retries=4):
    err=None
    for a in range(retries):
        try:
            r=requests.get(url,timeout=90); r.raise_for_status(); return pd.read_csv(io.BytesIO(r.content))
        except Exception as e:
            err=e; time.sleep(2*(a+1))
    raise RuntimeError(f'download failed {url}: {err}')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--from-month',required=True); ap.add_argument('--to-month',required=True); ap.add_argument('--out',required=True); a=ap.parse_args(); out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); first=True; total=0
    with out.open('w',encoding='utf-8',newline='') as fh:
        for y,m in months(a.from_month,a.to_month):
            b=get_csv(RAW.format(side='bid',year=y,month=m)); q=get_csv(RAW.format(side='ask',year=y,month=m)); x=b.merge(q,on='timestamp',how='inner',suffixes=('_bid','_ask'))
            x['timestamp']=pd.to_datetime(x['timestamp'],unit='ms',utc=True)
            for c in ['open','high','low','close']:x[c]=(x[f'{c}_bid']+x[f'{c}_ask'])/2.0
            x['spread']=x['close_ask']-x['close_bid']; keep=['timestamp','open','high','low','close','open_bid','high_bid','low_bid','close_bid','open_ask','high_ask','low_ask','close_ask','spread']; x=x[keep]
            if len(x)==0:raise RuntimeError(f'empty merged month {y}-{m:02d}')
            x.to_csv(fh,index=False,header=first); first=False; total+=len(x); print(f'{y}-{m:02d} rows={len(x)} total={total}',flush=True)
    print(f'DONE rows={total} out={out}',flush=True)

if __name__=='__main__':main()
