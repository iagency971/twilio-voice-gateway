#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

GO_DEV_TOKEN='GO_DEV_OUTCOME_OPENING'
GO_REPLICATION_TOKEN='GO_HISTORICAL_REPLICATION_DIAGNOSTIC'
FEATURES=['zone_width_v','display_persistence_c5','current_family']
SEED=20260829
BOOT_N=5000
MIN_VALID_BOOT=4750
DEV_START=pd.Timestamp('2024-08-01T00:00:00Z')
DEV_END=pd.Timestamp('2025-08-01T00:00:00Z')
REP_START=DEV_END
REP_END=pd.Timestamp('2026-08-01T00:00:00Z')


@dataclass
class FrozenModel:
    width_mean: float
    width_sd: float
    logpers_mean: float
    logpers_sd: float
    categories: list[str]
    reference_category: str
    coef: list[float]
    intercept: float
    dev_scores: np.ndarray
    quartiles: list[float]


def required_rows(d:pd.DataFrame):
    x=d.copy();before=len(x)
    miss=x[FEATURES].isna().any(axis=1)
    badpers=pd.to_numeric(x['display_persistence_c5'],errors='coerce')<1
    miss=miss|badpers
    return x.loc[~miss].copy(),{'input_rows':int(before),'feature_excluded_rows':int(miss.sum()),'feature_exclusion_rate':float(miss.mean()) if before else None}


def design_fit(d:pd.DataFrame):
    x,qa=required_rows(d)
    if not len(x):raise RuntimeError('no complete DEV rows')
    if x['primary_binary_label'].nunique()!=2:raise RuntimeError('DEV labels must contain both classes')
    w=x.zone_width_v.to_numpy(float);lp=np.log1p(x.display_persistence_c5.to_numpy(float))
    wm=float(w.mean());ws=float(w.std(ddof=0));pm=float(lp.mean());ps=float(lp.std(ddof=0))
    if not np.isfinite(ws) or ws<=0 or not np.isfinite(ps) or ps<=0:raise RuntimeError('zero/nonfinite DEV feature SD')
    cats=sorted(x.current_family.astype(str).unique().tolist())
    if len(cats)<1:raise RuntimeError('empty family vocabulary')
    ref=cats[0];cols=[(w-wm)/ws,(lp-pm)/ps]
    for c in cats[1:]:cols.append((x.current_family.astype(str).to_numpy()==c).astype(float))
    X=np.column_stack(cols);y=x.primary_binary_label.to_numpy(int)
    return x,X,y,qa,wm,ws,pm,ps,cats,ref


