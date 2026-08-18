#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,time
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import databento as db

NY=ZoneInfo('America/New_York'); DATASET='GLBX.MDP3'; SYMBOLS=['GC.v.0','GC.v.1','GC.v.2','GC.n.0','GC.c.0']; PARENT='GC.FUT'

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

def norm(res):
    try:return res.model_dump()
    except Exception:
        try:return dict(res)
        except Exception:return json.loads(json.dumps(res,default=lambda o:getattr(o,'__dict__',str(o))))

def resolve(c,symbol,date):
    d0=str(pd.Timestamp(date).date());d1=str((pd.Timestamp(date)+pd.Timedelta(days=1)).date())
    z=norm(c.symbology.resolve(dataset=DATASET,symbols=[symbol],stype_in='continuous',stype_out='instrument_id',start_date=d0,end_date=d1))
    seg=z.get('result',{}).get(symbol,[]);return sorted({str(x['s']) for x in seg if isinstance(x,dict) and x.get('s') is not None})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dates',nargs='+',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);key=os.environ.get('DATABENTO_API_KEY')
    if not key:raise SystemExit('DATABENTO_API_KEY missing')
    c=db.Historical(key);rows=[]
    for date in a.dates:
        s,e=bounds(date);parent_tr=count(c,PARENT,'parent','trades',s,e);parent_m1=count(c,PARENT,'parent','ohlcv-1m',s,e)
        for sym in SYMBOLS:
            rows.append({'research_trading_date':date,'symbol':sym,'instrument_ids':'|'.join(resolve(c,sym,date)),'trades_records':count(c,sym,'continuous','trades',s,e),'ohlcv_1m_records':count(c,sym,'continuous','ohlcv-1m',s,e),'parent_trades_all_children':parent_tr,'parent_ohlcv_1m_all_children':parent_m1})
    q=pd.DataFrame(rows);q.to_csv(out/'roll_symbol_candidate_counts.csv',index=False)
    result={'version':'COMEX_ROLL_SYMBOL_CANDIDATE_DIAGNOSTIC_V1','metadata_only':True,'market_data_download_performed':False,'dates':a.dates,'symbols':SYMBOLS,'rows':rows,'note':'Counts only. No symbol-selection rule is changed by this diagnostic.'}
    (out/'roll_symbol_candidate_counts.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
