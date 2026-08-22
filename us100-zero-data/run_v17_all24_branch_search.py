#!/usr/bin/env python3
from __future__ import annotations
import json, math, sys
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd

import run_native_12model_port_v5 as base
import run_native_12model_port_v5_fast as fast

OUT=Path('us100-zero-data/results/v17_all24_branch_search')
V16=Path('us100-zero-data/results/v16_all12_causal_segmentation/ALL12_CAUSAL_TRADES.csv')
RISK_GRID=tuple(round(x/10000,6) for x in range(25,101,5))
DEV_YEARS=(2021,2022,2023); DEV_SESS=746; TICK=.25; BEAM=60; TRUE_K=40

def pf(a):
 a=np.asarray(a,float); p=a[a>0].sum(); n=-a[a<0].sum(); return float(p/n) if n>0 else (1e99 if p>0 else None)
def stats(v):
 a=np.asarray(v,float)
 if not len(a):return {'n':0,'mean':None,'sum':0.,'pf':None,'win_rate':None,'max_dd':None,'losing_streak':None}
 eq=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0.,eq])[:-1]; dd=np.maximum(pk-eq,0); cur=ls=0
 for x in a:
  if x<0:cur+=1;ls=max(ls,cur)
  else:cur=0
 return {'n':int(len(a)),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0)),'losing_streak':int(ls)}
def worst_intraday_r(z,col='stress_r'):
 w=0.
 for _,g in z.sort_values('entry_time').groupby(z.entry_time.dt.date,sort=True):
  c=0.
  for x in g[col].to_numpy(float):c+=float(x);w=min(w,c)
 return float(w)
def min_cumulative_r(z,col='stress_r'):
 a=z.sort_values('entry_time')[col].to_numpy(float); return float(np.cumsum(a).min(initial=0.)) if len(a) else 0.
def remove_best10(a):
 a=np.asarray(a,float)
 if not len(a):return None
 n=int(math.ceil(len(a)*.10)); b=np.sort(a)[::-1][n:]; return float(b.mean()) if len(b) else None
def risk_choice(z,strict=True):
 s=stats(z.stress_r); wi=worst_intraday_r(z); mc=min_cumulative_r(z); yrs={y:float(z[z.entry_time.dt.year==y].stress_r.sum()) for y in DEV_YEARS}
 if s['n']==0 or s['sum']<=0:return None
 for r in reversed(RISK_GRID):
  if s['max_dd']*r>=.085 or abs(min(0.,wi))*r>=.04 or mc*r<=-.10:continue
  if strict:
   if s['n']<300 or s['pf'] is None or s['pf']<1.25 or not all(v>0 for v in yrs.values()):continue
  else:
   if s['n']<200 or s['pf'] is None or s['pf']<1.10 or sum(v>0 for v in yrs.values())<2:continue
  rps=s['sum']/DEV_SESS; pace=.10/(rps*r) if rps>0 else None
  return {'risk':r,'pace':pace,'stats':s,'worst_intraday_r':wi,'min_cumulative_r':mc,'years':yrs,'r_per_session':rps}
 return None
def causal(signals,cooldown=3):
 if not signals:return []
 groups={}
 for s in signals:groups.setdefault(int(s.idx),[]).append(s)
 same=[]
 for idx in sorted(groups):
  g=groups[idx];g.sort(key=lambda s:(s.priority,-s.rr,s.model,s.direction));same.append(g[0])
 out=[]
 for s in same:
  if not out or s.idx-out[-1].idx>=cooldown:out.append(s)
 return out

def rescore(trades,bars):
 exact=dict(zip(bars.datetime.dt.strftime('%Y-%m-%d %H:%M'),bars.spread_price.astype(float))); med=bars.assign(date=bars.datetime.dt.date).groupby('date').spread_price.median().to_dict(); rows=[]
 for t in trades:
  ts=pd.Timestamp(t.entry_time) if str(t.direction).lower()=='long' else pd.Timestamp(t.exit_time); k=ts.strftime('%Y-%m-%d %H:%M'); c=float(exact.get(k,med[ts.date()])); rp=float(t.risk_ticks)*TICK; raw=float(t.total_r)
  rows.append({'entry_time':t.entry_time,'exit_time':t.exit_time,'model':t.model,'direction':str(t.direction).lower(),'risk_ticks':t.risk_ticks,'raw_r':raw,'primary_r':raw-c/rp,'stress_r':raw-2*c/rp,'reason':t.exit_reason})
 z=pd.DataFrame(rows)
 if len(z):z['entry_time']=pd.to_datetime(z.entry_time);z['exit_time']=pd.to_datetime(z.exit_time);z['branch']=z.model+'__'+z.direction;z=z.sort_values('entry_time').reset_index(drop=True)
 return z

