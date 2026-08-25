import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

SEED=44
M0=['side','dist_v','absdist_v','width_v','tr','trend15','trend60','trend240','week_sin','week_cos','landmark_us','log_exposure_center']
G=['log_prom','log_bg','log_strength','log_mass','log_peak','same_share_center','same_minus_body_center','log_mean_wick','log_mean_body','wick_share_zone','width_vseg']
L=['log_age_active','log_age_civil','center_shift_vseg','width_log_change','prom_log_change','mass_log_change','strength_log_change','reinforce_streak','center_sd4_vseg','width_cv4','prom_vs_histmax']
MODELS={'M0':M0,'M0GL':M0+G+L}


def decorate(D):
    D=D.copy(); D['time']=pd.to_datetime(D.time,utc=True)
    D['log_age_active']=np.log1p(D.age_active_min); D['log_age_civil']=np.log1p(D.age_civil_min)
    D['log_prom']=np.log1p(D.prominence); D['log_bg']=np.log1p(D.background); D['log_strength']=np.log1p(D.strength_raw)
    D['log_mass']=np.log1p(D.mass); D['log_peak']=np.log1p(D.peak_height)
    D['log_mean_wick']=np.log1p(D.mean_wick); D['log_mean_body']=np.log1p(D.mean_body)
    return D


def weights(D):
    c=D.groupby('landmark_i').size()
    return D.landmark_i.map((1.0/c).to_dict()).to_numpy(float)


def fit_one(D,features):
    X=D[features].to_numpy(float); y=D.revisited.to_numpy(int); w=weights(D)
    if not np.isfinite(X).all(): raise RuntimeError('nonfinite feature matrix')
    sc=StandardScaler(); Xs=sc.fit_transform(X)
    m=LogisticRegression(C=.10,max_iter=500,tol=1e-6,solver='lbfgs',random_state=SEED)
    m.fit(Xs,y,sample_weight=w)
    return {
        'features':features,
        'train_rows':int(len(D)),
        'train_landmarks':int(D.landmark_i.nunique()),
        'scaler_mean':[float(x) for x in sc.mean_],
        'scaler_scale':[float(x) for x in sc.scale_],
        'coef':[float(x) for x in m.coef_[0]],
        'intercept':float(m.intercept_[0]),
        'C':0.1,'solver':'lbfgs','max_iter':500,'tol':1e-6,
        'equal_total_weight_per_landmark':True
    }


def main():
    p=argparse.ArgumentParser(); p.add_argument('--bid-pkl',required=True); p.add_argument('--ask-pkl',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    out={
      'status':'FROZEN_C5_DEV_MODEL_PARAMETERS_BEFORE_CADENCE_HISTORICAL_REPLICATION',
      'cadence_min':5,
      'lookback_active_m1':1440,
      'endpoint':'REVISIT_240_ACTIVE_M1',
      'training_period_utc':['2024-01-01','2024-08-01'],
      'reference_engine_git_blob':'a8a147615c3fd366c49e93b340fd2018b5b66e9e',
      'mechanical_c5_engine_sha256':'7bb47cfc78a26dd7a74965556352114a8e31ca1545ef4d21a987951daf417d24',
      'versions':{'python':'3.11','numpy':'2.3.2','pandas':'2.3.1','sklearn':'1.7.1'},
      'feeds':{}
    }
    for feed,path in [('BID',a.bid_pkl),('ASK',a.ask_pkl)]:
        D=decorate(pd.read_pickle(path))
        D=D[(D.time>=pd.Timestamp('2024-01-01',tz='UTC'))&(D.time<pd.Timestamp('2024-08-01',tz='UTC'))].copy()
        out['feeds'][feed]={}
        for name,features in MODELS.items(): out['feeds'][feed][name]=fit_one(D,features)
    Path(a.output).write_text(json.dumps(out,indent=2,allow_nan=False))
    print(json.dumps({f:{m:{'rows':out['feeds'][f][m]['train_rows'],'landmarks':out['feeds'][f][m]['train_landmarks'],'intercept':out['feeds'][f][m]['intercept']} for m in MODELS} for f in out['feeds']},indent=2))

if __name__=='__main__': main()
