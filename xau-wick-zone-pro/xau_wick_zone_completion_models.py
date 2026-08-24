import argparse, json, warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression, Ridge

warnings.filterwarnings('ignore')
SEED=44

M0=['side','dist_v','absdist_v','width_v','tr','trend15','trend60','trend240','week_sin','week_cos','landmark_us','log_exposure_center']
G=['log_prom','log_bg','log_strength','log_mass','log_peak','same_share_center','same_minus_body_center','log_mean_wick','log_mean_body','wick_share_zone','width_vseg']
L=['log_age_active','log_age_civil','center_shift_vseg','width_log_change','prom_log_change','mass_log_change','strength_log_change','reinforce_streak','center_sd4_vseg','width_cv4','prom_vs_histmax']
MODELS={'M0':M0,'M0G':M0+G,'M0L':M0+L,'M0GL':M0+G+L}
FOLDS=[('APR','2024-04-01','2024-05-01'),('MAY','2024-05-01','2024-06-01'),('JUN','2024-06-01','2024-07-01'),('JUL','2024-07-01','2024-08-01')]
BINARY_REACTION=[('pos30','y30'),('pos60','y60'),('sweep_reclaim_peak','sweep_reclaim_peak'),('sweep_reclaim_full','sweep_reclaim_full'),('full_retest_zone','sweep_reclaim_full_retest_zone'),('full_retest_peak','sweep_reclaim_full_retest_peak')]
CONTINUOUS=['dir5','dir15','dir30','dir60','mfe5_v','mfe15_v','mfe30_v','mfe60_v','violation5_v','violation15_v','violation30_v','violation60_v']

def parse():
    p=argparse.ArgumentParser(); p.add_argument('--bid-pkl',required=True); p.add_argument('--ask-pkl',required=True); p.add_argument('--manifest-json'); p.add_argument('--output',required=True); return p.parse_args()

def decorate(D):
    D=D.copy(); D['time']=pd.to_datetime(D.time,utc=True)
    D['log_age_active']=np.log1p(D.age_active_min); D['log_age_civil']=np.log1p(D.age_civil_min)
    D['log_prom']=np.log1p(D.prominence); D['log_bg']=np.log1p(D.background); D['log_strength']=np.log1p(D.strength_raw); D['log_mass']=np.log1p(D.mass); D['log_peak']=np.log1p(D.peak_height)
    D['log_mean_wick']=np.log1p(D.mean_wick); D['log_mean_body']=np.log1p(D.mean_body)
    for h in (5,15,30,60): D[f'y{h}']=(D[f'dir{h}']>0).astype(float)
    return D

def prep(D,features,label): return D.dropna(subset=features+[label]).copy()
def weights(D):
    c=D.groupby('landmark_i').size(); return D.landmark_i.map((1.0/c).to_dict()).to_numpy(float)
def weighted_mean(x,w): return float(np.sum(np.asarray(x,float)*w)/np.sum(w))
def binary_score(D,p,label):
    w=weights(D); y=D[label].to_numpy(float); p=np.clip(np.asarray(p,float),1e-8,1-1e-8)
    return weighted_mean((p-y)**2,w), weighted_mean(-y*np.log(p)-(1-y)*np.log(1-p),w)
def continuous_score(D,p,label):
    w=weights(D); y=D[label].to_numpy(float); p=np.asarray(p,float); return weighted_mean((p-y)**2,w),weighted_mean(np.abs(p-y),w)

def fit_binary(tr,te,feat,label):
    tr=prep(tr,feat,label); te=prep(te,feat,label); sc=StandardScaler(); X=sc.fit_transform(tr[feat]); Xt=sc.transform(te[feat])
    m=LogisticRegression(C=.1,max_iter=500,tol=1e-6,solver='lbfgs',random_state=SEED); m.fit(X,tr[label].astype(int),sample_weight=weights(tr)); return te,m.predict_proba(Xt)[:,1]
def fit_continuous(tr,te,feat,label):
    tr=prep(tr,feat,label); te=prep(te,feat,label); sc=StandardScaler(); X=sc.fit_transform(tr[feat]); Xt=sc.transform(te[feat]); m=Ridge(alpha=10.0); m.fit(X,tr[label].to_numpy(float),sample_weight=weights(tr)); return te,m.predict(Xt)

def bootstrap_mean(vals,n=10000):
    vals=np.asarray(vals,float)
    if len(vals)==0:return [float('nan')]*3+[0]
    rng=np.random.default_rng(SEED); b=np.empty(n,float)
    for i in range(n): b[i]=rng.choice(vals,len(vals),replace=True).mean()
    return [float(vals.mean()),float(np.quantile(b,.025)),float(np.quantile(b,.975)),int(len(vals))]

def day_delta(D,p0,p1,label):
    X=D[['time','landmark_i',label]].copy(); X['p0']=p0; X['p1']=p1; X['day']=X.time.dt.floor('D'); vals=[]
    for _,g in X.groupby('day'): vals.append(binary_score(g,g.p0.to_numpy(),label)[0]-binary_score(g,g.p1.to_numpy(),label)[0])
    return bootstrap_mean(vals,3000)

