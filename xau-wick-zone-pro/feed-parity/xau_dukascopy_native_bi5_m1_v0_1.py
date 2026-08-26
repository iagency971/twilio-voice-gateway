#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,lzma,struct,time
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import pandas as pd
import requests

SYMBOL='XAUUSD'; DIV=1000.0; REC=struct.Struct('>IIIff')
BASE='https://datafeed.dukascopy.com/datafeed'

def cli():
    p=argparse.ArgumentParser();p.add_argument('--from-date',required=True);p.add_argument('--to-date',required=True);p.add_argument('--out',required=True);p.add_argument('--meta',required=True);return p.parse_args()

def daterange(a,b):
    d=date.fromisoformat(a);e=date.fromisoformat(b)
    while d<=e:yield d;d+=timedelta(days=1)

def download(url):
    for i in range(3):
        try:
            r=requests.get(url,timeout=30,headers={'User-Agent':'Mozilla/5.0'})
            if r.status_code==404:return None
            r.raise_for_status();return r.content
        except Exception:
            if i==2:raise
            time.sleep(i+1)

def decode(blob,base,max_ms):
    if not blob:return []
    raw=lzma.decompress(blob)
    if len(raw)%20:raise RuntimeError(f'bad BI5 length {len(raw)}')
    out=[]
    for ms,ask,bid,av,bv in REC.iter_unpack(raw):
        if ms>=max_ms:raise RuntimeError(f'bad BI5 offset {ms}')
        out.append((base+timedelta(milliseconds=int(ms)),bid/DIV,ask/DIV,bv,av))
    return out

def fetch_day(d):
    ticks=[];hour_files=0
    for h in range(24):
        url=f'{BASE}/{SYMBOL}/{d.year:04d}/{d.month-1:02d}/{d.day:02d}/{h:02d}h_ticks.bi5'
        q=decode(download(url),datetime(d.year,d.month,d.day,h,tzinfo=timezone.utc),3_600_000)
        if q:hour_files+=1;ticks.extend(q)
    if hour_files==0:
        url=f'{BASE}/{SYMBOL}/{d.year:04d}/{d.month-1:02d}/{d.day:02d}_ticks.bi5'
        ticks=decode(download(url),datetime(d.year,d.month,d.day,tzinfo=timezone.utc),86_400_000)
    return ticks,hour_files

def aggregate(ticks):
    if not ticks:return pd.DataFrame()
    d=pd.DataFrame(ticks,columns=['time','bid','ask','bid_volume','ask_volume']).sort_values('time')
    d['time']=pd.to_datetime(d.time,utc=True);d['minute']=d.time.dt.floor('min')
    g=d.groupby('minute',sort=True);b=g.bid.agg(['first','max','min','last']);a=g.ask.agg(['first','max','min','last'])
    x=pd.DataFrame({'timestamp':b.index,'open_bid':b['first'],'high_bid':b['max'],'low_bid':b['min'],'close_bid':b['last'],'open_ask':a['first'],'high_ask':a['max'],'low_ask':a['min'],'close_ask':a['last']}).reset_index(drop=True)
    for c in ['open','high','low','close']:x[c]=(x[c+'_bid']+x[c+'_ask'])/2
    x['spread']=x.close_ask-x.close_bid
    return x[['timestamp','open','high','low','close','open_bid','high_bid','low_bid','close_bid','open_ask','high_ask','low_ask','close_ask','spread']]

def main():
    a=cli();ticks=[];dm=[]
    for d in daterange(a.from_date,a.to_date):
        q,n=fetch_day(d);ticks.extend(q);dm.append({'date':d.isoformat(),'ticks':len(q),'hour_files_with_ticks':n});print(d,len(q),n,flush=True)
    x=aggregate(ticks);Path(a.out).parent.mkdir(parents=True,exist_ok=True);x.to_csv(a.out,index=False)
    meta={'status':'PASS' if len(x) else 'EMPTY','symbol':SYMBOL,'price_divisor':DIV,'source':BASE,'from_date':a.from_date,'to_date':a.to_date,'tick_count':len(ticks),'m1_count':len(x),'first_m1':str(x.timestamp.min()) if len(x) else None,'last_m1':str(x.timestamp.max()) if len(x) else None,'days':dm,'aggregation':'BID/ASK tick OHLC per UTC minute; MID barwise average; no forward-fill'}
    Path(a.meta).write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
