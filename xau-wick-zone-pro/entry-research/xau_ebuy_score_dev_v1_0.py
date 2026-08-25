#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

HERE=Path(__file__).resolve().parent

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod

v01=load_module('score_v01',HERE/'xau_ebuy_coverage_v0_1.py')

DEV_LO=pd.Timestamp('2024-08-01T00:00:00Z')
DEV_HI=pd.Timestamp('2025-08-01T00:00:00Z')

NUMERIC=[
 'slot_rank','episode_age_c5','zone_width_v','arm_center_distance_v','tp_distance_v','minutes_to_us_end','v_contact',
 'trend5_v','trend15_v','trend60_v','trend240_v','contact_penetration_width','contact_bull','contact_close_position',
 'upper_z4_count','minutes_contact_to_trigger','trigger_body_v','trigger_range_v','trigger_lower_wick_v','trigger_upper_wick_v',
 'trigger_close_position','trigger_close_minus_zhi_v','trigger_close_minus_center_v','exec_gap_v','max_penetration_to_trigger_width'
]
CATEGORICAL=['family','episode_origin_family','us_subperiod']

FOLDS=[
 ('F1',pd.Timestamp('2024-12-01T00:00:00Z'),pd.Timestamp('2025-02-01T00:00:00Z')),
 ('F2',pd.Timestamp('2025-02-01T00:00:00Z'),pd.Timestamp('2025-04-01T00:00:00Z')),
 ('F3',pd.Timestamp('2025-04-01T00:00:00Z'),pd.Timestamp('2025-06-01T00:00:00Z')),
 ('F4',pd.Timestamp('2025-06-01T00:00:00Z'),pd.Timestamp('2025-08-01T00:00:00Z')),
]


def args():
    p=argparse.ArgumentParser()
    p.add_argument('--files',nargs='+',required=True)
    p.add_argument('--triggers-gz',required=True)
    p.add_argument('--candidates-gz',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--oof-csv',required=True)
    p.add_argument('--model-pkl',required=True)
    return p.parse_args()


def as_bool(s):
    if pd.api.types.is_bool_dtype(s):return s.fillna(False)
    return s.astype(str).str.lower().isin({'true','1','yes'})


def raw_pos(arr,t):
    q=np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None))
    i=int(np.searchsorted(arr,q,side='left'))
    if i>=len(arr) or arr[i]!=q:raise RuntimeError(f'raw timestamp not found: {t}')
    return i


def enrich(tr,raw,candidates):
    cand=candidates[candidates['window'].astype(str)=='OOS_H1'].copy() if 'window' in candidates.columns else candidates.copy()
    cand['time']=pd.to_datetime(cand.time,utc=True)
    upper=cand.groupby('time',sort=False)['upper_z4_count'].first().to_dict()
    arr=raw.time.to_numpy(dtype='datetime64[ns]')
    rows=[]
    for _,r in tr.iterrows():
        tt=pd.Timestamp(r.trigger_time);ct=pd.Timestamp(r.contact_time);et=pd.Timestamp(r.exec_time)
        ti=raw_pos(arr,tt);ci=raw_pos(arr,ct);ei=raw_pos(arr,et)
        rr=raw.iloc[ti];v=float(r.v_contact);width=max(float(r.zhi)-float(r.zlo),1e-12)
        o,h,l,c=map(float,[rr.open,rr.high,rr.low,rr.close]);rng=h-l
        lo=float(raw.low.iloc[min(ci,ti):max(ci,ti)+1].min())
        c5=pd.Timestamp(r.c5_time)
        if c5 not in upper:raise RuntimeError(f'missing frozen H1 candidate state for {c5}')
        x=r.to_dict()
        x.update({
          'upper_z4_count':float(upper[c5]),
          'minutes_contact_to_trigger':float((tt-ct).total_seconds()/60.0),
          'trigger_body_v':float((c-o)/v),
          'trigger_range_v':float(rng/v),
          'trigger_lower_wick_v':float((min(o,c)-l)/v),
          'trigger_upper_wick_v':float((h-max(o,c))/v),
          'trigger_close_position':float((c-l)/rng) if rng>0 else 0.0,
          'trigger_close_minus_zhi_v':float((c-float(r.zhi))/v),
          'trigger_close_minus_center_v':float((c-float(r.center))/v),
          'exec_gap_v':float((float(r.exec_price)-c)/v),
          'max_penetration_to_trigger_width':float((float(r.zhi)-lo)/width),
          'observation_time':et,
        })
        rows.append(x)
    d=pd.DataFrame(rows)
    for c in NUMERIC:d[c]=pd.to_numeric(d[c],errors='coerce')
    for c in CATEGORICAL:d[c]=d[c].astype(str).fillna('NA')
    return d


