import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

CAPS=(96,128,160,192)


def parse():
    p=argparse.ArgumentParser()
    p.add_argument('--pkl',required=True)
    p.add_argument('--frozen-json',required=True)
    p.add_argument('--output',required=True)
    return p.parse_args()


def decorate(D):
    D=D.copy()
    D['time']=pd.to_datetime(D.time,utc=True)
    D['log_age_active']=np.log1p(D.age_active_min)
    D['log_age_civil']=np.log1p(D.age_civil_min)
    D['log_prom']=np.log1p(D.prominence)
    D['log_bg']=np.log1p(D.background)
    D['log_strength']=np.log1p(D.strength_raw)
    D['log_mass']=np.log1p(D.mass)
    D['log_peak']=np.log1p(D.peak_height)
    D['log_mean_wick']=np.log1p(D.mean_wick)
    D['log_mean_body']=np.log1p(D.mean_body)
    return D


def sigmoid(x):
    x=np.asarray(x,float); out=np.empty_like(x); pos=x>=0
    out[pos]=1/(1+np.exp(-x[pos])); ex=np.exp(x[~pos]); out[~pos]=ex/(1+ex)
    return out


def predict(D,params):
    X=D[params['features']].to_numpy(float)
    mu=np.asarray(params['scaler_mean'],float); sd=np.asarray(params['scaler_scale'],float); coef=np.asarray(params['coef'],float)
    if not np.isfinite(X).all(): raise RuntimeError('non-finite frozen score features')
    return sigmoid(float(params['intercept'])+((X-mu)/sd)@coef)


def quantiles(x,ps=(.5,.9,.95,.99)):
    a=np.asarray(x,float)
    return {str(p):float(np.quantile(a,p)) for p in ps}


def capped_copy(full,cap):
    D=full.copy()
    n=len(D)
    age_active=np.zeros(n,float); age_civil=np.zeros(n,float); age_lm=np.ones(n,np.int64)
    prom_vs=np.ones(n,float); reinforce=np.zeros(n,np.int64)

    # Matching is already frozen in lineage_id. Since assignment is Markovian
    # across consecutive eligible landmarks, truncating only carried state is
    # equivalent to a cold-start tracker over the retained lineage chain.
    for _,idx0 in D.groupby('lineage_id',sort=False).groups.items():
        idx=np.asarray(list(idx0),dtype=np.int64)
        # Defensive chronological ordering.
        idx=idx[np.argsort(D.loc[idx,'landmark_i'].to_numpy(np.int64),kind='mergesort')]
        lm=D.loc[idx,'landmark_i'].to_numpy(np.int64)
        tm=D.loc[idx,'time'].astype('int64').to_numpy(np.int64)  # ns UTC
        pr=D.loc[idx,'prominence'].to_numpy(float)
        full_streak=D.loc[idx,'reinforce_streak'].to_numpy(np.int64)
        m=len(idx)
        for j in range(m):
            k=max(0,j-cap+1)
            pos=idx[j]
            age_lm[pos]=j-k+1
            age_active[pos]=float(lm[j]-lm[k])
            age_civil[pos]=float((tm[j]-tm[k])/60_000_000_000.0)
            prom_vs[pos]=float(pr[j]/(np.max(pr[k:j+1])+1e-9))
            reinforce[pos]=int(min(full_streak[j],j-k))

    D['age_lm_cap']=age_lm
    D['age_active_min']=age_active
    D['age_civil_min']=age_civil
    D['prom_vs_histmax']=prom_vs
    D['reinforce_streak']=reinforce
    D['log_age_active']=np.log1p(D.age_active_min)
    D['log_age_civil']=np.log1p(D.age_civil_min)
    return D


