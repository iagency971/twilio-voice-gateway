#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

SEED = 20260827
B = 1000
THRESHOLDS = np.array([0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90,0.95], float)
FEATURES = [
    'close_pos','body_frac','lower_wick_frac','upper_wick_frac',
    'log1p_lower_wick_to_body','range_v'
]
ALL_GEOM = FEATURES + [
    'low_penetration_zone_width','close_vs_center_zone_width',
    'close_vs_zhi_zone_width','body_zone_width'
]
OFFICIAL = {
    'H1': {'fired': 7127, 'tp_rate': 0.3143902095934731},
    'H2': {'fired': 7643, 'tp_rate': 0.3012963205447165},
}


def args():
    p=argparse.ArgumentParser()
    p.add_argument('--h1-contacts',required=True)
    p.add_argument('--h2-contacts',required=True)
    p.add_argument('--raw-dir',required=True)
    p.add_argument('--output-json',required=True)
    p.add_argument('--output-csv',required=True)
    return p.parse_args()


def load_raw(raw_dir: str) -> pd.DataFrame:
    parts=[]
    for f in sorted(Path(raw_dir).glob('xauusd_bid_m1_*.csv')):
        d=pd.read_csv(f)
        if 'timestamp' in d.columns:
            x=d['timestamp']
            if np.issubdtype(x.dtype,np.number):
                d['time']=pd.to_datetime(x,unit='ms',utc=True)
            else:
                d['time']=pd.to_datetime(x,utc=True)
        elif 'time' in d.columns:
            d['time']=pd.to_datetime(d['time'],utc=True)
        else:
            raise RuntimeError(f'no timestamp/time column in {f}')
        for c in ('open','high','low','close'):
            d[c]=pd.to_numeric(d[c],errors='coerce')
        parts.append(d[['time','open','high','low','close']])
    if not parts:
        raise RuntimeError('no raw files')
    raw=pd.concat(parts,ignore_index=True).dropna().sort_values('time').drop_duplicates('time',keep='last').reset_index(drop=True)
    return raw


def load_contacts(path: str) -> pd.DataFrame:
    d=pd.read_csv(path)
    d['contact_time']=pd.to_datetime(d['contact_time'],utc=True)
    need=['episode_id','contact_time','zlo','center','zhi','v_contact','tp1_zlo','slot_rank','family','zone_width_v']
    miss=[x for x in need if x not in d.columns]
    if miss: raise RuntimeError(f'missing contact columns {miss}')
    for c in ('zlo','center','zhi','v_contact','tp1_zlo','slot_rank','zone_width_v'):
        d[c]=pd.to_numeric(d[c],errors='coerce')
    return d.dropna(subset=['contact_time','zlo','center','zhi','v_contact','tp1_zlo']).copy()


def ny_end_ns(t: pd.Timestamp) -> int:
    ny=t.tz_convert('America/New_York')
    end=pd.Timestamp(year=ny.year,month=ny.month,day=ny.day,hour=17,tz='America/New_York').tz_convert('UTC')
    return int(end.value)


def outcome(arr, ex: int, end: int, tp: float, zlo: float):
    if ex>end: return ('NEITHER',None,None)
    hi=arr['high'][ex:end+1]
    cl=arr['close'][ex:end+1]
    ti=np.flatnonzero(hi>=tp)
    ii=np.flatnonzero(cl<zlo)
    t=int(ti[0]) if len(ti) else None
    i=int(ii[0]) if len(ii) else None
    if t is None and i is None: return ('NEITHER',None,None)
    if t is not None and i is not None:
        if t==i: return ('AMBIGUOUS',ex+t,ex+i)
        if t<i: return ('TP1_FIRST',ex+t,None)
        return ('INVALIDATION_FIRST',None,ex+i)
    if t is not None: return ('TP1_FIRST',ex+t,None)
    return ('INVALIDATION_FIRST',None,ex+i)


