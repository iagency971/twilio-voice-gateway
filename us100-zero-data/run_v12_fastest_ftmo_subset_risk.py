#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path('us100-zero-data')
LEDGER=ROOT/'results/native_12model_port_v5/TRADES_RESCORED.csv'
OUT=ROOT/'results/v12_fastest_ftmo_subset_risk'
EXPECTED_RAW_SHA='c2c705318ff19aee4fb1137b7ec2102e98a848b297701b334e1b777a0d5b7d31'
DEV_YEARS=(2021,2022,2023)
SESS={'DEV':746,'2024':246,'2025':83}
RISKS=tuple(round(x/10000,6) for x in range(25,101,5))  # .25%..1.00%


def sha256_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''): h.update(c)
 return h.hexdigest()

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

def remove_best10(z,col='primary_r'):
 if z.empty:return None
 n=int(math.ceil(len(z)*.10)); rem=z.sort_values(col,ascending=False).iloc[n:]
 return float(rem[col].mean()) if len(rem) else None

def worst_intraday_r(z,col):
 worst=0.0
 for _,g in z.sort_values('entry_time').groupby('date',sort=True):
  cum=0.0
  for r in g[col].to_numpy(float):
   cum+=float(r); worst=min(worst,cum)
 return float(worst)

def path_breach(z,col,risk):
 bal=0.0; peak=0.0; maxdd=0.0; worstday=0.0
 for _,g in z.sort_values('entry_time').groupby('date',sort=True):
  ds=bal
  for r in g[col].to_numpy(float):
   bal += float(r)*risk; peak=max(peak,bal); maxdd=max(maxdd,peak-bal); dm=bal-ds; worstday=min(worstday,dm)
   if dm<=-.05+1e-12:return {'breach':True,'reason':'daily','final':float(bal),'maxdd':float(maxdd),'worstday':float(worstday)}
   if bal<=-.10+1e-12:return {'breach':True,'reason':'total','final':float(bal),'maxdd':float(maxdd),'worstday':float(worstday)}
 return {'breach':False,'reason':None,'final':float(bal),'maxdd':float(maxdd),'worstday':float(worstday)}

def target_path(z,col,risk,target):
 bal=0.0; active=0; days=0
 for _,g in z.sort_values('entry_time').groupby('date',sort=True):
  days+=1; ds=bal
  if len(g):active+=1
  for r in g[col].to_numpy(float):
   bal += float(r)*risk; dm=bal-ds
   if dm<=-.05+1e-12:return {'status':'FAIL_DAILY','days':days,'final':float(bal)}
   if bal<=-.10+1e-12:return {'status':'FAIL_TOTAL','days':days,'final':float(bal)}
   if bal>=target-1e-12 and active>=4:return {'status':'PASS','days':days,'final':float(bal)}
 return {'status':'NOT_REACHED','days':None,'final':float(bal)}

