#!/usr/bin/env python3
from __future__ import annotations

import hashlib, io, json, os, subprocess, sys
from pathlib import Path
import numpy as np
import pandas as pd
import requests

EXT_REPO='https://github.com/s-k-28/nq-es-trader-5k-payout.git'
EXT_SHA='d472d6b442764c2adafbba4bbeb96881c100e3e0'
GET_URL='https://raw.githubusercontent.com/getdata-finance/nq-1m-ohlcv-stocks-historical-data/main/NQ_1m.csv'
GET_SHA='232fbc18375e6475dbe3b99e6e1504da69c58a962aa7a358b14f4e2b61cf229d'
TZ='America/New_York'
START=pd.Timestamp('2026-06-01')
END=pd.Timestamp('2026-07-31 23:59:59')


def pf(a):
    x=np.asarray(a,dtype=float);pos=x[x>0].sum();neg=-x[x<0].sum()
    if neg>0:return float(pos/neg)
    return 1e99 if pos>0 else None


def stats(a):
    x=np.asarray(a,dtype=float)
    if len(x)==0:return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None,'losing_streak':None}
    eq=np.cumsum(x);peak=np.maximum.accumulate(np.r_[0.0,eq])[:-1];dd=np.maximum(peak-eq,0)
    cur=ls=0
    for v in x:
        if v<0:cur+=1;ls=max(ls,cur)
        else:cur=0
    return {'n':int(len(x)),'mean':float(x.mean()),'sum':float(x.sum()),'pf':pf(x),'win_rate':float((x>0).mean()),'max_dd':float(dd.max(initial=0.0)),'losing_streak':int(ls)}


def prepare_proxy(ext: Path, out: Path):
    rr=requests.get(GET_URL,timeout=180);rr.raise_for_status();raw=rr.content
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=GET_SHA:raise RuntimeError(f'GetData snapshot changed: {sha}')
    d=pd.read_csv(io.BytesIO(raw))
    d['datetime']=pd.to_datetime(d['datetime'],utc=True,errors='coerce')
    for c in ['open','high','low','close','volume']:d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna(subset=['datetime','open','high','low','close']).sort_values('datetime').drop_duplicates('datetime',keep='last')
    d['datetime']=d['datetime'].dt.tz_convert(TZ).dt.tz_localize(None)
    d=d[['datetime','open','high','low','close','volume']]
    path=ext/'data'/'getdata_et_proxy.csv';d.to_csv(path,index=False)
    rth=d[(d.datetime.dt.time>=pd.Timestamp('09:30').time())&(d.datetime.dt.time<pd.Timestamp('16:00').time())]
    eval_rth=rth[(rth.datetime>=START)&(rth.datetime<=END)]
    days=int(eval_rth.datetime.dt.normalize().nunique())
    qa={'getdata_sha':sha,'bytes':len(raw),'rows':int(len(d)),'min':str(d.datetime.min()),'max':str(d.datetime.max()),'evaluation_rth_days':days,'known_unrepaired_anomaly':'2026-06-16'}
    (out/'data_qa.json').write_text(json.dumps(qa,indent=2))
    return path,days


def ensure_external(base: Path):
    ext=base/'external'
    if not ext.exists():
        subprocess.run(['git','clone','--quiet',EXT_REPO,str(ext)],check=True)
    subprocess.run(['git','checkout','--quiet',EXT_SHA],cwd=ext,check=True)
    got=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ext,text=True).strip()
    if got!=EXT_SHA:raise RuntimeError(f'external pin mismatch {got}')
    return ext


def run_external(ext: Path, proxy: Path, outcsv: Path):
    cmd=[sys.executable,'run_multi.py','--nq',str(proxy),'--csv',str(outcsv)]
    p=subprocess.run(cmd,cwd=ext,text=True,capture_output=True,timeout=900)
    Path(outcsv.parent/'external_stdout.txt').write_text(p.stdout)
    Path(outcsv.parent/'external_stderr.txt').write_text(p.stderr)
    if p.returncode!=0:raise RuntimeError(f'external run failed rc={p.returncode}: {p.stderr[-2000:]}')