def make_candidate(contact, j, ex, arr, end):
    o=float(arr['open'][j]);h=float(arr['high'][j]);l=float(arr['low'][j]);c=float(arr['close'][j])
    rng=h-l; body=c-o
    if rng<=0 or body<=0: raise RuntimeError('candidate must be bullish positive-range')
    zlo=float(contact.zlo); zhi=float(contact.zhi); center=float(contact.center); width=max(zhi-zlo,1e-12); v=float(contact.v_contact)
    lw=o-l; uw=h-c
    exec_price=float(arr['open'][ex])
    st,tpj,invj=outcome(arr,ex,end,float(contact.tp1_zlo),zlo)
    tt=pd.Timestamp(arr['time'][j],tz='UTC')
    ct=pd.Timestamp(contact.contact_time)
    ny=tt.tz_convert('America/New_York')
    return {
        'episode_id':contact.episode_id,
        'contact_time':ct.isoformat(),
        'trigger_time':tt.isoformat(),
        'exec_time':pd.Timestamp(arr['time'][ex],tz='UTC').isoformat(),
        'session_id':ny.strftime('%Y-%m-%d'),
        'family':str(contact.family),'slot_rank':int(contact.slot_rank),
        'zlo':zlo,'center':center,'zhi':zhi,'v_contact':v,'tp1_zlo':float(contact.tp1_zlo),
        'zone_width_v':float(contact.zone_width_v),
        'exec_price':exec_price,'tp_distance_v':(float(contact.tp1_zlo)-exec_price)/v,
        'minutes_contact_to_trigger':(tt-ct).total_seconds()/60.0,
        'minutes_to_us_end':(pd.Timestamp(ny_end_ns(tt),tz='UTC')-tt).total_seconds()/60.0,
        'close_pos':(c-l)/rng,
        'body_frac':body/rng,
        'lower_wick_frac':lw/rng,
        'upper_wick_frac':uw/rng,
        'lower_wick_to_body':lw/max(body,1e-12),
        'log1p_lower_wick_to_body':math.log1p(lw/max(body,1e-12)),
        'range_v':rng/v,
        'low_penetration_zone_width':(zhi-l)/width,
        'close_vs_center_zone_width':(c-center)/width,
        'close_vs_zhi_zone_width':(c-zhi)/width,
        'body_zone_width':body/width,
        'status':st,
        'label':1 if st=='TP1_FIRST' else (0 if st in ('INVALIDATION_FIRST','NEITHER') else np.nan),
        'tp_idx':tpj,'inv_idx':invj,
    }


def replay(contacts: pd.DataFrame, raw: pd.DataFrame, sample: str):
    tns=raw.time.astype('int64').to_numpy()
    arr={c:raw[c].to_numpy(float) for c in ('open','high','low','close')}
    arr['time']=tns
    first=[]
    thr={float(c):[] for c in THRESHOLDS}
    reasons={float(c):{} for c in THRESHOLDS}
    first_reasons={}

    def add_reason(dic,k): dic[k]=dic.get(k,0)+1

    for contact in contacts.itertuples(index=False):
        q=int(pd.Timestamp(contact.contact_time).value)
        j0=int(np.searchsorted(tns,q,side='left'))
        if j0>=len(tns):
            add_reason(first_reasons,'NO_RAW_CONTACT'); continue
        end_ns=ny_end_ns(pd.Timestamp(contact.contact_time))
        end=int(np.searchsorted(tns,end_ns,side='left')-1)
        if end<j0:
            add_reason(first_reasons,'NO_SESSION_PATH'); continue
        pending=set(float(x) for x in THRESHOLDS)
        first_done=False
        stop_reason='TRIGGER_NOT_SEEN'
        for j in range(j0,end+1):
            tp_now=float(arr['high'][j])>=float(contact.tp1_zlo)
            inv_now=float(arr['close'][j])<float(contact.zlo)
            if inv_now:
                stop_reason='INVALIDATED_BEFORE_TRIGGER'; break
            if tp_now:
                stop_reason='TARGET_ALREADY_REACHED_BEFORE_TRIGGER'; break
            bullish=float(arr['close'][j])>float(arr['open'][j])
            if not bullish: continue
            rng=float(arr['high'][j]-arr['low'][j])
            cp=(float(arr['close'][j]-arr['low'][j])/rng) if rng>0 else 0.0
            ex=j+1
            exec_ok=ex<=end and int(tns[ex])<end_ns and float(arr['open'][ex])<float(contact.tp1_zlo)
            if not first_done:
                first_done=True
                if exec_ok:
                    first.append({'sample':sample,**make_candidate(contact,j,ex,arr,end)})
                else:
                    add_reason(first_reasons,'NO_NEXT_OPEN_OR_TARGET')
            for cth in list(pending):
                if cp>=cth:
                    pending.remove(cth)
                    if exec_ok:
                        thr[cth].append({'sample':sample,'threshold':cth,**make_candidate(contact,j,ex,arr,end)})
                    else:
                        add_reason(reasons[cth],'NO_NEXT_OPEN_OR_TARGET')
            if not pending and first_done:
                break
        if not first_done: add_reason(first_reasons,stop_reason)
        for cth in pending: add_reason(reasons[cth],stop_reason)
    return pd.DataFrame(first), {k:pd.DataFrame(v) for k,v in thr.items()}, first_reasons, reasons