def prepare():
 ext=fast.ensure_external_fast();sys.path.insert(0,str(ext.resolve()));frames=[];complete=set()
 for y in base.SOURCE_YEARS:
  d,_=base.load_year(y);frames.append(d);complete|=base.complete_rth_days(d)
 bars=pd.concat(frames,ignore_index=True).sort_values('datetime').drop_duplicates('datetime').reset_index(drop=True);raw=bars[['datetime','open','high','low','close','volume']].copy()
 from data.loader import build_daily_bars
 from config import Config
 from strategy.vwap import compute_vwap,compute_opening_range
 from strategy.quant import compute_all_quant_features
 from strategy.multi import MultiModelGenerator
 from datetime import time as dt_time
 daily=build_daily_bars(raw).copy();daily['date']=pd.to_datetime(daily.date).dt.date;cfg=Config();gen=MultiModelGenerator(cfg)
 df=compute_vwap(raw);df=compute_opening_range(df,minutes=15);df=df.reset_index(drop=True);df=compute_all_quant_features(df);ctx=gen._build_context(daily);alls=[]
 for m in gen.models:alls.extend(m.generate(df,daily,ctx))
 alls=gen._apply_atr_hybrid_wider(alls,df);alls=gen._filter_disabled(alls);filt=[s for s in alls if s.ts.time()<dt_time(15,30)];filt.sort(key=lambda s:s.idx)
 return cfg,gen,df,filt,bars,len(complete)

def branch(s):return f'{s.model}__{s.direction}'

# Fast engine: same frozen logic, exact signal timestamp -> direct index lookup.
def make_fast_engine(BaseEngine,Trade,GLOBAL_MIN,GLOBAL_MAX):
 class FE(BaseEngine):
  def run(self,df,signals):self._idxmap={pd.Timestamp(x):i for i,x in enumerate(df['datetime'].tolist())};return super().run(df,signals)
  def _sim(self,df,sig):
   signal_idx=self._idxmap.get(pd.Timestamp(sig.ts));
   if signal_idx is None:return None
   fill_idx=signal_idx+1
   if fill_idx>=len(df):return None
   fill_bar=df.iloc[fill_idx];entry=fill_bar['open'];is_long=sig.direction=='long'
   if is_long and entry<=sig.stop:return None
   if (not is_long) and entry>=sig.stop:return None
   risk=abs(entry-sig.stop);risk_ticks=risk/self.tick;rp=sig.risk_profile
   if rp:
    floor=max(rp.min_risk_ticks,GLOBAL_MIN);ceiling=min(rp.max_risk_ticks,GLOBAL_MAX)
    if not(floor<=risk_ticks<=ceiling):return None
    reward=abs(sig.target-entry)
    if risk>0 and reward/risk<rp.min_rr:return None
   trade=Trade(signal=sig,entry_time=fill_bar['datetime'],entry_price=entry,direction=sig.direction,stop_price=sig.stop,target_price=sig.target,risk=risk,risk_ticks=risk_ticks,model=sig.model,tag=sig.tag)
   be_trigger=rp.be_trigger_rr if rp else self.cfg.risk.be_trigger_rr;partial_rr=rp.partial_rr if rp else self.cfg.risk.partial_rr;partial_pct=rp.partial_pct if rp else self.cfg.risk.partial_pct;time_stop_min=rp.time_stop_minutes if rp else self.cfg.strategy.time_stop_minutes
   trail_pct=rp.trail_pct if rp else 0.;trail_dist=trail_pct*risk if trail_pct>0 and risk>0 else 0.;trailing=False;cur_stop=sig.stop;be=partial=False;partial_r=0.;mfe=0.;time_limit=fill_bar['datetime']+pd.Timedelta(minutes=time_stop_min)
   for i in range(fill_idx,len(df)):
    b=df.iloc[i]
    if is_long:
     best=b['high']-entry
     if best>mfe:
      mfe=best
      if trailing and trail_dist>0:
       nt=entry+mfe-trail_dist
       if nt>cur_stop:cur_stop=self._round(nt)
     hit_stop=b['low']<=cur_stop;hit_target=(not trailing) and b['high']>=sig.target
    else:
     best=entry-b['low']
     if best>mfe:
      mfe=best
      if trailing and trail_dist>0:
       nt=entry-mfe+trail_dist
       if nt<cur_stop:cur_stop=self._round(nt)
     hit_stop=b['high']>=cur_stop;hit_target=(not trailing) and b['low']<=sig.target
    if hit_stop and hit_target:
     if abs(b['open']-cur_stop)<=abs(b['open']-sig.target):self._close(trade,b,cur_stop,'stop_ambiguous',is_long,partial_r,partial,partial_pct)
     else:self._close(trade,b,sig.target,'target',is_long,partial_r,partial,partial_pct)
     break
    if hit_stop:
     reason='trail' if trailing else ('breakeven' if be else 'stop');self._close(trade,b,cur_stop,reason,is_long,partial_r,partial,partial_pct);break
    if hit_target:self._close(trade,b,sig.target,'target',is_long,partial_r,partial,partial_pct);break
    if not partial and risk>0 and best>=risk*partial_rr:
     partial=True;partial_r=partial_pct*partial_rr;trade.partial_taken=True
     if trail_dist>0:trailing=True
    if not be and risk>0 and best>=risk*be_trigger:cur_stop=entry;be=True;trade.moved_be=True
    if b['datetime']>=time_limit and not be:self._close(trade,b,b['close'],'time_stop',is_long,partial_r,partial,partial_pct);break
    if b['datetime'].time()>=self.cfg.sessions.session_close:self._close(trade,b,b['close'],'session_close',is_long,partial_r,partial,partial_pct);break
   else:
    b=df.iloc[-1];self._close(trade,b,b['close'],'end_of_data',is_long,partial_r,partial,partial_pct)
   return trade
 return FE

