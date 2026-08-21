#!/usr/bin/env python3
from __future__ import annotations

import hashlib, io, json
from pathlib import Path
import numpy as np
import pandas as pd
import requests

SPY_URL='https://raw.githubusercontent.com/BrianWeiss1/StockList/main/5min_data_SPY_2015_to_2024.csv'
ES_URL='https://raw.githubusercontent.com/axb0306/cme-futures-ohlc/main/ES/ES_1min_20260120_20260415.csv'
TZ='America/New_York'; ES_POINT_VALUE=50.0; GAP=0.002


def stat(a):
    r=np.asarray(a,dtype=float)
    if len(r)==0:return {'n':0,'mean':None,'median':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None,'losing_streak':None}
    pos=r[r>0].sum();neg=-r[r<0].sum();pf=float(pos/neg) if neg>0 else (float('inf') if pos>0 else None)
    eq=np.cumsum(r);peak=np.maximum.accumulate(np.r_[0.0,eq])[:-1];dd=np.maximum(peak-eq,0.0)
    cur=ls=0
    for v in r:
        if v<0:cur+=1;ls=max(ls,cur)
        else:cur=0
    return {'n':int(len(r)),'mean':float(r.mean()),'median':float(np.median(r)),'sum':float(r.sum()),'pf':pf,'win_rate':float((r>0).mean()),'max_dd':float(dd.max(initial=0.0)),'losing_streak':int(ls)}


def normalize_spy(raw,out):
    d=pd.read_csv(io.BytesIO(raw));orig=[str(c) for c in d.columns];lk={str(c).strip().lower():c for c in d.columns}
    dt=None
    for k in ['datetime','date_time','timestamp','time_stamp','ds','date']:
        if k in lk:dt=lk[k];break
    if dt is not None and str(dt).strip().lower()=='date' and 'time' in lk:
        d['__dt__']=d[dt].astype(str)+' '+d[lk['time']].astype(str);dt='__dt__'
    if dt is None and len(d.columns)>0 and str(d.columns[0]).strip().lower().startswith('unnamed'):dt=d.columns[0]
    if dt is None:raise RuntimeError(f'SPY datetime unresolved: {orig}')
    def c(name):
        for x in {'open':['open','o'],'high':['high','h'],'low':['low','l'],'close':['close','c','adj close','adj_close']}[name]:
            if x in lk:return lk[x]
        raise RuntimeError(f'SPY missing {name}: {orig}')
    ts=pd.to_datetime(d[dt],errors='coerce')
    if isinstance(ts.dtype,pd.DatetimeTZDtype):ts=ts.dt.tz_convert(TZ).dt.tz_localize(None);tzmode='aware_to_ET'
    else:tzmode='naive_assumed_ET_after_anchor_QA'
    z=pd.DataFrame({'dt':ts,'open':pd.to_numeric(d[c('open')],errors='coerce'),'high':pd.to_numeric(d[c('high')],errors='coerce'),'low':pd.to_numeric(d[c('low')],errors='coerce'),'close':pd.to_numeric(d[c('close')],errors='coerce')}).dropna().sort_values('dt').drop_duplicates('dt',keep='last')
    z['date']=z.dt.dt.normalize();z['minute']=z.dt.dt.hour*60+z.dt.dt.minute
    ca=z[z.minute.isin([570,955])].groupby('date').minute.nunique();frac=float((ca>=2).sum()/max(z.date.nunique(),1))
    qa={'url':SPY_URL,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'columns':orig,'tz_mode':tzmode,'rows':int(len(z)),'min':str(z.dt.min()),'max':str(z.dt.max()),'anchor_fraction_0930_1555':frac}
    (out/'spy_qa.json').write_text(json.dumps(qa,indent=2))
    if frac<0.70:raise RuntimeError(f'SPY session QA failed: {qa}')
    return z