def resolved(d): return d[d['label'].notna()].copy()


def rate_summary(d):
    if len(d)==0: return {'n':0}
    r=resolved(d); vc=d['status'].value_counts().to_dict()
    return {
        'n':int(len(d)),'resolved_n':int(len(r)),'resolved_share':float(len(r)/len(d)),
        'tp1':int(vc.get('TP1_FIRST',0)),'invalidation':int(vc.get('INVALIDATION_FIRST',0)),
        'neither':int(vc.get('NEITHER',0)),'ambiguous':int(vc.get('AMBIGUOUS',0)),
        'tp_rate':float(r.label.mean()) if len(r) else None,
        'invalidation_rate_resolved':float((r.status=='INVALIDATION_FIRST').mean()) if len(r) else None,
        'neither_rate_resolved':float((r.status=='NEITHER').mean()) if len(r) else None,
        'median_contact_to_trigger_min':float(d.minutes_contact_to_trigger.median()),
        'median_tp_distance_v':float(d.tp_distance_v.median()),
    }


def bootstrap_rate(d, sessions, B=B, rng=None):
    rng=np.random.default_rng(SEED) if rng is None else rng
    ss=np.asarray(sorted(sessions))
    g=d.groupby('session_id').label.agg(['sum','count']).reindex(ss,fill_value=0)
    pos=g['sum'].to_numpy(float); n=g['count'].to_numpy(float)
    vals=[]
    for _ in range(B):
        ix=rng.integers(0,len(ss),len(ss)); den=n[ix].sum()
        if den>0: vals.append(pos[ix].sum()/den)
    if not vals:return [None,None]
    return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))]


def bootstrap_diff(a,b,sessions,B=B,seed=SEED):
    rng=np.random.default_rng(seed); ss=np.asarray(sorted(sessions))
    ga=a.groupby('session_id').label.agg(['sum','count']).reindex(ss,fill_value=0)
    gb=b.groupby('session_id').label.agg(['sum','count']).reindex(ss,fill_value=0)
    pa,na=ga['sum'].to_numpy(float),ga['count'].to_numpy(float)
    pb,nb=gb['sum'].to_numpy(float),gb['count'].to_numpy(float)
    vals=[]
    for _ in range(B):
        ix=rng.integers(0,len(ss),len(ss)); da=na[ix].sum(); db=nb[ix].sum()
        if da>0 and db>0:vals.append(pa[ix].sum()/da-pb[ix].sum()/db)
    return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))] if vals else [None,None]


def auc_ci(d, pred_col, B=B, seed=SEED):
    rng=np.random.default_rng(seed); sessions=sorted(d.session_id.unique()); by={s:d[d.session_id==s] for s in sessions}; vals=[]
    for _ in range(B):
        pick=rng.integers(0,len(sessions),len(sessions)); z=pd.concat([by[sessions[i]] for i in pick],ignore_index=True)
        if z.label.nunique()<2:continue
        vals.append(roc_auc_score(z.label,z[pred_col]))
    return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))] if vals else [None,None]


def auc_diff_ci(d,p1,p0,B=B,seed=SEED+1):
    rng=np.random.default_rng(seed); sessions=sorted(d.session_id.unique()); by={s:d[d.session_id==s] for s in sessions}; vals=[]
    for _ in range(B):
        pick=rng.integers(0,len(sessions),len(sessions)); z=pd.concat([by[sessions[i]] for i in pick],ignore_index=True)
        if z.label.nunique()<2:continue
        vals.append(roc_auc_score(z.label,z[p1])-roc_auc_score(z.label,z[p0]))
    return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))] if vals else [None,None]


