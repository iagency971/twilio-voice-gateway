#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

IN=Path('us100-zero-data/results/v14_six_model_segmentation/CANDIDATE_TRADES_SEGMENTED.csv')
OUT=Path('us100-zero-data/results/v14_six_model_segmentation')
RISK=.008
SESS={'DEV':746,'2024':246,'2025':83,'ALL':1075}

def pf(a):
 a=np.asarray(a,float); p=a[a>0].sum(); n=-a[a<0].sum(); return float(p/n) if n>0 else (1e99 if p>0 else None)
def st(v):
 a=np.asarray(v,float)
 if not len(a): return {'n':0,'mean':None,'sum':0.,'pf':None,'win_rate':None,'max_dd':None}
 eq=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0.,eq])[:-1]; dd=np.maximum(pk-eq,0)
 return {'n':int(len(a)),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0))}
def period(y): return 'DEV' if y<=2023 else ('2024' if y==2024 else '2025')
def pace(sumr):
 x=sumr/SESS['ALL']*RISK; return float(.10/x) if x>0 else None

def main():
 d=pd.read_csv(IN); d['entry_time']=pd.to_datetime(d.entry_time); d['year']=d.entry_time.dt.year; d['period']=d.year.map(period); d['model_direction']=d.model+'__'+d.direction
 base=st(d.stress_r); basepace=pace(base['sum'])
 stability={}
 for (wd,p),z in d.groupby(['weekday','period'],sort=True):
  stability.setdefault(wd,{})[p]=st(z.stress_r)
 remove={}
 for wd in sorted(d.weekday.unique()):
  z=d[d.weekday!=wd]; s=st(z.stress_r); p=pace(s['sum'])
  remove[wd]={'stress':s,'implied_step1_days_at_080':p,'delta_step1_days_vs_baseline':None if p is None else float(p-basepace),'delta_dd_r_vs_baseline':float(s['max_dd']-base['max_dd']),'delta_pf_vs_baseline':float(s['pf']-base['pf'])}
 tue=d[d.weekday=='Tuesday']
 tmd={k:st(z.stress_r) for k,z in tue.groupby('model_direction',sort=True)}
 tses={k:st(z.stress_r) for k,z in tue.groupby('session_bucket',sort=True)}
 # Other diagnostic axes, all descriptive
 hours={str(k):st(z.stress_r) for k,z in d.groupby('entry_hour',sort=True)}
 reasons={str(k):st(z.stress_r) for k,z in d.groupby('reason',sort=True)}
 quart={str(k):st(z.stress_r) for k,z in d.groupby('risk_quartile',sort=True)}
 out={'status':'V14B_WEEKDAY_STABILITY_COMPLETE','baseline_stress':base,'baseline_step1_days_at_080':basepace,'weekday_period_stability':stability,'marginal_remove_weekday':remove,'tuesday_model_direction':tmd,'tuesday_session':tses,'entry_hour':hours,'exit_reason':reasons,'risk_quartile':quart,'classification':'DESCRIPTIVE_ONLY'}
 (OUT/'WEEKDAY_STABILITY.json').write_text(json.dumps(out,indent=2,allow_nan=False,default=str))
 print(json.dumps(out,indent=2,default=str))
if __name__=='__main__': main()
