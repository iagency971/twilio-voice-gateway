#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

import run_native_12model_daily_stop_v7 as base

OUT=Path('us100-zero-data/results/ftmo_2step_robustness_v10')
RISK=0.004
BLOCKS=(5,10,20)
NSIM=25000
MAX_DAYS=250
SEED=26082210
FLOAT_PROBE_R=-1.0


def dump(x): OUT.mkdir(parents=True,exist_ok=True); (OUT/'RESULT.json').write_text(json.dumps(x,indent=2,allow_nan=False,default=str))

def qdays(a):
 if not len(a): return {'median':None,'p25':None,'p75':None,'p90':None}
 return {'median':float(np.median(a)),'p25':float(np.percentile(a,25)),'p75':float(np.percentile(a,75)),'p90':float(np.percentile(a,90))}

def day_paths(tr,col,ordered_days):
 groups={d:g.sort_values('entry_time')[col].to_numpy(float) for d,g in tr.groupby('date')}
 return [groups.get(d,np.empty(0,dtype=float)) for d in ordered_days]

def simulate_step(paths,target,starts,block):
 bal=0.0; peak=0.0; maxdd=0.0; active=0; daynum=0
 for bstart in starts:
  for off in range(block):
   if daynum>=MAX_DAYS: return False,daynum,'timeout',maxdd
   arr=paths[int(bstart)+off]; daynum+=1; day_start=bal
   if len(arr): active+=1
   for rr in arr:
    # conservative floating-equity probe before historical close
    probe=bal + FLOAT_PROBE_R*RISK
    if day_start-probe>=0.05-1e-12: return False,daynum,'daily_loss',maxdd
    if probe<=-0.10+1e-12: return False,daynum,'total_loss',maxdd
    bal += float(rr)*RISK
    peak=max(peak,bal); maxdd=max(maxdd,peak-bal)
    if day_start-bal>=0.05-1e-12: return False,daynum,'daily_loss',maxdd
    if bal<=-0.10+1e-12: return False,daynum,'total_loss',maxdd
    if bal>=target-1e-12 and active>=4: return True,daynum,'pass',maxdd
 return False,daynum,'timeout',maxdd

def scenario(paths,block,rng):
 n=len(paths); nblocks=(MAX_DAYS+block-1)//block
 starts1=rng.integers(0,n-block+1,size=(NSIM,nblocks),dtype=np.int32)
 starts2=rng.integers(0,n-block+1,size=(NSIM,nblocks),dtype=np.int32)
 s1pass=0; both=0; s1d=[]; s2d=[]; td=[]; full_dd=[]; fail1={'daily_loss':0,'total_loss':0,'timeout':0}; fail2={'daily_loss':0,'total_loss':0,'timeout':0}
 for i in range(NSIM):
  ok1,d1,r1,m1=simulate_step(paths,.10,starts1[i],block)
  if not ok1: fail1[r1]+=1; continue
  s1pass+=1; s1d.append(d1)
  ok2,d2,r2,m2=simulate_step(paths,.05,starts2[i],block)
  if not ok2: fail2[r2]+=1; continue
  both+=1; s2d.append(d2); td.append(d1+d2); full_dd.append(max(m1,m2))
 def shares(d,den): return {k:float(v/den) if den else 0.0 for k,v in d.items()}
 return {'step1_pass_probability':float(s1pass/NSIM),'step1_days':qdays(np.asarray(s1d)),'step1_failure_shares':shares(fail1,NSIM),
         'step2_conditional_pass_probability':float(both/s1pass) if s1pass else 0.0,'step2_days':qdays(np.asarray(s2d)),'step2_failure_shares_given_step1_pass':shares(fail2,s1pass),
         'combined_2step_pass_probability':float(both/NSIM),'combined_total_days':qdays(np.asarray(td)),
         'combined_median_max_closed_dd_pct_full_passes':float(np.median(full_dd)) if full_dd else None,'n_step1_pass':int(s1pass),'n_full_pass':int(both)}

def main():
 if not base.TRADES.exists() or base.sha(base.RAW)!=base.EXPECTED_RAW_SHA: raise RuntimeError('Frozen V5.3 ledger/SHA invalid')
 tr=pd.read_csv(base.TRADES); tr['entry_time']=pd.to_datetime(tr.entry_time,errors='coerce'); tr=tr.dropna(subset=['entry_time','primary_r','stress_r']).copy(); tr['date']=tr.entry_time.dt.date
 dates=base.dates_by_year(); ordered=sorted(set().union(*[dates[y] for y in base.YEARS]));
 ppaths=day_paths(tr,'primary_r',ordered); spaths=day_paths(tr,'stress_r',ordered)
 results={}
 for block in BLOCKS:
  pr=scenario(ppaths,block,np.random.default_rng(SEED+block*100+1)); sr=scenario(spaths,block,np.random.default_rng(SEED+block*100+2)); results[str(block)]={'PRIMARY':pr,'STRESS':sr}
 stress20=results['20']['STRESS']; gate={'step1_pass_ge_80pct':stress20['step1_pass_probability']>=.80,'combined_pass_ge_70pct':stress20['combined_2step_pass_probability']>=.70,
  'median_step1_le_55':stress20['step1_days']['median'] is not None and stress20['step1_days']['median']<=55,
  'median_combined_le_90':stress20['combined_total_days']['median'] is not None and stress20['combined_total_days']['median']<=90,
  'daily_loss_share_le_10pct':stress20['step1_failure_shares']['daily_loss']<=.10,
  'total_loss_share_le_15pct':stress20['step1_failure_shares']['total_loss']<=.15}
 passed=all(gate.values())
 dump({'status':'V10_ROBUST_FOR_FREE_TRIAL' if passed else 'V10_040_NOT_ROBUST_ENOUGH','classification':'FIXED_040_BLOCK_LENGTH_FLOATING_PROBE_STRESS',
       'raw_sha':base.EXPECTED_RAW_SHA,'risk_fraction':RISK,'risk_dollars_10k':RISK*10000,'floating_probe_r':FLOAT_PROBE_R,'n_complete_sessions':len(ordered),'n_simulations':NSIM,'block_lengths':list(BLOCKS),
       'results':results,'robustness_gate_20day_stress':gate,'pass':passed,
       'limitations':['-1R floating probe is a conservative proxy because true trade MAE is unavailable.','Historical block bootstrap cannot guarantee future regimes.','Direct FTMO spread/fill parity still requires prospective Free Trial validation.']})

if __name__=='__main__': main()