def threshold_best(x,y,weights=None):
    order=np.argsort(x,kind='mergesort'); xs=x[order]; ys=y[order]
    w=np.ones(len(xs),float) if weights is None else weights[order].astype(float)
    q20,q80=np.quantile(xs,[.2,.8]); splits=np.flatnonzero(np.r_[True,xs[1:]!=xs[:-1]])
    splits=splits[(xs[splits]>=q20)&(xs[splits]<=q80)&(splits>0)&(splits<len(xs))]
    cw=np.cumsum(w); cy=np.cumsum(w*ys); tw=cw[-1]; ty=cy[-1]
    n0=cw[splits-1]; y0=cy[splits-1]; n1=tw-n0; y1=ty-y0
    p0=np.clip(y0/np.maximum(n0,1e-12),1e-9,1-1e-9); p1=np.clip(y1/np.maximum(n1,1e-12),1e-9,1-1e-9)
    ll=y0*np.log(p0)+(n0-y0)*np.log(1-p0)+y1*np.log(p1)+(n1-y1)*np.log(1-p1)
    k=int(np.argmax(ll)); sp=int(splits[k])
    return float(xs[sp]),float(ll[k]),float(p0[k]),float(p1[k])


def threshold_bootstrap(d):
    d=d.reset_index(drop=True); x=d.close_pos.to_numpy(float); y=d.label.to_numpy(int); sessions=sorted(d.session_id.unique()); sm={s:i for i,s in enumerate(sessions)}; sid=np.array([sm[s] for s in d.session_id],int)
    rng=np.random.default_rng(SEED); vals=[]
    for _ in range(B):
        counts=np.bincount(rng.integers(0,len(sessions),len(sessions)),minlength=len(sessions)).astype(float)
        w=counts[sid]
        try: c,_,_,_=threshold_best(x,y,w); vals.append(c)
        except Exception: pass
    q=np.quantile(vals,[.1,.25,.5,.75,.9]) if vals else [np.nan]*5
    return {'n_boot':len(vals),'p10':float(q[0]),'p25':float(q[1]),'median':float(q[2]),'p75':float(q[3]),'p90':float(q[4]),'iqr':float(q[3]-q[1]),'p90_p10':float(q[4]-q[0]),'concentrated':bool((q[4]-q[0])<=.10 and (q[3]-q[1])<=.05)}


def cv_closepos(d):
    d=d.reset_index(drop=True); X=d[['close_pos']].to_numpy(float); y=d.label.to_numpy(int); groups=d.session_id.to_numpy(); gkf=GroupKFold(n_splits=5); cont=[]; thr=[]
    for tr,te in gkf.split(X,y,groups):
        sc=StandardScaler().fit(X[tr]); m=LogisticRegression(C=1.0,solver='lbfgs',max_iter=1000).fit(sc.transform(X[tr]),y[tr]); pc=m.predict_proba(sc.transform(X[te]))[:,1]
        cont.append(log_loss(y[te],pc,labels=[0,1]))
        c,_,p0,p1=threshold_best(X[tr,0],y[tr]); pt=np.where(X[te,0]>=c,p1,p0); thr.append(log_loss(y[te],np.clip(pt,1e-9,1-1e-9),labels=[0,1]))
    return {'continuous_mean_logloss':float(np.mean(cont)),'threshold_mean_logloss':float(np.mean(thr)),'continuous_folds':cont,'threshold_folds':thr}


def feature_analysis(h1,h2):
    out={}; sessions2=sorted(h2.session_id.unique())
    for feat in ALL_GEOM:
        x1=h1[feat].to_numpy(float); x2=h2[feat].to_numpy(float); y1=h1.label.to_numpy(int); y2=h2.label.to_numpy(int)
        mu=float(np.mean(x1)); sd=float(np.std(x1)) or 1.0
        m=LogisticRegression(C=1.0,solver='lbfgs',max_iter=1000).fit(((x1-mu)/sd).reshape(-1,1),y1)
        p1=m.predict_proba(((x1-mu)/sd).reshape(-1,1))[:,1]; p2=m.predict_proba(((x2-mu)/sd).reshape(-1,1))[:,1]
        orient=1.0 if float(m.coef_[0,0])>=0 else -1.0
        tmp2=h2[['session_id','label']].copy(); tmp2['oriented']=orient*x2
        q20,q80=np.quantile(x1,[.2,.8]);
        if orient>0:
            bot1=h1[x1<=q20];top1=h1[x1>=q80];bot2=h2[x2<=q20];top2=h2[x2>=q80]
        else:
            bot1=h1[x1>=q80];top1=h1[x1<=q20];bot2=h2[x2>=q80];top2=h2[x2<=q20]
        out[feat]={
            'h1_raw_auc':float(roc_auc_score(y1,x1)),'h2_raw_auc':float(roc_auc_score(y2,x2)),
            'h1_oriented_auc':float(roc_auc_score(y1,orient*x1)),'h2_oriented_auc':float(roc_auc_score(y2,orient*x2)),
            'h2_oriented_auc_ci':auc_ci(tmp2,'oriented'),
            'h1_logistic_slope_standardized':float(m.coef_[0,0]),
            'h1_frozen_logistic_auc':float(roc_auc_score(y1,p1)),'h2_frozen_logistic_auc':float(roc_auc_score(y2,p2)),
            'h1_top_bottom_rate_diff':float(top1.label.mean()-bot1.label.mean()),
            'h2_top_bottom_rate_diff':float(top2.label.mean()-bot2.label.mean()),
            'h2_top_bottom_diff_ci':bootstrap_diff(top2,bot2,sessions2),
            'h1_cut_q20':float(q20),'h1_cut_q80':float(q80),
        }
    return out


