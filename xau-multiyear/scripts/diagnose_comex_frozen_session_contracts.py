#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import databento as db

NY=ZoneInfo('America/New_York');DATASET='GLBX.MDP3';ROLLS={'V0':'GC.v.0','N0':'GC.n.0'}

def canonical_bounds(date):
    d=pd.Timestamp(date);prev=(d-pd.Timedelta(days=1)).date();cur=d.date()
    start=pd.Timestamp(f'{prev} 18:00:00',tz=NY).tz_convert('UTC')
    end_local='17:15:00' if d.date()<pd.Timestamp('2015-09-21').date() else '17:00:00'
    end=pd.Timestamp(f'{cur} {end_local}',tz=NY).tz_convert('UTC')
    return start,end

def retry(fn,**kw):
    err=None
    for k in range(7):
        try:return fn(**kw)
        except Exception as e:err=e;time.sleep(min(20,2**k))
    raise RuntimeError(err)

def norm(res):
    try:return res.model_dump()
    except Exception:
        try:return dict(res)
        except Exception:return json.loads(json.dumps(res,default=lambda o:getattr(o,'__dict__',str(o))))

def segments(client,sym):
    z=norm(client.symbology.resolve(dataset=DATASET,symbols=[sym],stype_in='continuous',stype_out='instrument_id',start_date='2010-12-30',end_date='2019-01-02'))
    return z.get('result',{}).get(sym,[])

def id_on_date(seg,d):
    d=pd.Timestamp(d).date()
    for x in seg:
        try:
            if pd.Timestamp(x['d0']).date()<=d<pd.Timestamp(x['d1']).date():return str(x['s'])
        except Exception:pass
    return ''

def metric(client,iid,start,end):
    common=dict(dataset=DATASET,symbols=iid,stype_in='instrument_id',start=start.isoformat(),end=end.isoformat())
    tr=int(retry(client.metadata.get_record_count,schema='trades',**common));m1=int(retry(client.metadata.get_record_count,schema='ohlcv-1m',**common));cost=float(retry(client.metadata.get_cost,schema='trades',**common));return tr,m1,cost

def job(client,date,iid,label):
    s,e=canonical_bounds(date);tr,m1,cost=metric(client,iid,s,e);return date,label,iid,tr,m1,cost,s.isoformat(),e.isoformat()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sessions',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    key=os.environ.get('DATABENTO_API_KEY');
    if not key:raise SystemExit('DATABENTO_API_KEY missing')
    c=db.Historical(key);p=pd.read_csv(a.sessions);p=p[p.acquisition_stage.eq('DEV_RANK1')].copy();p['research_trading_date']=p.research_trading_date.astype(str)
    seg={k:segments(c,v) for k,v in ROLLS.items()};tasks=[];mapping={}
    for r in p.itertuples():
        s,_=canonical_bounds(r.research_trading_date);start_date=s.date()
        for label in ROLLS:
            iid=id_on_date(seg[label],start_date);mapping[(r.research_trading_date,label)]=iid
            if not iid:raise SystemExit(f'no {label} mapping at session start for {r.research_trading_date} UTCdate={start_date}')
    vals={};errs=[]
    with ThreadPoolExecutor(max_workers=6) as ex:
        fs=[]
        for r in p.itertuples():
            for label in ROLLS:fs.append(ex.submit(job,c,str(r.research_trading_date),mapping[(str(r.research_trading_date),label)],label))
        for f in as_completed(fs):
            try:
                d,label,iid,tr,m1,cost,s,e=f.result();vals[(d,label)]=(iid,tr,m1,cost,s,e)
            except Exception as exc:errs.append(str(exc))
    if errs:raise SystemExit(f'failures={len(errs)} {errs[:3]}')
    rows=[]
    for r in p.itertuples():
        d=str(r.research_trading_date);v=vals[(d,'V0')];n=vals[(d,'N0')]
        rows.append({'research_trading_date':d,'year':int(r.year),'quarter':int(r.quarter),'vol_band':int(r.vol_band),'already_paid':bool(r.already_paid),'session_start_utc':v[4],'session_end_utc':v[5],'v0_start_instrument_id':v[0],'n0_start_instrument_id':n[0],'same_start_contract':v[0]==n[0],'v0_frozen_trades':v[1],'n0_frozen_trades':n[1],'v0_frozen_m1':v[2],'n0_frozen_m1':n[2],'v0_frozen_cost':v[3],'n0_frozen_cost':n[3],'n0_to_v0_trade_ratio':float(n[1]/max(v[1],1)),'winner':'N0' if n[1]>v[1] else ('V0' if v[1]>n[1] else 'TIE')})
    q=pd.DataFrame(rows);q.to_csv(out/'frozen_session_contracts.csv',index=False);new=q[~q.already_paid]
    diff=q[~q.same_start_contract]
    result={'version':'COMEX_FROZEN_SESSION_CONTRACT_DIAGNOSTIC_V1','metadata_only':True,'market_data_download_performed':False,'session_rule':'freeze actual instrument mapped by selected causal roll rule at canonical GC session start; never switch instrument within session','sessions':int(len(q)),'same_start_contract_sessions':int(q.same_start_contract.sum()),'different_start_contract_sessions':int((~q.same_start_contract).sum()),'n0_more_trades_sessions':int((q.n0_frozen_trades>q.v0_frozen_trades).sum()),'v0_more_trades_sessions':int((q.v0_frozen_trades>q.n0_frozen_trades).sum()),'ties':int((q.v0_frozen_trades==q.n0_frozen_trades).sum()),'different_mapping_comparison':diff[['research_trading_date','year','v0_start_instrument_id','n0_start_instrument_id','v0_frozen_trades','n0_frozen_trades','n0_to_v0_trade_ratio']].to_dict('records'),'new_session_costs_usd':{'v0_frozen_raw_trades':float(new.v0_frozen_cost.sum()),'n0_frozen_raw_trades':float(new.n0_frozen_cost.sum())},'paid_dev_sessions':q[q.already_paid][['research_trading_date','v0_start_instrument_id','n0_start_instrument_id','same_start_contract']].to_dict('records'),'note':'Rule comparison uses only market-data availability/liquidity metadata, not XAU outcomes. v.0 and n.0 are both causal smart-symbol mappings based on prior-day information.'}
    (out/'frozen_session_contracts.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
