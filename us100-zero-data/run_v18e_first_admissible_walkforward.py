#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

# Importing V18d installs exact caches into v17 before v18 helpers are used.
import run_v18d_selection_walkforward_cachedsim  # noqa: F401
import run_v17_all24_branch_search as v17
import run_v18_selection_walkforward as v18
import run_native_12model_port_v5 as base

OUT=Path('us100-zero-data/results/v18e_first_admissible_walkforward')
MAX_TRUE_ATTEMPTS=12


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    led=pd.read_csv(v18.V16); led['entry_time']=pd.to_datetime(led.entry_time); led['branch']=led.model+'__'+led.direction
    cfg,gen,df,filt,bars,total_sessions=v17.prepare()
    raw_branches=sorted(set(v17.branch(s) for s in filt))
    sess={}
    for y in base.SOURCE_YEARS:
        d,_=base.load_year(y); sess[y]=len(base.complete_rth_days(d))
    from backtest.engine_v2 import BacktestEngineV2,Trade
    from strategy.models.base import GLOBAL_MIN_RISK_TICKS,GLOBAL_MAX_RISK_TICKS
    FE=v17.make_fast_engine(BacktestEngineV2,Trade,GLOBAL_MIN_RISK_TICKS,GLOBAL_MAX_RISK_TICKS)

    folds={}; selected_sets=[]
    for name,train_years,test_year in v18.FOLDS:
        train_sessions=sum(sess[y] for y in train_years)
        ranked=v18.approx_beam(led,raw_branches,train_years,train_sessions)
        selected=None; attempts=[]; seen=set()
        for row in ranked:
            if len(attempts)>=MAX_TRUE_ATTEMPTS: break
            fs=row[-1]; key=tuple(sorted(fs))
            if key in seen: continue
            seen.add(key)
            z,tr,rc,diag=v18.true_eval(fs,cfg,df,filt,bars,FE,train_years,train_sessions)
            rec={'branches':list(key),'branch_count':len(key),'screen_pace':float(row[0]),'diag':diag,
                 'train_stats':v17.stats(tr.stress_r),'train_remove_best10':v17.remove_best10(tr.stress_r),'risk_choice':rc}
            attempts.append(rec)
            # Frozen first-admissible rule: no comparison among later true reruns.
            if rc is not None:
                selected=(rec,z); break
        if selected is None:
            folds[name]={'status':'NO_ADMISSIBLE_WITHIN_FIRST_ATTEMPTS','train_years':list(train_years),'test_year':test_year,'attempts':attempts}; continue
        rec,z=selected; risk=float(rec['risk_choice']['risk']); test=v18.period_eval(z,test_year,sess[test_year],risk); ss=set(rec['branches']); selected_sets.append(ss)
        folds[name]={'status':'SELECTED_FIRST_ADMISSIBLE','train_years':list(train_years),'train_sessions':train_sessions,'test_year':test_year,
                     'selected':rec,'test':test,'jaccard_vs_v17_final':float(len(ss&v18.V17_FINAL)/len(ss|v18.V17_FINAL)),'attempt_count':len(attempts)}

    pairwise=[]
    for i in range(len(selected_sets)):
        for j in range(i+1,len(selected_sets)):
            a,b=selected_sets[i],selected_sets[j]; pairwise.append(float(len(a&b)/len(a|b)))
    hold=[f.get('test',{}).get('basic_hold') for f in folds.values() if f.get('status')=='SELECTED_FIRST_ADMISSIBLE']
    complete=len(hold)==len(v18.FOLDS)
    out={'status':'V18E_FIRST_ADMISSIBLE_WALKFORWARD_STABLE' if complete and all(hold) else 'V18E_FIRST_ADMISSIBLE_WALKFORWARD_NOT_STABLE',
         'method':'FIRST_TRUE_ADMISSIBLE_IN_APPROX_SCREEN_ORDER','max_true_attempts_per_fold':MAX_TRUE_ATTEMPTS,
         'raw_branch_count':len(raw_branches),'session_counts':sess,'folds':folds,
         'mean_pairwise_jaccard':float(np.mean(pairwise)) if pairwise else None,'pairwise_selected_jaccard':pairwise,
         'all_three_folds_selected':complete,'all_selected_tests_basic_hold':bool(complete and all(hold)),
         'notes':['Each fold sees only its two training years for selection and risk.','The first causally rerun admissible candidate is selected; later candidates are not compared.','This is deliberately less optimized than V18/V17 and is used as an anti-overfitting procedure check.','2025 test ends April 30.']}
    (OUT/'RESULT.json').write_text(json.dumps(out,indent=2,allow_nan=False,default=str))
    print(json.dumps({'status':out['status'],'folds':{k:{'attempt_count':v.get('attempt_count'),'selected':v.get('selected',{}).get('branches'),'risk':v.get('selected',{}).get('risk_choice',{}).get('risk'),'test':v.get('test')} for k,v in folds.items()}},indent=2,default=str))

if __name__=='__main__': main()