def decile_maps(h1,h2):
    res={}; sessions1=sorted(h1.session_id.unique()); sessions2=sorted(h2.session_id.unique())
    for feat in ALL_GEOM:
        cuts=np.unique(np.quantile(h1[feat].to_numpy(float),np.linspace(0,1,11)))
        if len(cuts)<3:continue
        internal=cuts[1:-1]
        a=h1.copy();b=h2.copy();a['bin']=np.digitize(a[feat],internal,right=False);b['bin']=np.digitize(b[feat],internal,right=False)
        rows=[]
        for bi in range(len(cuts)-1):
            aa=a[a.bin==bi];bb=b[b.bin==bi]
            rows.append({'bin':bi,'lo':float(cuts[bi]),'hi':float(cuts[bi+1]),'h1_n':len(aa),'h1_rate':float(aa.label.mean()) if len(aa) else None,'h1_ci':bootstrap_rate(aa,sessions1),'h2_n':len(bb),'h2_rate':float(bb.label.mean()) if len(bb) else None,'h2_ci':bootstrap_rate(bb,sessions2)})
        res[feat]=rows
    return res


def multivar(h1,h2):
    X1=h1[FEATURES].to_numpy(float);X2=h2[FEATURES].to_numpy(float);y1=h1.label.to_numpy(int);y2=h2.label.to_numpy(int)
    sc=StandardScaler().fit(X1);m=LogisticRegression(C=1.0,solver='lbfgs',max_iter=2000).fit(sc.transform(X1),y1);p1=m.predict_proba(sc.transform(X1))[:,1];p2=m.predict_proba(sc.transform(X2))[:,1]
    sc0=StandardScaler().fit(h1[['close_pos']]);m0=LogisticRegression(C=1.0,solver='lbfgs',max_iter=1000).fit(sc0.transform(h1[['close_pos']]),y1);p20=m0.predict_proba(sc0.transform(h2[['close_pos']]))[:,1]
    z=h2[['session_id','label']].copy();z['multi']=p2;z['closeonly']=p20
    return {
        'coefficients':{f:float(c) for f,c in zip(FEATURES,m.coef_[0])},
        'h1':{'auc':float(roc_auc_score(y1,p1)),'ap':float(average_precision_score(y1,p1)),'brier':float(brier_score_loss(y1,p1))},
        'h2':{'auc':float(roc_auc_score(y2,p2)),'ap':float(average_precision_score(y2,p2)),'brier':float(brier_score_loss(y2,p2)),'auc_ci':auc_ci(z,'multi'),'closeonly_auc':float(roc_auc_score(y2,p20)),'auc_delta_vs_closeonly':float(roc_auc_score(y2,p2)-roc_auc_score(y2,p20)),'auc_delta_ci':auc_diff_ci(z,'multi','closeonly')},
    }


def threshold_curve(thr, total_contacts):
    rows=[];prev=None
    for c in THRESHOLDS:
        d=thr[float(c)];s=rate_summary(d);s['threshold']=float(c);s['fired_share']=float(len(d)/total_contacts)
        if prev is not None:
            s['delta_fired_share_vs_prev']=s['fired_share']-prev['fired_share'];s['delta_tp_rate_vs_prev']=(s['tp_rate']-prev['tp_rate']) if s.get('tp_rate') is not None and prev.get('tp_rate') is not None else None
        else:s['delta_fired_share_vs_prev']=None;s['delta_tp_rate_vs_prev']=None
        rows.append(s);prev=s
    return rows


