#!/usr/bin/env python3
from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd

import run_native_12model_port_v5 as base
import run_native_12model_port_v5_fast as fast

OUT=Path('us100-zero-data/results/v15_true6_causal_rerun')
MODELS=('ema_rev','kalman_mom','open_drive','ou_rev','pd_rev','pm_mom')
MODEL_TICK=.25
RISK_REF=.008


def pf(a):
 a=np.asarray(a,float); p=a[a>0].sum(); n=-a[a<0].sum(); return float(p/n) if n>0 else (1e99 if p>0 else None)
def stats(v):
 a=np.asarray(v,float)
 if not len(a):return {'n':0,'mean':None,'sum':0.,'pf':None,'win_rate':None,'max_dd':None,'losing_streak':None}
 eq=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0.,eq])[:-1]; dd=np.maximum(pk-eq,0); cur=ls=0
 for x in a:
  if x<0:cur+=1; ls=max(ls,cur)
  else:cur=0
 return {'n':int(len(a)),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0)),'losing_streak':int(ls)}
def remove_best10(a):
 a=np.asarray(a,float)
 if not len(a):return None
 n=int(math.ceil(len(a)*.10)); b=np.sort(a)[::-1][n:]; return float(b.mean()) if len(b) else None

def causal_resolver(signals,cooldown_bars=3):
 if not signals:return []
 # Same-bar candidates are contemporaneously knowable.
 groups={}
 for s in signals:groups.setdefault(int(s.idx),[]).append(s)
 winners=[]
 for idx in sorted(groups):
  g=groups[idx]
  g.sort(key=lambda s:(s.priority,-s.rr,s.model,s.direction))
  winners.append(g[0])
 accepted=[]
 for s in winners:
  if not accepted or s.idx-accepted[-1].idx>=cooldown_bars:accepted.append(s)
 return accepted

def prepare_six(raw,daily):
 """Compute frozen features and six-model pre-conflict signals exactly once.
 Both V15 arms consume this identical prepared signal stream; only resolver differs.
 """
 from config import Config
 from strategy.vwap import compute_vwap,compute_opening_range
 from strategy.quant import compute_all_quant_features
 from strategy.multi import MultiModelGenerator
 from strategy.models.ema_reversion import EMAReversionModel
 from strategy.models.kalman_momentum import KalmanMomentumModel
 from strategy.models.opening_drive import OpeningDriveModel
 from strategy.models.ou_reversion import OUReversionModel
 from strategy.models.pd_level_reversion import PDLevelReversionModel
 from strategy.models.afternoon_momentum import AfternoonMomentumModel
 from datetime import time as dt_time
 cfg=Config(); gen=MultiModelGenerator(cfg)
 gen.models=[EMAReversionModel(cfg),KalmanMomentumModel(cfg),OpeningDriveModel(cfg),OUReversionModel(cfg),PDLevelReversionModel(cfg),AfternoonMomentumModel(cfg)]
 df=compute_vwap(raw); df=compute_opening_range(df,minutes=15); df=df.reset_index(drop=True); df=compute_all_quant_features(df)
 context=gen._build_context(daily)
 allsig=[]
 for m in gen.models:allsig.extend(m.generate(df,daily,context))
 raw_model_counts={}
 for s in allsig:raw_model_counts[s.model]=raw_model_counts.get(s.model,0)+1
 allsig=gen._apply_atr_hybrid_wider(allsig,df); allsig=gen._filter_disabled(allsig)
 filt=[s for s in allsig if s.ts.time()<dt_time(15,30)]; filt.sort(key=lambda s:s.idx)
 prep={'raw_model_counts':raw_model_counts,'after_time_filter':len(filt)}
 return cfg,gen,df,filt,prep

def resolve_arm(gen,df,filt,prep,causal=False):
 from strategy.quality import filter_by_quality
 resolved=causal_resolver(filt) if causal else gen._resolve_conflicts(filt)
 final=filter_by_quality(resolved,df)
 diag=dict(prep); diag.update({'after_conflict':len(resolved),'after_quality':len(final)})
 return final,diag

def rescore(trades,sp):
 rows=[]; fallback=0
 exact=dict(zip(sp.datetime.dt.strftime('%Y-%m-%d %H:%M'),sp.spread_price.astype(float)))
 med=sp.assign(date=sp.datetime.dt.date).groupby('date').spread_price.median().to_dict()
 for t in trades:
  req=pd.Timestamp(t.entry_time) if t.direction=='long' else pd.Timestamp(t.exit_time); key=req.strftime('%Y-%m-%d %H:%M')
  if key in exact:c=float(exact[key])
  else:c=float(med[req.date()]); fallback+=1
  risk_points=float(t.risk_ticks)*MODEL_TICK
  raw=float(t.total_r); pr=raw-c/risk_points; sr=raw-2*c/risk_points
  rows.append({'entry_time':t.entry_time,'exit_time':t.exit_time,'direction':t.direction,'model':t.model,'tag':t.tag,'risk_ticks':t.risk_ticks,'raw_r':raw,'spread_cost_points':c,'primary_r':pr,'stress_r':sr,'reason':t.exit_reason})
 z=pd.DataFrame(rows)
 if len(z):
  z['entry_time']=pd.to_datetime(z.entry_time); z['year']=z.entry_time.dt.year; z=z.sort_values('entry_time').reset_index(drop=True)
 return z,fallback

