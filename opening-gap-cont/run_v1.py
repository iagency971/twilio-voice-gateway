#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, json
from pathlib import Path
import numpy as np
import pandas as pd
import requests

SPY_URL='https://raw.githubusercontent.com/BrianWeiss1/StockList/main/5min_data_SPY_2015_to_2024.csv'
ES_URL='https://raw.githubusercontent.com/axb0306/cme-futures-ohlc/main/ES/ES_1min_20260120_20260415.csv'
TZ='America/New_York'; GAP=.002; ES_POINT_VALUE=50.0

def stat(a):
    x=np.asarray(a,dtype=float)
    if len(x)==0:return {'n':0,'mean':None,'median':None,'sum':0.0,'pf':None,'win_rate':None}
    p=x[x>0].sum();n=-x[x<0].sum();pf=float(p/n) if n>0 else (1e99 if p>0 else None)
    return {'n':int(len(x)),'mean':float(x.mean()),'median':float(np.median(x)),'sum':float(x.sum()),'pf':pf,'win_rate':float((x>0).mean())}

def spy(raw,out):
    d=pd.read_csv(io.BytesIO(raw));lk={str(c).strip().lower():c for c in d.columns};orig=list(d.columns)
    dt=next((lk[k] for k in ['datetime','date_time','timestamp','ds','date'] if k in lk),None)
    if dt is None and str(d.columns[0]).lower().startswith('unnamed'):dt=d.columns[0]
    if dt is None:raise RuntimeError(f'no dt {orig}')
    def C(n):
        for k in {'open':['open','o'],'high':['high','h'],'low':['low','l'],'close':['close','c','adj close','adj_close']}[n]:
            if k in lk:return lk[k]
        raise RuntimeError(n)
    ts=pd.to_datetime(d[dt],errors='coerce')
    if isinstance(ts.dtype,pd.DatetimeTZDtype):ts=ts.dt.tz_convert(TZ).dt.tz_localize(None)
    z=pd.DataFrame({'dt':ts,'open':pd.to_numeric(d[C('open')],errors='coerce'),'high':pd.to_numeric(d[C('high')],errors='coerce'),'low':pd.to_numeric(d[C('low')],errors='coerce'),'close':pd.to_numeric(d[C('close')],errors='coerce')}).dropna().sort_values('dt').drop_duplicates('dt')
    z['date']=z.dt.dt.normalize();z['m']=z.dt.dt.hour*60+z.dt.dt.minute
    (out/'spy_qa.json').write_text(json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(z),'min':str(z.dt.min()),'max':str(z.dt.max())},indent=2))
    return z

def spy_trades(z,cost):
    rows=[];pc=None
    for day,g in z.groupby('date',sort=True):
        g=g.sort_values('m').drop_duplicates('m');cb=g[g.m.eq(955)];ob=g[g.m.eq(570)];e=g[g.m.eq(575)];x=g[g.m.eq(580)]
        if pc is not None and len(ob)==len(e)==len(x)==1:
            op=float(ob.iloc[0].open);gap=op/pc-1
            if abs(gap)>=GAP:
                side=1 if gap>0 else -1;ep=float(e.iloc[0].open);xp=float(x.iloc[0].open);gross=side*(xp/ep-1);net=gross-cost/10000
                rows.append({'date':day,'gap':gap,'side':side,'entry':ep,'exit':xp,'net':net})
        if len(cb)==1:pc=float(cb.iloc[0].close)
    return pd.DataFrame(rows)

def es(raw,out):
    d=pd.read_csv(io.BytesIO(raw));d['datetime']=pd.to_datetime(d.datetime,utc=True,errors='coerce')
    for c in ['open','high','low','close','volume']:d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna().sort_values('datetime').drop_duplicates('datetime');d.index=d.datetime.dt.tz_convert(TZ);d=d[['open','high','low','close','volume']].between_time('09:30','15:59');d=d[d.index.weekday<5]
    (out/'es_qa.json').write_text(json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(d),'min':str(d.index.min()),'max':str(d.index.max())},indent=2))
    return d