def valblock(d,year,mods,risk):
 z=d[(d.year==year)&d.model.isin(mods)].copy(); sessions=SESS[str(year)]; p=stats(z.primary_r); s=stats(z.stress_r)
 wi=worst_intraday_r(z,'stress_r'); rpd=s['sum']/sessions; daily=rpd*risk
 return {'year':year,'sessions':sessions,'n':len(z),'trades_per_session':float(len(z)/sessions),'primary':p,'stress':s,
         'risk_fraction':risk,'risk_dollars_10k':risk*10000,'stress_worst_intraday_r':wi,
         'stress_scaled_dd_pct':s['max_dd']*risk if s['max_dd'] is not None else None,'stress_scaled_worst_intraday_pct':abs(min(0.,wi))*risk,
         'stress_r_per_session':float(rpd),'stress_step1_days_implied':float(.10/daily) if daily>0 else None,'stress_step2_days_implied':float(.05/daily) if daily>0 else None,
         'stress_path_step1':target_path(z,'stress_r',risk,.10),'stress_path_step2':target_path(z,'stress_r',risk,.05)}

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 d=pd.read_csv(LEDGER); d['entry_time']=pd.to_datetime(d.entry_time,errors='coerce'); d['exit_time']=pd.to_datetime(d.exit_time,errors='coerce'); d=d.dropna(subset=['entry_time','model','primary_r','stress_r']).copy();
 d['year']=d.entry_time.dt.year; d['date']=d.entry_time.dt.date; d=d.sort_values(['entry_time','exit_time']).reset_index(drop=True)
 mods=tuple(sorted(d.model.unique().tolist()))
 if len(mods)!=12:raise RuntimeError(f'Expected 12 models, got {len(mods)}')
 dev=d[d.year.isin(DEV_YEARS)].copy(); pairs=[]; subset_count=0; quality_count=0
 for mask in range(1,1<<len(mods)):
  subset_count+=1; subset=tuple(mods[i] for i in range(len(mods)) if mask&(1<<i)); z=dev[dev.model.isin(subset)]
  p=stats(z.primary_r); s=stats(z.stress_r)
  posyrs=0; worstyr=1e9; yrs={}
  for y in DEV_YEARS:
   sy=stats(z[z.year==y].primary_r); yrs[str(y)]=sy
   if sy['sum']>0:posyrs+=1
   if sy['mean'] is not None:worstyr=min(worstyr,sy['mean'])
  q={'n_ge_200':p['n']>=200,'primary_mean_gt_0':p['mean'] is not None and p['mean']>0,'primary_pf_ge_1_15':p['pf'] is not None and p['pf']>=1.15,
     'stress_mean_ge_0_05':s['mean'] is not None and s['mean']>=.05,'stress_pf_ge_1_10':s['pf'] is not None and s['pf']>=1.10,'positive_years_ge_2':posyrs>=2,
     'worst_year_mean_ge_minus_0_10':worstyr<1e9 and worstyr>=-.10}
  if not all(q.values()):continue
  quality_count+=1; wi=worst_intraday_r(z,'stress_r'); rb=remove_best10(z); rpd=s['sum']/SESS['DEV']
  for risk in RISKS:
   scaleddd=s['max_dd']*risk; scaledwi=abs(min(0.,wi))*risk
   if scaleddd>=.09 or scaledwi>=.045:continue
   path=path_breach(z,'stress_r',risk)
   if path['breach']:continue
   daily=rpd*risk
   if daily<=0:continue
   pairs.append({'models':subset,'model_count':len(subset),'risk_fraction':risk,'risk_dollars_10k':risk*10000,
                 'primary':p,'stress':s,'positive_years':posyrs,'worst_year_mean':float(worstyr),'remove_best10_mean':rb,
                 'trades_per_session':float(len(z)/SESS['DEV']),'stress_r_per_session':float(rpd),'stress_worst_intraday_r':wi,
                 'stress_scaled_dd_pct':float(scaleddd),'stress_scaled_worst_intraday_pct':float(scaledwi),'dev_path':path,
                 'implied_step1_days':float(.10/daily),'implied_step2_days':float(.05/daily)})
 def rank(x):return (x['implied_step1_days'],-x['stress']['pf'],x['risk_fraction'],x['stress']['max_dd'],x['model_count'],','.join(x['models']))
 pairs.sort(key=rank); sel=pairs[0] if pairs else None
 res={'status':'V12_NO_ADMISSIBLE_PAIR' if sel is None else 'V12_DEV_SELECTED_VALIDATION_OPENED','ledger_sha256':sha256_file(LEDGER),'expected_raw_sha':EXPECTED_RAW_SHA,
      'models':mods,'subsets_tested':subset_count,'quality_eligible_subsets':quality_count,'admissible_subset_risk_pairs':len(pairs),'top_30_pairs':pairs[:30],'selected_dev':sel,'validation':None,'pass':False}
 if sel:
  vm=tuple(sel['models']); risk=float(sel['risk_fraction']); v24=valblock(d,2024,vm,risk); v25=valblock(d,2025,vm,risk)
  gates={'2024_stress_sum_gt_0':v24['stress']['sum']>0,'2024_stress_pf_ge_1_10':v24['stress']['pf'] is not None and v24['stress']['pf']>=1.10,
         '2025_stress_sum_gt_0':v25['stress']['sum']>0,'2025_stress_pf_ge_1_10':v25['stress']['pf'] is not None and v25['stress']['pf']>=1.10,
         '2024_dd_lt_9pct':v24['stress_scaled_dd_pct']<.09,'2025_dd_lt_9pct':v25['stress_scaled_dd_pct']<.09,
         '2024_intraday_lt_4_5pct':v24['stress_scaled_worst_intraday_pct']<.045,'2025_intraday_lt_4_5pct':v25['stress_scaled_worst_intraday_pct']<.045,
         '2024_step1_pace_le_45':v24['stress_step1_days_implied'] is not None and v24['stress_step1_days_implied']<=45,
         '2025_step1_pace_le_45':v25['stress_step1_days_implied'] is not None and v25['stress_step1_days_implied']<=45}
  res['validation']={'2024':v24,'2025':v25,'gates':gates}; res['pass']=all(gates.values()); res['status']='V12_PROMISING_FOR_MONTE_CARLO' if res['pass'] else 'V12_VALIDATION_NO_GO'
 (OUT/'RESULT.json').write_text(json.dumps(res,indent=2,allow_nan=False,default=str))
 rows=[]
 for x in pairs[:100]:rows.append({'models':'+'.join(x['models']),'model_count':x['model_count'],'risk_pct':x['risk_fraction']*100,'risk_dollars_10k':x['risk_dollars_10k'],'n':x['primary']['n'],'tpd':x['trades_per_session'],'stress_mean':x['stress']['mean'],'stress_pf':x['stress']['pf'],'stress_dd':x['stress']['max_dd'],'remove_best10_mean':x['remove_best10_mean'],'step1_days':x['implied_step1_days'],'step2_days':x['implied_step2_days']})
 pd.DataFrame(rows).to_csv(OUT/'TOP_PAIRS.csv',index=False)
 print(json.dumps({'status':res['status'],'selected_models':None if not sel else sel['models'],'selected_risk_pct':None if not sel else sel['risk_fraction']*100,'dev_step1_days':None if not sel else sel['implied_step1_days'],'validation_pass':res['pass']},indent=2,default=str))

if __name__=='__main__':main()
