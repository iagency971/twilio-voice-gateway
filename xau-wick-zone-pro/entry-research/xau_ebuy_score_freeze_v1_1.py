#!/usr/bin/env python3
from __future__ import annotations

import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

s=load_module('ebuy_score_v10',HERE/'xau_ebuy_score_dev_v1_0.py')


def args():
    p=argparse.ArgumentParser();p.add_argument('--files',nargs='+',required=True);p.add_argument('--triggers-gz',required=True);p.add_argument('--candidates-gz',required=True);p.add_argument('--v10-result',required=True);p.add_argument('--model-pkl',required=True);p.add_argument('--output',required=True);return p.parse_args()


def main():
    a=args();v10=json.load(open(a.v10_result))
    assert v10['status']=='E_BUY_US_DEV_FAIL'
    m=v10['models']['M1_LOGISTIC']['pooled'];base=float(m['baseline']);folds=v10['models']['M1_LOGISTIC']['folds']
    checks={
      'pooled_auc_ge_060':m['roc_auc']>=.60,
      'pooled_ap_ge_baseline_plus_005':m['average_precision']>=base+.05,
      'E80_n_ge_800':m['E80']['count']>=800,
      'E80_rate_ge_baseline_plus_008':m['E80']['positive_rate']>=base+.08,
      'E90_n_ge_350':m['E90']['count']>=350,
      'E90_rate_ge_baseline_plus_012':m['E90']['positive_rate']>=base+.12,
      'E80_positive_lift_in_at_least_3_of_4_folds':sum(int(x['E80_above_baseline']) for x in folds)>=3,
    }
    assert all(checks.values()),checks

    tr=pd.read_csv(a.triggers_gz,compression='gzip',low_memory=False)
    for c in ['trigger_time','contact_time','exec_time','c5_time']:tr[c]=pd.to_datetime(tr[c],utc=True,errors='coerce')
    bull=tr[(tr.trigger.astype(str)=='BULL_REJECTION')&s.as_bool(tr.fired)].copy();assert len(bull)==7128
    st=bull.tp1_invalidation_status.astype(str);amb=st.str.startswith('AMBIGUOUS')
    d0=bull[~amb&st.isin(['TP1_FIRST','INVALIDATION_FIRST','NEITHER'])].copy();d0['y']=(d0.tp1_invalidation_status.astype(str)=='TP1_FIRST').astype(int);assert len(d0)==7110
    raw=s.v01.load_raw(a.files);assert raw.time.min()>=s.DEV_LO and raw.time.max()<s.DEV_HI
    cand=pd.read_csv(a.candidates_gz,compression='gzip',low_memory=False)
    d=s.enrich(d0,raw,cand);assert len(d)==7110
    pipe=s.make_pipe('M1_LOGISTIC');pipe.fit(d[s.NUMERIC+s.CATEGORICAL],d.y.to_numpy(int));score=pipe.predict_proba(d[s.NUMERIC+s.CATEGORICAL])[:,1]
    artifact={'artifact_status':'E_BUY_US_M1_FROZEN_H1_V1_1','model_id':'M1_LOGISTIC','pipeline':pipe,'numeric_features':s.NUMERIC,'categorical_features':s.CATEGORICAL,
              'train_score_cdf_sorted':np.sort(score),'dev_window':[str(s.DEV_LO),str(s.DEV_HI)],'training_n':len(d),'positive_rate':float(d.y.mean()),
              'label':'TP1_FIRST vs INVALIDATION_FIRST_or_NEITHER; ambiguity excluded','e_mapping':'100 * empirical percentile in frozen H1 training score CDF'}
    joblib.dump(artifact,a.model_pkl,compress=3)
    sha=hashlib.sha256(Path(a.model_pkl).read_bytes()).hexdigest()
    out={'status':'E_BUY_US_M1_FALLBACK_FROZEN_V1_1','reaction_holdout_opened':False,'model_id':'M1_LOGISTIC','v10_m1_gate_checks':checks,
         'training_n':len(d),'training_positive_rate':float(d.y.mean()),'model_sha256':sha,'numeric_features':s.NUMERIC,'categorical_features':s.CATEGORICAL,
         'authorization':'PREREGISTER_H2_VALIDATION_BEFORE_ANY_H2_REACTION_OUTCOME','explicit_nonclaims':['DEV fallback, not independent validation','No H2 outcomes opened','No calibrated probability claim','No live profitability claim']}
    Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

if __name__=='__main__':main()
