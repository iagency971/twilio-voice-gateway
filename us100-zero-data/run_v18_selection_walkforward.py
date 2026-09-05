#!/usr/bin/env python3
from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd

import run_v17_all24_branch_search as v17
import run_native_12model_port_v5 as base

OUT=Path('us100-zero-data/results/v18_selection_walkforward')
V16=Path('us100-zero-data/results/v16_all12_causal_segmentation/ALL12_CAUSAL_TRADES.csv')
RISK_GRID=v17.RISK_GRID
BEAM=45
TRUE_K=24
FOLDS=(
    ('WF_2021_22_TO_2023',(2021,2022),2023),
    ('WF_2022_23_TO_2024',(2022,2023),2024),
    ('WF_2023_24_TO_2025',(2023,2024),2025),
)
V17_FINAL={
'ema_rev__long','kalman_mom__long','kalman_mom__short','open_drive__long',
'ou_lunch__long','ou_lunch__short','ou_rev__long','pd_rev__long','pm_mom__long',
'pm_mom__short','sweep__short','trend__long','vwap_rev__short','vwap_scalp__long'}

def risk_choice(z, train_years, train_sessions, strict=True):
    s=v17.stats(z.stress_r); wi=v17.worst_intraday_r(z); mc=v17.min_cumulative_r(z)
    yrs={int(y):float(z[z.entry_time.dt.year==y].stress_r.sum()) for y in train_years}
    if s['n']==0 or s['sum']<=0:return None
    min_n=max(150,int(math.ceil(train_sessions*0.40)))
    for r in reversed(RISK_GRID):
        if s['max_dd']*r>=.085 or abs(min(0.,wi))*r>=.04 or mc*r<=-.10:continue
        if strict:
            if s['n']<min_n or s['pf'] is None or s['pf']<1.25 or not all(v>0 for v in yrs.values()):continue
        else:
            if s['n']<max(100,int(math.ceil(train_sessions*0.25))) or s['pf'] is None or s['pf']<1.10 or sum(v>0 for v in yrs.values())<max(1,len(train_years)-1):continue
        rps=s['sum']/train_sessions
        return {'risk':float(r),'pace':float(.10/(rps*r)),'stats':s,'worst_intraday_r':wi,'min_cumulative_r':mc,'years':yrs,'r_per_session':float(rps),'min_n_required':min_n}
    return None

def approx_beam(ledger, branches, years, sessions):
    train=ledger[ledger.entry_time.dt.year.isin(years)].copy(); cache={}; pool=set()
    def ev(fs):
        key=tuple(sorted(fs))
        if key not in cache:
            cache[key]=risk_choice(train[train.branch.isin(key)],years,sessions,strict=False)
        return cache[key]
    full=frozenset(branches); beam=[full]; pool.add(full)
    for _ in range(max(0,len(branches)-4)):
        cand=set()
        for fs in beam:
            for b in fs:
                nf=frozenset(x for x in fs if x!=b)
                if len(nf)>=4:cand.add(nf)
        scored=[]
        for fs in cand:
            r=ev(fs)
            if r:scored.append((r['pace'],-r['stats']['pf'],r['stats']['max_dd'],len(fs),tuple(sorted(fs)),fs))
        scored.sort(); beam=[x[-1] for x in scored[:BEAM]]; pool.update(beam)
        if not beam:break
    # Prefix seeds from atomic train expectancy, including branches absent from executed baseline.
    atomic=[]
    for b in branches:
        z=train[train.branch==b]; s=v17.stats(z.stress_r)
        atomic.append((-(s['mean'] if s['mean'] is not None else -999.),-s['sum'],b))
    atomic.sort(); ordered=[x[2] for x in atomic]
    for k in range(4,len(ordered)+1):pool.add(frozenset(ordered[:k]))
    ranked=[]
    for fs in pool:
        r=ev(fs)
        if r:ranked.append((r['pace'],-r['stats']['pf'],r['stats']['max_dd'],len(fs),tuple(sorted(fs)),fs))
    ranked.sort(); return ranked

def true_eval(fs,cfg,df,filt,bars,FE,years,sessions):
    from strategy.quality import filter_by_quality
    sig=[s for s in filt if v17.branch(s) in fs]
    resolved=v17.causal(sig); final=filter_by_quality(resolved,df)
    z=v17.rescore(FE(cfg).run(df,final),bars)
    tr=z[z.entry_time.dt.year.isin(years)].copy()
    rc=risk_choice(tr,years,sessions,strict=True)
    return z,tr,rc,{'preconflict':len(sig),'postconflict':len(resolved),'postquality':len(final)}

