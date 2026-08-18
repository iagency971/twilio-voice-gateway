#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import databento as db

NY=ZoneInfo('America/New_York');DATASET='GLBX.MDP3';ROLLS={'V0':'GC.v.0','N0':'GC.n.0'}

def bounds(date):
    d=pd.Timestamp(date);prev=(d-pd.Timedelta(days=1)).date();cur=d.date()
    s=pd.Timestamp(f'{prev} 18:00:00',tz=NY).tz_convert('UTC')
    close='17:15:00' if d.date()<pd.Timestamp('2015-09-21').date() else '17:00:00'
    e=pd.Timestamp(f'{cur} {close}',tz=NY).tz_convert('UTC');return s,e

def norm(x):
    try:return x.model_dump()
    except Exception:
        try:return dict(x)
        except Exception:return json.loads(json.dumps(x,default=lambda o:getattr(o,'__dict__',str(o))))

def segments(c,sym):
    z=norm(c.symbology.resolve(dataset=DATASET,symbols=[sym],stype_in='continuous',stype_out='instrument_id',start_date='2010-12-30',end_date='2019-01-02'))
    return z.get('result',{}).get(sym,[])

def iid(seg,d):
    d=pd.Timestamp(d).date()
    for x in seg:
        if pd.Timestamp(x['d0']).date()<=d<pd.Timestamp(x['d1']).date():return str(x['s'])
    return ''

def retry(fn,**kw):
    err=None
    for k in range(6):
        try:return fn(**kw)
        except Exception as e:err=e;time.sleep(min(10,2**k))
    raise RuntimeError(str(err))

def metric(c,date,label,i):
    s,e=bounds(date);common=dict(dataset=DATASET,symbols=i,stype_in='instrument_id',start=s.isoformat(),end=e.isoformat())
    try:
        tr=int(retry(c.metadata.get_record_count,schema='trades',**common));m1=int(retry(c.metadata.get_record_count,schema='ohlcv-1m',**common));cost=float(retry(c.metadata.get_cost,schema='trades',**common));return {'date':date,'label':label,'iid':i,'trades':tr,'m1':m1,'cost':cost,'error':None}
    except Exception as e:return {'date':date,'label':label,'iid':i,'trades':None,'m1':None,'cost':None,'error':str(e)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sessions',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    key=os.environ.get('DATABENTO_API_KEY');
    if not key:raise SystemExit('missing key')
    c=db.Historical(key);p=pd.read_csv(a.sessions);p=p[p.acquisition_stage.eq('DEV_RANK1')].copy();p.research_trading_date=p.research_trading_date.astype(str)
    seg={k:segments(c,v) for k,v in ROLLS.items()};rows=[]
    for r in p.itertuples():
        s,_=bounds(r.research_trading_date);d=s.date();v=iid(seg['V0'],d);n=iid(seg['N0'],d)
        rows.append({'research_trading_date':r.research_trading_date,'year':int(r.year),'quarter':int(r.quarter),'vol_band':int(r.vol_band),'already_paid':bool(r.already_paid),'session_start_utc':s.isoformat(),'mapping_date_utc':str(d),'v0_start_iid':v,'n0_start_iid':n,'same_start_contract':v==n})
    q=pd.DataFrame(rows);diff=q[~q.same_start_contract].copy();metrics=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        fs=[ex.submit(metric,c,r.research_trading_date,label,getattr(r,'v0_start_iid' if label=='V0' else 'n0_start_iid')) for r in diff.itertuples() for label in ['V0','N0']]
        for f in as_completed(fs):metrics.append(f.result())
    md=pd.DataFrame(metrics);detail=[]
    for r in diff.itertuples():
        a1=md[(md.date==r.research_trading_date)&(md.label=='V0')].iloc[0].to_dict();a2=md[(md.date==r.research_trading_date)&(md.label=='N0')].iloc[0].to_dict()
        detail.append({'research_trading_date':r.research_trading_date,'year':int(r.year),'already_paid':bool(r.already_paid),'v0_start_iid':r.v0_start_iid,'n0_start_iid':r.n0_start_iid,'v0_trades':a1['trades'],'n0_trades':a2['trades'],'v0_m1':a1['m1'],'n0_m1':a2['m1'],'v0_cost':a1['cost'],'n0_cost':a2['cost'],'v0_error':a1['error'],'n0_error':a2['error'],'n0_to_v0_ratio':None if a1['trades'] is None or a2['trades'] is None else float(a2['trades']/max(a1['trades'],1))})
    q.to_csv(out/'frozen_session_mapping_all.csv',index=False);pd.DataFrame(detail).to_csv(out/'frozen_session_mapping_differences.csv',index=False)
    valid=[x for x in detail if not x['v0_error'] and not x['n0_error']]
    result={'version':'COMEX_FROZEN_SESSION_CONTRACT_DIAGNOSTIC_V2','metadata_only':True,'market_data_download_performed':False,'sessions':int(len(q)),'same_start_contract_sessions':int(q.same_start_contract.sum()),'different_start_contract_sessions':int((~q.same_start_contract).sum()),'difference_details':detail,'valid_diff_sessions':len(valid),'n0_wins_on_diff':sum((x['n0_trades'] or 0)>(x['v0_trades'] or 0) for x in valid),'v0_wins_on_diff':sum((x['v0_trades'] or 0)>(x['n0_trades'] or 0) for x in valid),'paid_dev_mapping_differences':q[q.already_paid & ~q.same_start_contract][['research_trading_date','v0_start_iid','n0_start_iid']].to_dict('records'),'note':'Only differing session-start mappings are queried. Contract is frozen at session start; no intraday switching and no XAU outcome is used.'}
    (out/'frozen_session_contracts_v2.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
