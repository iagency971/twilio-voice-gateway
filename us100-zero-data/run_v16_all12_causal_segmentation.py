#!/usr/bin/env python3
from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd

import run_native_12model_port_v5 as base
import run_native_12model_port_v5_fast as fast

OUT=Path('us100-zero-data/results/v16_all12_causal_segmentation')
RISK=.008
TICK=.25


def pf(a):
 a=np.asarray(a,float); p=a[a>0].sum(); n=-a[a<0].sum(); return float(p/n) if n>0 else (1e99 if p>0 else None)
def st(v):
 a=np.asarray(v,float)
 if not len(a): return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None,'losing_streak':None}
 eq=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0.,eq])[:-1]; dd=np.maximum(pk-eq,0); cur=ls=0
 for x in a:
  if x<0: cur+=1; ls=max(ls,cur)
  else: cur=0
 return {'n':int(len(a)),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0)),'losing_streak':int(ls)}
def bucket(t):
 m=t.hour*60+t.minute
 if 570<=m<630:return 'OPEN_0930_1030'
 if 630<=m<720:return 'MORNING_1030_1200'
 if 720<=m<810:return 'LUNCH_1200_1330'
 if 810<=m<900:return 'PM_1330_1500'
 if 900<=m<960:return 'POWER_1500_1600'
 return 'OTHER'
def period(y): return 'DEV' if y<=2023 else ('2024' if y==2024 else '2025')
def conf(n): return 'VERY_LOW' if n<15 else ('LOW' if n<30 else ('MODERATE' if n<60 else 'HIGH'))
def causal(signals,cooldown=3):
 if not signals:return []
 groups={}
 for s in signals: groups.setdefault(int(s.idx),[]).append(s)
 samebar=[]
 for idx in sorted(groups):
  g=groups[idx]; g.sort(key=lambda s:(s.priority,-s.rr,s.model,s.direction)); samebar.append(g[0])
 out=[]
 for s in samebar:
  if not out or s.idx-out[-1].idx>=cooldown: out.append(s)
 return out
def rescore(trades,bars):
 exact=dict(zip(bars.datetime.dt.strftime('%Y-%m-%d %H:%M'),bars.spread_price.astype(float)))
 med=bars.assign(date=bars.datetime.dt.date).groupby('date').spread_price.median().to_dict(); rows=[]; fb=0
 for t in trades:
  ts=pd.Timestamp(t.entry_time) if str(t.direction).lower()=='long' else pd.Timestamp(t.exit_time); k=ts.strftime('%Y-%m-%d %H:%M')
  if k in exact:c=float(exact[k])
  else:c=float(med[ts.date()]);fb+=1
  rp=float(t.risk_ticks)*TICK; raw=float(t.total_r)
  rows.append({'entry_time':t.entry_time,'exit_time':t.exit_time,'model':t.model,'direction':str(t.direction).lower(),'tag':t.tag,'risk_ticks':t.risk_ticks,'raw_r':raw,'spread_cost_points':c,'primary_r':raw-c/rp,'stress_r':raw-2*c/rp,'reason':t.exit_reason})
 z=pd.DataFrame(rows)
 if len(z): z['entry_time']=pd.to_datetime(z.entry_time); z['exit_time']=pd.to_datetime(z.exit_time); z=z.sort_values('entry_time').reset_index(drop=True)
 return z,fb
def seg(z,total_n,total_r):
 s=st(z.stress_r); p=st(z.primary_r)
 return {'primary':p,'stress':s,'share_trades':float(len(z)/total_n) if total_n else 0.0,'share_stress_r':float(s['sum']/total_r) if total_r else None,'scaled_dd_pct_at_080':None if s['max_dd'] is None else float(s['max_dd']*RISK),'confidence':conf(len(z))}
def group(z,col,total_n,total_r): return {str(k):seg(g,total_n,total_r) for k,g in z.groupby(col,sort=True,dropna=False)}
def pace(sumr,sessions):
 x=sumr/sessions*RISK if sessions else 0; return float(.10/x) if x>0 else None
def removal(z,col,baseline,sessions):
 out={}
 for k in sorted(z[col].dropna().unique(),key=lambda x:str(x)):
  r=z[z[col]!=k]; s=st(r.stress_r); p=pace(s['sum'],sessions)
  out[str(k)]={'remaining_n':int(len(r)),'stress':s,'step1_days_at_080':p,'delta_pf':None if s['pf'] is None else float(s['pf']-baseline['pf']),'delta_dd_r':None if s['max_dd'] is None else float(s['max_dd']-baseline['max_dd']),'delta_step1_days':None if p is None else float(p-pace(baseline['sum'],sessions))}
 return out

