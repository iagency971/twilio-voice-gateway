#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import run_native_12model_daily_stop_v7 as base

TRADES=Path('us100-zero-data/results/v17_all24_branch_search/SELECTED_TRUE_CAUSAL_TRADES.csv')
OUT=Path('us100-zero-data/results/v19_v17_070_robustness')
RISK=0.007
BLOCKS=(5,10,20)
PROBES=(-1.0,-1.25,-1.5)
NSIM=25000
MAX_DAYS=250
SEED=26082319

def q(a):
    if not len(a):return {'median':None,'p25':None,'p75':None,'p90':None}
    return {'median':float(np.median(a)),'p25':float(np.percentile(a,25)),'p75':float(np.percentile(a,75)),'p90':float(np.percentile(a,90))}
def day_paths(tr,col,days):
    g={d:x.sort_values('entry_time')[col].to_numpy(float) for d,x in tr.groupby('date')}
    return [g.get(d,np.empty(0,dtype=float)) for d in days]
def simulate(paths,target,starts,block,probe_r):
    bal=0.;peak=0.;maxdd=0.;active=0;dn=0
    for bs in starts:
        for off in range(block):
            if dn>=MAX_DAYS:return False,dn,'timeout',maxdd
            arr=paths[int(bs)+off];dn+=1;ds=bal
            if len(arr):active+=1
            for rr in arr:
                probe=bal+probe_r*RISK
                if ds-probe>=.05-1e-12:return False,dn,'daily_loss',maxdd
                if probe<=-.10+1e-12:return False,dn,'total_loss',maxdd
                bal+=float(rr)*RISK;peak=max(peak,bal);maxdd=max(maxdd,peak-bal)
                if ds-bal>=.05-1e-12:return False,dn,'daily_loss',maxdd
                if bal<=-.10+1e-12:return False,dn,'total_loss',maxdd
                if bal>=target-1e-12 and active>=4:return True,dn,'pass',maxdd
    return False,dn,'timeout',maxdd
def scenario(paths,block,probe_r,rng):
    n=len(paths);nb=(MAX_DAYS+block-1)//block
    st1=rng.integers(0,n-block+1,size=(NSIM,nb),dtype=np.int32);st2=rng.integers(0,n-block+1,size=(NSIM,nb),dtype=np.int32)
    p1=both=0;d1=[];d2=[];dt=[];dds=[];f1={'daily_loss':0,'total_loss':0,'timeout':0};f2={'daily_loss':0,'total_loss':0,'timeout':0}
    for i in range(NSIM):
        ok,a,r,m1=simulate(paths,.10,st1[i],block,probe_r)
        if not ok:f1[r]+=1;continue
        p1+=1;d1.append(a)
        ok,b,r,m2=simulate(paths,.05,st2[i],block,probe_r)
        if not ok:f2[r]+=1;continue
        both+=1;d2.append(b);dt.append(a+b);dds.append(max(m1,m2))
    return {'step1_pass_probability':p1/NSIM,'step1_days':q(np.asarray(d1)),'step1_failure_shares':{k:v/NSIM for k,v in f1.items()},'step2_conditional_pass_probability':both/p1 if p1 else 0.,'step2_days':q(np.asarray(d2)),'step2_failure_shares_given_step1_pass':{k:(v/p1 if p1 else 0.) for k,v in f2.items()},'combined_2step_pass_probability':both/NSIM,'combined_total_days':q(np.asarray(dt)),'combined_median_max_closed_dd_pct_full_passes':float(np.median(dds)) if dds else None,'n_step1_pass':p1,'n_full_pass':both}
def main():
    tr=pd.read_csv(TRADES);tr['entry_time']=pd.to_datetime(tr.entry_time);tr['date']=tr.entry_time.dt.date
    dates=base.dates_by_year();days=sorted(set().union(*[dates[y] for y in base.YEARS]));
    pp=day_paths(tr,'primary_r',days);sp=day_paths(tr,'stress_r',days);results={}
    for probe in PROBES:
        pk=f'{probe:.2f}R';results[pk]={}
        for block in BLOCKS:
            pr=scenario(pp,block,probe,np.random.default_rng(SEED+int(abs(probe)*1000)+block*10+1));sr=scenario(sp,block,probe,np.random.default_rng(SEED+int(abs(probe)*1000)+block*10+2));results[pk][str(block)]={'PRIMARY':pr,'STRESS':sr}
    hard=results['-1.50R']['20']['STRESS'];gate={'step1_pass_ge_75pct':hard['step1_pass_probability']>=.75,'combined_pass_ge_60pct':hard['combined_2step_pass_probability']>=.60,'median_step1_le_45':hard['step1_days']['median'] is not None and hard['step1_days']['median']<=45,'median_combined_le_75':hard['combined_total_days']['median'] is not None and hard['combined_total_days']['median']<=75,'daily_loss_share_le_15pct':hard['step1_failure_shares']['daily_loss']<=.15,'total_loss_share_le_20pct':hard['step1_failure_shares']['total_loss']<=.20}
    passed=all(gate.values());OUT.mkdir(parents=True,exist_ok=True);(OUT/'RESULT.json').write_text(json.dumps({'status':'V19_ROBUST_ENOUGH_FOR_FTMO_FREE_TRIAL' if passed else 'V19_NOT_ROBUST_ENOUGH','candidate':'V17_TRUE_CAUSAL_14_BRANCH','risk_fraction':RISK,'risk_dollars_10k':70.,'n_trades':len(tr),'n_sessions':len(days),'blocks':list(BLOCKS),'floating_probes_r':list(PROBES),'n_simulations_per_scenario':NSIM,'results':results,'decisive_gate_stress_20day_minus_1_50R':gate,'pass':passed,'limitations':['Floating probes are conservative proxies; true tick-level MAE is unavailable.','Historical block bootstrap cannot guarantee future regime distribution.','FTMO US100.cash quote/fill parity remains prospective and must be checked on Free Trial.']},indent=2,allow_nan=False,default=str));print(json.dumps({'status':'PASS' if passed else 'FAIL','hard':hard,'gate':gate},indent=2))
if __name__=='__main__':main()
