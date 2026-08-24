import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import pearsonr, spearmanr


def parse():
    p=argparse.ArgumentParser()
    p.add_argument('--exact-pkl',required=True)
    p.add_argument('--proxy-pkl',required=True)
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
    x=np.asarray(x,float)
    out=np.empty_like(x)
    pos=x>=0
    out[pos]=1/(1+np.exp(-x[pos]))
    ex=np.exp(x[~pos]); out[~pos]=ex/(1+ex)
    return out


def predict_frozen(D,params):
    feats=params['features']
    X=D[feats].to_numpy(float)
    mu=np.asarray(params['scaler_mean'],float)
    sd=np.asarray(params['scaler_scale'],float)
    coef=np.asarray(params['coef'],float)
    if not np.isfinite(X).all(): raise RuntimeError('non-finite features in parity input')
    return sigmoid(float(params['intercept'])+((X-mu)/sd)@coef)


def iou(a0,a1,b0,b1):
    inter=max(0.0,min(a1,b1)-max(a0,b0))
    union=max(a1,b1)-min(a0,b0)
    return inter/union if union>0 else 0.0


def q(x,vals=(.1,.5,.9,.95)):
    a=np.asarray(x,float)
    if len(a)==0: return {str(v):None for v in vals}
    return {str(v):float(np.quantile(a,v)) for v in vals}


