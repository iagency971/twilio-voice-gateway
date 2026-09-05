#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path('us100-zero-data'); LEDGER=ROOT/'results/native_12model_port_v5/TRADES_RESCORED.csv'; OUT=ROOT/'results/v12_fastest_ftmo_subset_risk'
EXPECTED_RAW_SHA='c2c705318ff19aee4fb1137b7ec2102e98a848b297701b334e1b777a0d5b7d31'; DEV_YEARS=(2021,2022,2023); SESS={'DEV':746,'2024':246,'2025':83}
RISKS=tuple(round(x/10000,6) for x in range(25,101,5))

def sha256_file(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
def pf(a):
 a=np.asarray(a,float);pos=a[a>0].sum();neg=-a[a<0].sum();return float(pos/neg) if neg>0 else (1e99 if pos>0 else None)
def stats(a):
 a=np.asarray(a,float)
 if not len(a):return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None,'losing_streak':None}
 eq=np.cumsum(a);peaks=np.maximum.accumulate(np.r_[0.,eq])[:-1];dd=np.maximum(peaks-eq,0);neg=a<0;longest=cur=0
 for b in neg:
  if b:cur+=1;longest=max(longest,cur)
  else:cur=0
 return {'n':int(len(a)),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0)),'losing_streak':int(longest)}
def path_chars(vals,dateids):
 vals=np.asarray(vals,float);dateids=np.asarray(dateids)
 if not len(vals):return 0.,0.
 mincum=float(min(0.,np.cumsum(vals).min(initial=0.)));worst=0.;cum=0.;last=None
 for v,did in zip(vals,dateids):
  if last is None or did!=last:cum=0.;last=did
  cum+=float(v);worst=min(worst,cum)
 return float(worst),mincum
def target_path(z,col,risk,target):
 bal=0.;active=days=0
 for _,g in z.sort_values('entry_time').groupby('date',sort=True):
  days+=1;ds=bal
  if len(g):active+=1
  for r in g[col].to_numpy(float):
   bal+=float(r)*risk;dm=bal-ds
   if dm<=-.05+1e-12:return {'status':'FAIL_DAILY','days':days,'final':float(bal)}
   if bal<=-.10+1e-12:return {'status':'FAIL_TOTAL','days':days,'final':float(bal)}
   if bal>=target-1e-12 and active>=4:return {'status':'PASS','days':days,'final':float(bal)}
 return {'status':'NOT_REACHED','days':None,'final':float(bal)}
def valblock(d,year,mods,risk):
 z=d[(d.year==year)&d.model.isin(mods)].copy();sessions=SESS[str(year)];p=stats(z.primary_r.to_numpy());s=stats(z.stress_r.to_numpy());dates=pd.factorize(z.date,sort=True)[0]
 wi,_=path_chars(z.stress_r.to_numpy(float),dates);rpd=s['sum']/sessions;daily=rpd*risk
 return {'year':year,'sessions':sessions,'n':len(z),'trades_per_session':float(len(z)/sessions),'primary':p,'stress':s,'risk_fraction':risk,'risk_dollars_10k':risk*10000,
 'stress_worst_intraday_r':wi,'stress_scaled_dd_pct':s['max_dd']*risk if s['max_dd'] is not None else None,'stress_scaled_worst_intraday_pct':abs(min(0.,wi))*risk,
 'stress_r_per_session':float(rpd),'stress_step1_days_implied':float(.10/daily) if daily>0 else None,'stress_step2_days_implied':float(.05/daily) if daily>0 else None,
 'stress_path_step1':target_path(z,'stress_r',risk,.10),'stress_path_step2':target_path(z,'stress_r',risk,.05)}
