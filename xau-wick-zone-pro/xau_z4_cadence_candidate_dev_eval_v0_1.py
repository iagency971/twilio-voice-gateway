import argparse, hashlib, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

FOLDS=[('APR','2024-04-01','2024-05-01'),
       ('MAY','2024-05-01','2024-06-01'),
       ('JUN','2024-06-01','2024-07-01'),
       ('JUL','2024-07-01','2024-08-01')]
SEED=44

def load_cm():
    here=Path(__file__).resolve().parent
    p=here/'xau_wick_zone_completion_models.py'
    spec=importlib.util.spec_from_file_location('z4cm',p)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

def finite_q(x,q):
    a=np.asarray(x,float); a=a[np.isfinite(a)]
    return None if len(a)==0 else float(np.quantile(a,q))

def geometry_hash(D):
    X=D.copy()
    X['time']=pd.to_datetime(X.time,utc=True)
    X=X[(X.time.dt.minute%15==0)&(X.time.dt.second==0)]
    X=X[['landmark_i','center','zlo','zhi','side']].sort_values(['landmark_i','center','zlo','zhi','side'])
    h=hashlib.sha256()
    for r in X.itertuples(index=False):
        h.update(f"{int(r.landmark_i)}|{float(r.center):.12f}|{float(r.zlo):.12f}|{float(r.zhi):.12f}|{int(r.side)}\n".encode())
    return {'sha256':h.hexdigest(),'rows':int(len(X)),'landmarks':int(X.landmark_i.nunique())}

def continuity_stats(D):
    if len(D)==0:
        return {'zone_snapshots':0}
    D=D.copy(); D['time']=pd.to_datetime(D.time,utc=True)
    zpl=D.groupby('landmark_i').size().to_numpy(int)
    lens=D.groupby('lineage_id').size().to_numpy(int)
    last_lm=int(D.landmark_i.max())
    denom=int((D.landmark_i<last_lm).sum())
    successful=int(np.maximum(lens-1,0).sum())
    cont=None if denom<=0 else float(successful/denom)
    life_active=D.groupby('lineage_id').age_active_min.max().to_numpy(float) if 'age_active_min' in D else np.array([])
    life_civil=D.groupby('lineage_id').age_civil_min.max().to_numpy(float) if 'age_civil_min' in D else np.array([])
    out={
        'zone_snapshots':int(len(D)),
        'represented_landmarks':int(D.landmark_i.nunique()),
        'lineages':int(D.lineage_id.nunique()),
        'zones_per_landmark':{
            'mean':float(np.mean(zpl)),'median':float(np.median(zpl)),
            'p90':float(np.quantile(zpl,.90)),'p95':float(np.quantile(zpl,.95)),
            'max':int(np.max(zpl))
        },
        'lineage_length_snapshots':{
            'mean':float(np.mean(lens)),'median':float(np.median(lens)),
            'p90':float(np.quantile(lens,.90)),'p95':float(np.quantile(lens,.95)),
            'max':int(np.max(lens))
        },
        'per_update_continuation_rate':cont,
        'per_update_drop_rate':None if cont is None else float(1-cont),
        'lineage_max_age_active_m1':{
            'median':finite_q(life_active,.5),'p90':finite_q(life_active,.9),'p95':finite_q(life_active,.95)
        },
        'lineage_max_age_civil_min':{
            'median':finite_q(life_civil,.5),'p90':finite_q(life_civil,.9),'p95':finite_q(life_civil,.95)
        }
    }
    for c,name in [('center_shift_vseg','abs_center_shift_vseg'),('width_log_change','abs_width_log_change')]:
        if c in D:
            x=np.abs(D[c].to_numpy(float))
            out[name]={'median':finite_q(x,.5),'p95':finite_q(x,.95)}
    return out

def common_anchor_stability(D):
    D=D.copy(); D['time']=pd.to_datetime(D.time,utc=True)
    C=D[(D.time.dt.minute%15==0)&(D.time.dt.second==0)].copy()
    out=continuity_stats(C)
    if len(C) and 'age_active_min' in C:
        x=C.age_active_min.to_numpy(float)
        out['snapshot_age_active_m1']={'median':finite_q(x,.5),'p90':finite_q(x,.9),'p95':finite_q(x,.95)}
    return out

def fit_fold(cm,tr,te):
    ref0,p0=cm.fit_binary(tr,te,cm.MODELS['M0'],'revisited')
    ref1,p1=cm.fit_binary(tr,te,cm.MODELS['M0GL'],'revisited')
    if len(ref0)!=len(ref1) or not np.array_equal(ref0.landmark_i.to_numpy(),ref1.landmark_i.to_numpy()):
        raise RuntimeError('M0/M0GL reference row mismatch')
    b0,l0=cm.binary_score(ref0,p0,'revisited')
    b1,l1=cm.binary_score(ref1,p1,'revisited')
    allm={'n':int(len(ref0)),'landmarks':int(ref0.landmark_i.nunique()),
          'M0_brier':float(b0),'M0GL_brier':float(b1),'delta_brier':float(b0-b1),
          'M0_logloss':float(l0),'M0GL_logloss':float(l1),'delta_logloss':float(l0-l1)}
    tt=pd.to_datetime(ref0.time,utc=True)
    mask=((tt.dt.minute%15==0)&(tt.dt.second==0)).to_numpy()
    C=ref0.iloc[np.where(mask)[0]].copy()
    cp0=np.asarray(p0)[mask]; cp1=np.asarray(p1)[mask]
    if len(C)==0:
        raise RuntimeError('no common-15 test rows')
    cb0,cl0=cm.binary_score(C,cp0,'revisited')
    cb1,cl1=cm.binary_score(C,cp1,'revisited')
    common={'n':int(len(C)),'landmarks':int(C.landmark_i.nunique()),
            'M0_brier':float(cb0),'M0GL_brier':float(cb1),'delta_brier':float(cb0-cb1),
            'M0_logloss':float(cl0),'M0GL_logloss':float(cl1),'delta_logloss':float(cl0-cl1)}
    O=ref0[['time','landmark_i','revisited']].copy()
    O['p0']=p0; O['p1']=p1
    OC=O.iloc[np.where(mask)[0]].copy()
    return allm,common,O,OC