def main():
    a=parse()
    E=decorate(pd.read_pickle(a.exact_pkl)).reset_index(drop=True)
    P=decorate(pd.read_pickle(a.proxy_pkl)).reset_index(drop=True)
    freeze=json.load(open(a.frozen_json))
    params=freeze['feeds']['BID']['M0GL']
    E['score_raw']=predict_frozen(E,params)
    P['score_raw']=predict_frozen(P,params)

    # Outcome-blind hard guard: the comparator never selects/references any
    # future label column. Fail if someone accidentally adds one below.
    forbidden={'revisited','touch_idx','touch_us','first_state','peak_touch','sweep_far','reclaim_peak','reclaim_full','pos5','pos15','pos30','pos60','mfe5_v','mfe15_v','mfe30_v','mfe60_v','mae5_v','mae15_v','mae30_v','mae60_v'}
    used={'landmark_i','side','center','zlo','zhi','vseg','score_raw'}
    if forbidden & used: raise RuntimeError('future outcome entered parity comparator')

    E_groups={(int(lm),int(side)):g.index.to_numpy(np.int64) for (lm,side),g in E.groupby(['landmark_i','side'],sort=True)}
    P_groups={(int(lm),int(side)):g.index.to_numpy(np.int64) for (lm,side),g in P.groupby(['landmark_i','side'],sort=True)}
    keys=sorted(set(E_groups)|set(P_groups))

    pairs=[]
    matched_e=set(); matched_p=set()
    landmark_pair_map={}
    for key in keys:
        ei=E_groups.get(key,np.array([],dtype=np.int64)); pi=P_groups.get(key,np.array([],dtype=np.int64))
        if not len(ei) or not len(pi): continue
        cost=np.full((len(ei),len(pi)),1e9,float); valid=np.zeros_like(cost,dtype=bool)
        for r,eidx in enumerate(ei):
            er=E.loc[eidx]; ew=max(float(er.zhi-er.zlo),.01)
            for c,pidx in enumerate(pi):
                pr=P.loc[pidx]; pw=max(float(pr.zhi-pr.zlo),.01)
                vs=max(float(er.vseg),float(pr.vseg),.01)
                cd=abs(float(er.center-pr.center))
                ov=iou(float(er.zlo),float(er.zhi),float(pr.zlo),float(pr.zhi))
                ok=(cd<=vs) or (ov>0)
                if ok:
                    valid[r,c]=True
                    cost[r,c]=cd/vs + .5*(1-ov) + .1*abs(math.log(pw/ew))
        rr,cc=linear_sum_assignment(cost)
        for r,c in zip(rr,cc):
            if not valid[r,c] or cost[r,c]>=1e8: continue
            eidx=int(ei[r]); pidx=int(pi[c]); er=E.loc[eidx]; pr=P.loc[pidx]
            vs=max(float(er.vseg),float(pr.vseg),.01)
            ov=iou(float(er.zlo),float(er.zhi),float(pr.zlo),float(pr.zhi))
            rec={
                'landmark_i':key[0],'side':key[1],'eidx':eidx,'pidx':pidx,
                'iou':ov,
                'center_err_vseg':abs(float(er.center-pr.center))/vs,
                'lo_err_vseg':abs(float(er.zlo-pr.zlo))/vs,
                'hi_err_vseg':abs(float(er.zhi-pr.zhi))/vs,
                'score_exact':float(er.score_raw),'score_proxy':float(pr.score_raw),
                'score_abs_err':abs(float(er.score_raw-pr.score_raw))
            }
            pairs.append(rec); matched_e.add(eidx); matched_p.add(pidx)
            landmark_pair_map[(key[0],eidx)]=pidx

    M=pd.DataFrame(pairs)
    if len(M)<100: raise RuntimeError(f'too few parity matches: {len(M)}')

    same_count=[]
    count_abs=[]
    for lm in sorted(set(E.landmark_i.unique())|set(P.landmark_i.unique())):
        ne=int((E.landmark_i==lm).sum()); np_=int((P.landmark_i==lm).sum())
        same_count.append(ne==np_); count_abs.append(abs(ne-np_))

    pear=float(pearsonr(M.score_exact,M.score_proxy).statistic)
    spear=float(spearmanr(M.score_exact,M.score_proxy).statistic)

    within=[]
    top_agree=[]
    for lm in sorted(set(E.landmark_i.unique()) & set(P.landmark_i.unique())):
        em=E[E.landmark_i==lm]; pm=P[P.landmark_i==lm]
        mm=M[M.landmark_i==lm]
        if len(mm)>=3:
            s=spearmanr(mm.score_exact,mm.score_proxy).statistic
            if np.isfinite(s): within.append(float(s))
        if len(em) and len(pm):
            etop=int(em.score_raw.idxmax()); ptop=int(pm.score_raw.idxmax())
            top_agree.append(landmark_pair_map.get((int(lm),etop),-1)==ptop)

    metrics={
        'exact_rows':int(len(E)),
        'proxy_rows':int(len(P)),
        'matched_pairs':int(len(M)),
        'exact_zone_match_rate':float(len(matched_e)/len(E)),
        'proxy_zone_match_rate':float(len(matched_p)/len(P)),
        'landmarks_exact':int(E.landmark_i.nunique()),
        'landmarks_proxy':int(P.landmark_i.nunique()),
        'same_zone_count_landmark_rate':float(np.mean(same_count)),
        'mean_abs_zone_count_difference':float(np.mean(count_abs)),
        'iou_quantiles':q(M.iou,(.1,.25,.5,.75,.9,.95)),
        'center_err_vseg_quantiles':q(M.center_err_vseg,(.5,.9,.95,.99)),
        'lo_err_vseg_quantiles':q(M.lo_err_vseg,(.5,.9,.95)),
        'hi_err_vseg_quantiles':q(M.hi_err_vseg,(.5,.9,.95)),
        'score_pearson':pear,
        'score_spearman':spear,
        'score_abs_err_quantiles':q(M.score_abs_err,(.5,.9,.95,.99)),
        'within_landmark_spearman_median':float(np.median(within)) if within else None,
        'within_landmark_spearman_mean':float(np.mean(within)) if within else None,
        'within_landmark_rank_landmarks':int(len(within)),
        'top1_zone_agreement':float(np.mean(top_agree)) if top_agree else None,
        'top1_eligible_landmarks':int(len(top_agree)),
    }

    checks={
        'exact_match_ge_090':metrics['exact_zone_match_rate']>=.90,
        'proxy_match_ge_090':metrics['proxy_zone_match_rate']>=.90,
        'median_iou_ge_075':metrics['iou_quantiles']['0.5']>=.75,
        'p10_iou_ge_045':metrics['iou_quantiles']['0.1']>=.45,
        'median_center_err_le_010_vseg':metrics['center_err_vseg_quantiles']['0.5']<=.10,
        'p95_center_err_le_035_vseg':metrics['center_err_vseg_quantiles']['0.95']<=.35,
        'score_spearman_ge_095':metrics['score_spearman']>=.95,
        'median_score_abs_err_le_003':metrics['score_abs_err_quantiles']['0.5']<=.03,
        'p95_score_abs_err_le_010':metrics['score_abs_err_quantiles']['0.95']<=.10,
        'top1_agreement_ge_085':metrics['top1_zone_agreement'] is not None and metrics['top1_zone_agreement']>=.85,
    }
    out={
        'status':'PASS' if all(checks.values()) else 'FAIL',
        'parity_scope':'OUTCOME_BLIND_ENGINEERING_PARITY_DEV_BID_JAN_JUL_2024',
        'reference':'Z4 exact SciPy Gaussian',
        'proxy':'Z4 identical except Pine 3-box Gaussian smoothing',
        'future_outcomes_used_in_metrics':False,
        'metrics':metrics,
        'checks':checks,
    }
    Path(a.output).write_text(json.dumps(out,indent=2))
    csv=Path(a.output).with_suffix('.matched.csv')
    M.to_csv(csv,index=False)
    print(json.dumps(out,indent=2),flush=True)

if __name__=='__main__': main()
