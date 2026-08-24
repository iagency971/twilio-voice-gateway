import argparse, json
from pathlib import Path
import numpy as np, pandas as pd

SEED=44
OOS_START=pd.Timestamp('2025-08-01',tz='UTC')
OOS_SPLIT=pd.Timestamp('2026-02-01',tz='UTC')
OOS_END=pd.Timestamp('2026-08-01',tz='UTC')


def parse():
    p=argparse.ArgumentParser()
    p.add_argument('--bid-pkl',required=True)
    p.add_argument('--ask-pkl')
    p.add_argument('--frozen-json',required=True)
    p.add_argument('--source-manifest',required=True)
    p.add_argument('--validation-json',required=True)
    p.add_argument('--output',required=True)
    return p.parse_args()


def decorate(D):
    D=D.copy(); D['time']=pd.to_datetime(D.time,utc=True)
    D['log_age_active']=np.log1p(D.age_active_min); D['log_age_civil']=np.log1p(D.age_civil_min)
    D['log_prom']=np.log1p(D.prominence); D['log_bg']=np.log1p(D.background); D['log_strength']=np.log1p(D.strength_raw)
    D['log_mass']=np.log1p(D.mass); D['log_peak']=np.log1p(D.peak_height); D['log_mean_wick']=np.log1p(D.mean_wick); D['log_mean_body']=np.log1p(D.mean_body)
    return D


def weights(D):
    c=D.groupby('landmark_i').size(); return D.landmark_i.map((1.0/c).to_dict()).to_numpy(float)


def sigmoid(x):
    x=np.asarray(x,float); out=np.empty_like(x); pos=x>=0; out[pos]=1/(1+np.exp(-x[pos])); ex=np.exp(x[~pos]); out[~pos]=ex/(1+ex); return out


def predict_frozen(D,params):
    feats=params['features']; X=D[feats].to_numpy(float)
    if not np.isfinite(X).all(): raise RuntimeError('non-finite frozen model features')
    mu=np.asarray(params['scaler_mean'],float); sd=np.asarray(params['scaler_scale'],float); coef=np.asarray(params['coef'],float)
    if not (len(feats)==len(mu)==len(sd)==len(coef)): raise RuntimeError('frozen parameter length mismatch')
    return sigmoid(float(params['intercept'])+((X-mu)/sd)@coef)


def score_with_weights(y,p,w):
    p=np.clip(np.asarray(p,float),1e-12,1-1e-12); y=np.asarray(y,float); w=np.asarray(w,float)
    return float(np.sum(w*(p-y)**2)/np.sum(w)),float(np.sum(w*(-y*np.log(p)-(1-y)*np.log(1-p)))/np.sum(w))


def score(D,p,label='revisited'):
    return score_with_weights(D[label].to_numpy(float),p,weights(D))


def period_score(D,p0,p1):
    b0,l0=score(D,p0); b1,l1=score(D,p1)
    return {'n_rows':int(len(D)),'landmarks':int(D.landmark_i.nunique()),'rate_unweighted':float(D.revisited.mean()),'M0_brier':b0,'M0GL_brier':b1,'delta_brier':float(b0-b1),'M0_logloss':l0,'M0GL_logloss':l1,'delta_logloss':float(l0-l1)}


def weekly(D,p0,p1,nboot=10000):
    X=D[['time','landmark_i','revisited']].copy(); X['p0']=p0; X['p1']=p1; X['week']=X.time.dt.floor('D')-pd.to_timedelta(X.time.dt.weekday,unit='D')
    rows=[]
    for wk,g in X.groupby('week',sort=True):
        b0,l0=score(g,g.p0.to_numpy()); b1,l1=score(g,g.p1.to_numpy()); rows.append({'week_utc':wk.strftime('%Y-%m-%d'),'n_rows':int(len(g)),'landmarks':int(g.landmark_i.nunique()),'delta_brier':float(b0-b1),'delta_logloss':float(l0-l1)})
    vals=np.asarray([r['delta_brier'] for r in rows],float); rng=np.random.default_rng(SEED); boot=np.empty(nboot,float)
    for i in range(nboot): boot[i]=rng.choice(vals,len(vals),replace=True).mean()
    return {'n_weeks':len(rows),'positive_weeks':int(np.sum(vals>0)),'mean_week_delta_brier':float(vals.mean()),'bootstrap_seed':SEED,'bootstrap_n':nboot,'bootstrap_95':[float(np.quantile(boot,.025)),float(np.quantile(boot,.975))],'weeks':rows}


def calibration_correct(D,praw,platt):
    p=np.clip(np.asarray(praw,float),1e-8,1-1e-8); pc=sigmoid(float(platt['intercept'])+float(platt['slope'])*np.log(p/(1-p)))
    wall=weights(D); y=D.revisited.to_numpy(float); b,ll=score_with_weights(y,pc,wall); total=float(wall.sum()); bins=[]; ece=0.0
    for lo in np.arange(0,1,.1):
        hi=lo+.1; mask=(pc>=lo)&((pc<hi) if hi<1 else (pc<=hi))
        if not mask.any(): continue
        ww=wall[mask]; mass=float(ww.sum()/total); pred=float(np.sum(ww*pc[mask])/ww.sum()); obs=float(np.sum(ww*y[mask])/ww.sum()); ece+=mass*abs(pred-obs)
        bins.append({'lo':round(float(lo),1),'hi':round(float(hi),1),'n_rows':int(mask.sum()),'weighted_mass':mass,'mean_pred':pred,'observed':obs})
    return {'brier':b,'logloss':ll,'ece10_correct_global_landmark_weights':float(ece),'bins':bins,'note':'Validation v0.1 ECE/weighted_mass used within-bin recomputed landmark weights and is non-primary; this OOS diagnostic uses the correct global row weights.'}


