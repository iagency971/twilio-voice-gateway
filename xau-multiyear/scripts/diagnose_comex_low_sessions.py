#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,time
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import databento as db

NY=ZoneInfo('America/New_York'); DATASET='GLBX.MDP3'; CONT='GC.v.0'

def bounds(d):
    d=pd.Timestamp(d);prev=(d-pd.Timedelta(days=1)).date();cur=d.date()
    return pd.Timestamp(f'{prev} 17:00:00',tz=NY).tz_convert('UTC'),pd.Timestamp(f'{cur} 18:00:00',tz=NY).tz_convert('UTC')

def retry(fn,**kw):
    err=None
    for k in range(7):
        try:return fn(**kw)
        except Exception as e:err=e;time.sleep(min(20,2**k))
    raise RuntimeError(err)

def count(c,symbol,stype,schema,a,b):
    return int(retry(c.metadata.get_record_count,dataset=DATASET,symbols=symbol,stype_in=stype,schema=schema,start=a.isoformat(),end=b.isoformat()))

def normalize(res):
    try:return res.model_dump()
    except Exception:
        try:return dict(res)
        except Exception:return json.loads(json.dumps(res,default=lambda o:getattr(o,'__dict__',str(o))))

def resolve(c,symbols,stype_in,stype_out,start_date,end_date):
    return normalize(c.symbology.resolve(dataset=DATASET,symbols=symbols,stype_in=stype_in,stype_out=stype_out,start_date=start_date,end_date=end_date))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--quotes',required=True);ap.add_argument('--out',required=True);ap.add_argument('--threshold',type=int,default=5000);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    key=os.environ.get('DATABENTO_API_KEY');
    if not key:raise SystemExit('DATABENTO_API_KEY missing')
    c=db.Historical(key);q=pd.read_csv(a.quotes);low=q[q.trades_record_count<a.threshold].copy();rows=[]
    for r in low.itertuples():
        date=str(r.research_trading_date); d0=pd.Timestamp(date).date(); d1=(pd.Timestamp(date)+pd.Timedelta(days=1)).date(); s,e=bounds(date)
        cm=resolve(c,[CONT],'continuous','instrument_id',str(d0),str(d1)); segs=cm.get('result',{}).get(CONT,[]); ids=sorted({str(x['s']) for x in segs if isinstance(x,dict) and x.get('s') is not None})
        raw_symbols=[]
        for iid in ids:
            rm=resolve(c,[iid],'instrument_id','raw_symbol',str(d0),str(d1)); vals=rm.get('result',{}).get(iid,[]); raw_symbols += [str(x['s']) for x in vals if isinstance(x,dict) and x.get('s') is not None]
        raw_symbols=sorted(set(raw_symbols))
        raw_trade=sum(count(c,sym,'raw_symbol','trades',s,e) for sym in raw_symbols) if raw_symbols else None
        cont_m1=count(c,CONT,'continuous','ohlcv-1m',s,e)
        raw_m1=sum(count(c,sym,'raw_symbol','ohlcv-1m',s,e) for sym in raw_symbols) if raw_symbols else None
        rows.append({'research_trading_date':date,'year':int(r.year),'continuous_trades':int(r.trades_record_count),'continuous_ohlcv_1m':cont_m1,'instrument_ids':'|'.join(ids),'raw_symbols':'|'.join(raw_symbols),'raw_symbol_trades':raw_trade,'raw_symbol_ohlcv_1m':raw_m1,'continuous_vs_raw_trade_equal':bool(raw_trade==int(r.trades_record_count)) if raw_trade is not None else None})
    f=pd.DataFrame(rows);f.to_csv(out/'low_session_symbology_diagnostic.csv',index=False)
    result={'version':'COMEX_LOW_SESSION_SYMBOLOGY_DIAGNOSTIC_V1','metadata_only':True,'market_data_download_performed':False,'threshold_trades':a.threshold,'sessions':rows,'note':'No session is excluded by this diagnostic. It distinguishes sparse/closed raw markets from continuous-symbol mapping anomalies.'}
    (out/'low_session_symbology_diagnostic.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
