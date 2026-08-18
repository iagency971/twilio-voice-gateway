#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,time
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

def count(c,sym,schema,a,b):return int(retry(c.metadata.get_record_count,dataset=DATASET,symbols=sym,stype_in='continuous',schema=schema,start=a.isoformat(),end=b.isoformat()))
def cost(c,sym,a,b):return float(retry(c.metadata.get_cost,dataset=DATASET,symbols=sym,stype_in='continuous',schema='trades',start=a.isoformat(),end=b.isoformat()))
def norm(res):
    try:return res.model_dump()
    except Exception:
        try:return dict(res)
        except Exception:return json.loads(json.dumps(res,default=lambda o:getattr(o,'__dict__',str(o))))
def maps(c,sym,a,b):
    d0=str(a.date());d1=str((b+pd.Timedelta(days=1)).date());z=norm(c.symbology.resolve(dataset=DATASET,symbols=[sym],stype_in='continuous',stype_out='instrument_id',start_date=d0,end_date=d1));return sorted({str(x['s']) for x in z.get('result',{}).get(sym,[]) if isinstance(x,dict) and x.get('s') is not None})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sessions',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);key=os.environ.get('DATABENTO_API_KEY');
    if not key:raise SystemExit('DATABENTO_API_KEY missing')
    c=db.Historical(key);p=pd.read_csv(a.sessions);p=p[p.acquisition_stage.eq('DEV_RANK1')].copy();rows=[]
    for r in p.itertuples():
        s,e=bounds(str(r.research_trading_date));d={'research_trading_date':str(r.research_trading_date),'year':int(r.year),'quarter':int(r.quarter),'vol_band':int(r.vol_band),'already_paid':bool(r.already_paid)}
        for sym in SYMS:
            tag='v0' if '.v.' in sym else 'n0';d[tag+'_instrument_ids']='|'.join(maps(c,sym,s,e));d[tag+'_trades']=count(c,sym,'trades',s,e);d[tag+'_m1']=count(c,sym,'ohlcv-1m',s,e);d[tag+'_trades_cost']=cost(c,sym,s,e)
        d['same_mapping_set']=d['v0_instrument_ids']==d['n0_instrument_ids'];d['n0_to_v0_trade_ratio']=float(d['n0_trades']/max(d['v0_trades'],1));d['dominant_by_records']='N0' if d['n0_trades']>d['v0_trades'] else ('V0' if d['v0_trades']>d['n0_trades'] else 'TIE');rows.append(d)
    q=pd.DataFrame(rows);q.to_csv(out/'dev_rank1_v0_n0_panel.csv',index=False);new=q[~q.already_paid]
    result={'version':'COMEX_DEV_RANK1_V0_N0_PANEL_DIAGNOSTIC_V1','metadata_only':True,'market_data_download_performed':False,'sessions':len(q),'same_mapping_sessions':int(q.same_mapping_set.sum()),'different_mapping_sessions':int((~q.same_mapping_set).sum()),'n0_more_trades_sessions':int((q.n0_trades>q.v0_trades).sum()),'v0_more_trades_sessions':int((q.v0_trades>q.n0_trades).sum()),'n0_at_least_2x_v0_sessions':int((q.n0_to_v0_trade_ratio>=2).sum()),'n0_at_least_5x_v0_sessions':int((q.n0_to_v0_trade_ratio>=5).sum()),'n0_at_least_20x_v0_sessions':int((q.n0_to_v0_trade_ratio>=20).sum()),'largest_n0_to_v0':q.sort_values('n0_to_v0_trade_ratio',ascending=False).head(15)[['research_trading_date','year','v0_trades','n0_trades','n0_to_v0_trade_ratio','v0_instrument_ids','n0_instrument_ids']].to_dict('records'),'new_92_costs_usd':{'v0_trades':float(new.v0_trades_cost.sum()),'n0_trades':float(new.n0_trades_cost.sum()),'v0_plus_n0_naive_sum':float((new.v0_trades_cost+new.n0_trades_cost).sum())},'note':'Diagnostic only. Full-day record counts cannot be used as a live contract-selection rule. They diagnose how often previous-day volume and open-interest continuous mappings diverge.'}
    (out/'dev_rank1_v0_n0_panel.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
