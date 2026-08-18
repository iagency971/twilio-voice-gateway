#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math,os,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import databento as db

NY=ZoneInfo('America/New_York');DATASET='GLBX.MDP3';STYPE_RAW='instrument_id';CREDIT=125.0;PILOT_SPEND=4.01

def bounds(date):
    d=pd.Timestamp(date);prev=(d-pd.Timedelta(days=1)).date();cur=d.date();s=pd.Timestamp(f'{prev} 18:00:00',tz=NY).tz_convert('UTC');close='17:15:00' if d.date()<pd.Timestamp('2015-09-21').date() else '17:00:00';e=pd.Timestamp(f'{cur} {close}',tz=NY).tz_convert('UTC');return s,e

def retry(fn,**kw):
    err=None
    for k in range(7):
        try:return fn(**kw)
        except Exception as e:err=e;time.sleep(min(20,2**k))
    raise RuntimeError(str(err))

def metric(c,iid,start,end):
    common=dict(dataset=DATASET,symbols=str(iid),stype_in=STYPE_RAW,schema='trades',start=start.isoformat(),end=end.isoformat())
    return float(retry(c.metadata.get_cost,**common)),int(retry(c.metadata.get_record_count,**common)),int(retry(c.metadata.get_billable_size,**common))

def qone(c,row,label):
    iid=str(row.n0_start_iid if label=='N0' else row.v0_start_iid);s,e=bounds(row.research_trading_date);cost,records,billable=metric(c,iid,s,e);return {'research_trading_date':str(row.research_trading_date),'year':int(row.year),'quarter':int(row.quarter),'vol_band':int(row.vol_band),'label':label,'instrument_id':iid,'start_utc':s.isoformat(),'end_utc':e.isoformat(),'cost_usd':cost,'records':records,'billable_bytes':billable}

def m1(c,symbol):
    common=dict(dataset=DATASET,symbols=symbol,stype_in='continuous',schema='ohlcv-1m',start='2010-06-06',end='2019-01-01')
    return {'symbol':symbol,'cost_usd':float(retry(c.metadata.get_cost,**common)),'records':int(retry(c.metadata.get_record_count,**common)),'billable_bytes':int(retry(c.metadata.get_billable_size,**common))}

def cap(x):return math.ceil((x+0.005)*100)/100

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mapping',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);key=os.environ.get('DATABENTO_API_KEY')
    if not key:raise SystemExit('DATABENTO_API_KEY missing')
    c=db.Historical(key);p=pd.read_csv(a.mapping);p=p[p.acquisition_stage.eq('DEV_RANK1')].copy() if 'acquisition_stage' in p.columns else p.copy();p.research_trading_date=p.research_trading_date.astype(str)
    # The frozen-session mapping file has 96 DEV_RANK1 rows. Reuse a paid session only when candidate contract equals paid V0 contract.
    if len(p)!=96:raise SystemExit(f'expected 96 rank1 rows, got {len(p)}')
    rows=[];errs=[]
    with ThreadPoolExecutor(max_workers=6) as ex:
        fs=[]
        for r in p.itertuples():
            for label in ['V0','N0']:
                iid=str(getattr(r,'v0_start_iid' if label=='V0' else 'n0_start_iid'))
                paid=bool(r.already_paid)
                # Pilot was acquired using GC.v.0. V0 always reusable; N0 reusable only if same start contract.
                reusable=paid and (label=='V0' or str(r.n0_start_iid)==str(r.v0_start_iid))
                if reusable:
                    rows.append({'research_trading_date':str(r.research_trading_date),'year':int(r.year),'quarter':int(r.quarter),'vol_band':int(r.vol_band),'label':label,'instrument_id':iid,'already_paid_reusable':True,'new_download_required':False,'cost_usd':0.0,'records':None,'billable_bytes':None})
                else:fs.append(ex.submit(qone,c,r,label))
        for f in as_completed(fs):
            try:
                z=f.result();z['already_paid_reusable']=False;z['new_download_required']=True;rows.append(z)
            except Exception as e:errs.append(str(e))
    if errs:raise SystemExit(f'quote failures {len(errs)}: {errs[:3]}')
    q=pd.DataFrame(rows).sort_values(['label','research_trading_date']);q.to_csv(out/'dev_rank1_frozen_contract_quotes.csv',index=False)
    m1rows=[m1(c,'GC.v.0'),m1(c,'GC.n.0')];pd.DataFrame(m1rows).to_csv(out/'dev_rank1_continuous_m1_quotes.csv',index=False)
    arch=[]
    for label,sym in [('V0','GC.v.0'),('N0','GC.n.0')]:
        z=q[q.label.eq(label)];tape=float(z.cost_usd.sum());mm=next(x for x in m1rows if x['symbol']==sym);total=tape+float(mm['cost_usd']);hard=cap(total)
        arch.append({'architecture':f'{label}_FROZEN_SESSION_RAW_TRADES_PLUS_{sym}_OHLCV1M','continuous_symbol':sym,'analytical_sessions':96,'new_tape_requests':int(z.new_download_required.sum()),'reused_paid_sessions':int(z.already_paid_reusable.sum()),'new_tape_cost_usd':tape,'continuous_ohlcv_1m_cost_usd':float(mm['cost_usd']),'new_total_quote_usd':total,'recommended_hard_cap_usd':hard,'project_spend_after_purchase_usd':PILOT_SPEND+total,'nominal_credit_remaining_usd':CREDIT-PILOT_SPEND-total,'zero_record_new_requests':z[(z.new_download_required)&(pd.to_numeric(z.records,errors='coerce').fillna(0)==0)].research_trading_date.astype(str).tolist()})
    result={'version':'COMEX_DEV_RANK1_FINAL_CONTRACT_CANDIDATE_QUOTES_V1','metadata_only':True,'market_data_download_performed':False,'pilot_actual_spend_usd':PILOT_SPEND,'architectures':arch,'candidate_preference_before_pro_review':'N0 frozen at canonical session start; chosen for causal roll robustness, not XAU outcomes','n0_paid_session_requiring_primary_contract_topup':q[(q.label=='N0')&q.new_download_required&pd.Series(q.research_trading_date).isin(p[p.already_paid].research_trading_date)].research_trading_date.astype(str).tolist(),'notes':['No session is dropped for low/zero activity.','Raw trade contract is frozen at canonical GC session start; no intraday contract switching.','Continuous OHLCV is context only. Selected-session M1 may be reconstructed from raw trades when continuous OHLCV is incomplete.','Prior-session exact tape is not automatically purchased; native-zone retests are deferred to Stage2.']}
    (out/'dev_rank1_final_contract_candidate_quotes.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
