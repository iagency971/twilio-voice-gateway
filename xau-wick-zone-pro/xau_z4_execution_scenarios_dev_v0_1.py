import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd

LOOKBACK=1440
HORIZON=240
REACT_H=(5,15,30,60)
EPS=1e-9


def parse():
    p=argparse.ArgumentParser()
    p.add_argument('--z4-pkl',required=True)
    p.add_argument('--raw-files',nargs='+',required=True)
    p.add_argument('--frozen-json',required=True)
    p.add_argument('--score-map-json',required=True)
    p.add_argument('--output',required=True)
    return p.parse_args()


def load_active(files):
    frames=[]
    for f in files:
        d=pd.read_csv(f)
        d['time']=pd.to_datetime(d.timestamp,unit='ms',utc=True)
        frames.append(d[['time','open','high','low','close']])
    d=pd.concat(frames,ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    return d[d.high>d.low].reset_index(drop=True)


def decorate(D):
    D=D.copy(); D['time']=pd.to_datetime(D.time,utc=True)
    D['log_age_active']=np.log1p(D.age_active_min); D['log_age_civil']=np.log1p(D.age_civil_min)
    D['log_prom']=np.log1p(D.prominence); D['log_bg']=np.log1p(D.background); D['log_strength']=np.log1p(D.strength_raw)
    D['log_mass']=np.log1p(D.mass); D['log_peak']=np.log1p(D.peak_height); D['log_mean_wick']=np.log1p(D.mean_wick); D['log_mean_body']=np.log1p(D.mean_body)
    return D


def sigmoid(x):
    x=np.asarray(x,float); out=np.empty_like(x); pos=x>=0
    out[pos]=1/(1+np.exp(-x[pos])); ex=np.exp(x[~pos]); out[~pos]=ex/(1+ex)
    return out


def predict_frozen(D,p):
    feats=p['features']; X=D[feats].to_numpy(float)
    mu=np.asarray(p['scaler_mean'],float); sd=np.asarray(p['scaler_scale'],float); coef=np.asarray(p['coef'],float)
    if not np.isfinite(X).all() or not (len(feats)==len(mu)==len(sd)==len(coef)):
        raise RuntimeError('frozen parameter / feature failure')
    return sigmoid(float(p['intercept'])+((X-mu)/sd)@coef)


def r_float(raw, thresholds):
    vals=np.asarray(thresholds,float)
    x=np.asarray(raw,float); out=np.empty_like(x)
    for j,v in enumerate(x):
        if v<=vals[0]: out[j]=0.0; continue
        if v>=vals[-1]: out[j]=100.0; continue
        k=int(np.searchsorted(vals,v,side='right')-1)
        den=vals[k+1]-vals[k]
        out[j]=float(k) if den<=0 else k+(v-vals[k])/den
    return out


def is_landmark(ts):
    return ts.minute%15==0 and ts.second==0


def fill_idx_for_level(A, start_i, end_i, level, side):
    if start_i>end_i: return None
    if side<0:
        hit=np.where(A.low.to_numpy()[start_i:end_i+1] <= level+EPS)[0]
    else:
        hit=np.where(A.high.to_numpy()[start_i:end_i+1] >= level-EPS)[0]
    return None if len(hit)==0 else start_i+int(hit[0])


def path_metrics(A, fill_i, level, side, v60):
    H=A.high.to_numpy(float); L=A.low.to_numpy(float)
    out={}
    for h in REACT_H:
        j=min(len(A)-1,fill_i+h)
        if side<0:
            fav=max(0.0,float(np.max(H[fill_i:j+1])-level))
            adv=max(0.0,float(level-np.min(L[fill_i:j+1])))
        else:
            fav=max(0.0,float(level-np.min(L[fill_i:j+1])))
            adv=max(0.0,float(np.max(H[fill_i:j+1])-level))
        vv=max(float(v60),1e-12)
        out[f'fav{h}_v']=fav/vv; out[f'adv{h}_v']=adv/vv
        out[f'dir{h}']=(fav-adv)/(fav+adv+EPS)
        out[f'fav_gt_adv{h}']=int(fav>adv)
    return out


def q(x,qv):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    return None if len(x)==0 else float(np.quantile(x,qv))


def summarize(df):
    if len(df)==0:
        return {'n_orders':0,'n_filled':0}
    fill=df.filled.to_numpy(int)==1
    o={'n_orders':int(len(df)),'n_filled':int(fill.sum()),'fill_rate':float(fill.mean())}
    if fill.any():
        F=df[fill]
        o['time_to_fill_active_m1']={'median':q(F.time_to_fill,0.5),'p90':q(F.time_to_fill,0.9)}
        o['filled_after_drop_rate_among_fills']=float(F.filled_after_drop.mean())
        o['R_at_order']={'median':q(F.R_float,0.5),'p25':q(F.R_float,0.25),'p75':q(F.R_float,0.75)}
        for h in REACT_H:
            o[f'h{h}']={
                'fav_v_mean':float(F[f'fav{h}_v'].mean()),
                'fav_v_median':q(F[f'fav{h}_v'],0.5),
                'adv_v_mean':float(F[f'adv{h}_v'].mean()),
                'adv_v_median':q(F[f'adv{h}_v'],0.5),
                'dir_mean':float(F[f'dir{h}'].mean()),
                'fav_gt_adv_rate':float(F[f'fav_gt_adv{h}'].mean())
            }
    return o


def main():
    a=parse()
    A=load_active(a.raw_files)
    Z=decorate(pd.read_pickle(a.z4_pkl)).sort_values(['landmark_i','center']).reset_index(drop=True)
    freeze=json.load(open(a.frozen_json)); smap=json.load(open(a.score_map_json))
    p=freeze['feeds']['BID']['M0GL']; raw=predict_frozen(Z,p)
    thresholds=[x['raw_threshold'] for x in smap['percentile_thresholds']]
    Z['raw_m0gl']=raw; Z['R_float']=r_float(raw,thresholds)

    eligible=[]
    for i,t in enumerate(A.time):
        if i<LOOKBACK-1 or i+HORIZON+60>=len(A): continue
        if is_landmark(t): eligible.append(i)
    eligible=np.asarray(eligible,dtype=int)
    elig_pos={int(v):j for j,v in enumerate(eligible)}

    last_lm=Z.groupby('lineage_id').landmark_i.max().to_dict()
    drop_i={}
    for lid,lm in last_lm.items():
        pos=elig_pos.get(int(lm))
        if pos is None or pos+1>=len(eligible): drop_i[int(lid)]=None
        else: drop_i[int(lid)]=int(eligible[pos+1])

    rows=[]
    levelspec={
        'E1_NEAR_EDGE_TOUCH': lambda r: r.zhi if r.side<0 else r.zlo,
        'E2_PEAK_LIMIT': lambda r: r.center,
        'E3_MID_LIMIT': lambda r: (r.zlo+r.zhi)/2.0,
        'E4_FAR_EDGE_LIMIT': lambda r: r.zlo if r.side<0 else r.zhi,
    }
    for r in Z.itertuples(index=False):
        i=int(r.landmark_i)
        if i+HORIZON>=len(A): continue
        horizon_end=i+HORIZON
        di=drop_i.get(int(r.lineage_id))
        for scen,fn in levelspec.items():
            lev=float(fn(r))
            fkeep=fill_idx_for_level(A,i+1,horizon_end,lev,int(r.side))
            c_end=horizon_end if di is None else min(horizon_end,int(di))
            fcancel=fill_idx_for_level(A,i+1,c_end,lev,int(r.side))
            for pol,fi in [('C1_CANCEL_ON_DROP',fcancel),('C2_KEEP_AFTER_DROP',fkeep)]:
                rec={
                    'scenario':scen,'policy':pol,'landmark_i':i,'time':str(r.time),
                    'lineage_id':int(r.lineage_id),'side':int(r.side),'level':lev,
                    'zlo':float(r.zlo),'zhi':float(r.zhi),'peak':float(r.center),
                    'R_float':float(r.R_float),'v60':float(r.tr),'drop_i':None if di is None else int(di),
                    'filled':int(fi is not None),'fill_i':None if fi is None else int(fi),
                    'time_to_fill':None if fi is None else int(fi-i),
                    'filled_after_drop':int(fi is not None and di is not None and fi>di),
                }
                if fi is not None: rec.update(path_metrics(A,fi,lev,int(r.side),float(r.tr)))
                else:
                    for h in REACT_H:
                        rec[f'fav{h}_v']=np.nan; rec[f'adv{h}_v']=np.nan; rec[f'dir{h}']=np.nan; rec[f'fav_gt_adv{h}']=np.nan
                rows.append(rec)
    R=pd.DataFrame(rows)

    secondary={}
    for name,col in [
        ('E5_PEAK_RECLAIM','reclaim_peak'),
        ('E6_FAR_SWEEP_FULL_RECLAIM_RETEST_ZONE','sweep_reclaim_full_retest_zone'),
        ('E6B_FAR_SWEEP_FULL_RECLAIM_RETEST_PEAK','sweep_reclaim_full_retest_peak')]:
        if col in Z.columns:
            secondary[name]={
                'n_zone_snapshots':int(len(Z)),
                'event_rate':float(Z[col].mean()),
                'BUY_rate':float(Z.loc[Z.side<0,col].mean()),
                'SELL_rate':float(Z.loc[Z.side>0,col].mean()),
                'US_rate':float(Z.loc[Z.landmark_us==1,col].mean()),
                'NON_US_rate':float(Z.loc[Z.landmark_us==0,col].mean()),
                'note':'Descriptive secondary branch only; not a validated trade rule.'
            }

    summaries={}
    for (s,poli),g in R.groupby(['scenario','policy'],sort=True): summaries[f'{s}__{poli}']=summarize(g)

    cancel_compare={}
    for s in levelspec:
        c=R[(R.scenario==s)&(R.policy=='C1_CANCEL_ON_DROP')].reset_index(drop=True)
        k=R[(R.scenario==s)&(R.policy=='C2_KEEP_AFTER_DROP')].reset_index(drop=True)
        assert len(c)==len(k)
        would_later=(c.filled.eq(0)&k.filled.eq(1))
        cc={
            'orders':int(len(c)),
            'cancel_policy_fill_rate':float(c.filled.mean()),
            'keep_policy_fill_rate':float(k.filled.mean()),
            'share_orders_lost_by_cancel_but_later_filled':float(would_later.mean()),
            'n_lost_by_cancel_but_later_filled':int(would_later.sum()),
        }
        if would_later.any():
            kk=k[would_later]
            for h in REACT_H:
                cc[f'c2_only_h{h}']={
                    'fav_v_mean':float(kk[f'fav{h}_v'].mean()),
                    'adv_v_mean':float(kk[f'adv{h}_v'].mean()),
                    'dir_mean':float(kk[f'dir{h}'].mean()),
                    'fav_gt_adv_rate':float(kk[f'fav_gt_adv{h}'].mean())
                }
        cancel_compare[s]=cc

    out={
        'status':'EXECUTION_DEV_SCREEN_COMPLETE_NO_TRADING_RULE_PROMOTION',
        'scope':'Dukascopy BID Jan-Jul 2024 exact Z4; execution hypotheses preregistered 2026-08-24 before this result',
        'unit':'every eligible Z4 zone snapshot; this is a scientific execution-screen unit, not yet de-duplicated trade ideas',
        'no_pnl_optimization':True,
        'n_z4_rows':int(len(Z)),
        'landmarks':int(Z.landmark_i.nunique()),
        'lineages':int(Z.lineage_id.nunique()),
        'scenario_summaries':summaries,
        'cancel_vs_keep':cancel_compare,
        'secondary_confirmation_branch':secondary,
        'interpretation_limits':[
            'Historical DEV screening only; not independent confirmation.',
            'No scenario is promoted to live trading from this screen alone.',
            'No SL/TP/RR/position sizing optimized.',
            'R remains revisit rank, not reaction probability.'
        ]
    }
    Path(a.output).write_text(json.dumps(out,indent=2,allow_nan=False))
    csv=Path(a.output).with_suffix('.csv'); R.to_csv(csv,index=False)
    print(json.dumps({'status':out['status'],'n_z4_rows':out['n_z4_rows'],'landmarks':out['landmarks'],'lineages':out['lineages'],'cancel_vs_keep':cancel_compare,'scenario_summaries':summaries,'secondary':secondary},indent=2,allow_nan=False))

if __name__=='__main__': main()
