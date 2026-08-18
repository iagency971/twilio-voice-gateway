#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import pandas as pd
import databento as db

PANEL_SEED='COMEX_SESSION_PANEL_V1_SEED_971'
DATASET='GLBX.MDP3'; SYMBOL='GC.v.0'; STYPE='continuous'
OHLCV_FULL=20.342466905713
BBO1M_FULL=7.630651295185
PORTAL_PILOT_COST=4.01
INITIAL_CREDIT=125.0


def h(*parts): return hashlib.sha256('|'.join(str(x) for x in parts).encode()).hexdigest()

def prepare(c):
    x=c.copy()
    for col in ['year','quarter','vol_band','panel_rank']: x[col]=pd.to_numeric(x[col],errors='raise').astype(int)
    x['date_ts']=pd.to_datetime(x.research_trading_date); x['weekday']=x.date_ts.dt.weekday
    old=x[x.panel_rank<=2].copy(); weekend=old[old.weekday>=5].copy()
    v=x[x.weekday<5].copy()
    if 'panel_hash' not in v.columns: v['panel_hash']=[h(PANEL_SEED,r.year,r.quarter,r.vol_band,r.research_trading_date) for r in v.itertuples()]
    v=v.sort_values(['year','quarter','vol_band','panel_hash','research_trading_date']).copy()
    v['panel_rank_v4']=v.groupby(['year','quarter','vol_band']).cumcount()+1
    t=v[v.panel_rank_v4<=2].copy()
    assert len(t)==357, len(t); assert not (t.weekday>=5).any()
    return t,weekend

def era(y):
    if y<=2013:return 'E1_2011_2013'
    if y<=2018:return 'E2_2014_2018'
    if y<=2022:return 'E3_2019_2022'
    return 'E4_2023_2025'

def bounds(date_str):
    from zoneinfo import ZoneInfo
    NY=ZoneInfo('America/New_York'); d=pd.Timestamp(date_str); prev=(d-pd.Timedelta(days=1)).date(); cur=d.date()
    return pd.Timestamp(f'{prev} 17:00:00',tz=NY).tz_convert('UTC'),pd.Timestamp(f'{cur} 18:00:00',tz=NY).tz_convert('UTC')

def qcost(client,row,schema):
    a,b=bounds(row.research_trading_date); err=None
    for k in range(7):
        try:
            x=float(client.metadata.get_cost(dataset=DATASET,symbols=SYMBOL,stype_in=STYPE,schema=schema,start=a.isoformat(),end=b.isoformat()))
            return row.research_trading_date,schema,x,None
        except Exception as e:
            err=str(e); time.sleep(min(20,2**k))
    return row.research_trading_date,schema,None,err

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--sessions',required=True); ap.add_argument('--pilot',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    key=os.environ.get('DATABENTO_API_KEY');
    if not key: raise SystemExit('DATABENTO_API_KEY missing')
    raw=pd.read_csv(a.sessions); panel,old_weekend=prepare(raw); pilot=pd.read_csv(a.pilot); pdates=set(pilot.research_trading_date.astype(str))
    panel['research_trading_date']=panel.research_trading_date.astype(str); panel['era']=panel.year.map(era); panel['already_paid_pilot']=panel.research_trading_date.isin(pdates)
    if not pdates.issubset(set(panel.research_trading_date)): raise SystemExit('pilot dates are not subset of corrected tier2')
    remaining=panel[~panel.already_paid_pilot].copy(); assert len(remaining)==345,len(remaining)
    c=db.Historical(key); vals={}; errs=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        fs=[ex.submit(qcost,c,r,s) for r in remaining.itertuples() for s in ['trades','tbbo']]
        for f in as_completed(fs):
            d,s,x,e=f.result();
            if e: errs.append({'date':d,'schema':s,'error':e})
            else: vals[(d,s)]=x
    if errs: raise SystemExit(f'metadata failures: {errs[:5]} total={len(errs)}')
    rows=[]
    for r in remaining.itertuples():
        for s in ['trades','tbbo']:
            rows.append({'research_trading_date':r.research_trading_date,'year':int(r.year),'quarter':int(r.quarter),'vol_band':int(r.vol_band),'panel_rank_v4':int(r.panel_rank_v4),'era':r.era,'schema':s,'cost_usd':vals[(r.research_trading_date,s)]})
    q=pd.DataFrame(rows); q.to_csv(out/'tier2_remaining_session_schema_costs.csv',index=False)
    panel[['research_trading_date','year','quarter','vol_band','panel_rank_v4','era','already_paid_pilot']].to_csv(out/'tier2_sessions_v4.csv',index=False)
    def cost_for(name,fn):
        z=q[q.apply(lambda r: fn(int(r.year),str(r.schema)),axis=1)]
        sess=float(z.cost_usd.sum()); add=OHLCV_FULL+BBO1M_FULL+sess; total=PORTAL_PILOT_COST+add
        return {'architecture':name,'remaining_session_data_cost_usd':sess,'continuous_ohlcv_1m_usd':OHLCV_FULL,'continuous_bbo_1m_usd':BBO1M_FULL,'new_stage1_cost_usd':add,'pilot_already_spent_usd':PORTAL_PILOT_COST,'total_project_spend_after_stage1_usd':total,'credit_remaining_from_125_usd':INITIAL_CREDIT-total}
    arch=[]
    arch.append(cost_for('TRADES_ALL_357',lambda y,s:s=='trades'))
    arch.append(cost_for('TBBO_ALL_357',lambda y,s:s=='tbbo'))
    arch.append(cost_for('HYBRID_TBBO_2011_2013_TRADES_2014_2025',lambda y,s:(s=='tbbo' if y<=2013 else s=='trades')))
    arch.append(cost_for('HYBRID_TBBO_2011_2018_TRADES_2019_2025',lambda y,s:(s=='tbbo' if y<=2018 else s=='trades')))
    result={'version':'COMEX_V4_TIER2_ARCHITECTURE_COSTS_V1','metadata_only':True,'download_performed':False,'corrected_tier2_sessions':357,'already_paid_pilot_sessions':12,'remaining_sessions_to_buy':345,'old_tier2_weekend_sessions':int(len(old_weekend)),'continuous_costs_usd':{'ohlcv_1m':OHLCV_FULL,'bbo_1m':BBO1M_FULL},'portal_observed_pilot_spend_usd':PORTAL_PILOT_COST,'architectures':arch,'note':'Pilot 12 sessions are excluded from new session-data requests to prevent double spending; all costs here are metadata.get_cost only.'}
    (out/'tier2_architecture_costs.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if __name__=='__main__':main()
