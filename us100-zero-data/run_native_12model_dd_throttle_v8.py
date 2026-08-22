#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

import run_native_12model_daily_stop_v7 as base

OUT=Path('us100-zero-data/results/native_12model_dd_throttle_v8')
POLICIES={
 'T3_6':(3.0,6.0),
 'T4_8':(4.0,8.0),
 'T5_10':(5.0,10.0),
}

def dump(x): OUT.mkdir(parents=True,exist_ok=True); (OUT/'RESULT.json').write_text(json.dumps(x,indent=2,allow_nan=False,default=str))

def simulate(z,col,levels):
 lo,hi=levels; eq=0.0; peak=0.0; rows=[]; weights=[]; wr=[]
 for idx,row in z.sort_values('entry_time').iterrows():
  dd=peak-eq
  w=1.0 if dd<lo else (0.5 if dd<hi else 0.25)
  x=float(row[col])*w; eq+=x; peak=max(peak,eq)
  rows.append(idx); weights.append(w); wr.append(x)
 out=z.loc[rows].copy(); out['weight']=weights; out['weighted_r']=wr
 return out

def ev(z,levels,sessions):
 p=simulate(z,'primary_r',levels); s=simulate(z,'stress_r',levels)
 ps=base.stats(p.weighted_r); ss=base.stats(s.weighted_r)
 return {'primary':ps,'stress':ss,'sessions':sessions,'trade_count':int(len(z)),
         'primary_r_per_day':float(ps['sum']/sessions),'stress_r_per_day':float(ss['sum']/sessions),
         'primary_weight_mean':float(p.weight.mean()),'stress_weight_mean':float(s.weight.mean()),
         'primary_weight_counts':{str(k):int(v) for k,v in p.weight.value_counts().sort_index().items()},
         'stress_weight_counts':{str(k):int(v) for k,v in s.weight.value_counts().sort_index().items()},
         'primary_frame':p,'stress_frame':s}

def challenge(rpd,dd,worst):
 if not(rpd>0 and dd>0): return {'safe':None,'aggressive':None}
 lev={'safe':min(.005,.08/(2*dd)),'aggressive':min(.005,.08/(1.5*dd))}; o={}
 for k,r in lev.items():
  wl=abs(min(0.,worst))*r; ok=wl<.04; daily=rpd*r
  o[k]={'base_risk_pct':float(r),'base_risk_dollars_10k':float(r*10000),'worst_day_loss_pct':float(wl),'admissible':bool(ok),
        'expected_daily_return_pct':float(daily),'step1_days':float(.10/daily) if ok else None,'step2_days':float(.05/daily) if ok else None,'total_days':float(.15/daily) if ok else None}
 return o

def clean(e): return {k:v for k,v in e.items() if not k.endswith('_frame')}

