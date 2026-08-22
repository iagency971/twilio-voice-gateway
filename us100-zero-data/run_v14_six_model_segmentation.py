#!/usr/bin/env python3
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd

LEDGER=Path('us100-zero-data/results/native_12model_port_v5/TRADES_RESCORED.csv')
OUT=Path('us100-zero-data/results/v14_six_model_segmentation')
MODELS=('ema_rev','kalman_mom','open_drive','ou_rev','pd_rev','pm_mom')
RISK=0.008
SESSIONS={'DEV':746,'2024':246,'2025':83,'ALL':1075}


def pf(a):
    a=np.asarray(a,float); pos=a[a>0].sum(); neg=-a[a<0].sum()
    return float(pos/neg) if neg>0 else (1e99 if pos>0 else None)

def stats(v):
    a=np.asarray(v,float)
    if len(a)==0:return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None,'losing_streak':None}
    eq=np.cumsum(a); peaks=np.maximum.accumulate(np.r_[0.,eq])[:-1]; dd=np.maximum(peaks-eq,0.0)
    cur=longest=0
    for x in a:
        if x<0:cur+=1; longest=max(longest,cur)
        else:cur=0
    return {'n':int(len(a)),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0.0)),'losing_streak':int(longest)}

def bucket(t):
    m=t.hour*60+t.minute
    if 570<=m<630:return 'OPEN_0930_1030'
    if 630<=m<720:return 'MORNING_1030_1200'
    if 720<=m<810:return 'LUNCH_1200_1330'
    if 810<=m<900:return 'PM_1330_1500'
    if 900<=m<960:return 'POWER_1500_1600'
    return 'OTHER'

def confidence(n):
    if n<15:return 'VERY_LOW'
    if n<30:return 'LOW'
    if n<60:return 'MODERATE'
    return 'HIGH'

def segrec(z,total_n,total_stress,session_den=None):
    p=stats(z.primary_r.to_numpy()); s=stats(z.stress_r.to_numpy())
    return {'primary':p,'stress':s,'share_of_trades':float(len(z)/total_n) if total_n else 0.0,
            'share_of_stress_total_r':float(s['sum']/total_stress) if total_stress else None,
            'scaled_stress_dd_pct_at_080':float(s['max_dd']*RISK) if s['max_dd'] is not None else None,
            'stress_r_per_session':float(s['sum']/session_den) if session_den else None,
            'confidence':confidence(len(z))}

def period_name(y):
    if y<=2023:return 'DEV'
    if y==2024:return '2024'
    return '2025'

def group_table(d,col,total_n,total_stress):
    out={}
    for k,z in d.groupby(col,sort=True,dropna=False):out[str(k)]=segrec(z,total_n,total_stress)
    return out

def nested_period(d,cols):
    out={}
    for keys,z in d.groupby(cols+['period'],sort=True,dropna=False):
        if not isinstance(keys,tuple):keys=(keys,)
        label='__'.join(str(x) for x in keys[:-1]); per=str(keys[-1])
        out.setdefault(label,{})[per]=segrec(z,len(d),float(d.stress_r.sum()),SESSIONS[per])
    return out

def pace(sum_r,sessions):
    rps=sum_r/sessions if sessions else 0.0; daily=rps*RISK
    return float(.10/daily) if daily>0 else None