def rescore(df,extra_points):
    risk_points=pd.to_numeric(df.risk_ticks,errors='coerce')*0.25
    base=pd.to_numeric(df.total_r,errors='coerce')
    return base-extra_points/risk_points


def group_stats(df,col,key):
    out={}
    if df.empty:return out
    for k,g in df.groupby(key):out[str(k)]=stats(g[col].to_numpy())
    return out


def main():
    out=Path('mnq-12model-proxy/results/v1');out.mkdir(parents=True,exist_ok=True)
    try:
        work=Path('/tmp/mnq12proxy');work.mkdir(parents=True,exist_ok=True)
        ext=ensure_external(work)
        proxy,days=prepare_proxy(ext,out)
        csv=work/'trades_external.csv';run_external(ext,proxy,csv)
        d=pd.read_csv(csv);d['entry_time']=pd.to_datetime(d.entry_time,errors='coerce')
        ev=d[(d.entry_time>=START)&(d.entry_time<=END)].copy().sort_values('entry_time').reset_index(drop=True)
        if ev.empty:raise RuntimeError('No Jun-Jul trades from external engine')
        ev['month']=ev.entry_time.dt.strftime('%Y-%m')
        ev['primary_r']=rescore(ev,1.0);ev['stress_r']=rescore(ev,2.0)
        ev.to_csv(out/'trades_rescored.csv',index=False)
        result={'status':'','external_repo':EXT_REPO,'external_commit':EXT_SHA,'evaluation_start':str(START.date()),'evaluation_end':str(END.date()),'observed_rth_days':days,'known_proxy_anomaly_retained':'2026-06-16','scenarios':{},'gates':{}}
        for sc,col in [('PRIMARY','primary_r'),('STRESS','stress_r')]:
            vals=ev[col].to_numpy();ncut=max(1,int(np.ceil(len(vals)*.05)));rem=np.sort(vals)[:-ncut] if len(vals)>ncut else np.array([])
            result['scenarios'][sc]={'full':stats(vals),'by_month':group_stats(ev,col,'month'),'by_model':group_stats(ev,col,'model'),'by_direction':group_stats(ev,col,'direction'),'remove_best_5pct_mean':float(rem.mean()) if len(rem) else None,'removed_best_n':ncut}
        p=result['scenarios']['PRIMARY']['full'];s=result['scenarios']['STRESS']['full'];bm=result['scenarios']['PRIMARY']['by_month']
        trades_per_day=p['n']/max(days,1);june=bm.get('2026-06',{}).get('sum',0);july=bm.get('2026-07',{}).get('sum',0);rem=result['scenarios']['PRIMARY']['remove_best_5pct_mean']
        gates={'n_ge_100':p['n']>=100,'trades_per_day_ge_2':trades_per_day>=2.0,'primary_mean_ge_0_10R':p['mean'] is not None and p['mean']>=.10,'primary_pf_ge_1_25':p['pf'] is not None and p['pf']>=1.25,'june_positive':june>0,'july_positive':july>0,'primary_max_dd_le_10R':p['max_dd'] is not None and p['max_dd']<=10,'remove_best_5pct_mean_nonnegative':rem is not None and rem>=0,'stress_mean_positive':s['mean'] is not None and s['mean']>0,'stress_pf_ge_1_10':s['pf'] is not None and s['pf']>=1.10}
        result['trades_per_day']=trades_per_day;result['gates']=gates
        result['status']='MNQ_12MODEL_PROXY_PASS_JUSTIFIES_TRUE_CME_VALIDATION' if all(gates.values()) else 'MNQ_12MODEL_PROXY_NO_GO'
        result['notes']=['Proxy screen only; never a futures validation.','External code is pinned and executed unchanged; friction is only rescored downward.','Known June 16 proxy anomaly is retained, not repaired or excluded.','No model removal or post-outcome rescue allowed.']
        (out/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False));print(json.dumps(result,indent=2,allow_nan=False))
    except Exception as e:
        obj={'status':'MNQ_12MODEL_PROXY_INVALID_ABORT','error':repr(e)};(out/'RESULT.json').write_text(json.dumps(obj,indent=2));print(json.dumps(obj,indent=2));raise

if __name__=='__main__':main()