def eval_feed(D,feed,cadence,cm):
    D=cm.decorate(D)
    folds={}; of=[]; oc=[]
    for name,start,end in FOLDS:
        s=pd.Timestamp(start,tz='UTC'); e=pd.Timestamp(end,tz='UTC')
        tr=D[D.time<s].copy(); te=D[(D.time>=s)&(D.time<e)].copy()
        if len(te)==0: raise RuntimeError(f'{feed} C{cadence} {name}: no test rows')
        a,c,o,q=fit_fold(cm,tr,te)
        folds[name]={'all_cadence':a,'common15':c}
        o['fold']=name; q['fold']=name; of.append(o); oc.append(q)
    O=pd.concat(of,ignore_index=True); C=pd.concat(oc,ignore_index=True)
    pa=cm.pooled_oof_score(O); wa=cm.weighted_weekly_oof(O)
    pc=cm.pooled_oof_score(C); wc=cm.weighted_weekly_oof(C)
    def compact(P,W):
        return {
            'n':int(P['n']),'landmarks':int(P['landmarks']),
            'M0_brier':float(P['M0_brier']),'M0GL_brier':float(P['M0GL_brier']),
            'delta_brier':float(P['delta_brier']),
            'M0_logloss':float(P['M0_logloss']),'M0GL_logloss':float(P['M0GL_logloss']),
            'delta_logloss':float(P['delta_logloss']),
            'weekly':{
                'n_weeks':int(W['n_weeks']),'positive_weeks':int(W['positive_weeks']),
                'mean_delta_brier':float(W['mean_delta_brier']),
                'bootstrap_95':[float(W['bootstrap_95'][0]),float(W['bootstrap_95'][1])]
            }
        }
    return {
        'feed':feed,'cadence_min':cadence,'rows':int(len(D)),
        'landmarks':int(D.landmark_i.nunique()),'lineages':int(D.lineage_id.nunique()),
        'folds':folds,'pooled_all_cadence':compact(pa,wa),'pooled_common15':compact(pc,wc),
        'geometry_common15':geometry_hash(D),
        'stability_per_update':continuity_stats(D),
        'stability_common15':common_anchor_stability(D),
    }

def flag(F,which):
    key='all_cadence' if which=='all' else 'common15'
    pooled=F['pooled_all_cadence'] if which=='all' else F['pooled_common15']
    return bool(
        all(F['folds'][m][key]['delta_brier']>0 for m,_,_ in FOLDS)
        and pooled['delta_brier']>0
        and pooled['weekly']['bootstrap_95'][0]>0
    )

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--bid-pkl',required=True); p.add_argument('--ask-pkl',required=True)
    p.add_argument('--cadence',required=True,type=int); p.add_argument('--engine-patch-json',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    if a.cadence not in {1,5,15}: raise RuntimeError('cadence not preregistered')
    cm=load_cm()
    bid=pd.read_pickle(a.bid_pkl); ask=pd.read_pickle(a.ask_pkl)
    print('CADENCE',a.cadence,'BID',flush=True)
    B=eval_feed(bid,'BID',a.cadence,cm)
    print('CADENCE',a.cadence,'ASK',flush=True)
    A=eval_feed(ask,'ASK',a.cadence,cm)
    br=flag(B,'all'); ar=flag(A,'all')
    bc=flag(B,'common'); ac=flag(A,'common')
    out={
        'status':'DEV_CADENCE_SENSITIVITY_CANDIDATE_COMPLETE_NO_PROMOTION',
        'cadence_min':a.cadence,
        'incumbent_control':bool(a.cadence==15),
        'lookback_active_m1':1440,
        'scientific_endpoint':'REVISIT_240',
        'frozen_reference_engine_git_blob':'a8a147615c3fd366c49e93b340fd2018b5b66e9e',
        'engine_patch_attestation':json.load(open(a.engine_patch_json)),
        'BID':B,'ASK':A,
        'preregistered_flags':{
            'BID_ROBUST_PASS':br,
            'DUAL_FEED_STRONG_PASS':bool(br and ar),
            'COMMON15_BID_ROBUST_PASS':bc,
            'COMMON15_DUAL_FEED_STRONG_PASS':bool(bc and ac)
        },
        'limits':[
            'DEV Jan-Jul 2024 only.',
            'No cadence is promoted by this file.',
            'C15 remains validated incumbent until later explicit decision.',
            'No Validation/OOS data used.',
            'Per-update churn is not directly comparable across 1m/5m/15m intervals.'
        ]
    }
    Path(a.output).write_text(json.dumps(out,indent=2,allow_nan=False))
    print(json.dumps({
        'cadence':a.cadence,
        'BID_all_delta':B['pooled_all_cadence']['delta_brier'],
        'ASK_all_delta':A['pooled_all_cadence']['delta_brier'],
        'BID_common_delta':B['pooled_common15']['delta_brier'],
        'ASK_common_delta':A['pooled_common15']['delta_brier'],
        'flags':out['preregistered_flags'],
        'BID_common_hash':B['geometry_common15']['sha256'],
        'ASK_common_hash':A['geometry_common15']['sha256']
    },indent=2),flush=True)

if __name__=='__main__':
    main()
