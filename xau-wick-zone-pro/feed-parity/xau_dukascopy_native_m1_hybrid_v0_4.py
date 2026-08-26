#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, lzma, struct, time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import requests

SYMBOL='XAUUSD'; DIV=1000.0; REC=struct.Struct('>IIIIIf')
BASES=('https://www.dukascopy.com/datafeed','https://datafeed.dukascopy.com/datafeed')
HERE=Path(__file__).resolve().parent
TICK_PATH=HERE/'xau_dukascopy_native_bi5_m1_v0_1.py'

def cli():
    p=argparse.ArgumentParser();p.add_argument('--from-date',required=True);p.add_argument('--to-date',required=True);p.add_argument('--out',required=True);p.add_argument('--meta',required=True);return p.parse_args()

def daterange(a,b):
    d=date.fromisoformat(a);e=date.fromisoformat(b)
    while d<=e:yield d;d+=timedelta(days=1)

def download(path):
    attempts=[]
    for base in BASES:
        u=base+'/'+path
        for k in range(3):
            try:
                r=requests.get(u,timeout=12,headers={'User-Agent':'Mozilla/5.0'})
                attempts.append({'url':u,'status':r.status_code})
                if r.status_code==200 and r.content:return r.content,base,attempts
                if r.status_code==404:break
            except Exception as e:attempts.append({'url':u,'error':type(e).__name__})
            time.sleep(.4*(k+1))
    return None,None,attempts

def decode_candles(blob,d,side):
    if not blob:return pd.DataFrame(),None
    raw=lzma.decompress(blob)
    if len(raw)%24:raise RuntimeError(f'bad candle BI5 length {len(raw)}')
    rows=list(REC.iter_unpack(raw))
    if not rows:return pd.DataFrame(),None
    a=np.asarray([r[:5] for r in rows],dtype=np.float64)
    sec=a[:,0];v=a[:,1:]/DIV
    if np.any(sec<0) or np.any(sec>=86400):raise RuntimeError('bad candle seconds')
    # Two layouts observed in public Dukascopy decoders. Choose only from OHLC structural validity, never from mirror/outcomes.
    layouts={
      'O_H_L_C':(0,1,2,3),
      'O_C_L_H':(0,3,2,1),
    }
    scores={}
    for name,(oi,hi,li,ci) in layouts.items():
        o,h,l,c=v[:,oi],v[:,hi],v[:,li],v[:,ci]
        scores[name]=float(np.mean((h>=np.maximum(o,c))&(l<=np.minimum(o,c))&(h>=l)))
    best=max(scores,key=scores.get)
    if scores[best]<.99:raise RuntimeError(f'no plausible candle layout {scores}')
    oi,hi,li,ci=layouts[best];base=pd.Timestamp(datetime(d.year,d.month,d.day,tzinfo=timezone.utc))
    suf='_'+side.lower()
    out=pd.DataFrame({'timestamp':base+pd.to_timedelta(sec.astype('int64'),unit='s'),
                      'open'+suf:v[:,oi],'high'+suf:v[:,hi],'low'+suf:v[:,li],'close'+suf:v[:,ci]})
    out=out.sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)
    return out,{'layout':best,'layout_scores':scores,'records':len(out)}

def load_tick_module():
    spec=importlib.util.spec_from_file_location('duka_tick_v01',TICK_PATH);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def tick_fallback(d):
    m=load_tick_module();ticks,_,hosts,missing=m.fetch_day(d);x=m.aggregate(ticks)
    if len(x):x['timestamp']=pd.to_datetime(x.timestamp,utc=True)
    return x,{'rows':len(x),'hosts':hosts,'missing_request_count':len(missing)}

def merge_day(d):
    sides={};info={'date':d.isoformat(),'direct':{},'fallback_used':False}
    for side in ('BID','ASK'):
        path=f'{SYMBOL}/{d.year:04d}/{d.month-1:02d}/{d.day:02d}/{side}_candles_min_1.bi5'
        blob,host,att=download(path)
        q,dec=decode_candles(blob,d,side)
        sides[side]=q;info['direct'][side]={'host':host,'attempts':att,'decode':dec,'rows':len(q)}
    need_fallback=(len(sides['BID'])==0 or len(sides['ASK'])==0)
    # Also fallback when direct side timestamps disagree; direct values retain priority.
    if not need_fallback:
        need_fallback=set(sides['BID'].timestamp)!=set(sides['ASK'].timestamp)
    if need_fallback:
        tf,tmeta=tick_fallback(d);info['fallback_used']=True;info['fallback']=tmeta
        for side in ('BID','ASK'):
            suf='_'+side.lower();cols=['timestamp']+[c+suf for c in ('open','high','low','close')]
            fb=tf[cols].copy() if len(tf) else pd.DataFrame(columns=cols)
            direct=sides[side]
            if len(direct):
                z=pd.concat([direct.assign(_p=0),fb.assign(_p=1)],ignore_index=True).sort_values(['timestamp','_p']).drop_duplicates('timestamp',keep='first').drop(columns='_p')
            else:z=fb
            sides[side]=z
    x=sides['BID'].merge(sides['ASK'],on='timestamp',how='inner')
    for c in ('open','high','low','close'):x[c]=(x[c+'_bid']+x[c+'_ask'])/2.0
    x['spread']=x.close_ask-x.close_bid
    keep=['timestamp','open','high','low','close','open_bid','high_bid','low_bid','close_bid','open_ask','high_ask','low_ask','close_ask','spread']
    x=x[keep].sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True);info['final_common_rows']=len(x)
    return x,info

def main():
    a=cli();parts=[];days=[]
    for d in daterange(a.from_date,a.to_date):
        x,meta=merge_day(d);parts.append(x);days.append(meta);print(d,len(x),'fallback',meta['fallback_used'],flush=True)
    out=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame();Path(a.out).parent.mkdir(parents=True,exist_ok=True);out.to_csv(a.out,index=False)
    meta={'status':'PASS' if len(out) else 'EMPTY','symbol':SYMBOL,'price_divisor':DIV,'method':'native daily BID/ASK M1 first; native tick fallback only for missing side/timestamps; direct values always win; no interpolation/forward-fill','sources':list(BASES),'from_date':a.from_date,'to_date':a.to_date,'m1_count':len(out),'first_m1':str(out.timestamp.min()) if len(out) else None,'last_m1':str(out.timestamp.max()) if len(out) else None,'days':days}
    Path(a.meta).write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
