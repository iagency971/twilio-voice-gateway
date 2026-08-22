#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

import run_native_12model_daily_stop_v7 as base

OUT=Path('us100-zero-data/results/ftmo_2step_monte_carlo_v9')
RISKS=(0.0025,0.0030,0.0035,0.0040,0.0045,0.0050)
NSIM=25000
MAX_DAYS=250
BLOCK=5
SEED=26082209


def dump(x): OUT.mkdir(parents=True,exist_ok=True); (OUT/'RESULT.json').write_text(json.dumps(x,indent=2,allow_nan=False,default=str))

def qdays(a):
 if not len(a): return {'median':None,'p25':None,'p75':None,'p90':None}
 return {'median':float(np.median(a)),'p25':float(np.percentile(a,25)),'p75':float(np.percentile(a,75)),'p90':float(np.percentile(a,90))}

def day_paths(tr,col,ordered_days):
 groups={d:g.sort_values('entry_time')[col].to_numpy(float) for d,g in tr.groupby('date')}
 return [groups.get(d,np.empty(0,dtype=float)) for d in ordered_days]

def simulate_step(paths,risk,target,starts):
 bal=0.0; peak=0.0; maxdd=0.0; active=0; daynum=0; n=len(paths)
 for bstart in starts:
  for off in range(BLOCK):
   if daynum>=MAX_DAYS: return False,daynum,'timeout',maxdd
   arr=paths[int(bstart)+off]; daynum+=1; day_start=bal
   if len(arr): active+=1
   for r in arr:
    bal += float(r)*risk
    peak=max(peak,bal); maxdd=max(maxdd,peak-bal)
    day_loss=day_start-bal
    if day_loss>=0.05-1e-12: return False,daynum,'daily_loss',maxdd
    if bal<=-0.10+1e-12: return False,daynum,'total_loss',maxdd
    if bal>=target-1e-12 and active>=4: return True,daynum,'pass',maxdd
 return False,daynum,'timeout',maxdd

def scenario(paths,risk,starts1,starts2):
 step1_pass=0; both=0; s1days=[]; totaldays=[]; s2days=[]; dd1=[]; ddfull=[]
 fail1={'daily_loss':0,'total_loss':0,'timeout':0}; fail2={'daily_loss':0,'total_loss':0,'timeout':0}
 for i in range(NSIM):
  ok1,d1,r1,m1=simulate_step(paths,risk,0.10,starts1[i]); dd1.append(m1)
  if not ok1:
   fail1[r1]+=1; continue
  step1_pass+=1; s1days.append(d1)
  ok2,d2,r2,m2=simulate_step(paths,risk,0.05,starts2[i])
  if not ok2:
   fail2[r2]+=1; continue
  both+=1; s2days.append(d2); totaldays.append(d1+d2); ddfull.append(max(m1,m2))
 def shares(d,den): return {k:float(v/den) if den else 0.0 for k,v in d.items()}
 return {
  'step1_pass_probability':float(step1_pass/NSIM),
  'step1_days_passes':qdays(np.asarray(s1days)),
  'step1_failure_shares_all_sims':shares(fail1,NSIM),
  'step1_median_max_drawdown_pct':float(np.median(dd1)) if dd1 else None,
  'step2_conditional_pass_probability':float(both/step1_pass) if step1_pass else 0.0,
  'step2_days_full_passes':qdays(np.asarray(s2days)),
  'step2_failure_shares_given_step1_pass':shares(fail2,step1_pass),
  'combined_2step_pass_probability':float(both/NSIM),
  'combined_total_days_full_passes':qdays(np.asarray(totaldays)),
  'combined_median_max_drawdown_pct_full_passes':float(np.median(ddfull)) if ddfull else None,
  'n_step1_pass':int(step1_pass),'n_full_pass':int(both)
 }

def main():
 if not base.TRADES.exists() or base.sha(base.RAW)!=base.EXPECTED_RAW_SHA: raise RuntimeError('Frozen V5.3 ledger/SHA invalid')
 tr=pd.read_csv(base.TRADES); tr['entry_time']=pd.to_datetime(tr.entry_time,errors='coerce'); tr=tr.dropna(subset=['entry_time','primary_r','stress_r']).copy(); tr['date']=tr.entry_time.dt.date
 dates=base.dates_by_year(); ordered=sorted(set().union(*[dates[y] for y in base.YEARS])); n=len(ordered)
 if n<1000: raise RuntimeError(f'Unexpected complete-session count {n}')
 ppaths=day_paths(tr,'primary_r',ordered); spaths=day_paths(tr,'stress_r',ordered)
 rng=np.random.default_rng(SEED); nblocks=(MAX_DAYS+BLOCK-1)//BLOCK
 starts1=rng.integers(0,n-BLOCK+1,size=(NSIM,nblocks),dtype=np.int32)
 starts2=rng.integers(0,n-BLOCK+1,size=(NSIM,nblocks),dtype=np.int32)
 results={}
 candidates=[]
 for risk in RISKS:
  key=f'{risk*100:.2f}%'; pr=scenario(ppaths,risk,starts1,starts2); sr=scenario(spaths,risk,starts1,starts2)
  gate={'primary_combined_ge_65pct':pr['combined_2step_pass_probability']>=.65,
        'stress_combined_ge_55pct':sr['combined_2step_pass_probability']>=.55,
        'primary_median_total_le_70':pr['combined_total_days_full_passes']['median'] is not None and pr['combined_total_days_full_passes']['median']<=70,
        'stress_median_total_le_90':sr['combined_total_days_full_passes']['median'] is not None and sr['combined_total_days_full_passes']['median']<=90,
        'primary_step1_ge_75pct':pr['step1_pass_probability']>=.75,
        'stress_step1_ge_65pct':sr['step1_pass_probability']>=.65}
  passed=all(gate.values())
  results[key]={'risk_fraction':risk,'risk_dollars_10k':risk*10000,'PRIMARY':pr,'STRESS':sr,'gate':gate,'practical_candidate':passed}
  if passed: candidates.append(risk)
 selected=min(candidates) if candidates else None
 dump({'status':'V9_PRACTICAL_FAST_2STEP_SIZING_FOUND' if selected is not None else 'V9_NO_PRACTICAL_FAST_2STEP_SIZING',
       'classification':'FTMO_2STEP_5DAY_BLOCK_BOOTSTRAP_FIXED_RISK','raw_sha':base.EXPECTED_RAW_SHA,'n_complete_sessions':n,'n_simulations_per_scenario_risk':NSIM,
       'block_sessions':BLOCK,'max_sessions_per_step':MAX_DAYS,'seed':SEED,'risk_levels':[float(x) for x in RISKS],
       'selected_lowest_passing_risk':float(selected) if selected is not None else None,'results':results,
       'limitations':['Daily-loss enforcement uses closed-trade intraday P&L because historical ledger lacks tick-level floating MAE.','Historical block bootstrap cannot guarantee future regime distribution.','Live FTMO spread/execution parity still requires a prospective Free Trial even if sizing passes.']})

if __name__=='__main__': main()