def removal(d,col,baseline):
    out={}
    for k in sorted(d[col].dropna().unique(),key=lambda x:str(x)):
        z=d[d[col]!=k].copy(); s=stats(z.stress_r.to_numpy())
        p10=pace(s['sum'],SESSIONS['ALL'])
        out[str(k)]={'remaining_n':int(len(z)),'stress':s,'stress_r_per_session':float(s['sum']/SESSIONS['ALL']),
                     'implied_step1_days_at_080':p10,
                     'delta_stress_total_r_vs_baseline':float(s['sum']-baseline['stress']['sum']),
                     'delta_stress_pf_vs_baseline':None if s['pf'] is None or baseline['stress']['pf'] is None else float(s['pf']-baseline['stress']['pf']),
                     'delta_stress_dd_r_vs_baseline':None if s['max_dd'] is None else float(s['max_dd']-baseline['stress']['max_dd']),
                     'delta_step1_days_vs_baseline':None if p10 is None else float(p10-baseline['implied_step1_days_at_080'])}
    return out

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    d=pd.read_csv(LEDGER)
    d['entry_time']=pd.to_datetime(d.entry_time,errors='coerce'); d['exit_time']=pd.to_datetime(d.exit_time,errors='coerce')
    d=d.dropna(subset=['entry_time','model','direction','primary_r','stress_r']).copy()
    d=d[d.model.isin(MODELS)].sort_values(['entry_time','exit_time']).reset_index(drop=True)
    d['year']=d.entry_time.dt.year; d['period']=d.year.map(period_name); d['session_bucket']=d.entry_time.map(bucket)
    d['entry_hour']=d.entry_time.dt.hour.astype(int); d['weekday']=d.entry_time.dt.day_name()
    d['direction']=d.direction.astype(str).str.lower(); d['reason']=d.reason.astype(str)
    d['risk_ticks']=pd.to_numeric(d.risk_ticks,errors='coerce')
    q=pd.qcut(d['risk_ticks'],4,labels=['Q1_TIGHT','Q2','Q3','Q4_WIDE'],duplicates='drop'); d['risk_quartile']=q.astype(str)
    d['model_direction']=d.model+'__'+d.direction

    total_n=len(d); total_stress=float(d.stress_r.sum()); base_s=stats(d.stress_r.to_numpy()); base_p=stats(d.primary_r.to_numpy())
    baseline={'primary':base_p,'stress':base_s,'trades_per_session':float(total_n/SESSIONS['ALL']),
              'stress_r_per_session':float(base_s['sum']/SESSIONS['ALL']),
              'scaled_stress_dd_pct_at_080':float(base_s['max_dd']*RISK),
              'implied_step1_days_at_080':pace(base_s['sum'],SESSIONS['ALL'])}

    by_model_direction={}
    for k,z in d.groupby('model_direction',sort=True):by_model_direction[k]=segrec(z,total_n,total_stress)

    result={'status':'V14_SEGMENTATION_DIAGNOSTIC_COMPLETE','classification':'DESCRIPTIVE_NOT_NEW_OOS_VALIDATION',
            'candidate_models':list(MODELS),'risk_reference_pct':0.8,'baseline':baseline,
            'direction':group_table(d,'direction',total_n,total_stress),
            'model':group_table(d,'model',total_n,total_stress),
            'model_direction':by_model_direction,
            'session_bucket':group_table(d,'session_bucket',total_n,total_stress),
            'entry_hour':group_table(d,'entry_hour',total_n,total_stress),
            'weekday':group_table(d,'weekday',total_n,total_stress),
            'exit_reason':group_table(d,'reason',total_n,total_stress),
            'risk_quartile':group_table(d,'risk_quartile',total_n,total_stress),
            'period_stability_direction':nested_period(d,['direction']),
            'period_stability_session':nested_period(d,['session_bucket']),
            'period_stability_model_direction':nested_period(d,['model_direction']),
            'marginal_remove_direction':removal(d,'direction',baseline),
            'marginal_remove_session':removal(d,'session_bucket',baseline),
            'marginal_remove_model':removal(d,'model',baseline),
            'notes':['Diagnostic only: aggregate 2024/2025 candidate outcomes were already observed before V14.','Any filter suggested by V14 must be validated prospectively on FTMO Free Trial/forward.','Cells with N<30 are low-confidence; N<15 very-low-confidence.']}
    (OUT/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False,default=str))
    cols=['entry_time','exit_time','direction','model','session_bucket','entry_hour','weekday','reason','risk_quartile','primary_r','stress_r','risk_ticks']
    d[cols].to_csv(OUT/'CANDIDATE_TRADES_SEGMENTED.csv',index=False)
    # compact sortable segment export
    rows=[]
    for typ,keymap in [('direction',result['direction']),('model',result['model']),('model_direction',result['model_direction']),('session',result['session_bucket']),('weekday',result['weekday'])]:
        for name,r in keymap.items():
            s=r['stress']; rows.append({'type':typ,'segment':name,'n':s['n'],'mean_r':s['mean'],'sum_r':s['sum'],'pf':s['pf'],'win_rate':s['win_rate'],'max_dd_r':s['max_dd'],'share_trades':r['share_of_trades'],'share_total_r':r['share_of_stress_total_r'],'confidence':r['confidence']})
    pd.DataFrame(rows).sort_values(['type','mean_r'],ascending=[True,False]).to_csv(OUT/'SEGMENT_SUMMARY.csv',index=False)
    print(json.dumps({'status':result['status'],'baseline':baseline,'directions':result['direction'],'sessions':result['session_bucket']},indent=2,default=str))

if __name__=='__main__':main()