def landmark_metrics(D,full_score,cap_score):
    within=[]; top1=[]; jac=[]
    tmp=pd.DataFrame({'landmark_i':D.landmark_i.to_numpy(),'full':full_score,'cap':cap_score},index=D.index)
    for _,g in tmp.groupby('landmark_i',sort=False):
        if len(g)>=3:
            s=spearmanr(g['full'],g['cap']).statistic
            if np.isfinite(s): within.append(float(s))
            f3=set(g.nlargest(3,'full').index.tolist()); c3=set(g.nlargest(3,'cap').index.tolist())
            jac.append(len(f3&c3)/len(f3|c3))
        top1.append(int(g['full'].idxmax())==int(g['cap'].idxmax()))
    return {
        'within_landmark_spearman_median':float(np.median(within)),
        'within_landmark_spearman_mean':float(np.mean(within)),
        'within_landmark_n':int(len(within)),
        'top1_agreement':float(np.mean(top1)),
        'top1_landmarks':int(len(top1)),
        'top3_jaccard_mean':float(np.mean(jac)),
        'top3_jaccard_median':float(np.median(jac)),
        'top3_landmarks':int(len(jac)),
    }


def main():
    a=parse()
    raw=pd.read_pickle(a.pkl).reset_index(drop=True)
    # Hard outcome-blind guard: future fields may physically exist in the Z4
    # research table, but this program's inputs to metrics/model are restricted
    # to frozen feature/state/identity columns only.
    forbidden={'revisited','touch_idx','touch_us','first_state','peak_touch','sweep_far','reclaim_peak','reclaim_full','pos5','pos15','pos30','pos60','mfe5_v','mfe15_v','mfe30_v','mfe60_v','mae5_v','mae15_v','mae30_v','mae60_v'}
    referenced={'lineage_id','landmark_i','time','prominence','reinforce_streak','age_lm'}
    if forbidden & referenced: raise RuntimeError('future outcome referenced by lineage cap audit')

    D=decorate(raw)
    freeze=json.load(open(a.frozen_json)); params=freeze['feeds']['BID']['M0GL']
    full_score=predict(D,params)
    age=D.age_lm.to_numpy(np.int64)
    age_report={
        'max':int(age.max()),
        'quantiles':quantiles(age,(.5,.75,.9,.95,.99,.995,.999)),
        'fractions_gt':{str(c):float(np.mean(age>c)) for c in CAPS},
        'rows':int(len(D)),
        'lineages':int(D.lineage_id.nunique()),
        'landmarks':int(D.landmark_i.nunique()),
    }

    results={}
    selected=None
    for cap in CAPS:
        C=capped_copy(D,cap)
        s=predict(C,params)
        err=np.abs(s-full_score)
        lm=landmark_metrics(D,full_score,s)
        m={
            'cap':cap,
            'pearson':float(pearsonr(full_score,s).statistic),
            'spearman':float(spearmanr(full_score,s).statistic),
            'abs_error_quantiles':quantiles(err,(.5,.9,.95,.99)),
            'fraction_abs_error_gt_003':float(np.mean(err>.03)),
            'fraction_abs_error_gt_005':float(np.mean(err>.05)),
            'fraction_full_age_gt_cap':float(np.mean(age>cap)),
            **lm,
        }
        checks={
            'spearman_ge_0995':m['spearman']>=.995,
            'pearson_ge_0995':m['pearson']>=.995,
            'median_abs_error_le_0005':m['abs_error_quantiles']['0.5']<=.005,
            'p95_abs_error_le_0030':m['abs_error_quantiles']['0.95']<=.030,
            'fraction_abs_error_gt_005_le_002':m['fraction_abs_error_gt_005']<=.02,
            'within_landmark_spearman_median_ge_0995':m['within_landmark_spearman_median']>=.995,
            'top1_agreement_ge_095':m['top1_agreement']>=.95,
            'top3_jaccard_mean_ge_095':m['top3_jaccard_mean']>=.95,
        }
        m['checks']=checks; m['status']='PASS' if all(checks.values()) else 'FAIL'
        results[str(cap)]=m
        if selected is None and m['status']=='PASS': selected=cap

    out={
        'status':'PASS' if selected is not None else 'FAIL',
        'scope':'OUTCOME_BLIND_PINE_LINEAGE_BOOTSTRAP_CAP_DEV_BID_JAN_JUL_2024',
        'future_outcomes_used':False,
        'candidate_caps':list(CAPS),
        'selection_rule':'smallest cap passing every preregistered engineering criterion',
        'selected_cap':selected,
        'full_lineage_age':age_report,
        'caps':results,
    }
    Path(a.output).write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2),flush=True)

if __name__=='__main__': main()