def spy_trades(z,cost_bps):
    rows=[];prev_close=None
    for day,g in z.groupby('date',sort=True):
        g=g.sort_values('minute').drop_duplicates('minute',keep='last')
        closebar=g[g.minute.eq(955)];openbar=g[g.minute.eq(570)];ent=g[g.minute.eq(580)];ex=g[g.minute.eq(640)]
        if prev_close is not None and len(openbar)==len(ent)==len(ex)==1:
            op=float(openbar.iloc[0].open);gap=op/prev_close-1.0
            if abs(gap)>=GAP:
                direction=-1 if gap>0 else 1
                ep=float(ent.iloc[0].open);xp=float(ex.iloc[0].open);gross=direction*(xp/ep-1.0);net=gross-cost_bps/10000.0
                rows.append({'date':day,'gap':gap,'direction':'short' if direction<0 else 'long','entry':ep,'exit':xp,'gross_return':gross,'net_return':net})
        if len(closebar)==1:prev_close=float(closebar.iloc[0].close)
    return pd.DataFrame(rows)


def load_es(raw,out):
    d=pd.read_csv(io.BytesIO(raw));d['datetime']=pd.to_datetime(d['datetime'],utc=True,errors='coerce')
    for c in ['open','high','low','close','volume']:d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna(subset=['datetime','open','high','low','close']).sort_values('datetime').drop_duplicates('datetime',keep='last')
    d.index=d['datetime'].dt.tz_convert(TZ);d=d[['open','high','low','close','volume']].between_time('09:30','15:59');d=d[d.index.weekday<5]
    (out/'es_qa.json').write_text(json.dumps({'url':ES_URL,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'rows':int(len(d)),'min':str(d.index.min()),'max':str(d.index.max()),'days':int(d.index.normalize().nunique())},indent=2))
    return d


def es_trades(d,cost_usd):
    rows=[];prev_close=None
    for day,g in d.groupby(d.index.normalize(),sort=True):
        m={ts.hour*60+ts.minute:ts for ts in g.index};ct=m.get(959);ot=m.get(570);et=m.get(580);xt=m.get(640)
        if prev_close is not None and ot is not None and et is not None and xt is not None:
            op=float(g.loc[ot,'open']);gap=op/prev_close-1.0
            if abs(gap)>=GAP:
                direction=-1 if gap>0 else 1;ep=float(g.loc[et,'open']);xp=float(g.loc[xt,'open']);gross=direction*(xp-ep);net=gross-cost_usd/ES_POINT_VALUE
                rows.append({'date':day,'gap':gap,'direction':'short' if direction<0 else 'long','entry':ep,'exit':xp,'gross_points':gross,'net_points':net,'net_usd':net*ES_POINT_VALUE})
        if ct is not None:prev_close=float(g.loc[ct,'close'])
    return pd.DataFrame(rows)


def annual(t,col):
    if t.empty:return {}
    z=t.copy();z['year']=pd.to_datetime(z.date).dt.year
    return {str(int(y)):stat(g[col].to_numpy()) for y,g in z.groupby('year')}

def monthly(t,col):
    if t.empty:return {}
    z=t.copy();z['month']=pd.to_datetime(z.date).dt.strftime('%Y-%m')
    return {str(m):stat(g[col].to_numpy()) for m,g in z.groupby('month')}

def by_dir(t,col):
    if t.empty:return {}
    return {str(k):stat(g[col].to_numpy()) for k,g in t.groupby('direction')}