def main():
 if not base.TRADES.exists() or base.sha(base.RAW)!=base.EXPECTED_RAW_SHA: raise RuntimeError('Frozen V5.3 ledger/SHA invalid')
 tr=pd.read_csv(base.TRADES); tr['entry_time']=pd.to_datetime(tr.entry_time,errors='coerce'); tr=tr.dropna(subset=['entry_time','primary_r','stress_r']).copy(); tr['year']=tr.entry_time.dt.year; tr['month']=tr.entry_time.dt.to_period('M').astype(str); tr['date']=tr.entry_time.dt.date
 dates=base.dates_by_year(); dev=tr[tr.year.isin([2021,2022,2023])].copy(); dsess=sum(len(dates[y]) for y in [2021,2022,2023])
 candidates={}; passing=[]
 for name,levels in POLICIES.items():
  e=ev(dev,levels,dsess); p=e['primary_frame']; s=e['stress_frame']; yrs={str(y):base.stats(p[p.year==y].weighted_r) for y in [2021,2022,2023]}
  g={'trade_count_unchanged':len(p)==len(dev),'primary_rpd_ge_0_43':e['primary_r_per_day']>=.43,'primary_pf_ge_1_38':e['primary']['pf'] is not None and e['primary']['pf']>=1.38,'primary_dd_le_11':e['primary']['max_dd']<=11,
     'all_3_years_positive':all(x['sum']>0 for x in yrs.values()),'stress_rpd_ge_0_37':e['stress_r_per_day']>=.37,'stress_pf_ge_1_28':e['stress']['pf'] is not None and e['stress']['pf']>=1.28,'stress_dd_le_12_5':e['stress']['max_dd']<=12.5}
  rec=clean(e); rec['levels_r']=levels; rec['primary_by_year']=yrs; rec['gates']=g; rec['pass']=all(g.values()); candidates[name]=rec
  if rec['pass']: passing.append((name,levels,rec))
 if not passing:
  dump({'status':'V8_DD_THROTTLE_DEV_NO_GO','raw_sha':base.EXPECTED_RAW_SHA,'dev_candidates':candidates,'validation_status':'NOT_OPENED'}); return
 pref={'T3_6':0,'T4_8':1,'T5_10':2}
 passing.sort(key=lambda x:(x[2]['primary_r_per_day'],-x[2]['primary']['max_dd'],pref[x[0]]),reverse=True); name,levels,sel=passing[0]
 val=tr[tr.year.isin([2024,2025])].copy(); vsess=sum(len(dates[y]) for y in [2024,2025]); e=ev(val,levels,vsess); p=e['primary_frame']; s=e['stress_frame']
 years={str(y):base.stats(p[p.year==y].weighted_r) for y in [2024,2025]}; monthly=p.groupby('month').weighted_r.sum(); posrate=float((monthly>0).mean()); worstmonth=float(monthly.min()); daily=p.groupby('date').weighted_r.sum(); worstday=float(daily.min())
 cp=challenge(e['primary_r_per_day'],e['primary']['max_dd'],worstday); speed=any(x and x['admissible'] and x['step1_days']<=45 and x['step2_days']<=23 and x['total_days']<=68 for x in cp.values())
 vg={'primary_rpd_ge_0_44':e['primary_r_per_day']>=.44,'primary_pf_ge_1_40':e['primary']['pf'] is not None and e['primary']['pf']>=1.40,'primary_dd_le_10_7':e['primary']['max_dd']<=10.7,
     '2024_positive':years['2024']['sum']>0,'2025_janapr_positive':years['2025']['sum']>0,'positive_months_ge_70pct':posrate>=.70,'worst_month_ge_minus_8':worstmonth>=-8,
     'stress_rpd_ge_0_38':e['stress_r_per_day']>=.38,'stress_pf_ge_1_30':e['stress']['pf'] is not None and e['stress']['pf']>=1.30,'stress_dd_le_12':e['stress']['max_dd']<=12,'challenge_speed':speed}
 passed=all(vg.values()); p.to_csv(OUT/'VALIDATION_PRIMARY_WEIGHTED.csv',index=False)
 dump({'status':'V8_DD_THROTTLE_PROMISING_REQUIRES_FTMO_FORWARD' if passed else 'V8_DD_THROTTLE_NO_GO','raw_sha':base.EXPECTED_RAW_SHA,'selected_policy':name,'selected_levels_r':levels,
       'dev_candidates':candidates,'selected_dev':sel,'validation':clean(e),'validation_by_year':years,'validation_monthly_r':{str(k):float(v) for k,v in monthly.items()},
       'validation_positive_month_rate':posrate,'validation_worst_month_r':worstmonth,'validation_worst_daily_weighted_r':worstday,'challenge_plan_10k':cp,'validation_gates':vg,'pass':passed,
       'notes':['Zero paid external data.','All V5 signals retained; only position size is throttled by realised strategy drawdown.','Prospective FTMO Free Trial required if PASS.']})

if __name__=='__main__': main()
