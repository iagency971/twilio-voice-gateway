import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

TOL_CENTER=1e-12
TOL_BOUND=1e-8


def common(D):
    X=D[['time','landmark_i','center','zlo','zhi','side']].copy()
    X['time']=pd.to_datetime(X.time,utc=True)
    X=X[(X.time.dt.minute%15==0)&(X.time.dt.second==0)].copy()
    return X.sort_values(['landmark_i','side','center','zlo','zhi']).reset_index(drop=True)


def q(x,p):
    a=np.asarray(x,float)
    return 0.0 if len(a)==0 else float(np.quantile(a,p))


def compare(a,b,label):
    A=common(pd.read_pickle(a)); B=common(pd.read_pickle(b))
    la=A.groupby('landmark_i').size(); lb=B.groupby('landmark_i').size()
    all_lm=sorted(set(la.index)|set(lb.index))
    bad_count=[int(i) for i in all_lm if int(la.get(i,0))!=int(lb.get(i,0))]
    out={
      'label':label,
      'rows_A':int(len(A)),'rows_B':int(len(B)),
      'landmarks_A':int(A.landmark_i.nunique()),'landmarks_B':int(B.landmark_i.nunique()),
      'bad_landmark_zone_count_n':int(len(bad_count)),
      'bad_landmark_zone_count_first10':bad_count[:10],
    }
    if len(A)!=len(B) or len(bad_count):
        out['GEOMETRY_PARITY_PASS']=False
        out['reason']='row_or_per_landmark_count_mismatch'
        return out
    # Per-landmark sorted rows ensure duplicate centers cannot silently reorder across groups.
    side_bad=0; center_err=[]; lo_err=[]; hi_err=[]; bad_center=0; bad_lo=0; bad_hi=0
    for lm in all_lm:
        aa=A[A.landmark_i==lm].sort_values(['side','center','zlo','zhi']).reset_index(drop=True)
        bb=B[B.landmark_i==lm].sort_values(['side','center','zlo','zhi']).reset_index(drop=True)
        sa=aa.side.to_numpy(int); sb=bb.side.to_numpy(int)
        side_bad += int(np.sum(sa!=sb))
        ce=np.abs(aa.center.to_numpy(float)-bb.center.to_numpy(float))
        le=np.abs(aa.zlo.to_numpy(float)-bb.zlo.to_numpy(float))
        he=np.abs(aa.zhi.to_numpy(float)-bb.zhi.to_numpy(float))
        center_err.extend(ce.tolist()); lo_err.extend(le.tolist()); hi_err.extend(he.tolist())
        bad_center += int(np.sum(ce>TOL_CENTER)); bad_lo += int(np.sum(le>TOL_BOUND)); bad_hi += int(np.sum(he>TOL_BOUND))
    out.update({
      'side_mismatch_rows':side_bad,
      'center_abs_error_usd':{'median':q(center_err,.5),'p99':q(center_err,.99),'max':q(center_err,1.0),'n_over_tol':bad_center,'tol':TOL_CENTER},
      'zlo_abs_error_usd':{'median':q(lo_err,.5),'p99':q(lo_err,.99),'max':q(lo_err,1.0),'n_over_tol':bad_lo,'tol':TOL_BOUND},
      'zhi_abs_error_usd':{'median':q(hi_err,.5),'p99':q(hi_err,.99),'max':q(hi_err,1.0),'n_over_tol':bad_hi,'tol':TOL_BOUND},
    })
    out['GEOMETRY_PARITY_PASS']=bool(side_bad==0 and bad_center==0 and bad_lo==0 and bad_hi==0 and len(A)==len(B) and A.landmark_i.nunique()==B.landmark_i.nunique())
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--bid-short',required=True); p.add_argument('--bid-15',required=True)
    p.add_argument('--ask-short',required=True); p.add_argument('--ask-15',required=True)
    p.add_argument('--cadence',type=int,required=True); p.add_argument('--output',required=True)
    a=p.parse_args()
    if a.cadence not in {1,5}: raise RuntimeError('short cadence must be 1 or 5')
    B=compare(a.bid_short,a.bid_15,f'BID_C{a.cadence}_vs_C15')
    A=compare(a.ask_short,a.ask_15,f'ASK_C{a.cadence}_vs_C15')
    out={
      'status':'OUTCOME_BLIND_CADENCE_GEOMETRY_PARITY_QA',
      'cadence_short':a.cadence,
      'lookback_active_m1':1440,
      'criteria':{'center_tol_usd':TOL_CENTER,'bound_tol_usd':TOL_BOUND,'same_rows_landmarks_counts':True,'same_side':True},
      'BID':B,'ASK':A,
      'GEOMETRY_PARITY_PASS':bool(B['GEOMETRY_PARITY_PASS'] and A['GEOMETRY_PARITY_PASS']),
      'outcomes_read':False,
    }
    Path(a.output).write_text(json.dumps(out,indent=2,allow_nan=False))
    print(json.dumps(out,indent=2,allow_nan=False))

if __name__=='__main__': main()