def main():
    a=args();raw=load_raw(a.raw_dir);h1c=load_contacts(a.h1_contacts);h2c=load_contacts(a.h2_contacts)
    h1,th1,r1,rr1=replay(h1c,raw,'H1');h2,th2,r2,rr2=replay(h2c,raw,'H2')
    h1r=resolved(h1);h2r=resolved(h2)
    if len(h1r)<1000 or len(h2r)<1000:raise RuntimeError('too few FIRST_BULL resolved observations')
    c1=threshold_curve(th1,len(h1c));c2=threshold_curve(th2,len(h2c))
    p70_1=next(x for x in c1 if abs(x['threshold']-.70)<1e-12);p70_2=next(x for x in c2 if abs(x['threshold']-.70)<1e-12)
    parity={
      'H1_fired':p70_1['n']==OFFICIAL['H1']['fired'],'H1_rate':abs(p70_1['tp_rate']-OFFICIAL['H1']['tp_rate'])<1e-12,
      'H2_fired':p70_2['n']==OFFICIAL['H2']['fired'],'H2_rate':abs(p70_2['tp_rate']-OFFICIAL['H2']['tp_rate'])<1e-12,
    }
    parity_pass=all(parity.values())
    result={'status':'PARITY_FAIL' if not parity_pass else 'BULL_CANDLE_GEOMETRY_COMPLETE','parity':parity,'parity_pass':parity_pass,
            'contacts':{'H1':len(h1c),'H2':len(h2c)},'first_bull':{'H1':rate_summary(h1),'H2':rate_summary(h2),'H1_nonfire':r1,'H2_nonfire':r2},
            'wait_threshold_curve':{'H1':c1,'H2':c2},'wait_threshold_nonfire':{'H1':rr1,'H2':rr2}}
    if parity_pass:
        fa=feature_analysis(h1r,h2r);dm=decile_maps(h1r,h2r);mv=multivar(h1r,h2r)
        c,ll,p0,p1=threshold_best(h1r.close_pos.to_numpy(float),h1r.label.to_numpy(int));tb=threshold_bootstrap(h1r);cv=cv_closepos(h1r)
        above=h2r[h2r.close_pos>=c];below=h2r[h2r.close_pos<c];tdiff=bootstrap_diff(above,below,sorted(h2r.session_id.unique()))
        cp=fa['close_pos'];continuous=bool(cp['h2_oriented_auc_ci'][0] is not None and cp['h2_oriented_auc_ci'][0]>.5 and cp['h2_top_bottom_diff_ci'][0] is not None and cp['h2_top_bottom_diff_ci'][0]>0)
        multi=bool(mv['h2']['auc_ci'][0]>.5 and mv['h2']['auc_delta_ci'][0]>0)
        change=bool(tb['concentrated'] and (float(above.label.mean())>float(below.label.mean())) and tdiff[0]>0 and cv['threshold_mean_logloss']<cv['continuous_mean_logloss'])
        anygeom=continuous
        if not anygeom:
            for f,v in fa.items():
                if v['h2_oriented_auc_ci'][0] is not None and v['h2_oriented_auc_ci'][0]>.5 and v['h2_top_bottom_diff_ci'][0] is not None and v['h2_top_bottom_diff_ci'][0]>0:
                    anygeom=True;break
        classification='MULTIVARIATE_REJECTION_GEOMETRY' if multi else ('STABLE_CLOSEPOS_CHANGEPOINT_CANDIDATE' if change else ('CONTINUOUS_GEOMETRY_SIGNAL' if anygeom else 'NO_GEOMETRY_SIGNAL'))
        result.update({'feature_analysis':fa,'decile_maps':dm,'multivariate':mv,'closepos_change_point':{'h1_point':c,'h1_loglik':ll,'h1_below_rate':p0,'h1_above_rate':p1,'bootstrap':tb,'cv':cv,'h2_above_n':len(above),'h2_below_n':len(below),'h2_above_rate':float(above.label.mean()),'h2_below_rate':float(below.label.mean()),'h2_above_minus_below':float(above.label.mean()-below.label.mean()),'h2_diff_ci':tdiff},'classification':classification,'classification_flags':{'multivariate':multi,'stable_changepoint':change,'continuous_closepos':continuous,'any_geometry':anygeom},'explicit_nonclaim':'H2 is retrospective replication, not pristine OOS; no Pine change authorized.'})
    pd.concat([h1,h2],ignore_index=True).to_csv(a.output_csv,index=False)
    Path(a.output_json).write_text(json.dumps(result,indent=2,sort_keys=True,default=str),encoding='utf-8')
    print(json.dumps({'status':result['status'],'parity':parity,'classification':result.get('classification')},indent=2))

if __name__=='__main__':main()
