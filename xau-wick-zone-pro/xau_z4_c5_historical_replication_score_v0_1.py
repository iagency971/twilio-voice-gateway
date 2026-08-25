import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

SEED=44
PERIODS={'H1':['2024-08-01','2025-08-01'],'H2':['2025-08-01','2026-08-01']}


def decorate(D):
    D=D.copy(); D['time']=pd.to_datetime(D.time,utc=True)
    D['log_age_active']=np.log1p(D.age_active_min); D['log_age_civil']=np.log1p(D.age_civil_min)
    D['log_prom']=np.log1p(D.prominence); D['log_bg']=np.log1p(D.background); D['log_strength']=np.log1p(D.strength_raw)
    D['log_mass']=np.log1p(D.mass); D['log_peak']=np.log1p(D.peak_height)
    D['log_mean_wick']=np.log1p(D.mean_wick); D['log_mean_body']=np.log1p(D.mean_body)
    return D


def weights(D):
    c=D.groupby('landmark_i').size(); return D.landmark_i.map((1.0/c).to_dict()).to_numpy(float)


def wmean(x,w):
    x=np.asarray(x,float); w=np.asarray(w,float); return float(np.sum(x*w)/np.sum(w))


def sigmoid(z):
    z=np.asarray(z,float); out=np.empty_like(z); pos=z>=0
    out[pos]=1/(1+np.exp(-z[pos])); e=np.exp(z[~pos]); out[~pos]=e/(1+e); return out


def predict(D,p):
    X=D[p['features']].to_numpy(float); mu=np.asarray(p['scaler_mean'],float); sd=np.asarray(p['scaler_scale'],float); co=np.asarray(p['coef'],float)
    if not np.isfinite(X).all(): raise RuntimeError('nonfinite features')
    return sigmoid(float(p['intercept'])+((X-mu)/sd)@co)


def score(D,p0,p1):
    w=weights(D); y=D.revisited.to_numpy(float); p0=np.clip(np.asarray(p0,float),1e-8,1-1e-8); p1=np.clip(np.asarray(p1,float),1e-8,1-1e-8)
    b0=wmean((p0-y)**2,w); b1=wmean((p1-y)**2,w)
    l0=wmean(-y*np.log(p0)-(1-y)*np.log(1-p0),w); l1=wmean(-y*np.log(p1)-(1-y)*np.log(1-p1),w)
    return {'M0_brier':b0,'M0GL_brier':b1,'delta_brier':float(b0-b1),'M0_logloss':l0,'M0GL_logloss':l1,'delta_logloss':float(l0-l1)}


def bootstrap(vals,n=10000):
    vals=np.asarray(vals,float); rng=np.random.default_rng(SEED); b=np.empty(n,float)
    for i in range(n): b[i]=rng.choice(vals,len(vals),replace=True).mean()
    return [float(vals.mean()),float(np.quantile(b,.025)),float(np.quantile(b,.975))]


def weekly(D,p0,p1):
    X=D[['time','landmark_i','revisited']].copy(); X['p0']=p0; X['p1']=p1
    X['week']=X.time.dt.tz_localize(None).dt.to_period('W-SUN').astype(str)
    rows=[]; vals=[]
    for wk,g in X.groupby('week',sort=True):
        s=score(g,g.p0.to_numpy(),g.p1.to_numpy()); vals.append(s['delta_brier']); rows.append({'week':wk,'n':int(len(g)),'landmarks':int(g.landmark_i.nunique()),'delta_brier':s['delta_brier'],'delta_logloss':s['delta_logloss']})
    bs=bootstrap(vals)
    return {'n_weeks':len(rows),'positive_weeks':int(sum(r['delta_brier']>0 for r in rows)),'mean_delta_brier':bs[0],'bootstrap_95':[bs[1],bs[2]],'weeks':rows}