def main():
 OUT.mkdir(parents=True,exist_ok=True);d=pd.read_csv(LEDGER);d['entry_time']=pd.to_datetime(d.entry_time,errors='coerce');d['exit_time']=pd.to_datetime(d.exit_time,errors='coerce');d=d.dropna(subset=['entry_time','model','primary_r','stress_r']).copy();d['year']=d.entry_time.dt.year;d['date']=d.entry_time.dt.date;d=d.sort_values(['entry_time','exit_time']).reset_index(drop=True)
 mods=tuple(sorted(d.model.unique().tolist()));
 if len(mods)!=12:raise RuntimeError(f'Expected 12 models, got {len(mods)}')
 dev=d[d.year.isin(DEV_YEARS)].copy();midx={m:i for i,m in enumerate(mods)};bits=np.asarray([1<<midx[m] for m in dev.model],dtype=np.int64);pa=dev.primary_r.to_numpy(float);sa=dev.stress_r.to_numpy(float);ya=dev.year.to_numpy(int);dateids=pd.factorize(dev.date,sort=True)[0]
 pairs=[];quality_count=0
 for mask in range(1,1<<len(mods)):
  sel=(bits&mask)!=0;pvals=pa[sel];svals=sa[sel]
  if len(pvals)<200:continue
  p=stats(pvals);s=stats(svals);posyrs=0;worstyr=1e9
  for y in DEV_YEARS:
   yvals=pvals[ya[sel]==y];sy=stats(yvals)
   if sy['sum']>0:posyrs+=1
   if sy['mean'] is not None:worstyr=min(worstyr,sy['mean'])
  q=(p['mean'] is not None and p['mean']>0 and p['pf'] is not None and p['pf']>=1.15 and s['mean'] is not None and s['mean']>=.05 and s['pf'] is not None and s['pf']>=1.10 and posyrs>=2 and worstyr>=-.10)
  if not q:continue
  quality_count+=1;sv=svals;di=dateids[sel];wi,mincum=path_chars(sv,di);nrm=int(math.ceil(len(pvals)*.10));sp=np.sort(pvals)[::-1];rb=float(sp[nrm:].mean()) if len(sp)>nrm else None;rpd=s['sum']/SESS['DEV'];subset=tuple(mods[i] for i in range(len(mods)) if mask&(1<<i))
  for risk in RISKS:
   scaleddd=s['max_dd']*risk;scaledwi=abs(min(0.,wi))*risk;scaledmin=mincum*risk
   if scaleddd>=.09 or scaledwi>=.045 or scaledmin<=-.10+1e-12:continue
   daily=rpd*risk
   if daily<=0:continue
   pairs.append({'models':subset,'model_count':len(subset),'risk_fraction':risk,'risk_dollars_10k':risk*10000,'primary':p,'stress':s,'positive_years':posyrs,'worst_year_mean':float(worstyr),'remove_best10_mean':rb,'trades_per_session':float(len(pvals)/SESS['DEV']),'stress_r_per_session':float(rpd),'stress_worst_intraday_r':wi,'stress_scaled_dd_pct':float(scaleddd),'stress_scaled_worst_intraday_pct':float(scaledwi),'dev_path':{'breach':False,'final':float(s['sum']*risk),'maxdd':float(scaleddd),'worstday':float(wi*risk),'min_cumulative':float(scaledmin)},'implied_step1_days':float(.10/daily),'implied_step2_days':float(.05/daily)})
 def rank(x):return (x['implied_step1_days'],-x['stress']['pf'],x['risk_fraction'],x['stress']['max_dd'],x['model_count'],','.join(x['models']))
 pairs.sort(key=rank);sel=pairs[0] if pairs else None;res={'status':'V12_NO_ADMISSIBLE_PAIR' if sel is None else 'V12_DEV_SELECTED_VALIDATION_OPENED','implementation_note':'V12.2 NumPy mask acceleration; frozen V12 logic unchanged','ledger_sha256':sha256_file(LEDGER),'expected_raw_sha':EXPECTED_RAW_SHA,'models':mods,'subsets_tested':4095,'quality_eligible_subsets':quality_count,'admissible_subset_risk_pairs':len(pairs),'top_30_pairs':pairs[:30],'selected_dev':sel,'validation':None,'pass':False}
 if sel:
  vm=tuple(sel['models']);risk=float(sel['risk_fraction']);v24=valblock(d,2024,vm,risk);v25=valblock(d,2025,vm,risk);g={'2024_stress_sum_gt_0':v24['stress']['sum']>0,'2024_stress_pf_ge_1_10':v24['stress']['pf'] is not None and v24['stress']['pf']>=1.10,'2025_stress_sum_gt_0':v25['stress']['sum']>0,'2025_stress_pf_ge_1_10':v25['stress']['pf'] is not None and v25['stress']['pf']>=1.10,'2024_dd_lt_9pct':v24['stress_scaled_dd_pct']<.09,'2025_dd_lt_9pct':v25['stress_scaled_dd_pct']<.09,'2024_intraday_lt_4_5pct':v24['stress_scaled_worst_intraday_pct']<.045,'2025_intraday_lt_4_5pct':v25['stress_scaled_worst_intraday_pct']<.045,'2024_step1_pace_le_45':v24['stress_step1_days_implied'] is not None and v24['stress_step1_days_implied']<=45,'2025_step1_pace_le_45':v25['stress_step1_days_implied'] is not None and v25['stress_step1_days_implied']<=45};res['validation']={'2024':v24,'2025':v25,'gates':g};res['pass']=all(g.values());res['status']='V12_PROMISING_FOR_MONTE_CARLO' if res['pass'] else 'V12_VALIDATION_NO_GO'
 (OUT/'RESULT.json').write_text(json.dumps(res,indent=2,allow_nan=False,default=str));rows=[{'models':'+'.join(x['models']),'model_count':x['model_count'],'risk_pct':x['risk_fraction']*100,'risk_dollars_10k':x['risk_dollars_10k'],'n':x['primary']['n'],'tpd':x['trades_per_session'],'stress_mean':x['stress']['mean'],'stress_pf':x['stress']['pf'],'stress_dd':x['stress']['max_dd'],'remove_best10_mean':x['remove_best10_mean'],'step1_days':x['implied_step1_days'],'step2_days':x['implied_step2_days']} for x in pairs[:100]];pd.DataFrame(rows).to_csv(OUT/'TOP_PAIRS.csv',index=False);print(json.dumps({'status':res['status'],'selected_models':None if not sel else sel['models'],'selected_risk_pct':None if not sel else sel['risk_fraction']*100,'dev_step1_days':None if not sel else sel['implied_step1_days'],'validation_pass':res['pass']},indent=2,default=str))
if __name__=='__main__':main()