def make_pipe(model_id):
    if model_id=='M1_LOGISTIC':
        num=Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())])
        cat=Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('ohe',OneHotEncoder(handle_unknown='ignore',sparse_output=False))])
        pre=ColumnTransformer([('num',num,NUMERIC),('cat',cat,CATEGORICAL)],sparse_threshold=0.0)
        clf=LogisticRegression(penalty='l2',C=1.0,max_iter=2000,solver='lbfgs')
    elif model_id=='M2_HGB':
        num=Pipeline([('impute',SimpleImputer(strategy='median'))])
        cat=Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('ohe',OneHotEncoder(handle_unknown='ignore',sparse_output=False))])
        pre=ColumnTransformer([('num',num,NUMERIC),('cat',cat,CATEGORICAL)],sparse_threshold=0.0)
        clf=HistGradientBoostingClassifier(learning_rate=.05,max_iter=200,max_depth=3,min_samples_leaf=50,l2_regularization=1.0,random_state=20260825)
    else:raise ValueError(model_id)
    return Pipeline([('pre',pre),('clf',clf)])


def e_percentile(train_scores,test_scores):
    a=np.sort(np.asarray(train_scores,float));b=np.asarray(test_scores,float)
    return 100.0*np.searchsorted(a,b,side='right')/max(len(a),1)


def band_stats(y,e,cut):
    m=e>=cut;n=int(m.sum())
    return {'count':n,'positive_rate':float(np.mean(y[m])) if n else None}


def fp_band(vals,e,cut):
    m=e>=cut;s=pd.Series(np.asarray(vals,dtype=object)[m]).value_counts().to_dict()
    fav=int(s.get('FAVORABLE_FIRST',0));adv=int(s.get('ADVERSE_FIRST',0));amb=int(s.get('AMBIGUOUS',0))+int(s.get('AMBIGUOUS_CONTACT_BAR',0));nei=int(s.get('NEITHER',0))
    return {'favorable':fav,'adverse':adv,'ambiguous':amb,'neither':nei,'favorable_vs_adverse_rate':float(fav/(fav+adv)) if fav+adv else None}


def evaluate_model(d,model_id):
    fold_results=[];oof=[]
    for name,test_lo,test_hi in FOLDS:
        train=d[(d.observation_time>=DEV_LO)&(d.observation_time<test_lo)].copy()
        test=d[(d.observation_time>=test_lo)&(d.observation_time<test_hi)].copy()
        if len(train)<500 or len(test)<100:raise RuntimeError((name,len(train),len(test)))
        ytr=train.y.to_numpy(int);yte=test.y.to_numpy(int)
        if len(np.unique(ytr))<2 or len(np.unique(yte))<2:raise RuntimeError(f'single class {name}')
        pipe=make_pipe(model_id);pipe.fit(train[NUMERIC+CATEGORICAL],ytr)
        ptr=pipe.predict_proba(train[NUMERIC+CATEGORICAL])[:,1];pte=pipe.predict_proba(test[NUMERIC+CATEGORICAL])[:,1]
        e=e_percentile(ptr,pte)
        baseline=float(yte.mean());auc=float(roc_auc_score(yte,pte));ap=float(average_precision_score(yte,pte));brier=float(brier_score_loss(yte,pte))
        b80=band_stats(yte,e,80);b90=band_stats(yte,e,90)
        fr={'fold':name,'train_n':len(train),'test_n':len(test),'baseline':baseline,'roc_auc':auc,'average_precision':ap,'brier':brier,'E80':b80,'E90':b90,'E80_above_baseline':bool(b80['positive_rate'] is not None and b80['positive_rate']>baseline)}
        fold_results.append(fr)
        for j,(_,r) in enumerate(test.iterrows()):
            oof.append({'model':model_id,'fold':name,'observation_time':r.observation_time,'episode_id':r.episode_id,'y':int(yte[j]),'score':float(pte[j]),'E_BUY_US':float(e[j]),'fp1_status':r['FP_1.00v_vs_0.50v']})
    od=pd.DataFrame(oof);y=od.y.to_numpy(int);p=od.score.to_numpy(float);e=od.E_BUY_US.to_numpy(float)
    pooled={'n':len(od),'baseline':float(y.mean()),'roc_auc':float(roc_auc_score(y,p)),'average_precision':float(average_precision_score(y,p)),'brier':float(brier_score_loss(y,p)),
            'E80':band_stats(y,e,80),'E90':band_stats(y,e,90),
            'fp1_all':fp_band(od.fp1_status,e,0),'fp1_E80':fp_band(od.fp1_status,e,80),'fp1_E90':fp_band(od.fp1_status,e,90)}
    return fold_results,pooled,od