def groups(D,p0,p1):
    masks={'BUY':D.side.to_numpy()<0,'SELL':D.side.to_numpy()>0,'US':D.landmark_us.to_numpy()==1,'NON_US':D.landmark_us.to_numpy()==0}
    out={}
    for k,m in masks.items():
        d=D.iloc[np.where(m)[0]]
        if len(d)<20: continue
        s=score(d,np.asarray(p0)[m],np.asarray(p1)[m]); out[k]={'n':int(len(d)),'rate':float(d.revisited.mean()),'delta_brier':s['delta_brier'],'delta_logloss':s['delta_logloss']}
    return out


def eval_feed(D,params):
    D=decorate(D); out={}
    for nm,(ss,ee) in PERIODS.items():
        s=pd.Timestamp(ss,tz='UTC'); e=pd.Timestamp(ee,tz='UTC'); X=D[(D.time>=s)&(D.time<e)].copy()
        if len(X)==0: raise RuntimeError(f'no rows {nm}')
        p0=predict(X,params['M0']); p1=predict(X,params['M0GL']); sc=score(X,p0,p1); wk=weekly(X,p0,p1)
        sc.update({'rows':int(len(X)),'landmarks':int(X.landmark_i.nunique()),'rate_unweighted':float(X.revisited.mean()),'weekly':wk,'groups':groups(X,p0,p1)})
        sc['primary_bid_rule_components']={'delta_brier_gt_0':bool(sc['delta_brier']>0),'delta_logloss_gt_0':bool(sc['delta_logloss']>0),'weekly_ci_lower_gt_0':bool(wk['bootstrap_95'][0]>0)}
        out[nm]=sc
    return out


def main():
    p=argparse.ArgumentParser(); p.add_argument('--bid-pkl',required=True); p.add_argument('--ask-pkl',required=True); p.add_argument('--frozen-json',required=True); p.add_argument('--source-manifest',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    frozen=json.load(open(a.frozen_json)); src=json.load(open(a.source_manifest))
    if frozen.get('status')!='FROZEN_C5_DEV_MODEL_PARAMETERS_BEFORE_CADENCE_HISTORICAL_REPLICATION': raise RuntimeError('bad model freeze status')
    B=eval_feed(pd.read_pickle(a.bid_pkl),frozen['feeds']['BID']); A=eval_feed(pd.read_pickle(a.ask_pkl),frozen['feeds']['ASK'])
    bid_pass={h:bool(all(B[h]['primary_bid_rule_components'].values())) for h in PERIODS}
    ask_support={h:bool(A[h]['delta_brier']>0 and A[h]['delta_logloss']>0) for h in PERIODS}
    overall=bool(all(bid_pass.values()) and all(ask_support.values()) and src.get('status')=='C5_HISTORICAL_REPLICATION_SOURCE_QA_PASS')
    out={'status':'C5_HISTORICAL_REPLICATION_COMPLETE','cadence_min':5,'lookback_active_m1':1440,'endpoint':'REVISIT_240_ACTIVE_M1','model_refit_after_dev':False,'calibration_refit':False,'periods':PERIODS,'source_manifest':src,'feeds':{'BID':B,'ASK':A},'gate':{'H1_BID_PRIMARY_PASS':bid_pass['H1'],'H2_BID_PRIMARY_PASS':bid_pass['H2'],'H1_ASK_SUPPORT_PASS':ask_support['H1'],'H2_ASK_SUPPORT_PASS':ask_support['H2'],'C5_HISTORICAL_REPLICATION_PASS':overall},'interpretation':'Historical temporal replication of a cadence hypothesis formulated after original C15 Validation/OOS were already known; not a pristine new independent holdout.'}
    Path(a.output).write_text(json.dumps(out,indent=2,allow_nan=False))
    print(json.dumps({'gate':out['gate'],'BID':{h:{k:B[h][k] for k in ['rows','landmarks','delta_brier','delta_logloss']}|{'weekly95':B[h]['weekly']['bootstrap_95']} for h in PERIODS},'ASK':{h:{k:A[h][k] for k in ['rows','landmarks','delta_brier','delta_logloss']}|{'weekly95':A[h]['weekly']['bootstrap_95']} for h in PERIODS}},indent=2))

if __name__=='__main__': main()
