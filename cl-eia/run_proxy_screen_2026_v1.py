#!/usr/bin/env python3
from __future__ import annotations

import hashlib, io, json
from pathlib import Path
import numpy as np
import pandas as pd
import requests

URL='https://raw.githubusercontent.com/getdata-finance/usoil-1m-ohlcv-commodities-historical-data/main/USOIL_1m.csv'
TZ='America/New_York'
PRIMARY_COST=0.03
STRESS_COST=0.05
EXCLUDED_SHIFTED={pd.Timestamp('2026-02-19').date(),pd.Timestamp('2026-05-28').date()}

def pf(a):
    a=np.asarray(a,dtype=float); pos=a[a>0].sum(); neg=-a[a<0].sum()
    if neg>0:return float(pos/neg)
    return 1e99 if pos>0 else None

def stats(vals):
    a=np.asarray(vals,dtype=float)
    if len(a)==0:return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None}
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.0,eq])[:-1]; dd=np.maximum(peak-eq,0)
    return {'n':int(len(a)),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0.0))}

def remove_best_mean(a,pct):
    a=np.asarray(a,dtype=float)
    if len(a)==0:return None
    k=max(1,int(np.ceil(len(a)*pct)))
    rem=np.sort(a)[:-k] if len(a)>k else np.array([])
    return float(rem.mean()) if len(rem) else None

def load(out):
    r=requests.get(URL,timeout=180);r.raise_for_status();raw=r.content
    d=pd.read_csv(io.BytesIO(raw));d['datetime']=pd.to_datetime(d['datetime'],utc=True,errors='coerce')
    for c in ['open','high','low','close','volume']:d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna(subset=['datetime','open','high','low','close']).sort_values('datetime').drop_duplicates('datetime')
    d['datetime']=d['datetime'].dt.tz_convert(TZ)
    qa={'url':URL,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'rows':int(len(d)),'min':str(d.datetime.min()),'max':str(d.datetime.max()),'duplicates':int(d.datetime.duplicated().sum())}
    (out/'data_qa.json').write_text(json.dumps(qa,indent=2));return d

def day_value(g,h,m,col):
    z=g[(g.datetime.dt.hour==h)&(g.datetime.dt.minute==m)]
    return float(z.iloc[0][col]) if len(z)==1 else None

def simulate(d):
    rows=[]
    for day,g in d.groupby(d.datetime.dt.date,sort=True):
        if pd.Timestamp(day).weekday()>=5:continue
        if day in EXCLUDED_SHIFTED:continue
        eia=(pd.Timestamp(day).weekday()==2)
        # 2026 sample: all standard Wednesdays except holiday-shift release weeks; shifted release days excluded above.
        if eia:
            s0=day_value(g,10,30,'open');s1=day_value(g,10,59,'close');engine='EIA'
        else:
            s0=day_value(g,9,0,'open');s1=day_value(g,9,29,'close');engine='NON_EIA'
        ent=day_value(g,14,0,'open');ex=day_value(g,14,29,'close')
        if None in (s0,s1,ent,ex):continue
        direction=1 if s1>s0 else (-1 if s1<s0 else 0)
        if direction==0:continue
        gross=direction*(ex-ent)
        rows.append({'date':str(day),'engine':engine,'direction':'long' if direction>0 else 'short','signal_open':s0,'signal_close':s1,'entry':ent,'exit':ex,'gross_points':gross,'primary_points':gross-PRIMARY_COST,'stress_points':gross-STRESS_COST})
    return pd.DataFrame(rows)

def main():
    out=Path('cl-eia/results/proxy_screen_2026_v1');out.mkdir(parents=True,exist_ok=True)
    try:
        d=load(out);t=simulate(d);t.to_csv(out/'trades.csv',index=False)
        result={}
        for eng in ['NON_EIA','EIA']:
            g=t[t.engine.eq(eng)].copy();p=stats(g.primary_points.to_numpy());s=stats(g.stress_points.to_numpy());rb=remove_best_mean(g.primary_points.to_numpy(),0.05 if eng=='NON_EIA' else 0.10)
            result[eng]={'PRIMARY':p,'STRESS':s,'remove_best_mean':rb}
        n=result['NON_EIA'];e=result['EIA']
        non_gates={'n_ge80':n['PRIMARY']['n']>=80,'mean_positive':n['PRIMARY']['mean'] is not None and n['PRIMARY']['mean']>0,'pf_ge1_05':n['PRIMARY']['pf'] is not None and n['PRIMARY']['pf']>=1.05,'stress_mean_positive':n['STRESS']['mean'] is not None and n['STRESS']['mean']>0,'remove_best5_nonnegative':n['remove_best_mean'] is not None and n['remove_best_mean']>=0}
        eia_gates={'n_ge18':e['PRIMARY']['n']>=18,'mean_positive':e['PRIMARY']['mean'] is not None and e['PRIMARY']['mean']>0,'pf_ge1_15':e['PRIMARY']['pf'] is not None and e['PRIMARY']['pf']>=1.15,'stress_mean_positive':e['STRESS']['mean'] is not None and e['STRESS']['mean']>0,'remove_best10_nonnegative':e['remove_best_mean'] is not None and e['remove_best_mean']>=0}
        npass=all(non_gates.values());epass=all(eia_gates.values())
        if npass and epass:status='PROXY_BOTH_PASS_JUSTIFY_CME'
        elif epass:status='PROXY_EIA_PASS_JUSTIFY_CME'
        elif npass:status='PROXY_NON_EIA_PASS_JUSTIFY_CME'
        else:status='PROXY_NO_GO_DO_NOT_BUY_CME_DATA'
        obj={'status':status,'source_status':'PROXY_ONLY_NOT_CME','results':result,'non_eia_gates':non_gates,'eia_gates':eia_gates,'excluded_shifted_eia_sessions':sorted(map(str,EXCLUDED_SHIFTED)),'notes':['Rules frozen before proxy outcomes.','No post-result rescue or filter permitted.','Proxy outcomes cannot validate CL; they only decide whether official CME data is worth buying.']}
        (out/'RESULT.json').write_text(json.dumps(obj,indent=2,allow_nan=False));print(json.dumps(obj,indent=2,allow_nan=False))
    except Exception as ex:
        obj={'status':'CL_PROXY_SCREEN_INVALID_ABORT','error':repr(ex)};(out/'RESULT.json').write_text(json.dumps(obj,indent=2));print(json.dumps(obj,indent=2));raise
if __name__=='__main__':main()
