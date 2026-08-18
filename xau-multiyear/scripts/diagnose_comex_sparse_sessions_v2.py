#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, os, time
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import databento as db

NY=ZoneInfo('America/New_York'); DATASET='GLBX.MDP3'; CONT='GC.v.0'; PARENT='GC.FUT'

def bounds(d):
    d=pd.Timestamp(d); prev=(d-pd.Timedelta(days=1)).date(); cur=d.date()
    return pd.Timestamp(f'{prev} 17:00:00',tz=NY).tz_convert('UTC'),pd.Timestamp(f'{cur} 18:00:00',tz=NY).tz_convert('UTC')

def retry(fn,**kw):
    err=None
    for k in range(7):
        try:return fn(**kw)
        except Exception as e:err=e;time.sleep(min(20,2**k))
    raise RuntimeError(err)

def count(c,symbol,stype,schema,a,b):
    return int(retry(c.metadata.get_record_count,dataset=DATASET,symbols=symbol,stype_in=stype,schema=schema,start=a.isoformat(),end=b.isoformat()))

def norm(res):
    try:return res.model_dump()
    except Exception:
        try:return dict(res)
        except Exception:return json.loads(json.dumps(res,default=lambda o:getattr(o,'__dict__',str(o))))

def resolve(c,symbols,stype_in,stype_out,d0,d1):
    return norm(c.symbology.resolve(dataset=DATASET,symbols=symbols,stype_in=stype_in,stype_out=stype_out,start_date=d0,end_date=d1))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--availability',required=True); ap.add_argument('--out',required=True); ap.add_argument('--trade-threshold',type=int,default=5000); ap.add_argument('--m1-threshold',type=int,default=300); a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);key=os.environ.get('DATABENTO_API_KEY');
    if not key:raise SystemExit('DATABENTO_API_KEY missing')
    c=db.Historical(key); q=pd.read_csv(a.availability); flag=q[(q.trades_records<a.trade_threshold)|(q.ohlcv_1m_records<a.m1_threshold)].copy(); rows=[]
    for r in flag.itertuples():
        date=str(r.research_trading_date); d0=str(pd.Timestamp(date).date()); d1=str((pd.Timestamp(date)+pd.Timedelta(days=1)).date()); s,e=bounds(date)
        cm=resolve(c,[CONT],'continuous','instrument_id',d0,d1); segs=cm.get('result',{}).get(CONT,[]); ids=sorted({str(x['s']) for x in segs if isinstance(x,dict) and x.get('s') is not None})
        raw=[]
        for iid in ids:
            rm=resolve(c,[iid],'instrument_id','raw_symbol',d0,d1); raw += [str(x['s']) for x in rm.get('result',{}).get(iid,[]) if isinstance(x,dict) and x.get('s') is not None]
        raw=sorted(set(raw))
        mapped_raw_trades=sum(count(c,x,'raw_symbol','trades',s,e) for x in raw) if raw else None
        mapped_raw_m1=sum(count(c,x,'raw_symbol','ohlcv-1m',s,e) for x in raw) if raw else None
        parent_trades=count(c,PARENT,'parent','trades',s,e)
        parent_m1=count(c,PARENT,'parent','ohlcv-1m',s,e)
        rows.append({
            'research_trading_date':date,'year':int(r.year),'continuous_trades':int(r.trades_records),'continuous_ohlcv_1m':int(r.ohlcv_1m_records),
            'mapped_instrument_ids':ids,'mapped_raw_symbols':raw,'mapped_raw_trades':mapped_raw_trades,'mapped_raw_ohlcv_1m':mapped_raw_m1,
            'parent_GC_FUT_trades_all_children':parent_trades,'parent_GC_FUT_ohlcv_1m_all_children':parent_m1,
            'continuous_equals_mapped_raw_trades':bool(mapped_raw_trades==int(r.trades_records)) if mapped_raw_trades is not None else None,
            'continuous_equals_mapped_raw_m1':bool(mapped_raw_m1==int(r.ohlcv_1m_records)) if mapped_raw_m1 is not None else None,
            'parent_to_continuous_trade_ratio':float(parent_trades/max(int(r.trades_records),1)),
            'parent_to_continuous_m1_ratio':float(parent_m1/max(int(r.ohlcv_1m_records),1)),
        })
    flat=pd.DataFrame(rows)
    for col in ['mapped_instrument_ids','mapped_raw_symbols']:
        if col in flat: flat[col]=flat[col].map(json.dumps)
    flat.to_csv(out/'sparse_session_parent_diagnostic.csv',index=False)
    result={'version':'COMEX_SPARSE_SESSION_PARENT_DIAGNOSTIC_V2','metadata_only':True,'market_data_download_performed':False,'trade_threshold':a.trade_threshold,'m1_threshold':a.m1_threshold,'sessions':rows,'interpretation_rule':'Do not drop a date for low activity alone. Compare continuous, mapped raw contract, and GC.FUT parent counts before classifying closure, short session, mapping issue, or OHLCV-schema gap.'}
    (out/'sparse_session_parent_diagnostic.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