def summarize(z,sessions):
 p=stats(z.primary_r if len(z) else []); s=stats(z.stress_r if len(z) else [])
 byy={}
 if len(z):
  for y,g in z.groupby('year',sort=True):byy[str(int(y))]={'primary':stats(g.primary_r),'stress':stats(g.stress_r)}
 bym={}
 if len(z):
  for m,g in z.groupby('model',sort=True):bym[str(m)]={'primary':stats(g.primary_r),'stress':stats(g.stress_r)}
 byd={}
 if len(z):
  for d,g in z.groupby('direction',sort=True):byd[str(d)]={'primary':stats(g.primary_r),'stress':stats(g.stress_r)}
 rps=s['sum']/sessions if sessions else 0.; pace=.10/(rps*RISK_REF) if rps>0 else None
 return {'primary':p,'stress':s,'trades_per_session':float(len(z)/sessions),'stress_r_per_session':float(rps),'stress_scaled_dd_pct_at_080':None if s['max_dd'] is None else float(s['max_dd']*RISK_REF),'implied_step1_days_at_080':None if pace is None else float(pace),'stress_remove_best10_mean':remove_best10(z.stress_r if len(z) else []),'by_year':byy,'by_model':bym,'by_direction':byd}

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 ext=fast.ensure_external_fast(); sys.path.insert(0,str(ext.resolve()))
 frames=[]; sessions=0
 for y in base.SOURCE_YEARS:
  d,q=base.load_year(y); frames.append(d); sessions+=len(base.complete_rth_days(d))
 allbars=pd.concat(frames,ignore_index=True).sort_values('datetime').drop_duplicates('datetime').reset_index(drop=True)
 from data.loader import build_daily_bars
 raw=allbars[['datetime','open','high','low','close','volume']].copy()
 daily=build_daily_bars(raw).copy(); daily['date']=pd.to_datetime(daily['date']).dt.date
 from backtest.engine_v2 import BacktestEngineV2
 cfg,gen,df,filt,prep=prepare_six(raw,daily)
 results={}
 for name,causal in [('ARM_A_TRUE6_ORIGINAL_RESOLVER',False),('ARM_B_TRUE6_CAUSAL_RESOLVER',True)]:
  signals,diag=resolve_arm(gen,df,filt,prep,causal)
  engine=BacktestEngineV2(cfg); trades=engine.run(df,signals); z,fb=rescore(trades,allbars); z.to_csv(OUT/f'{name}_TRADES.csv',index=False)
  results[name]={'signal_diagnostics':diag,'executed_trade_count':len(z),'spread_fallback_count':fb,'summary':summarize(z,sessions)}
 # Prior V14 filtered-ledger benchmark.
 old=pd.read_csv('us100-zero-data/results/native_12model_port_v5/TRADES_RESCORED.csv'); old['entry_time']=pd.to_datetime(old.entry_time); old=old[old.model.isin(MODELS)].copy(); old['year']=old.entry_time.dt.year
 oldsum=summarize(old,sessions)
 a=results['ARM_A_TRUE6_ORIGINAL_RESOLVER']['summary']; b=results['ARM_B_TRUE6_CAUSAL_RESOLVER']['summary']
 out={'status':'V15_TRUE6_CAUSAL_RERUN_COMPLETE','implementation_note':'V15.1 one prepared signal pass shared by both arms; resolver logic/protocol unchanged','sessions':sessions,'candidate_models':list(MODELS),'prior_filtered_v14':oldsum,'arms':results,
      'deltas':{'armA_minus_prior_n':int(a['stress']['n']-oldsum['stress']['n']),'armA_minus_prior_stress_mean':float(a['stress']['mean']-oldsum['stress']['mean']),'armA_minus_prior_dd_r':float(a['stress']['max_dd']-oldsum['stress']['max_dd']),
                'armB_minus_armA_n':int(b['stress']['n']-a['stress']['n']),'armB_minus_armA_stress_mean':float(b['stress']['mean']-a['stress']['mean']),'armB_minus_armA_dd_r':float(b['stress']['max_dd']-a['stress']['max_dd'])},
      'methodology_note':'Only ARM B is causally implementable as the proposed MT5 design. V15 changes no model/feature/exit parameter.'}
 (OUT/'RESULT.json').write_text(json.dumps(out,indent=2,allow_nan=False,default=str))
 print(json.dumps({'status':out['status'],'sessions':sessions,'prior':oldsum,'armA':a,'armB':b,'deltas':out['deltas']},indent=2,default=str))
if __name__=='__main__':main()