def approx_beam(ledger,branches):
 dev=ledger[ledger.entry_time.dt.year.isin(DEV_YEARS)].copy();cache={};seen={}
 def ev(fs):
  key=tuple(sorted(fs))
  if key in cache:return cache[key]
  z=dev[dev.branch.isin(key)];r=risk_choice(z,strict=False);cache[key]=r;return r
 full=frozenset(branches);beam=[full];pool={full}
 # Backward beam across all subset sizes down to 4 branches.
 for _ in range(max(0,len(branches)-4)):
  cand=set()
  for fs in beam:
   for b in fs:
    nf=frozenset(x for x in fs if x!=b)
    if len(nf)>=4:cand.add(nf)
  scored=[]
  for fs in cand:
   r=ev(fs)
   if r and r['pace'] is not None:scored.append((r['pace'],-r['stats']['pf'],r['stats']['max_dd'],len(fs),tuple(sorted(fs)),fs))
  scored.sort();beam=[x[-1] for x in scored[:BEAM]];pool.update(beam)
  if not beam:break
 # Add deterministic top-branch prefix seeds by DEV branch expectancy and R contribution.
 br=[]
 for b in branches:
  z=dev[dev.branch==b];s=stats(z.stress_r);br.append((-(s['mean'] or -999),-(s['sum']),b))
 br.sort();ordered=[x[2] for x in br]
 for k in range(4,len(ordered)+1):pool.add(frozenset(ordered[:k]))
 ranked=[]
 for fs in pool:
  r=ev(fs)
  if r and r['pace'] is not None:ranked.append((r['pace'],-r['stats']['pf'],r['stats']['max_dd'],len(fs),tuple(sorted(fs)),fs,r))
 ranked.sort();return ranked,cache

