#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import run_native_12model_daily_stop_v7 as base

OUT=Path('us100-zero-data/results/v13_six_model_080_robustness')
MODELS=('ema_rev','kalman_mom','open_drive','ou_rev','pd_rev','pm_mom')
RISK=.008
BLOCKS=(5,10,20)
PROBES=(-1.0,-1.25)
NSIM=25000
MAX_DAYS=250
SEED=26082213

def dump(x):OUT.mkdir(parents=True,exist_ok=True);(OUT/'RESULT.json').write_text(json.dumps(x,indent=2,allow_nan=False,default=str))
def q(a):
 if not len(a):return {'median':None,'p25':None,'p75':None,'p90':None}
 a=np.asarray(a,float);return {'median':float(np.median(a)),'p25':float(np.percentile(a,25)),'p75':float(np.percentile(a,75)),'p90':float(np.percentile(a,90))}
def day_paths(tr,col,days):
 groups={d:g.sort_values('entry_time')[col].to_numpy(float) for d,g in tr.groupby('date')}
 return [groups.get(d,np.empty(0,float)) for d in days]
def simulate_step(paths,target,starts,block,probe_r):
 bal=0.;peak=0.;maxdd=0.;active=0;daynum=0
 for bs in starts:
  for off in range(block):
   if daynum>=MAX_DAYS:return False,daynum,'timeout',maxdd
   arr=paths[int(bs)+off];daynum+=1;daystart=bal
   if len(arr):active+=1
   for rr in arr:
    probe=bal+probe_r*RISK
    if daystart-probe>=.05-1e-12:return False,daynum,'daily_loss',maxdd
    if probe<=-.10+1e-12:return False,daynum,'total_loss',maxdd
    bal+=float(rr)*RISK;peak=max(peak,bal);maxdd=max(maxdd,peak-bal)
    if daystart-bal>=.05-1e-12:return False,daynum,'daily_loss',maxdd
    if bal<=-.10+1e-12:return False,daynum,'total_loss',maxdd
    if bal>=target-1e-12 and active>=4:return True,daynum,'pass',maxdd
 return False,daynum,'timeout',maxdd
def scenario(paths,block,probe_r,rng):
 n=len(paths);nb=(MAX_DAYS+block-1)//block;starts1=rng.integers(0,n-block+1,size=(NSIM,nb),dtype=np.int32);starts2=rng.integers(0,n-block+1,size=(NSIM,nb),dtype=np.int32)
 s1=both=0;s1d=[];s2d=[];td=[];dds=[];f1={'daily_loss':0,'total_loss':0,'timeout':0};f2={'daily_loss':0,'total_loss':0,'timeout':0}
 for i in range(NSIM):
  ok,d1,r1,m1=simulate_step(paths,.10,starts1[i],block,probe_r)
  if not ok:f1[r1]+=1;continue
  s1+=1;s1d.append(d1);ok2,d2,r2,m2=simulate_step(paths,.05,starts2[i],block,probe_r)
  if not ok2:f2[r2]+=1;continue
  both+=1;s2d.append(d2);td.append(d1+d2);dds.append(max(m1,m2))
 def sh(d,den):return {k:float(v/den) if den else 0. for k,v in d.items()}
 return {'step1_pass_probability':float(s1/NSIM),'step1_days':q(s1d),'step1_failure_shares':sh(f1,NSIM),'step2_conditional_pass_probability':float(both/s1) if s1 else 0.,'step2_days':q(s2d),'step2_failure_shares_given_step1_pass':sh(f2,s1),'combined_2step_pass_probability':float(both/NSIM),'combined_total_days':q(td),'combined_median_max_closed_dd_pct_full_passes':float(np.median(dds)) if dds else None,'n_step1_pass':int(s1),'n_full_pass':int(both)}
def main():
 if not base.TRADES.exists() or base.sha(base.RAW)!=base.EXPECTED_RAW_SHA:raise RuntimeError('Frozen V5.3 ledger/SHA invalid')
 tr=pd.read_csv(base.TRADES);tr['entry_time']=pd.to_datetime(tr.entry_time,errors='coerce');tr=tr.dropna(subset=['entry_time','primary_r','stress_r','model']).copy();tr=tr[tr.model.isin(MODELS)].copy();tr['date']=tr.entry_time.dt.date
 dates=base.dates_by_year();ordered=sorted(set().union(*[dates[y] for y in base.YEARS]));pp=day_paths(tr,'primary_r',ordered);sp=day_paths(tr,'stress_r',ordered)
 results={}
 for probe in PROBES:
  pk=f'{probe:.2f}R';results[pk]={}
  for block in BLOCKS:
   pr=scenario(pp,block,probe,np.random.default_rng(SEED+int(abs(probe)*1000)+block*100+1));sr=scenario(sp,block,probe,np.random.default_rng(SEED+int(abs(probe)*1000)+block*100+2));results[pk][str(block)]={'PRIMARY':pr,'STRESS':sr}
 dec=results['-1.25R']['20']['STRESS'];gate={'step1_pass_ge_80pct':dec['step1_pass_probability']>=.80,'combined_pass_ge_70pct':dec['combined_2step_pass_probability']>=.70,'median_step1_le_55':dec['step1_days']['median'] is not None and dec['step1_days']['median']<=55,'median_combined_le_90':dec['combined_total_days']['median'] is not None and dec['combined_total_days']['median']<=90,'daily_loss_share_le_10pct':dec['step1_failure_shares']['daily_loss']<=.10,'total_loss_share_le_15pct':dec['step1_failure_shares']['total_loss']<=.15};passed=all(gate.values())
 dump({'status':'V13_ROBUST_ENOUGH_FOR_FTMO_FREE_TRIAL' if passed else 'V13_080_NOT_ROBUST_ENOUGH','classification':'SIX_MODEL_FIXED_080_LONG_BLOCK_FLOATING_STRESS','models':list(MODELS),'risk_fraction':RISK,'risk_dollars_10k':RISK*10000,'raw_sha':base.EXPECTED_RAW_SHA,'n_complete_sessions':len(ordered),'n_trades':int(len(tr)),'n_simulations_per_scenario':NSIM,'block_lengths':list(BLOCKS),'floating_probes_r':list(PROBES),'results':results,'decisive_gate_20day_stress_minus_1_25R':gate,'pass':passed,'limitations':['Floating probes are conservative proxies because true tick-level MAE is unavailable.','Historical block bootstrap cannot guarantee future regimes.','Direct FTMO US100.cash spread/fill parity still requires prospective Free Trial validation.']})
 print(json.dumps({'status':'PASS' if passed else 'NO_GO','decisive':dec,'gate':gate},indent=2))
if __name__=='__main__':main()
