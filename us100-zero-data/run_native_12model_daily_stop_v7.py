#!/usr/bin/env python3
from __future__ import annotations

import hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
import requests

BASE=Path('us100-zero-data/results/native_12model_port_v5')
TRADES=BASE/'TRADES_RESCORED.csv'; RAW=BASE/'external_trades_raw.csv'
OUT=Path('us100-zero-data/results/native_12model_daily_stop_v7')
EXPECTED_RAW_SHA='c2c705318ff19aee4fb1137b7ec2102e98a848b297701b334e1b777a0d5b7d31'
SRC='CodyOutcast/Academic-Paper-Data-Source'; COMMIT='50052606c16d71850755e6dbdda02d43b4399c2b'
YEARS=(2021,2022,2023,2024,2025); CACHE=Path('/tmp/us100_v7_dates'); SHIFT=7
CAPS=(-1.5,-2.0,-2.5,-3.0)

def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''): h.update(c)
 return h.hexdigest()

def dump(x): OUT.mkdir(parents=True,exist_ok=True); (OUT/'RESULT.json').write_text(json.dumps(x,indent=2,allow_nan=False,default=str))

def pf(a):
 a=np.asarray(a,float); pos=a[a>0].sum(); neg=-a[a<0].sum()
 return float(pos/neg) if neg>0 else (1e99 if pos>0 else None)

def stats(v):
 a=np.asarray(v,float)
 if not len(a): return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None,'losing_streak':None}
 eq=np.cumsum(a); peaks=np.maximum.accumulate(np.r_[0.,eq])[:-1]; dd=np.maximum(peaks-eq,0); cur=longest=0
 for x in a:
  if x<0: cur+=1; longest=max(longest,cur)
  else: cur=0
 return {'n':int(len(a)),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0)),'losing_streak':int(longest)}

def srcpath(y):
 CACHE.mkdir(parents=True,exist_ok=True); p=CACHE/f'OHLC-USTEC-M1-{y}.csv'
 if not p.exists() or p.stat().st_size<1000:
  u=f'https://raw.githubusercontent.com/{SRC}/{COMMIT}/OHLC-USTEC-M1-{y}.csv'; r=requests.get(u,timeout=180); r.raise_for_status(); p.write_bytes(r.content)
 return p

def dates_by_year():
 o={}
 for y in YEARS:
  d=pd.read_csv(srcpath(y),sep=';',usecols=['time'],low_memory=False); d['time']=pd.to_datetime(d.time,format='%Y.%m.%d %H:%M:%S',errors='coerce'); d=d.dropna().drop_duplicates('time')
  dt=d.time-pd.Timedelta(hours=SHIFT); x=pd.DataFrame({'dt':dt}); x['date']=x.dt.dt.date; t=x.dt.dt.time
  r=x[(t>=pd.Timestamp('09:30').time())&(t<pd.Timestamp('16:00').time())]; c=r.groupby('date').size(); o[y]=set(c[c>=380].index)
 return o

def apply_cap(z, col, cap):
 kept=[]
 for d,g in z.sort_values('entry_time').groupby('date',sort=True):
  cum=0.0
  for idx,row in g.iterrows():
   if cum<=cap: continue
   kept.append(idx); cum+=float(row[col])
 return z.loc[kept].sort_values('entry_time').copy()

def eval_cap(z,cap,sessions):
 pz=apply_cap(z,'primary_r',cap); sz=apply_cap(z,'stress_r',cap)
 ps=stats(pz.primary_r); ss=stats(sz.stress_r)
 return {'cap_r':cap,'primary':ps,'stress':ss,'sessions':sessions,
         'primary_trades_per_day':float(len(pz)/sessions),'stress_trades_per_day':float(len(sz)/sessions),
         'primary_r_per_day':float(ps['sum']/sessions),'stress_r_per_day':float(ss['sum']/sessions),
         'primary_kept_indices':pz.index.tolist(),'stress_kept_indices':sz.index.tolist()}

def plan(rpd,dd,worst):
 if not(rpd>0 and dd>0): return {'safe':None,'aggressive':None}
 levels={'safe':min(.005,.08/(2*dd)),'aggressive':min(.005,.08/(1.5*dd))}; out={}
 for k,r in levels.items():
  wl=abs(min(0.,worst))*r; ok=wl<.04; daily=rpd*r
  out[k]={'risk_pct_per_trade_base':float(r),'risk_dollars_10k_base':float(r*10000),'observed_worst_day_loss_pct':float(wl),'admissible':bool(ok),
          'expected_daily_return_pct':float(daily),'step1_days':float(.10/daily) if ok and daily>0 else None,'step2_days':float(.05/daily) if ok and daily>0 else None,'total_days':float(.15/daily) if ok and daily>0 else None}
 return out