def period_eval(z,year,sessions,risk):
    q=z[z.entry_time.dt.year==year].copy(); s=v17.stats(q.stress_r); wi=v17.worst_intraday_r(q)
    rps=s['sum']/sessions if sessions else 0.; pace=.10/(rps*risk) if rps>0 else None
    return {'year':year,'sessions':sessions,'n':len(q),'trades_per_session':float(len(q)/sessions) if sessions else None,'stress':s,'r_per_session':float(rps),'risk':risk,'scaled_dd_pct':None if s['max_dd'] is None else float(s['max_dd']*risk),'scaled_worst_intraday_pct':float(abs(min(0.,wi))*risk),'implied_step1_days':None if pace is None else float(pace),'remove_best10_mean':v17.remove_best10(q.stress_r),'basic_hold':bool(s['sum']>0 and s['pf'] is not None and s['pf']>=1.10 and s['max_dd']*risk<.09 and abs(min(0.,wi))*risk<.045)}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    led=pd.read_csv(V16); led['entry_time']=pd.to_datetime(led.entry_time); led['branch']=led.model+'__'+led.direction
    cfg,gen,df,filt,bars,total_sessions=v17.prepare()
    raw_branches=sorted(set(v17.branch(s) for s in filt))
    executed_branches=sorted(led.branch.unique().tolist())
    # Session counts from exact source QA.
    sess={}
    for y in base.SOURCE_YEARS:
        d,_=base.load_year(y); sess[y]=len(base.complete_rth_days(d))
    from backtest.engine_v2 import BacktestEngineV2,Trade
    from strategy.models.base import GLOBAL_MIN_RISK_TICKS,GLOBAL_MAX_RISK_TICKS
    FE=v17.make_fast_engine(BacktestEngineV2,Trade,GLOBAL_MIN_RISK_TICKS,GLOBAL_MAX_RISK_TICKS)
    folds={}; selected_sets=[]
    for name,train_years,test_year in FOLDS:
        train_sessions=sum(sess[y] for y in train_years); ranked=approx_beam(led,raw_branches,train_years,train_sessions)
        best=None; true=[]; seen=set()
        for row in ranked[:TRUE_K]:
            fs=row[-1]; key=tuple(sorted(fs))
            if key in seen:continue
            seen.add(key); z,tr,rc,diag=true_eval(fs,cfg,df,filt,bars,FE,train_years,train_sessions)
            rec={'branches':list(key),'branch_count':len(key),'screen_pace':float(row[0]),'diag':diag,'train_stats':v17.stats(tr.stress_r),'train_remove_best10':v17.remove_best10(tr.stress_r),'risk_choice':rc}
            true.append(rec)
            if rc is not None:
                rank=(rc['pace'],-rc['stats']['pf'],rc['stats']['max_dd'],len(key),key)
                if best is None or rank<best['_rank']:
                    best={'_rank':rank,'rec':rec,'ledger':z}
        if best is None:
            folds[name]={'status':'NO_ADMISSIBLE_TRUE_SUBSET','train_years':list(train_years),'test_year':test_year,'top_true':true};continue
        rec=best['rec']; risk=float(rec['risk_choice']['risk']); test=period_eval(best['ledger'],test_year,sess[test_year],risk); ss=set(rec['branches']); selected_sets.append(ss)
        folds[name]={'status':'SELECTED','train_years':list(train_years),'train_sessions':train_sessions,'test_year':test_year,'selected':rec,'test':test,'jaccard_vs_v17_final':float(len(ss&V17_FINAL)/len(ss|V17_FINAL)),'top_true':true[:10]}
    # Selection stability across folds.
    pairwise=[]
    for i in range(len(selected_sets)):
        for j in range(i+1,len(selected_sets)):
            a,b=selected_sets[i],selected_sets[j]; pairwise.append(float(len(a&b)/len(a|b)))
    branch_freq={b:sum(b in s for s in selected_sets) for b in raw_branches}
    hold=[f.get('test',{}).get('basic_hold') for f in folds.values() if f.get('status')=='SELECTED']
    out={'status':'V18_WALKFORWARD_SELECTION_STABLE' if hold and all(hold) else 'V18_WALKFORWARD_SELECTION_NOT_STABLE','raw_branch_count':len(raw_branches),'raw_branches':raw_branches,'executed_baseline_branch_count':len(executed_branches),'executed_baseline_branches':executed_branches,'session_counts':sess,'folds':folds,'pairwise_selected_jaccard':pairwise,'mean_pairwise_jaccard':float(np.mean(pairwise)) if pairwise else None,'branch_selection_frequency':branch_freq,'all_selected_tests_basic_hold':bool(hold and all(hold)),'notes':['Each fold selects only on its two training years; next year is untouched by that fold selection.','Candidate subsets are re-run causally before ranking, not merely filtered from the old ledger.','2025 source ends April 30, so the final fold test is partial-year.']}
    (OUT/'RESULT.json').write_text(json.dumps(out,indent=2,allow_nan=False,default=str))
    print(json.dumps({'status':out['status'],'raw_branch_count':len(raw_branches),'mean_pairwise_jaccard':out['mean_pairwise_jaccard'],'folds':{k:{'selected':v.get('selected',{}).get('branches'),'risk':v.get('selected',{}).get('risk_choice',{}).get('risk'),'test':v.get('test')} for k,v in folds.items()}},indent=2,default=str))
if __name__=='__main__':main()
