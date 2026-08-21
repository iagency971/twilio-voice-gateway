#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, json
from pathlib import Path
import numpy as np
import pandas as pd
import requests

URL='https://raw.githubusercontent.com/axb0306/cme-futures-ohlc/main/ES/ES_1min_20260120_20260415.csv'
TZ='America/New_York'; POINT_VALUE=50.0
SCENARIOS={'PRIMARY':30.0,'STRESS':55.0}

def stats(a):
    r=np.asarray(a,dtype=float)
    if len(r)==0:return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None,'losing_streak':None}
    ps=r[r>0].sum();ns=-r[r<0].sum();pf=float(ps/ns) if ns>0 else (float('inf') if ps>0 else None)
    eq=np.cumsum(r);peak=np.maximum.accumulate(np.r_[0.0,eq])[:-1];dd=np.maximum(peak-eq,0.0)
    cur=ls=0
    for v in r:
        if v<0:cur+=1;ls=max(ls,cur)
        else:cur=0
    return {'n':int(len(r)),'mean':float(r.mean()),'sum':float(r.sum()),'pf':pf,'win_rate':float((r>0).mean()),'max_dd':float(dd.max(initial=0.0)),'losing_streak':int(ls)}

def load(out):
    rr=requests.get(URL,timeout=180);rr.raise_for_status();raw=rr.content
    d=pd.read_csv(io.BytesIO(raw));d['datetime']=pd.to_datetime(d['datetime'],utc=True,errors='coerce')
    for c in ['open','high','low','close','volume']:d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna(subset=['datetime','open','high','low','close']).sort_values('datetime').drop_duplicates('datetime',keep='last')
    d.index=d['datetime'].dt.tz_convert(TZ);d=d[['open','high','low','close','volume']].between_time('09:30','15:59');d=d[d.index.weekday<5]
    counts=pd.Series(1,index=d.index).groupby(d.index.normalize()).sum()
    (out/'data_qa.json').write_text(json.dumps({'url':URL,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'rows_rth':int(len(d)),'min':str(d.index.min()),'max':str(d.index.max()),'days':int(counts.size),'median_rows_day':float(counts.median()),'days_ge380':int((counts>=380).sum())},indent=2))
    return d

def simulate(d,cost):
    rows=[];prev_close=None
    for day,g in d.groupby(d.index.normalize(),sort=True):
        g=g.sort_index();m={ts.hour*60+ts.minute:ts for ts in g.index};sig=m.get(929);ent=m.get(930);clo=m.get(959)
        if prev_close is not None and sig is not None and ent is not None and clo is not None:
            sp=float(g.loc[sig,'close']);direction=1 if sp>prev_close else (-1 if sp<prev_close else 0)
            if direction:
                ep=float(g.loc[ent,'open']);xp=float(g.loc[clo,'close']);gross=direction*(xp-ep);net=gross-cost/POINT_VALUE
                rows.append({'date':day,'direction':'long' if direction>0 else 'short','prior_close':prev_close,'signal_px':sp,'entry':ep,'exit':xp,'gross_points':gross,'net_points':net,'net_usd':net*POINT_VALUE})
        if clo is not None:prev_close=float(g.loc[clo,'close'])
    return pd.DataFrame(rows)

def monthly(t):
    if t.empty:return {}
    z=t.copy();z['month']=pd.to_datetime(z.date).dt.strftime('%Y-%m')
    return {str(m):stats(g.net_points.to_numpy()) for m,g in z.groupby('month')}

def main():
    out=Path('es-rod/results/v1');out.mkdir(parents=True,exist_ok=True)
    try:
        d=load(out);res={};led=[]
        for sc,cost in SCENARIOS.items():
            t=simulate(d,cost);t['scenario']=sc;led.append(t);res[sc]={'full':stats(t.net_points.to_numpy()),'monthly':monthly(t),'round_turn_cost_usd':cost}
        pd.concat(led,ignore_index=True).to_csv(out/'trades.csv',index=False)
        p=res['PRIMARY']['full'];s=res['STRESS']['full'];pm=sum(1 for m,v in res['PRIMARY']['monthly'].items() if m in {'2026-02','2026-03','2026-04'} and v['sum']>0)
        gates={'n_ge45':p['n']>=45,'mean_positive':p['mean'] is not None and p['mean']>0,'pf_ge1_15':p['pf'] is not None and p['pf']>=1.15,'positive_feb_mar_apr_ge2':pm>=2,'max_dd_le100pts':p['max_dd'] is not None and p['max_dd']<=100,'win_rate_ge52pct':p['win_rate'] is not None and p['win_rate']>=0.52,'stress_mean_positive':s['mean'] is not None and s['mean']>0,'stress_pf_ge1_05':s['pf'] is not None and s['pf']>=1.05}
        status='ES_ROD_INTRADAY_MOMENTUM_V1_PASS_REQUIRES_SECOND_ES_REPLICATION_BEFORE_PROP_SIM' if all(gates.values()) else 'ES_ROD_INTRADAY_MOMENTUM_V1_NO_GO'
        obj={'status':status,'results':res,'positive_feb_mar_apr':pm,'gates':gates,'notes':['Final rROD-family test; no gamma/news/volatility rescue filters permitted after result.','Direct ES source only; no CFD proxy.']}
        (out/'RESULT.json').write_text(json.dumps(obj,indent=2,allow_nan=False));print(json.dumps(obj,indent=2,allow_nan=False))
    except Exception as e:
        obj={'status':'ES_ROD_INTRADAY_MOMENTUM_V1_INVALID_ABORT','error':repr(e)};(out/'RESULT.json').write_text(json.dumps(obj,indent=2));print(json.dumps(obj,indent=2));raise
if __name__=='__main__':main()