def main():
 OUT.mkdir(parents=True,exist_ok=True); ext=fast.ensure_external_fast(); sys.path.insert(0,str(ext.resolve()))
 frames=[]; complete=set()
 for y in base.SOURCE_YEARS:
  d,q=base.load_year(y); frames.append(d); complete|=base.complete_rth_days(d)
 bars=pd.concat(frames,ignore_index=True).sort_values('datetime').drop_duplicates('datetime').reset_index(drop=True); sessions=len(complete)
 raw=bars[['datetime','open','high','low','close','volume']].copy()
 from data.loader import build_daily_bars
 from config import Config
 from strategy.vwap import compute_vwap,compute_opening_range
 from strategy.quant import compute_all_quant_features
 from strategy.multi import MultiModelGenerator
 from strategy.quality import filter_by_quality
 from backtest.engine_v2 import BacktestEngineV2
 from datetime import time as dt_time
 daily=build_daily_bars(raw).copy(); daily['date']=pd.to_datetime(daily.date).dt.date
 cfg=Config(); gen=MultiModelGenerator(cfg)
 df=compute_vwap(raw); df=compute_opening_range(df,minutes=15); df=df.reset_index(drop=True); df=compute_all_quant_features(df)
 ctx=gen._build_context(daily); allsig=[]
 for m in gen.models: allsig.extend(m.generate(df,daily,ctx))
 raw_counts={}
 for s in allsig: raw_counts[s.model]=raw_counts.get(s.model,0)+1
 allsig=gen._apply_atr_hybrid_wider(allsig,df); allsig=gen._filter_disabled(allsig)
 filt=[s for s in allsig if s.ts.time()<dt_time(15,30)]; filt.sort(key=lambda s:s.idx)
 resolved=causal(filt); final=filter_by_quality(resolved,df)
 trades=BacktestEngineV2(cfg).run(df,final); z,fb=rescore(trades,bars)
 z['year']=z.entry_time.dt.year; z['period']=z.year.map(period); z['session']=z.entry_time.map(bucket); z['hour']=z.entry_time.dt.hour.astype(int); z['weekday']=z.entry_time.dt.day_name(); z['model_direction']=z.model+'__'+z.direction
 z['md_session']=z.model_direction+'__'+z.session
 z['md_weekday']=z.model_direction+'__'+z.weekday
 z['risk_quartile']=pd.qcut(pd.to_numeric(z.risk_ticks),4,labels=['Q1_TIGHT','Q2','Q3','Q4_WIDE'],duplicates='drop').astype(str)
 z.to_csv(OUT/'ALL12_CAUSAL_TRADES.csv',index=False)
 n=len(z); total=float(z.stress_r.sum()); base_s=st(z.stress_r); base_p=st(z.primary_r)
 by_period={}
 for p,g in z.groupby('period',sort=True): by_period[str(p)]={'overall':seg(g,n,total),'model':group(g,'model',n,total),'direction':group(g,'direction',n,total),'model_direction':group(g,'model_direction',n,total),'session':group(g,'session',n,total)}
 result={'status':'V16_ALL12_CAUSAL_SEGMENTATION_COMPLETE','sessions':sessions,'risk_reference_pct':.8,
  'signal_diagnostics':{'raw_model_counts':raw_counts,'after_time_filter':len(filt),'after_causal_conflict':len(resolved),'after_quality':len(final),'executed_trades':len(z),'spread_fallback_count':fb},
  'baseline':{'primary':base_p,'stress':base_s,'trades_per_session':float(n/sessions),'stress_r_per_session':float(total/sessions),'step1_days_at_080':pace(total,sessions),'scaled_dd_pct_at_080':float(base_s['max_dd']*RISK)},
  'model':group(z,'model',n,total),'direction':group(z,'direction',n,total),'model_direction':group(z,'model_direction',n,total),'session':group(z,'session',n,total),'model_direction_session':group(z,'md_session',n,total),'hour':group(z,'hour',n,total),'weekday':group(z,'weekday',n,total),'model_direction_weekday':group(z,'md_weekday',n,total),'exit_reason':group(z,'reason',n,total),'risk_quartile':group(z,'risk_quartile',n,total),'periods':by_period,
  'remove_model':removal(z,'model',base_s,sessions),'remove_model_direction':removal(z,'model_direction',base_s,sessions),'remove_direction':removal(z,'direction',base_s,sessions),'remove_session':removal(z,'session',base_s,sessions),'remove_weekday':removal(z,'weekday',base_s,sessions),
  'classification':'DIAGNOSTIC_ON_CAUSAL_FULL12_LEDGER; NEW FILTERS REQUIRE TRUE RERUN/FORWARD'}
 (OUT/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False,default=str))
 rows=[]
 for typ,m in [('model',result['model']),('direction',result['direction']),('model_direction',result['model_direction']),('session',result['session']),('weekday',result['weekday'])]:
  for name,r in m.items():
   s=r['stress']; rows.append({'type':typ,'segment':name,'n':s['n'],'mean_r':s['mean'],'sum_r':s['sum'],'pf':s['pf'],'win_rate':s['win_rate'],'max_dd_r':s['max_dd'],'share_trades':r['share_trades'],'share_r':r['share_stress_r'],'confidence':r['confidence']})
 pd.DataFrame(rows).to_csv(OUT/'SEGMENT_SUMMARY.csv',index=False)
 print(json.dumps({'status':result['status'],'baseline':result['baseline'],'model_direction':result['model_direction'],'session':result['session'],'weekday':result['weekday']},indent=2,default=str))
if __name__=='__main__':main()