def main():
    a=args()
    tr=pd.read_csv(a.triggers_gz,compression='gzip',low_memory=False)
    tr['trigger_time']=pd.to_datetime(tr.trigger_time,utc=True,errors='coerce');tr['contact_time']=pd.to_datetime(tr.contact_time,utc=True,errors='coerce');tr['exec_time']=pd.to_datetime(tr.exec_time,utc=True,errors='coerce');tr['c5_time']=pd.to_datetime(tr.c5_time,utc=True,errors='coerce')
    bull=tr[(tr.trigger.astype(str)=='BULL_REJECTION')&as_bool(tr.fired)].copy()
    assert len(bull)==7128,len(bull)
    assert bull.exec_time.max()<DEV_HI
    status=bull.tp1_invalidation_status.astype(str)
    ambiguous=status.str.startswith('AMBIGUOUS')
    resolved=bull[~ambiguous & status.isin(['TP1_FIRST','INVALIDATION_FIRST','NEITHER'])].copy()
    resolved['y']=(resolved.tp1_invalidation_status.astype(str)=='TP1_FIRST').astype(int)
    assert len(resolved)==7110,(len(resolved),int(ambiguous.sum()))

    raw=v01.load_raw(a.files)
    assert raw.time.min()>=DEV_LO and raw.time.max()<DEV_HI
    cand=pd.read_csv(a.candidates_gz,compression='gzip',low_memory=False)
    d=enrich(resolved,raw,cand)
    assert len(d)==7110 and d.observation_time.max()<DEV_HI

    models={};oofs=[]
    for mid in ('M1_LOGISTIC','M2_HGB'):
        folds,pooled,od=evaluate_model(d,mid);models[mid]={'folds':folds,'pooled':pooled,'mean_fold_ap':float(np.mean([x['average_precision'] for x in folds]))};oofs.append(od)
        print(mid,models[mid]['mean_fold_ap'],pooled,flush=True)

    order={'M1_LOGISTIC':0,'M2_HGB':1}
    selected=sorted(models,key=lambda m:(-models[m]['mean_fold_ap'],-models[m]['pooled']['roc_auc'],models[m]['pooled']['brier'],order[m]))[0]
    s=models[selected];p=s['pooled'];base=float(p['baseline']);fold_pos=sum(int(x['E80_above_baseline']) for x in s['folds'])
    checks={
      'pooled_auc_ge_060':p['roc_auc']>=.60,
      'pooled_ap_ge_baseline_plus_005':p['average_precision']>=base+.05,
      'E80_n_ge_800':p['E80']['count']>=800,
      'E80_rate_ge_baseline_plus_008':p['E80']['positive_rate'] is not None and p['E80']['positive_rate']>=base+.08,
      'E90_n_ge_350':p['E90']['count']>=350,
      'E90_rate_ge_baseline_plus_012':p['E90']['positive_rate'] is not None and p['E90']['positive_rate']>=base+.12,
      'E80_positive_lift_in_at_least_3_of_4_folds':fold_pos>=3,
    }
    passed=all(checks.values());status_out='E_BUY_US_DEV_PASS' if passed else 'E_BUY_US_DEV_FAIL'

    all_oof=pd.concat(oofs,ignore_index=True);all_oof.to_csv(a.oof_csv,index=False)
    model_meta=None
    if passed:
        pipe=make_pipe(selected);pipe.fit(d[NUMERIC+CATEGORICAL],d.y.to_numpy(int));train_scores=pipe.predict_proba(d[NUMERIC+CATEGORICAL])[:,1]
        artifact={'model_id':selected,'pipeline':pipe,'numeric_features':NUMERIC,'categorical_features':CATEGORICAL,'train_score_cdf_sorted':np.sort(train_scores),'dev_window':[str(DEV_LO),str(DEV_HI)],'label':'TP1_FIRST vs INVALIDATION_FIRST_or_NEITHER','e_mapping':'empirical percentile of H1 training scores'}
        joblib.dump(artifact,a.model_pkl,compress=3)
        model_meta={'path':str(a.model_pkl),'sha256':hashlib.sha256(Path(a.model_pkl).read_bytes()).hexdigest(),'training_n':len(d),'positive_rate':float(d.y.mean())}

    out={'status':status_out,'scope':'BUY_ONLY_E_BUY_US_SCORE_DEV_H1','reaction_holdout_opened':False,'bull_rejection_fired_total':len(bull),'ambiguous_excluded':int(ambiguous.sum()),'model_dataset_n':len(d),'feature_schema':{'numeric':NUMERIC,'categorical':CATEGORICAL},
         'models':models,'selected_model':selected,'selected_checks':checks,'selected_fold_E80_lift_count':fold_pos,'final_model_artifact':model_meta,
         'authorization':('FREEZE_E_BUY_US_AND_PREREGISTER_H2_VALIDATION' if passed else 'KEEP_H2_CLOSED_NO_PRODUCTION_SCORE'),
         'explicit_nonclaims':['No H2 reaction result opened','E_BUY_US is a rank not calibrated probability','No live profitability claim','No R_US route claim']}
    Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps({'status':status_out,'selected_model':selected,'checks':checks,'authorization':out['authorization']},indent=2),flush=True)

if __name__=='__main__':main()
