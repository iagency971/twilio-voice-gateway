#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,time
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import databento as db

NY=ZoneInfo('America/New_York'); DATASET='GLBX.MDP3'; SYMBOL='GC.v.0'; STYPE='continuous'

def bounds(d):
    d=pd.Timestamp(d); prev=(d-pd.Timedelta(days=1)).date(); cur=d.date()
    return pd.Timestamp(f'{prev} 17:00:00',tz=NY).tz_convert('UTC'),pd.Timestamp(f'{cur} 18:00:00',tz=NY).tz_convert('UTC')

def count(c,schema,a,b):
    err=None
    for k in range(7):
        try:return int(c.metadata.get_record_count(dataset=DATASET,symbols=SYMBOL,stype_in=STYPE,schema=schema,start=a.isoformat(),end=b.isoformat()))
        except Exception as e:err=e;time.sleep(min(20,2**k))
    raise RuntimeError(err)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sessions',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    key=os.environ.get('DATABENTO_API_KEY');
    if not key:raise SystemExit('DATABENTO_API_KEY missing')
    c=db.Historical(key);p=pd.read_csv(a.sessions);p=p[p.acquisition_stage.eq('DEV_RANK1')].copy();rows=[]
    for r in p.itertuples():
        s,e=bounds(r.research_trading_date);tr=count(c,'trades',s,e);m1=count(c,'ohlcv-1m',s,e)
        rows.append({'research_trading_date':str(r.research_trading_date),'year':int(r.year),'quarter':int(r.quarter),'vol_band':int(r.vol_band),'analysis_rank':int(r.analysis_rank),'already_paid':bool(r.already_paid),'trades_records':tr,'ohlcv_1m_records':m1,'trades_per_active_m1':float(tr/m1) if m1 else None})
    q=pd.DataFrame(rows);q.to_csv(out/'dev_rank1_session_availability.csv',index=False)
    def qs(col):
        s=q[col];return {str(x):float(s.quantile(x)) for x in [0,0.01,0.05,0.10,0.25,0.5,0.75,0.9,0.95,0.99,1]}
    result={'version':'COMEX_DEV_RANK1_SESSION_AVAILABILITY_V1','metadata_only':True,'market_data_download_performed':False,'sessions':len(q),'trades_quantiles':qs('trades_records'),'ohlcv_m1_quantiles':qs('ohlcv_1m_records'),'zero_trade_sessions':q.loc[q.trades_records.eq(0),'research_trading_date'].tolist(),'zero_m1_sessions':q.loc[q.ohlcv_1m_records.eq(0),'research_trading_date'].tolist(),'under_5000_trades':q.loc[q.trades_records.lt(5000),['research_trading_date','trades_records','ohlcv_1m_records']].to_dict('records'),'under_300_active_m1':q.loc[q.ohlcv_1m_records.lt(300),['research_trading_date','trades_records','ohlcv_1m_records']].to_dict('records'),'note':'Threshold lists are diagnostics only; this script does not change session selection.'}
    (out/'dev_rank1_session_availability.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