def group_binary(D,p0,p1,label):
    arr={'ALL':np.ones(len(D),bool),'BUY':D.side.to_numpy()<0,'SELL':D.side.to_numpy()>0,'LANDMARK_US':D.landmark_us.to_numpy()==1,'LANDMARK_NON_US':D.landmark_us.to_numpy()==0}
    if 'touch_us' in D.columns: arr.update({'TOUCH_US':D.touch_us.to_numpy()==1,'TOUCH_NON_US':D.touch_us.to_numpy()==0,'BUY_US_TOUCH':(D.side.to_numpy()<0)&(D.touch_us.to_numpy()==1),'SELL_US_TOUCH':(D.side.to_numpy()>0)&(D.touch_us.to_numpy()==1)})
    out={}
    for k,m in arr.items():
        if int(m.sum())<20: continue
        d=D.iloc[np.where(m)[0]]; b0,l0=binary_score(d,np.asarray(p0)[m],label); b1,l1=binary_score(d,np.asarray(p1)[m],label)
        out[k]={'n':int(m.sum()),'rate':float(d[label].mean()),'delta_brier':float(b0-b1),'delta_logloss':float(l0-l1)}
    return out

def eval_binary_task(tr,te,label,condition_revisited=False,ablations=False):
    if condition_revisited: tr=tr[tr.revisited==1].copy(); te=te[te.revisited==1].copy()
    names=['M0','M0GL']+(['M0G','M0L'] if ablations else []); preds={}; scores={}; ref=None
    for name in names: ref,p=fit_binary(tr,te,MODELS[name],label); preds[name]=p; scores[name]=binary_score(ref,p,label)
    base=scores['M0']; out={'n_test':int(len(ref)),'rate':float(ref[label].mean()),'models':{}}
    for name in names: out['models'][name]={'brier':scores[name][0],'logloss':scores[name][1],'delta_brier':float(base[0]-scores[name][0]),'delta_logloss':float(base[1]-scores[name][1])}
    out['M0GL_day_bootstrap']=day_delta(ref,preds['M0'],preds['M0GL'],label); out['groups_M0GL']=group_binary(ref,preds['M0'],preds['M0GL'],label)
    return out,ref,preds['M0'],preds['M0GL']

def eval_continuous_task(tr,te,label):
    tr=tr[tr.revisited==1].copy(); te=te[te.revisited==1].copy(); out={'models':{}}; ref=None
    for name in ['M0','M0GL']:
        ref,p=fit_continuous(tr,te,MODELS[name],label); mse,mae=continuous_score(ref,p,label); out['models'][name]={'mse':mse,'mae':mae}
    out['n_test']=int(len(ref)); out['mean_target']=float(ref[label].mean()); out['delta_mse']=float(out['models']['M0']['mse']-out['models']['M0GL']['mse']); out['delta_mae']=float(out['models']['M0']['mae']-out['models']['M0GL']['mae']); return out

def weighted_weekly_oof(O):
    O=O.copy(); O['week']=O.time.dt.tz_localize(None).dt.to_period('W-SUN').astype(str); vals=[]; rows=[]
    for wk,g in O.groupby('week',sort=True):
        b0,l0=binary_score(g,g.p0.to_numpy(),'revisited'); b1,l1=binary_score(g,g.p1.to_numpy(),'revisited'); d=b0-b1; vals.append(d); rows.append({'week':wk,'n':int(len(g)),'landmarks':int(g.landmark_i.nunique()),'delta_brier':float(d),'delta_logloss':float(l0-l1)})
    boot=bootstrap_mean(vals,10000); return {'weeks':rows,'n_weeks':len(rows),'positive_weeks':int(sum(r['delta_brier']>0 for r in rows)),'mean_delta_brier':boot[0],'bootstrap_95':boot[1:3]}

def pooled_oof_score(O):
    b0,l0=binary_score(O,O.p0.to_numpy(),'revisited'); b1,l1=binary_score(O,O.p1.to_numpy(),'revisited'); return {'n':int(len(O)),'landmarks':int(O.landmark_i.nunique()),'M0_brier':b0,'M0GL_brier':b1,'delta_brier':float(b0-b1),'M0_logloss':l0,'M0GL_logloss':l1,'delta_logloss':float(l0-l1)}

def platt_freeze(O):
    y=O.revisited.to_numpy(int); p=np.clip(O.p1.to_numpy(float),1e-6,1-1e-6); x=np.log(p/(1-p)).reshape(-1,1); w=weights(O); m=LogisticRegression(C=1e6,solver='lbfgs',max_iter=1000); m.fit(x,y,sample_weight=w)
    slope=float(m.coef_[0,0]); intercept=float(m.intercept_[0]); pc=m.predict_proba(x)[:,1]; bins=[]
    for lo in np.arange(0,1,.1):
        hi=lo+.1; mask=(pc>=lo)&((pc<hi) if hi<1 else (pc<=hi))
        if mask.sum()==0: continue
        d=O.iloc[np.where(mask)[0]]; ww=weights(d); bins.append({'lo':round(float(lo),1),'hi':round(float(hi),1),'n':int(mask.sum()),'mean_pred':weighted_mean(pc[mask],ww),'observed':weighted_mean(d.revisited.to_numpy(float),ww)})
    return {'intercept':intercept,'slope':slope,'bins_calibrated_dev_fit':bins}

