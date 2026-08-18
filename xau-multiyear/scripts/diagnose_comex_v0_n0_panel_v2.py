#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import databento as db

NY=ZoneInfo('America/New_York');DATASET='GLBX.MDP3';SYMS=['GC.v.0','GC.n.0']

def bounds(d):
    d=pd.Timestamp(d);prev=(d-pd.Timedelta(days=1)).date();cur=d.date();return pd.Timestamp(f'{prev} 17:00:00',tz=NY).tz_convert('UTC'),pd.Timestamp(f'{cur} 18:00:00',tz=NY).tz_convert('UTC')

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

def resolve_segments(c,sym):
    z=norm(c.symbology.resolve(dataset=DATASET,symbols=[sym],stype_in='continuous',stype_out='instrument_id',start_date='2011-01-01',end_date='2019-01-02'))
    return z.get('result',{}).get(sym,[])

def mapped_id(segments,date):
    d=pd.Timestamp(date).date()
    for x in segments:
        try:
            if pd.Timestamp(x['d0']).date()<=d<pd.Timestamp(x['d1']).date():return str(x['s'])
        except Exception:pass
    return ''

def one(client,date,sym):
    a,b=bounds(date);tag='v0' if sym=='GC.v.0' else 'n0'
    common=dict(dataset=DATASET,symbols=sym,stype_in='continuous',start=a.isoformat(),end=b.isoformat())
    tr=int(retry(client.metadata.get_record_count,schema='trades',**common))
    m1=int(retry(client.metadata.get_record_count,schema='ohlcv-1m',**common))
    cost=float(retry(client.metadata.get_cost,schema='trades',**common))
    return date,tag,tr,m1,cost

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sessions',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    key=os.environ.get('DATABENTO_API_KEY');
    if not key:raise SystemExit('DATABENTO_API_KEY missing')
    c=db.Historical(key);p=pd.read_csv(a.sessions);p=p[p.acquisition_stage.eq('DEV_RANK1')].copy();p['research_trading_date']=p.research_trading_date.astype(str)
    seg={s:resolve_segments(c,s) for s in SYMS};vals={};errs=[]
    with ThreadPoolExecutor(max_workers=6) as ex:
        fs=[ex.submit(one,c,d,s) for d in p.research_trading_date for s in SYMS]
        for f in as_completed(fs):
            try:
                d,tag,tr,m1,cost=f.result();vals[(d,tag)]=(tr,m1,cost)
            except Exception as e:errs.append(str(e))
    if errs:raise SystemExit(f'metadata failures {len(errs)}: {errs[:3]}')
    rows=[]
    for r in p.itertuples():
        d=str(r.research_trading_date);v=vals[(d,'v0')];n=vals[(d,'n0')]
        rows.append({'research_trading_date':d,'year':int(r.year),'quarter':int(r.quarter),'vol_band':int(r.vol_band),'already_paid':bool(r.already_paid),'v0_instrument_id':mapped_id(seg['GC.v.0'],d),'n0_instrument_id':mapped_id(seg['GC.n.0'],d),'same_mapping':mapped_id(seg['GC.v.0'],d)==mapped_id(seg['GC.n.0'],d),'v0_trades':v[0],'n0_trades':n[0],'v0_m1':v[1],'n0_m1':n[1],'v0_cost':v[2],'n0_cost':n[2],'n0_to_v0_trade_ratio':float(n[0]/max(v[0],1)),'record_winner':'N0' if n[0]>v[0] else ('V0' if v[0]>n[0] else 'TIE')})
    q=pd.DataFrame(rows);q.to_csv(out/'dev_rank1_v0_n0_panel_v2.csv',index=False);new=q[~q.already_paid]
    result={'version':'COMEX_DEV_RANK1_V0_N0_PANEL_DIAGNOSTIC_V2','metadata_only':True,'market_data_download_performed':False,'sessions':int(len(q)),'same_mapping_sessions':int(q.same_mapping.sum()),'different_mapping_sessions':int((~q.same_mapping).sum()),'n0_more_trades_sessions':int((q.n0_trades>q.v0_trades).sum()),'v0_more_trades_sessions':int((q.v0_trades>q.n0_trades).sum()),'ties':int((q.v0_trades==q.n0_trades).sum()),'n0_at_least_2x_v0_sessions':int((q.n0_to_v0_trade_ratio>=2).sum()),'n0_at_least_5x_v0_sessions':int((q.n0_to_v0_trade_ratio>=5).sum()),'n0_at_least_20x_v0_sessions':int((q.n0_to_v0_trade_ratio>=20).sum()),'largest_n0_to_v0':q.sort_values('n0_to_v0_trade_ratio',ascending=False).head(15)[['research_trading_date','year','v0_trades','n0_trades','n0_to_v0_trade_ratio','v0_instrument_id','n0_instrument_id']].to_dict('records'),'new_session_costs_usd':{'v0_trades':float(new.v0_cost.sum()),'n0_trades':float(new.n0_cost.sum())},'note':'Metadata-only. v.0 ranks by previous-day volume; n.0 ranks by previous-day close open interest. Full-day record counts are diagnostic only and are not used as an ex-post live switching rule.'}
    (out/'dev_rank1_v0_n0_panel_v2.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