def es_trades(d,cost):
    rows=[];pc=None
    for day,g in d.groupby(d.index.normalize(),sort=True):
        m={t.hour*60+t.minute:t for t in g.index};ct=m.get(959);ot=m.get(570);et=m.get(571);xt=m.get(580)
        if pc is not None and ot is not None and et is not None and xt is not None:
            op=float(g.loc[ot,'open']);gap=op/pc-1
            if abs(gap)>=GAP:
                side=1 if gap>0 else -1;ep=float(g.loc[et,'open']);xp=float(g.loc[xt,'open']);gross=side*(xp-ep);net=gross-cost/ES_POINT_VALUE
                rows.append({'date':day,'gap':gap,'side':side,'entry':ep,'exit':xp,'net_points':net})
        if ct is not None:pc=float(g.loc[ct,'close'])
    return pd.DataFrame(rows)

def yearly(t,col):
    if t.empty:return {}
    q=t.copy();q['y']=pd.to_datetime(q.date).dt.year
    return {str(y):stat(g[col].to_numpy()) for y,g in q.groupby('y')}

def main():
    out=Path('opening-gap-cont/results/v1');out.mkdir(parents=True,exist_ok=True)
    try:
        a=requests.get(SPY_URL,timeout=180);a.raise_for_status();z=spy(a.content,out)
        b=requests.get(ES_URL,timeout=180);b.raise_for_status();ed=es(b.content,out)
        sr={};er={};led=[]
        for sc,c in {'PRIMARY':2.0,'STRESS':5.0}.items():
            t=spy_trades(z,c);t['scenario']=sc;t['asset']='SPY';led.append(t);vals=t.net.to_numpy();cut=max(1,int(np.ceil(len(vals)*.05)));rem=np.sort(vals)[:-cut] if len(vals)>cut else np.array([]);sr[sc]={'full':stat(vals),'yearly':yearly(t,'net'),'remove_best5_mean':float(rem.mean()) if len(rem) else None}
        for sc,c in {'PRIMARY':30.0,'STRESS':55.0}.items():
            t=es_trades(ed,c);t['scenario']=sc;t['asset']='ES';led.append(t);er[sc]={'full':stat(t.net_points.to_numpy())}
        pd.concat(led,ignore_index=True,sort=False).to_csv(out/'trades.csv',index=False)
        p=sr['PRIMARY']['full'];s=sr['STRESS']['full'];ep=er['PRIMARY']['full'];est=er['STRESS']['full'];py=sum(v['sum']>0 for v in sr['PRIMARY']['yearly'].values())
        sg={'spy_n_ge150':p['n']>=150,'spy_mean_positive':p['mean'] is not None and p['mean']>0,'spy_pf_ge1_10':p['pf'] is not None and p['pf']>=1.10,'spy_years_ge7':py>=7,'spy_median_nonnegative':p['median'] is not None and p['median']>=0,'spy_stress_mean_positive':s['mean'] is not None and s['mean']>0,'spy_stress_pf_ge1_03':s['pf'] is not None and s['pf']>=1.03,'spy_remove_best5_nonnegative':sr['PRIMARY']['remove_best5_mean'] is not None and sr['PRIMARY']['remove_best5_mean']>=0}
        if ep['n']>=10:eg={'es_n_ge10':True,'es_mean_positive':ep['mean']>0,'es_pf_ge1_15':ep['pf'] is not None and ep['pf']>=1.15,'es_stress_mean_positive':est['mean']>0,'es_stress_pf_ge1_05':est['pf'] is not None and est['pf']>=1.05}
        else:eg={'es_n_ge10':False}
        spy_pass=all(sg.values());es_pass=ep['n']>=10 and all(eg.values())
        status='OPENING_GAP_CONT_V1_PASS_FOR_PROPFIRM_RISK_RESEARCH' if spy_pass and es_pass else ('OPENING_GAP_CONT_V1_STRUCTURAL_PASS_ES_INCONCLUSIVE' if spy_pass and ep['n']<10 else 'OPENING_GAP_CONT_V1_NO_GO')
        obj={'status':status,'spy':sr,'es':er,'spy_positive_years':py,'gates':{**sg,**eg},'notes':['Initial-continuation hypothesis frozen independently from failed later-reversal trade.','No sign/threshold/timing rescue.']}
        (out/'RESULT.json').write_text(json.dumps(obj,indent=2,allow_nan=False));print(json.dumps(obj,indent=2,allow_nan=False))
    except Exception as e:
        obj={'status':'OPENING_GAP_CONT_V1_INVALID_ABORT','error':repr(e)};(out/'RESULT.json').write_text(json.dumps(obj,indent=2));print(json.dumps(obj,indent=2));raise
if __name__=='__main__':main()