def true_eval(fs,cfg,gen,df,filt,bars,FE):
 from strategy.quality import filter_by_quality
 from backtest.engine_v2 import BacktestEngineV2
 sig=[s for s in filt if branch(s) in fs];resolved=causal(sig);final=filter_by_quality(resolved,df);z=rescore(FE(cfg).run(df,final),bars);dev=z[z.entry_time.dt.year.isin(DEV_YEARS)].copy();rc=risk_choice(dev,strict=True)
 return z,dev,rc,{'preconflict':len(sig),'postconflict':len(resolved),'postquality':len(final)}
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 led=pd.read_csv(V16);led['entry_time']=pd.to_datetime(led.entry_time);led['branch']=led.model+'__'+led.direction;branches=sorted(led.branch.unique().tolist());ranked,_=approx_beam(led,branches)
 cfg,gen,df,filt,bars,sessions=prepare()
 from backtest.engine_v2 import BacktestEngineV2,Trade
 from strategy.models.base import GLOBAL_MIN_RISK_TICKS,GLOBAL_MAX_RISK_TICKS
 from strategy.quality import filter_by_quality
 FE=make_fast_engine(BacktestEngineV2,Trade,GLOBAL_MIN_RISK_TICKS,GLOBAL_MAX_RISK_TICKS)
 # Fast-engine parity against published V16 full-12 causal ledger.
 allres=causal(filt);allfinal=filter_by_quality(allres,df);parity_z=rescore(FE(cfg).run(df,allfinal),bars);ref=led.sort_values('entry_time').reset_index(drop=True);pz=parity_z.sort_values('entry_time').reset_index(drop=True)
 parity=bool(len(ref)==len(pz) and np.all(pd.to_datetime(ref.entry_time).values==pd.to_datetime(pz.entry_time).values) and np.all(ref.model.astype(str).values==pz.model.astype(str).values) and np.all(ref.direction.astype(str).values==pz.direction.astype(str).values) and np.allclose(ref.stress_r.to_numpy(float),pz.stress_r.to_numpy(float),rtol=0,atol=1e-12))
 if not parity:
  (OUT/'RESULT.json').write_text(json.dumps({'status':'V17_FAST_ENGINE_PARITY_FAIL','reference_n':len(ref),'fast_n':len(pz)},indent=2));return
 shortlisted=[];true_seen=set();selected=None;all_true=[]
 for row in ranked[:TRUE_K]:
  fs=row[-2]
  key=tuple(sorted(fs))
  if key in true_seen:continue
  true_seen.add(key);z,dev,rc,diag=true_eval(fs,cfg,gen,df,filt,bars,FE)
  rec={'branches':list(key),'branch_count':len(key),'screen_pace':float(row[0]),'diag':diag,'dev_stats':stats(dev.stress_r),'dev_remove_best10':remove_best10(dev.stress_r),'dev_risk_choice':rc}
  all_true.append(rec)
  if rc is not None:
   if selected is None or (rc['pace'],-rc['stats']['pf'],rc['stats']['max_dd'],len(key),key)<(selected['dev_risk_choice']['pace'],-selected['dev_risk_choice']['stats']['pf'],selected['dev_risk_choice']['stats']['max_dd'],selected['branch_count'],tuple(selected['branches'])):
    selected=rec;selected['_ledger']=z
 if selected is None:
  out={'status':'V17_NO_TRUE_CAUSAL_ADMISSIBLE_SUBSET','fast_engine_parity':parity,'branches':branches,'screened_candidates':len(ranked),'true_reruns':all_true};(OUT/'RESULT.json').write_text(json.dumps(out,indent=2,allow_nan=False,default=str));return
 z=selected.pop('_ledger');risk=float(selected['dev_risk_choice']['risk']);periods={}
 for label,mask,sess in [('DEV',z.entry_time.dt.year.isin(DEV_YEARS),DEV_SESS),('2024',z.entry_time.dt.year==2024,246),('2025',z.entry_time.dt.year==2025,83),('ALL',pd.Series(True,index=z.index),1075)]:
  q=z[mask].copy();s=stats(q.stress_r);wi=worst_intraday_r(q);periods[label]={'n':len(q),'trades_per_session':float(len(q)/sess),'stress':s,'r_per_session':float(s['sum']/sess),'scaled_dd_pct':float(s['max_dd']*risk) if s['max_dd'] is not None else None,'scaled_worst_intraday_pct':float(abs(min(0.,wi))*risk),'implied_step1_days':float(.10/((s['sum']/sess)*risk)) if s['sum']>0 else None,'remove_best10_mean':remove_best10(q.stress_r)}
 z.to_csv(OUT/'SELECTED_TRUE_CAUSAL_TRADES.csv',index=False)
 out={'status':'V17_TRUE_CAUSAL_BRANCH_SUBSET_SELECTED','fast_engine_parity':parity,'atomic_branch_count':len(branches),'screened_candidates':len(ranked),'true_rerun_count':len(all_true),'selected':selected,'periods_descriptive':periods,'top_true_reruns':all_true[:20],'notes':['Selection algorithm uses DEV 2021-2023 only.','2024/2025 are descriptive because already observed in prior diagnostics.','No weekday/session filter was optimized.','FTMO Free Trial forward is required before paid Challenge use.']}
 (OUT/'RESULT.json').write_text(json.dumps(out,indent=2,allow_nan=False,default=str));print(json.dumps({'status':out['status'],'selected':selected,'periods':periods},indent=2,default=str))
if __name__=='__main__':main()
