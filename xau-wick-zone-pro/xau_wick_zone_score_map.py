import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse():
    p=argparse.ArgumentParser()
    p.add_argument('--pkl',required=True)
    p.add_argument('--frozen-json',required=True)
    p.add_argument('--output',required=True)
    return p.parse_args()


def sigmoid(x):
    x=np.asarray(x,float); out=np.empty_like(x); pos=x>=0
    out[pos]=1/(1+np.exp(-x[pos])); ex=np.exp(x[~pos]); out[~pos]=ex/(1+ex)
    return out


def decorate(D):
    D=D.copy()
    D['log_age_active']=np.log1p(D.age_active_min); D['log_age_civil']=np.log1p(D.age_civil_min)
    D['log_prom']=np.log1p(D.prominence); D['log_bg']=np.log1p(D.background); D['log_strength']=np.log1p(D.strength_raw)
    D['log_mass']=np.log1p(D.mass); D['log_peak']=np.log1p(D.peak_height); D['log_mean_wick']=np.log1p(D.mean_wick); D['log_mean_body']=np.log1p(D.mean_body)
    return D


def predict(D,params):
    X=D[params['features']].to_numpy(float)
    mu=np.asarray(params['scaler_mean'],float); sd=np.asarray(params['scaler_scale'],float); coef=np.asarray(params['coef'],float)
    return sigmoid(float(params['intercept'])+((X-mu)/sd)@coef)


def weighted_quantiles(values,weights,probs):
    o=np.argsort(values,kind='mergesort'); v=np.asarray(values,float)[o]; w=np.asarray(weights,float)[o]
    cw=np.cumsum(w); cw/=cw[-1]
    # prepend the minimum at cumulative probability zero so q=0 is exact min
    xp=np.r_[0.0,cw]; fp=np.r_[v[0],v]
    return np.interp(np.asarray(probs,float),xp,fp)


def main():
    a=parse(); D=decorate(pd.read_pickle(a.pkl)).reset_index(drop=True)
    freeze=json.load(open(a.frozen_json)); params=freeze['feeds']['BID']['M0GL']
    p=predict(D,params)
    counts=D.groupby('landmark_i').size(); w=D.landmark_i.map((1.0/counts).to_dict()).to_numpy(float)
    probs=np.arange(101,dtype=float)/100.0; thr=weighted_quantiles(p,w,probs)
    out={
      'status':'FROZEN_USER_FACING_SCORE_MAP_DEV_ONLY',
      'scientific_model':'Z4 BID M0GL P_REVISIT_240',
      'reference_period':'DEV Jan-Jul 2024 only',
      'mapping':'equal-landmark-weighted empirical percentile of frozen raw M0GL output',
      'not_probability':True,
      'rows':int(len(D)),
      'landmarks':int(D.landmark_i.nunique()),
      'raw_score_min':float(np.min(p)),
      'raw_score_max':float(np.max(p)),
      'percentile_thresholds':[{'R':int(i),'raw_threshold':float(thr[i])} for i in range(101)],
      'deciles':{str(i):float(thr[i]) for i in range(0,101,10)},
    }
    Path(a.output).write_text(json.dumps(out,indent=2))
    print(json.dumps({'rows':out['rows'],'landmarks':out['landmarks'],'deciles':out['deciles']},indent=2),flush=True)

if __name__=='__main__': main()
