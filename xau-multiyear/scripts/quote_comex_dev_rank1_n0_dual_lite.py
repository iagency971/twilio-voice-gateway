#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math,os,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import databento as db

NY=ZoneInfo('America/New_York');DATASET='GLBX.MDP3';PILOT_SPEND=4.01;CREDIT=125.0

def bounds(date):
    d=pd.Timestamp(date);prev=(d-pd.Timedelta(days=1)).date();cur=d.date();s=pd.Timestamp(f'{prev} 18:00:00',tz=NY).tz_convert('UTC');close='17:15:00' if d.date()<pd.Timestamp('2015-09-21').date() else '17:00:00';e=pd.Timestamp(f'{cur} {close}',tz=NY).tz_convert('UTC');return s,e

def retry(fn,**kw):
    err=None
    for k in range(6):
        try:return fn(**kw)
        except Exception as e:err=e;time.sleep(min(10,2**k))
    raise RuntimeError(str(err))

def quote_raw(c,date,iid,label):
    s,e=bounds(date);common=dict(dataset=DATASET,symbols=str(iid),stype_in='instrument_id',schema='trades',start=s.isoformat(),end=e.isoformat())
    return {'research_trading_date':date,'label':label,'instrument_id':str(iid),'cost_usd':float(retry(c.metadata.get_cost,**common)),'records':int(retry(c.metadata.get_record_count,**common)),'start_utc':s.isoformat(),'end_utc':e.isoformat()}

def cap(x):return math.ceil((x+0.005)*100)/100

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mapping',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    key=os.environ.get('DATABENTO_API_KEY');
    if not key:raise SystemExit('missing key')
    c=db.Historical(key);p=pd.read_csv(a.mapping);p.research_trading_date=p.research_trading_date.astype(str)
    if len(p)!=96:raise SystemExit(f'expected 96 rows, got {len(p)}')
    paid=p[p.already_paid].copy();tasks=[];reused=[]
    # N0 primary: paid V0 tape is reusable only when N0 and V0 start contract are the same.
    for r in p.itertuples():
        same=str(r.v0_start_iid)==str(r.n0_start_iid)
        if bool(r.already_paid) and same:
            reused.append({'research_trading_date':r.research_trading_date,'label':'N0','instrument_id':str(r.n0_start_iid),'cost_usd':0.0,'records':None,'reused_paid':True})
        else:
            tasks.append((r.research_trading_date,str(r.n0_start_iid),'N0'))
    # DUAL adds V0 only where mappings differ; paid V0 is always already available for paid dates.
    for r in p[~p.same_start_contract].itertuples():
        if bool(r.already_paid):
            reused.append({'research_trading_date':r.research_trading_date,'label':'V0_ALT','instrument_id':str(r.v0_start_iid),'cost_usd':0.0,'records':None,'reused_paid':True})
        else:
            tasks.append((r.research_trading_date,str(r.v0_start_iid),'V0_ALT'))
    rows=[];errs=[]
    with ThreadPoolExecutor(max_workers=6) as ex:
        fs=[ex.submit(quote_raw,c,*x) for x in tasks]
        for f in as_completed(fs):
            try:
                z=f.result();z['reused_paid']=False;rows.append(z)
            except Exception as e:errs.append(str(e))
    if errs:raise SystemExit(f'failures={len(errs)} {errs[:3]}')
    q=pd.DataFrame(rows+reused);q.to_csv(out/'dev_rank1_n0_dual_quotes.csv',index=False)
    common=dict(dataset=DATASET,symbols='GC.n.0',stype_in='continuous',schema='ohlcv-1m',start='2010-06-06',end='2019-01-01')
    m1_cost=float(retry(c.metadata.get_cost,**common));m1_records=int(retry(c.metadata.get_record_count,**common))
    n0_new=float(q[(q.label=='N0')&(~q.reused_paid)].cost_usd.sum());alt=float(q[(q.label=='V0_ALT')&(~q.reused_paid)].cost_usd.sum())
    n0_total=n0_new+m1_cost;dual_total=n0_new+alt+m1_cost
    n0_zeros=q[(q.label=='N0')&(~q.reused_paid)&(pd.to_numeric(q.records,errors='coerce').fillna(0)==0)].research_trading_date.astype(str).tolist()
    result={'version':'COMEX_DEV_RANK1_N0_DUAL_LITE_QUOTE_V1','metadata_only':True,'market_data_download_performed':False,'continuous_context':{'symbol':'GC.n.0','schema':'ohlcv-1m','start':'2010-06-06','end':'2019-01-01','cost_usd':m1_cost,'records':m1_records},'n0_frozen':{'analytical_sessions':96,'new_n0_requests':int(((q.label=='N0')&(~q.reused_paid)).sum()),'reused_paid_sessions':int(((q.label=='N0')&q.reused_paid).sum()),'new_tape_cost_usd':n0_new,'total_new_quote_usd':n0_total,'recommended_hard_cap_usd':cap(n0_total),'project_spend_after_purchase_usd':PILOT_SPEND+n0_total,'credit_remaining_usd':CREDIT-PILOT_SPEND-n0_total,'zero_record_dates':n0_zeros},'dual_roll_robustness':{'rule':'Acquire N0 frozen contract on all sessions; where V0!=N0 at session start, also acquire V0. At each causal decision, active contract is candidate with greater cumulative volume from canonical session start through the immediately preceding completed minute; tie-break N0. Terminal native-zone source contract is full-session volume winner, known only after session close.','divergent_sessions':int((~p.same_start_contract).sum()),'new_v0_alt_requests':int(((q.label=='V0_ALT')&(~q.reused_paid)).sum()),'reused_paid_v0_alt_sessions':int(((q.label=='V0_ALT')&q.reused_paid).sum()),'v0_alt_cost_usd':alt,'total_new_quote_usd':dual_total,'recommended_hard_cap_usd':cap(dual_total),'project_spend_after_purchase_usd':PILOT_SPEND+dual_total,'credit_remaining_usd':CREDIT-PILOT_SPEND-dual_total},'paid_n0_topups':q[(q.label=='N0')&(~q.reused_paid)&q.research_trading_date.isin(set(paid.research_trading_date))][['research_trading_date','instrument_id','cost_usd','records']].to_dict('records'),'notes':['No selected date is removed for low/zero activity.','All selected-session profile/flow features use raw contracts, never a mid-session-spliced continuous stream.','Selected-session M1 is reconstructed from raw trades when continuous OHLCV is incomplete.','This quote is metadata-only and authorizes no download.']}
    (out/'dev_rank1_n0_dual_lite_quote.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