def main():
 if not TRADES.exists() or not RAW.exists(): raise RuntimeError('V5.3 ledger missing')
 if sha(RAW)!=EXPECTED_RAW_SHA: raise RuntimeError('raw SHA mismatch')
 tr=pd.read_csv(TRADES); tr['entry_time']=pd.to_datetime(tr.entry_time,errors='coerce'); tr=tr.dropna(subset=['entry_time','primary_r','stress_r']).copy(); tr['date']=tr.entry_time.dt.date; tr['year']=tr.entry_time.dt.year; tr['month']=tr.entry_time.dt.to_period('M').astype(str)
 dates=dates_by_year(); dev=tr[tr.year.isin([2021,2022,2023])].copy(); dsess=sum(len(dates[y]) for y in [2021,2022,2023])
 cand={}; passing=[]
 for cap in CAPS:
  e=eval_cap(dev,cap,dsess); p=e['primary']; s=e['stress']; pk=dev.loc[e['primary_kept_indices']]; years={str(y):stats(pk[pk.year==y].primary_r) for y in [2021,2022,2023]}
  g={'n_ge_1800':p['n']>=1800,'tpd_ge_2_4':e['primary_trades_per_day']>=2.4,'mean_ge_0_16':p['mean']>=.16,'pf_ge_1_40':p['pf'] is not None and p['pf']>=1.40,'maxdd_le_13':p['max_dd']<=13,
     'all_3_years_positive':all(v['sum']>0 for v in years.values()),'stress_mean_ge_0_13':s['mean']>=.13,'stress_pf_ge_1_30':s['pf'] is not None and s['pf']>=1.30,'stress_maxdd_le_15':s['max_dd']<=15}
  rec={k:v for k,v in e.items() if not k.endswith('_indices')}; rec['primary_by_year']=years; rec['gates']=g; rec['pass']=all(g.values()); cand[str(cap)]=rec
  if rec['pass']: passing.append((cap,rec))
 if not passing:
  dump({'status':'V7_DAILY_STOP_DEV_NO_GO','raw_sha':EXPECTED_RAW_SHA,'dev_candidates':cand,'validation_status':'NOT_OPENED'}); return
 # hierarchy: highest primary R/day, then lower DD, then looser cap (more negative)
 passing.sort(key=lambda x:(x[1]['primary_r_per_day'],-x[1]['primary']['max_dd'],-abs(x[0])),reverse=True); cap=passing[0][0]
 selected_dev=cand[str(cap)]
 val=tr[tr.year.isin([2024,2025])].copy(); vsess=sum(len(dates[y]) for y in [2024,2025]); ve=eval_cap(val,cap,vsess)
 vp=val.loc[ve['primary_kept_indices']].copy(); vsp=val.loc[ve['stress_kept_indices']].copy(); p=ve['primary']; s=ve['stress']
 years={str(y):stats(vp[vp.year==y].primary_r) for y in [2024,2025]}; monthly=vp.groupby('month').primary_r.sum(); posrate=float((monthly>0).mean()) if len(monthly) else 0; worstmonth=float(monthly.min()) if len(monthly) else 0
 daily=vp.groupby('date').primary_r.sum(); worstday=float(daily.min()) if len(daily) else 0; cp=plan(ve['primary_r_per_day'],p['max_dd'],worstday)
 speed=any(x is not None and x['admissible'] and x['step1_days'] is not None and x['step1_days']<=45 and x['step2_days'] is not None and x['step2_days']<=23 and x['total_days'] is not None and x['total_days']<=68 for x in cp.values())
 vg={'n_ge_650':p['n']>=650,'tpd_ge_2_4':ve['primary_trades_per_day']>=2.4,'mean_ge_0_16':p['mean']>=.16,'pf_ge_1_40':p['pf'] is not None and p['pf']>=1.40,'maxdd_le_10_7':p['max_dd']<=10.7,
     'year_2024_positive':years['2024']['sum']>0,'jan_apr_2025_positive':years['2025']['sum']>0,'positive_months_ge_70pct':posrate>=.70,'worst_month_ge_minus_8':worstmonth>=-8,
     'stress_mean_ge_0_13':s['mean']>=.13,'stress_pf_ge_1_30':s['pf'] is not None and s['pf']>=1.30,'stress_maxdd_le_12_5':s['max_dd']<=12.5,'challenge_speed':speed}
 passed=all(vg.values()); vp.to_csv(OUT/'VALIDATION_PRIMARY_TRADES.csv',index=False)
 dump({'status':'V7_DAILY_STOP_PROMISING_REQUIRES_FTMO_FORWARD' if passed else 'V7_DAILY_STOP_NO_GO','raw_sha':EXPECTED_RAW_SHA,'selected_cap_r':cap,'dev_candidates':cand,'selected_dev':selected_dev,
       'validation':{k:v for k,v in ve.items() if not k.endswith('_indices')},'validation_by_year':years,'validation_monthly_r':{str(k):float(v) for k,v in monthly.items()},'validation_positive_month_rate':posrate,
       'validation_worst_month_r':worstmonth,'validation_worst_daily_r':worstday,'challenge_plan_10k':cp,'validation_gates':vg,'pass':passed,
       'notes':['No paid data required.','V7 adds only a closed-P&L daily stop to the unchanged V5 signal stream.','Prospective FTMO Free Trial remains required if PASS.']})

if __name__=='__main__': main()