def fit_dev(d:pd.DataFrame):
    x,X,y,qa,wm,ws,pm,ps,cats,ref=design_fit(d)
    model=LogisticRegression(penalty='l2',C=1.0,solver='lbfgs',max_iter=5000,class_weight=None,fit_intercept=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');model.fit(X,y)
    conv=[str(w.message) for w in caught if issubclass(w.category,ConvergenceWarning)]
    if conv or int(np.max(model.n_iter_))>=5000:raise RuntimeError(f'logistic convergence failure: {conv} n_iter={model.n_iter_.tolist()}')
    scores=model.decision_function(X).astype(float);q=np.quantile(scores,[.25,.50,.75],method='linear').astype(float)
    if not (q[0]<q[1]<q[2]):raise RuntimeError(f'tied quartile cutpoints: {q.tolist()}')
    fm=FrozenModel(wm,ws,pm,ps,cats,ref,model.coef_[0].astype(float).tolist(),float(model.intercept_[0]),scores,q.tolist())
    qa.update({'n_iter':int(model.n_iter_[0]),'categories':cats,'reference_category':ref})
    return fm,x,qa


def transform_score(d:pd.DataFrame,m:FrozenModel):
    x,qa=required_rows(d);fam=x.current_family.astype(str).to_numpy()
    unseen=~np.isin(fam,np.array(m.categories,dtype=object));qa['unseen_family_rows']=int(unseen.sum());qa['unseen_family_rate']=float(unseen.mean()) if len(x) else None
    w=x.zone_width_v.to_numpy(float);lp=np.log1p(x.display_persistence_c5.to_numpy(float));cols=[(w-m.width_mean)/m.width_sd,(lp-m.logpers_mean)/m.logpers_sd]
    for c in m.categories[1:]:cols.append((fam==c).astype(float))
    X=np.column_stack(cols);beta=np.asarray(m.coef,float);scores=m.intercept+X.dot(beta)
    x=x.copy();x['continuous_logit']=scores
    dev=np.sort(np.asarray(m.dev_scores,float));left=np.searchsorted(dev,scores,side='left');right=np.searchsorted(dev,scores,side='right')
    x['E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1']=(left+.5*(right-left))/len(dev)
    q1,q2,q3=m.quartiles;x['fixed_quartile']=np.where(scores<=q1,'Q1',np.where(scores<=q2,'Q2',np.where(scores<=q3,'Q3','Q4')))
    return x,qa


def auc_assoc(d):
    if len(d)==0 or d.primary_binary_label.nunique()!=2:return None
    return float(roc_auc_score(d.primary_binary_label.to_numpy(int),d.continuous_logit.to_numpy(float))-.5)


def quartile_rates(d):
    out={}
    for q in ['Q1','Q2','Q3','Q4']:
        g=d[d.fixed_quartile==q];out[q]={'n':int(len(g)),'success_rate':float(g.primary_binary_label.mean()) if len(g) else None}
    return out


def q4_q1(d):
    a=d[d.fixed_quartile=='Q1'];b=d[d.fixed_quartile=='Q4']
    if not len(a) or not len(b):return None
    return float(b.primary_binary_label.mean()-a.primary_binary_label.mean())


def bootstrap(d,metric,n=BOOT_N,seed=SEED):
    sessions=np.array(sorted(d.session_date_ny.astype(str).unique()));groups={s:d[d.session_date_ny.astype(str)==s] for s in sessions}
    rng=np.random.default_rng(seed);vals=[];invalid=0
    for _ in range(n):
        picks=rng.choice(sessions,size=len(sessions),replace=True);samp=pd.concat([groups[s] for s in picks],ignore_index=True);v=metric(samp)
        if v is None or not np.isfinite(v):invalid+=1;continue
        vals.append(float(v))
    ok=len(vals)>=MIN_VALID_BOOT;ci=[float(np.quantile(vals,.025)),float(np.quantile(vals,.975))] if ok else [None,None]
    return {'requested':n,'valid':len(vals),'invalid':invalid,'minimum_valid_required':MIN_VALID_BOOT,'ci95_percentile':ci,'ci_available':ok}


def evaluation(d):
    return {'n':int(len(d)),'sessions':int(d.session_date_ny.nunique()),'auc_minus_0_5':auc_assoc(d),'auc_cluster_bootstrap':bootstrap(d,auc_assoc),'fixed_quartiles':quartile_rates(d),'q4_minus_q1':q4_q1(d),'q4_minus_q1_cluster_bootstrap':bootstrap(d,q4_q1,seed=SEED)}


def prospective_blocks(d):
    ss=sorted(d.session_date_ny.astype(str).unique());parts=np.array_split(np.array(ss,dtype=object),3);out=[]
    for i,p in enumerate(parts,1):
        g=d[d.session_date_ny.astype(str).isin(p.tolist())];out.append({'block':i,'sessions':p.tolist(),'session_n':len(p),'episode_n':int(len(g)),'q4_minus_q1':q4_q1(g)})
    return out


def prospective_gate(d,qa,ev):
    rates=[ev['fixed_quartiles'][q]['success_rate'] for q in ['Q1','Q2','Q3','Q4']];blocks=prospective_blocks(d)
    checks={'threshold_episodes_ge_1000':len(d)>=1000,'threshold_sessions_ge_90':d.session_date_ny.nunique()>=90,'auc_positive':ev['auc_minus_0_5'] is not None and ev['auc_minus_0_5']>0,'auc_ci_lower_gt_0':ev['auc_cluster_bootstrap']['ci_available'] and ev['auc_cluster_bootstrap']['ci95_percentile'][0]>0,'quartiles_all_nonempty':all(x is not None for x in rates),'quartiles_monotone':all(x is not None for x in rates) and rates[0]<=rates[1]<=rates[2]<=rates[3],'q4_q1_positive':ev['q4_minus_q1'] is not None and ev['q4_minus_q1']>0,'q4_q1_ci_lower_gt_0':ev['q4_minus_q1_cluster_bootstrap']['ci_available'] and ev['q4_minus_q1_cluster_bootstrap']['ci95_percentile'][0]>0,'q4_q1_positive_all_3_blocks':all(b['q4_minus_q1'] is not None and b['q4_minus_q1']>0 for b in blocks),'feature_exclusion_le_2pct':qa['feature_exclusion_rate'] is not None and qa['feature_exclusion_rate']<=.02,'unseen_family_le_5pct':qa['unseen_family_rate'] is not None and qa['unseen_family_rate']<=.05}
    return {'checks':checks,'blocks':blocks,'pass':all(checks.values())}


def model_json(m:FrozenModel):
    return {'status':'E_DISPLAY_EPISODE_DEV_MODEL_V1_FROZEN','feature_order':['zone_width_v_z','log1p_display_persistence_c5_z']+[f'family__{c}' for c in m.categories[1:]],'width_mean':m.width_mean,'width_sd_ddof0':m.width_sd,'logpers_mean':m.logpers_mean,'logpers_sd_ddof0':m.logpers_sd,'categories':m.categories,'reference_category':m.reference_category,'coef':m.coef,'intercept':m.intercept,'quartile_cutpoints_linear':m.quartiles,'dev_score_distribution':m.dev_scores.astype(float).tolist(),'rank_definition':'midrank empirical CDF: (count< + 0.5*count==)/N','replication_outcomes_used_to_fit':False}


def load_model(path:str)->FrozenModel:
    d=json.load(open(path));required={'width_mean','width_sd_ddof0','logpers_mean','logpers_sd_ddof0','categories','reference_category','coef','intercept','dev_score_distribution','quartile_cutpoints_linear'}
    miss=sorted(required-set(d));
    if miss:raise RuntimeError(f'frozen model missing fields {miss}')
    return FrozenModel(float(d['width_mean']),float(d['width_sd_ddof0']),float(d['logpers_mean']),float(d['logpers_sd_ddof0']),list(d['categories']),str(d['reference_category']),[float(x) for x in d['coef']],float(d['intercept']),np.asarray(d['dev_score_distribution'],float),[float(x) for x in d['quartile_cutpoints_linear']])


def environment():return {'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'scikit_learn':sklearn.__version__}


def primary_contacts(path:str):
    d=pd.read_csv(path,compression='infer');return d[d.selection_status=='PRIMARY_CONTACT'].copy()


def assert_contact_window(d:pd.DataFrame,start:pd.Timestamp,end:pd.Timestamp,name:str):
    if not len(d):raise RuntimeError(f'{name}: no PRIMARY_CONTACT rows')
    if 'contact_bar_open_time_utc' not in d:raise RuntimeError(f'{name}: contact_bar_open_time_utc missing')
    t=pd.to_datetime(d.contact_bar_open_time_utc,utc=True,errors='coerce')
    if t.isna().any() or not bool(((t>=start)&(t<end)).all()):raise RuntimeError(f'{name}: contact time outside declared window')


def run_dev_fit(labels:str,model_path:str,report_path:str,token:str):
    if token!=GO_DEV_TOKEN:raise RuntimeError('DEV_MODELING_BLOCKED: GO_DEV_OUTCOME_OPENING token required')
    dev=primary_contacts(labels);assert_contact_window(dev,DEV_START,DEV_END,'DEV')
    m,devfit,fitqa=fit_dev(dev);devsc,devqa=transform_score(devfit,m)
    report={'status':'E_DISPLAY_EPISODE_MODEL_V1_FROZEN_AFTER_DEV','environment':environment(),'fit_qa':fitqa,'dev_transform_qa':devqa,'dev_evaluation':evaluation(devsc),'historical_replication_outcomes_read':False,'historical_replication_outcomes_scored':False,'next_authorization':'FREEZE_DEV_MODEL_BEFORE_HISTORICAL_REPLICATION'}
    Path(model_path).write_text(json.dumps(model_json(m),indent=2,sort_keys=True)+'\n');Path(report_path).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return report


def run_replication(labels:str,model_path:str,report_path:str,token:str):
    if token!=GO_REPLICATION_TOKEN:raise RuntimeError('HISTORICAL_REPLICATION_BLOCKED: GO_HISTORICAL_REPLICATION_DIAGNOSTIC token required')
    rep=primary_contacts(labels);assert_contact_window(rep,REP_START,REP_END,'HISTORICAL_REPLICATION_DIAGNOSTIC')
    m=load_model(model_path);repsc,repqa=transform_score(rep,m)
    report={'status':'E_DISPLAY_EPISODE_HISTORICAL_REPLICATION_DIAGNOSTIC_COMPLETE','environment':environment(),'frozen_dev_model_status':'LOADED_NO_REFIT','replication_transform_qa':repqa,'historical_replication_diagnostic':evaluation(repsc),'production_authorization':'NONE_HISTORICAL_REPLICATION_CANNOT_AUTHORIZE'}
    Path(report_path).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');return report


def parse_args():
    p=argparse.ArgumentParser();p.add_argument('--phase',required=True,choices=['DEV_FIT','HISTORICAL_REPLICATION_DIAGNOSTIC']);p.add_argument('--labels',required=True);p.add_argument('--model-json',required=True);p.add_argument('--report-json',required=True);p.add_argument('--authorization-token',default='');return p.parse_args()


def main():
    a=parse_args()
    if a.phase=='DEV_FIT':r=run_dev_fit(a.labels,a.model_json,a.report_json,a.authorization_token)
    else:r=run_replication(a.labels,a.model_json,a.report_json,a.authorization_token)
    print(json.dumps({k:v for k,v in r.items() if k not in ['dev_evaluation','historical_replication_diagnostic']},indent=2,sort_keys=True))

if __name__=='__main__':main()
