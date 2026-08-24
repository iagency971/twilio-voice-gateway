import argparse,json,platform
from pathlib import Path
import numpy as np,pandas as pd,sklearn
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

SEED=44
M0=['side','dist_v','absdist_v','width_v','tr','trend15','trend60','trend240','week_sin','week_cos','landmark_us','log_exposure_center']
G=['log_prom','log_bg','log_strength','log_mass','log_peak','same_share_center','same_minus_body_center','log_mean_wick','log_mean_body','wick_share_zone','width_vseg']
L=['log_age_active','log_age_civil','center_shift_vseg','width_log_change','prom_log_change','mass_log_change','strength_log_change','reinforce_streak','center_sd4_vseg','width_cv4','prom_vs_histmax']
MODELS={'M0':M0,'M0GL':M0+G+L}

def decorate(D):
 D=D.copy();D['time']=pd.to_datetime(D.time,utc=True)
 D['log_age_active']=np.log1p(D.age_active_min);D['log_age_civil']=np.log1p(D.age_civil_min);D['log_prom']=np.log1p(D.prominence);D['log_bg']=np.log1p(D.background);D['log_strength']=np.log1p(D.strength_raw);D['log_mass']=np.log1p(D.mass);D['log_peak']=np.log1p(D.peak_height);D['log_mean_wick']=np.log1p(D.mean_wick);D['log_mean_body']=np.log1p(D.mean_body)
 return D

def weights(D):
 c=D.groupby('landmark_i').size();return D.landmark_i.map((1.0/c).to_dict()).to_numpy(float)

def fit_freeze(D,features):
 Xd=D.dropna(subset=features+['revisited']).copy();sc=StandardScaler();X=sc.fit_transform(Xd[features]);m=LogisticRegression(C=.1,max_iter=500,tol=1e-6,solver='lbfgs',random_state=SEED);m.fit(X,Xd.revisited.astype(int),sample_weight=weights(Xd))
 return {'features':features,'train_rows':int(len(Xd)),'train_landmarks':int(Xd.landmark_i.nunique()),'scaler_mean':[float(x) for x in sc.mean_],'scaler_scale':[float(x) for x in sc.scale_],'coef':[float(x) for x in m.coef_[0]],'intercept':float(m.intercept_[0]),'C':0.1,'solver':'lbfgs','max_iter':500,'tol':1e-6,'equal_total_weight_per_landmark':True}

def main():
 p=argparse.ArgumentParser();p.add_argument('--bid-pkl',required=True);p.add_argument('--ask-pkl',required=True);p.add_argument('--completion-json',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 comp=json.load(open(a.completion_json));out={'status':'FROZEN_DEV_MODEL_PARAMETERS_BEFORE_VALIDATION','training_period':'DEV only through 2024-07-31','versions':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__},'feeds':{}}
 for feed,path in [('BID',a.bid_pkl),('ASK',a.ask_pkl)]:
  D=decorate(pd.read_pickle(path));D=D[D.time<pd.Timestamp('2024-08-01',tz='UTC')].copy();out['feeds'][feed]={'M0':fit_freeze(D,M0),'M0GL':fit_freeze(D,M0+G+L),'platt_from_oof_dev':comp['feeds'][feed]['platt_dev_freeze_candidate']}
 Path(a.output).write_text(json.dumps(out,indent=2))
 print(json.dumps({f:{'m0gl_intercept':out['feeds'][f]['M0GL']['intercept'],'platt_intercept':out['feeds'][f]['platt_from_oof_dev']['intercept'],'platt_slope':out['feeds'][f]['platt_from_oof_dev']['slope']} for f in out['feeds']},indent=2))
if __name__=='__main__':main()
