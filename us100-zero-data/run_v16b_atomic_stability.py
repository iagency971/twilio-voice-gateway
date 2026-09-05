#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

IN=Path('us100-zero-data/results/v16_all12_causal_segmentation/ALL12_CAUSAL_TRADES.csv')
OUT=Path('us100-zero-data/results/v16b_atomic_stability')
PERIODS=('DEV','2024','2025')

def pf(a):
 a=np.asarray(a,float); p=a[a>0].sum(); n=-a[a<0].sum(); return float(p/n) if n>0 else (1e99 if p>0 else None)
def st(v):
 a=np.asarray(v,float)
 if not len(a):return {'n':0,'mean':None,'sum':0.,'pf':None,'win_rate':None,'max_dd':None}
 eq=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0.,eq])[:-1]; dd=np.maximum(pk-eq,0)
 return {'n':int(len(a)),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0))}
def period(y):return 'DEV' if y<=2023 else ('2024' if y==2024 else '2025')
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 d=pd.read_csv(IN); d['entry_time']=pd.to_datetime(d.entry_time); d['year']=d.entry_time.dt.year; d['period']=d.year.map(period); d['model_direction']=d.model+'__'+d.direction
 rows=[]; detail={}
 for md,g in d.groupby('model_direction',sort=True):
  rec={'ALL':st(g.stress_r)}; pos=0; observed=0
  for p in PERIODS:
   x=g[g.period==p]; s=st(x.stress_r); rec[p]=s
   if s['n']>0:
    observed+=1
    if s['sum']>0:pos+=1
  detail[md]=rec
  rows.append({'model_direction':md,'all_n':rec['ALL']['n'],'all_mean':rec['ALL']['mean'],'all_pf':rec['ALL']['pf'],'all_dd':rec['ALL']['max_dd'],
               'dev_n':rec['DEV']['n'],'dev_mean':rec['DEV']['mean'],'dev_pf':rec['DEV']['pf'],'dev_sum':rec['DEV']['sum'],
               'y2024_n':rec['2024']['n'],'y2024_mean':rec['2024']['mean'],'y2024_pf':rec['2024']['pf'],'y2024_sum':rec['2024']['sum'],
               'y2025_n':rec['2025']['n'],'y2025_mean':rec['2025']['mean'],'y2025_pf':rec['2025']['pf'],'y2025_sum':rec['2025']['sum'],
               'positive_periods':pos,'observed_periods':observed,'all_periods_positive':pos==observed and observed==3,
               'min_period_mean':min([x['mean'] for p,x in rec.items() if p!='ALL' and x['mean'] is not None],default=None)})
 pd.DataFrame(rows).sort_values(['all_periods_positive','min_period_mean','all_mean'],ascending=[False,False,False]).to_csv(OUT/'MODEL_DIRECTION_PERIODS.csv',index=False)
 # Same period stability for weekday/session.
 for col,name in [('weekday','WEEKDAY_PERIODS.csv'),('session','SESSION_PERIODS.csv'),('model','MODEL_PERIODS.csv')]:
  rr=[]
  for key,g in d.groupby(col,sort=True):
   x={'segment':key,'type':col}
   for p in PERIODS:
    s=st(g[g.period==p].stress_r); x[f'{p}_n']=s['n'];x[f'{p}_mean']=s['mean'];x[f'{p}_pf']=s['pf'];x[f'{p}_sum']=s['sum']
   a=st(g.stress_r);x.update({'all_n':a['n'],'all_mean':a['mean'],'all_pf':a['pf'],'all_dd':a['max_dd']});rr.append(x)
  pd.DataFrame(rr).to_csv(OUT/name,index=False)
 (OUT/'RESULT.json').write_text(json.dumps({'status':'V16B_ALL12_ATOMIC_STABILITY_COMPLETE','model_direction':detail},indent=2,allow_nan=False,default=str))
 print(pd.DataFrame(rows).sort_values(['all_periods_positive','min_period_mean','all_mean'],ascending=[False,False,False]).to_string(index=False))
if __name__=='__main__':main()