def feed_eval(D,feed_name):
    D=decorate(D); fold_results={}; oof=[]
    for name,start,end in FOLDS:
        s=pd.Timestamp(start,tz='UTC'); e=pd.Timestamp(end,tz='UTC'); tr=D[D.time<s].copy(); te=D[(D.time>=s)&(D.time<e)].copy()
        if len(te)==0: raise RuntimeError(f'{feed_name} {name}: no test rows')
        print(feed_name,name,'train',len(tr),'test',len(te),flush=True); fr={}; revisit,ref,p0,p1=eval_binary_task(tr,te,'revisited',False,True); fr['revisit']=revisit
        oo=ref[['time','landmark_i','side','landmark_us','revisited']].copy(); oo['p0']=p0; oo['p1']=p1; oo['fold']=name; oof.append(oo)
        for nm,label in BINARY_REACTION:
            if tr.loc[tr.revisited==1,label].nunique()>=2 and te.loc[te.revisited==1,label].nunique()>=2: fr[nm]=eval_binary_task(tr,te,label,True,False)[0]
        fr['continuous']={}
        for label in CONTINUOUS:
            if label in D.columns: fr['continuous'][label]=eval_continuous_task(tr,te,label)
        fold_results[name]=fr
    O=pd.concat(oof,ignore_index=True); weekly=weighted_weekly_oof(O); pooled=pooled_oof_score(O); calib=platt_freeze(O)
    all_positive=all(fold_results[f]['revisit']['models']['M0GL']['delta_brier']>0 for f,_,_ in FOLDS); all_logloss_nonneg=all(fold_results[f]['revisit']['models']['M0GL']['delta_logloss']>=0 for f,_,_ in FOLDS)
    return {'feed':feed_name,'rows':int(len(D)),'landmarks':int(D.landmark_i.nunique()),'lineages':int(D.lineage_id.nunique()),'folds':fold_results,'revisit_oof_pooled':pooled,'revisit_weekly':weekly,'platt_dev_freeze_candidate':calib,'dev_sign_checks':{'all_four_folds_positive_brier':bool(all_positive),'all_four_folds_nonnegative_logloss':bool(all_logloss_nonneg),'weekly_ci_lower_gt_zero':bool(weekly['bootstrap_95'][0]>0)}}

def main():
    a=parse(); bid=pd.read_pickle(a.bid_pkl); ask=pd.read_pickle(a.ask_pkl)
    out={'status':'DEV_ONLY_Z4_CONTINUOUS_BID_ASK_NO_VALIDATION_OOS','architecture':{'zone':'Z4','step_usd':0.01,'lookback_active_m1':1440,'horizon_active_m1':240,'segmentation_volatility':'median TR over same 1440 active M1','gaussian_scales_vseg':[0.25,0.50,1.00],'bounds':'medium peak width at 50% prominence (P50)','grid_origin_usd':0.0,'lineage_gap_rule':'missing eligible landmark terminates lineage','lineage_age':'exact active-bar index difference from birth','model':'StandardScaler train only + LogisticRegression C=0.10 lbfgs; equal total weight per landmark','folds':[x[0] for x in FOLDS]},'manifest':json.load(open(a.manifest_json)) if a.manifest_json else None,'feeds':{}}
    out['feeds']['BID']=feed_eval(bid,'BID'); out['feeds']['ASK']=feed_eval(ask,'ASK'); b=out['feeds']['BID']; q=out['feeds']['ASK']
    out['prospective_gate_before_validation']={'bid_all_folds_positive':b['dev_sign_checks']['all_four_folds_positive_brier'],'ask_all_folds_positive':q['dev_sign_checks']['all_four_folds_positive_brier'],'bid_weekly_ci_lower_gt_zero':b['dev_sign_checks']['weekly_ci_lower_gt_zero'],'ask_weekly_ci_lower_gt_zero':q['dev_sign_checks']['weekly_ci_lower_gt_zero'],'bid_pooled_delta_brier':b['revisit_oof_pooled']['delta_brier'],'ask_pooled_delta_brier':q['revisit_oof_pooled']['delta_brier'],'same_pooled_sign':bool(np.sign(b['revisit_oof_pooled']['delta_brier'])==np.sign(q['revisit_oof_pooled']['delta_brier']))}
    Path(a.output).write_text(json.dumps(out,indent=2)); print(json.dumps(out['prospective_gate_before_validation'],indent=2),flush=True)

if __name__=='__main__': main()