def main():
    out=Path('opening-gap/results/v1');out.mkdir(parents=True,exist_ok=True)
    try:
        sr=requests.get(SPY_URL,timeout=180);sr.raise_for_status();spy=normalize_spy(sr.content,out)
        er=requests.get(ES_URL,timeout=180);er.raise_for_status();es=load_es(er.content,out)
        sres={};eres={};led=[]
        for sc,cost in {'PRIMARY':2.0,'STRESS':5.0}.items():
            t=spy_trades(spy,cost);t['scenario']=sc;t['asset']='SPY';led.append(t)
            vals=t.net_return.to_numpy();ncut=int(np.ceil(len(vals)*0.05));rem=np.sort(vals)[:-ncut] if ncut>0 and len(vals)>ncut else np.array([])
            sres[sc]={'full':stat(vals),'annual':annual(t,'net_return'),'by_direction':by_dir(t,'net_return'),'remove_best_5pct_mean':float(rem.mean()) if len(rem) else None}
        for sc,cost in {'PRIMARY':30.0,'STRESS':55.0}.items():
            t=es_trades(es,cost);t['scenario']=sc;t['asset']='ES';led.append(t)
            eres[sc]={'full':stat(t.net_points.to_numpy()),'monthly':monthly(t,'net_points'),'by_direction':by_dir(t,'net_points')}
        pd.concat(led,ignore_index=True,sort=False).to_csv(out/'trades.csv',index=False)
        sp=sres['PRIMARY']['full'];ss=sres['STRESS']['full'];ep=eres['PRIMARY']['full'];esst=eres['STRESS']['full']
        spy_pos_years=sum(1 for v in sres['PRIMARY']['annual'].values() if v['sum']>0);es_pos_months=sum(1 for m,v in eres['PRIMARY']['monthly'].items() if m in {'2026-02','2026-03','2026-04'} and v['sum']>0)
        gates={'spy_n_ge150':sp['n']>=150,'spy_mean_positive':sp['mean'] is not None and sp['mean']>0,'spy_pf_ge1_10':sp['pf'] is not None and sp['pf']>=1.10,'spy_positive_years_ge7':spy_pos_years>=7,'spy_median_nonnegative':sp['median'] is not None and sp['median']>=0,'spy_stress_mean_positive':ss['mean'] is not None and ss['mean']>0,'spy_stress_pf_ge1_03':ss['pf'] is not None and ss['pf']>=1.03,'spy_remove_best5pct_mean_nonnegative':sres['PRIMARY']['remove_best_5pct_mean'] is not None and sres['PRIMARY']['remove_best_5pct_mean']>=0,
               'es_n_ge10':ep['n']>=10,'es_mean_positive':ep['mean'] is not None and ep['mean']>0,'es_pf_ge1_15':ep['pf'] is not None and ep['pf']>=1.15,'es_positive_months_ge2':es_pos_months>=2,'es_stress_mean_positive':esst['mean'] is not None and esst['mean']>0,'es_stress_pf_ge1_05':esst['pf'] is not None and esst['pf']>=1.05}
        spy_pass=all(gates[k] for k in gates if k.startswith('spy_'));es_core=all(gates[k] for k in gates if k.startswith('es_'))
        if spy_pass and es_core:status='OPENING_GAP_REVERSAL_V1_PASS_FOR_PROPFIRM_RISK_RESEARCH'
        elif spy_pass and ep['n']<10:status='OPENING_GAP_REVERSAL_V1_STRUCTURAL_PASS_ES_INCONCLUSIVE'
        else:status='OPENING_GAP_REVERSAL_V1_NO_GO'
        obj={'status':status,'spy':sres,'es':eres,'spy_positive_years':spy_pos_years,'es_positive_feb_mar_apr_months':es_pos_months,'gates':gates,'notes':['Gap threshold, 10-minute wait, 60-minute fade and both directions frozen before outcomes.','Direction diagnostics cannot rescue the opened test.','Explicit transaction-cost stress applied because the original paper warned cost-adjusted significance was much weaker.']}
        (out/'RESULT.json').write_text(json.dumps(obj,indent=2,allow_nan=False));print(json.dumps(obj,indent=2,allow_nan=False))
    except Exception as e:
        obj={'status':'OPENING_GAP_REVERSAL_V1_INVALID_ABORT','error':repr(e)};(out/'RESULT.json').write_text(json.dumps(obj,indent=2));print(json.dumps(obj,indent=2));raise
if __name__=='__main__':main()