def groups(D,p0,p1):
    masks={'ALL':np.ones(len(D),bool),'BUY':D.side.to_numpy()<0,'SELL':D.side.to_numpy()>0,'LANDMARK_US':D.landmark_us.to_numpy()==1,'LANDMARK_NON_US':D.landmark_us.to_numpy()==0}
    out={}
    for k,m in masks.items():
        if m.sum()<50: continue
        out[k]=period_score(D.iloc[np.where(m)[0]],np.asarray(p0)[m],np.asarray(p1)[m])
    return out


def eval_feed(D,feed,freeze):
    D=decorate(D); V=D[(D.time>=OOS_START)&(D.time<OOS_END)].copy().reset_index(drop=True)
    if len(V)==0: raise RuntimeError(f'{feed}: no OOS rows')
    allf=freeze['feeds'][feed]['M0GL']['features']; X=V[allf].to_numpy(float)
    qa={'rows_in_oos':int(len(V)),'first_scored_time':str(V.time.min()),'last_scored_time':str(V.time.max()),'landmarks':int(V.landmark_i.nunique()),'all_features_present':bool(all(f in V.columns for f in allf)),'all_features_finite':bool(np.isfinite(X).all()),'outcome_binary':bool(set(V.revisited.dropna().unique()).issubset({0,1}))}
    p0=predict_frozen(V,freeze['feeds'][feed]['M0']); p1=predict_frozen(V,freeze['feeds'][feed]['M0GL']); raw=period_score(V,p0,p1); w=weekly(V,p0,p1)
    h1=V.time<OOS_SPLIT; h2=~h1
    halves={'H1_2025-08_to_2026-01':period_score(V[h1],p0[h1],p1[h1]),'H2_2026-02_to_2026-07':period_score(V[h2],p0[h2],p1[h2])}
    return {'feed':feed,'qa':qa,'raw_primary':raw,'weekly':w,'halves':halves,'groups_diagnostic':groups(V,p0,p1),'calibrated_m0gl_diagnostic':calibration_correct(V,p1,freeze['feeds'][feed]['platt_from_oof_dev'])}


def main():
    a=parse(); freeze=json.load(open(a.frozen_json)); manifest=json.load(open(a.source_manifest)); validation=json.load(open(a.validation_json))
    if freeze.get('status')!='FROZEN_DEV_MODEL_PARAMETERS_BEFORE_VALIDATION': raise RuntimeError('wrong frozen parameter artifact')
    if validation.get('primary_gate_status')!='PASS': raise RuntimeError('Validation did not authorize OOS')
    out={'status':'OOS_SCORED_WITH_ORIGINAL_DEV_FROZEN_Z4','oos_period_utc':['2025-08-01','2026-08-01'],'primary_feed':'BID','primary_endpoint':'REVISIT_240_ACTIVE_M1','model_training':'DEV through 2024-07-31 only; no Validation/OOS refit','source_manifest':manifest,'validation_gate_provenance':{'status':validation['primary_gate_status'],'bid_delta_brier':validation['feeds']['BID']['raw_primary']['delta_brier'],'validation_result_git_blob_expected':'d7a5120e58c9fa39c78d0453c417cd0694522e05'},'feeds':{}}
    out['feeds']['BID']=eval_feed(pd.read_pickle(a.bid_pkl),'BID',freeze)
    if a.ask_pkl: out['feeds']['ASK']=eval_feed(pd.read_pickle(a.ask_pkl),'ASK',freeze)
    b=out['feeds']['BID']; r=b['raw_primary']; ci=b['weekly']['bootstrap_95']; h1=b['halves']['H1_2025-08_to_2026-01']['delta_brier']; h2=b['halves']['H2_2026-02_to_2026-07']['delta_brier']; qa=b['qa']
    checks={'global_delta_brier_gt_0':bool(r['delta_brier']>0),'weekly_ci_lower_gt_0':bool(ci[0]>0),'global_delta_logloss_ge_0':bool(r['delta_logloss']>=0),'H1_delta_brier_ge_0':bool(h1>=0),'H2_delta_brier_ge_0':bool(h2>=0),'data_causal_qa_pass':bool(qa['all_features_present'] and qa['all_features_finite'] and qa['outcome_binary'])}
    out['primary_gate_checks']=checks; out['primary_gate_status']='PASS' if all(checks.values()) else 'FAIL'
    out['promotion_status']='P_REVISIT_240_REPLICATION_PASSED' if out['primary_gate_status']=='PASS' else 'NO_PREDICTIVE_SCORE_PROMOTION'
    Path(a.output).write_text(json.dumps(out,indent=2))
    print(json.dumps({'status':out['primary_gate_status'],'BID_raw':r,'weekly_95':ci,'halves':{'H1':h1,'H2':h2},'checks':checks,'ask_delta_brier':out['feeds'].get('ASK',{}).get('raw_primary',{}).get('delta_brier'),'calibration':b['calibrated_m0gl_diagnostic']},indent=2),flush=True)

if __name__=='__main__': main()
