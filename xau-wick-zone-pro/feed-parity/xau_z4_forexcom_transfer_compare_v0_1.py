#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import pearsonr,spearmanr

LOOKBACK=1440
WARMUP_C5=96
STEP=.01


def parse():
    p=argparse.ArgumentParser()
    p.add_argument('--forex-csv',required=True)
    p.add_argument('--duka-csv',required=True)
    p.add_argument('--duka-mid-pkl',required=True)
    p.add_argument('--duka-bid-pkl',required=True)
    p.add_argument('--forex-pkl',required=True)
    p.add_argument('--frozen-json',required=True)
    p.add_argument('--rmap-json',required=True)
    p.add_argument('--output',required=True)
    return p.parse_args()


def q(x, ps=(.1,.5,.9,.95,.99)):
    a=np.asarray(x,float)
    a=a[np.isfinite(a)]
    return {str(v):(float(np.quantile(a,v)) if len(a) else None) for v in ps}


def iou(a0,a1,b0,b1):
    inter=max(0.0,min(a1,b1)-max(a0,b0))
    union=max(a1,b1)-min(a0,b0)
    return inter/union if union>0 else 0.0


def safe_corr(a,b,kind='pearson'):
    a=np.asarray(a,float);b=np.asarray(b,float);m=np.isfinite(a)&np.isfinite(b)
    if m.sum()<3:return None
    if kind=='pearson': return float(pearsonr(a[m],b[m]).statistic)
    return float(spearmanr(a[m],b[m]).statistic)


def load_forex(path):
    d=pd.read_csv(path,compression='infer')
    d['time']=pd.to_datetime(d['timestamp_utc'],utc=True)
    for c in ['open','high','low','close']: d[c]=pd.to_numeric(d[c],errors='coerce')
    return d[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time').reset_index(drop=True)


def load_duka(path,mode):
    d=pd.read_csv(path); d['time']=pd.to_datetime(d['timestamp'],utc=True)
    if mode=='mid': cols=['open','high','low','close']
    elif mode=='bid': cols=['open_bid','high_bid','low_bid','close_bid']
    else: raise ValueError(mode)
    out=pd.DataFrame({'time':d.time})
    for src,dst in zip(cols,['open','high','low','close']):out[dst]=pd.to_numeric(d[src],errors='coerce')
    return out.dropna().sort_values('time').drop_duplicates('time').reset_index(drop=True)


def active(d):
    return d[(d.high>d.low)&np.isfinite(d.open)&np.isfinite(d.high)&np.isfinite(d.low)&np.isfinite(d.close)].copy().reset_index(drop=True)


def mature_time(d):
    a=active(d)
    if len(a)<LOOKBACK+WARMUP_C5*4:return None
    e=a.iloc[LOOKBACK-1:].copy()
    e=e[(e.time.dt.minute%5==0)&(e.time.dt.second==0)].reset_index(drop=True)
    if len(e)<WARMUP_C5:return None
    return pd.Timestamp(e.iloc[WARMUP_C5-1].time)


def raw_metrics(ref,tgt):
    R=active(ref);T=active(tgt)
    lo=max(R.time.min(),T.time.min()); hi=min(R.time.max(),T.time.max())
    R=R[(R.time>=lo)&(R.time<=hi)];T=T[(T.time>=lo)&(T.time<=hi)]
    M=R.merge(T,on='time',how='inner',suffixes=('_ref','_tgt')).sort_values('time').reset_index(drop=True)
    coverage=float(len(M)/len(T)) if len(T) else 0.0
    dt=M.time.diff().dt.total_seconds(); consec=dt.eq(60)
    dr=M.close_ref.diff();dtgt=M.close_tgt.diff(); mr=consec&dr.notna()&dtgt.notna()
    gaps={}
    for c in ['open','high','low','close']:
        x=M[f'{c}_tgt']-M[f'{c}_ref'];gaps[c]={'signed_median':float(np.median(x)),'abs_quantiles':q(np.abs(x),(.5,.9,.95,.99))}
    retp=safe_corr(dr[mr],dtgt[mr],'pearson'); rets=safe_corr(dr[mr],dtgt[mr],'spearman')
    rr=(M.high_ref-M.low_ref);tr=(M.high_tgt-M.low_tgt)
    return {
      'window_utc':[str(lo),str(hi)],'reference_active_rows':int(len(R)),'target_active_rows':int(len(T)),'common_active_rows':int(len(M)),
      'target_timestamp_coverage':coverage,'consecutive_return_pairs':int(mr.sum()),'return_pearson':retp,'return_spearman':rets,
      'bar_range_pearson':safe_corr(rr,tr,'pearson'),'bar_range_spearman':safe_corr(rr,tr,'spearman'),'price_gap':gaps
    },set(M.time.tolist())


def decorate(D,params,thresholds):
    D=D.copy();D['time']=pd.to_datetime(D.time,utc=True)
    D['log_age_active']=np.log1p(D.age_active_min);D['log_age_civil']=np.log1p(D.age_civil_min)
    D['log_prom']=np.log1p(D.prominence);D['log_bg']=np.log1p(D.background);D['log_strength']=np.log1p(D.strength_raw)
    D['log_mass']=np.log1p(D.mass);D['log_peak']=np.log1p(D.peak_height);D['log_mean_wick']=np.log1p(D.mean_wick);D['log_mean_body']=np.log1p(D.mean_body)
    X=D[params['features']].to_numpy(float);mu=np.asarray(params['scaler_mean'],float);sd=np.asarray(params['scaler_scale'],float);coef=np.asarray(params['coef'],float)
    if not np.isfinite(X).all():raise RuntimeError('non-finite frozen-model features')
    z=float(params['intercept'])+((X-mu)/sd)@coef
    score=np.empty(len(z),float);pos=z>=0;score[pos]=1/(1+np.exp(-z[pos]));ez=np.exp(z[~pos]);score[~pos]=ez/(1+ez)
    D['score_raw']=score
    T=np.asarray(thresholds,float);x=score;rf=np.zeros(len(x),float);rf[x>=T[-1]]=100.;mid=(x>T[0])&(x<T[-1]);xx=x[mid];k=np.searchsorted(T,xx,side='right')-1;k=np.clip(k,0,99);lo=T[k];hi=T[k+1];rf[mid]=k+(xx-lo)/np.maximum(hi-lo,1e-20)
    D['r_float']=rf;D['r_display']=np.floor(rf+.5).astype(int)
    return D


def match_pair(ref_z,tgt_z,ref_raw,tgt_raw,common_times,eval_start,params,thresholds,label):
    R=decorate(pd.read_pickle(ref_z),params,thresholds).reset_index(drop=True)
    T=decorate(pd.read_pickle(tgt_z),params,thresholds).reset_index(drop=True)
    common={pd.Timestamp(t) for t in common_times}
    R=R[(R.time>=eval_start)&R.time.isin(common)].copy().reset_index(drop=True)
    T=T[(T.time>=eval_start)&T.time.isin(common)].copy().reset_index(drop=True)
    rc=active(ref_raw).set_index('time').close.to_dict();tc=active(tgt_raw).set_index('time').close.to_dict()
    # Mature common C5 times only.
    valid_times=sorted(t for t in common if t>=eval_start and t.minute%5==0 and t.second==0)
    valid_set=set(valid_times);R=R[R.time.isin(valid_set)].reset_index(drop=True);T=T[T.time.isin(valid_set)].reset_index(drop=True)
    RG={(pd.Timestamp(tm),int(side)):g.index.to_numpy(np.int64) for (tm,side),g in R.groupby(['time','side'],sort=True)}
    TG={(pd.Timestamp(tm),int(side)):g.index.to_numpy(np.int64) for (tm,side),g in T.groupby(['time','side'],sort=True)}
    pairs=[];matched_r=set();matched_t=set();map_rt={}
    for key in sorted(set(RG)|set(TG),key=lambda x:(x[0],x[1])):
        ri=RG.get(key,np.array([],dtype=np.int64));ti=TG.get(key,np.array([],dtype=np.int64))
        if not len(ri) or not len(ti):continue
        tm=key[0];cr=float(rc[tm]);ct=float(tc[tm])
        cost=np.full((len(ri),len(ti)),1e9,float);okm=np.zeros_like(cost,dtype=bool)
        for a,ridx in enumerate(ri):
            rr=R.loc[ridx];rw=max(float(rr.zhi-rr.zlo),STEP);r0=float(rr.zlo-cr);r1=float(rr.zhi-cr);rcen=float(rr.center-cr)
            for b,tidx in enumerate(ti):
                tr=T.loc[tidx];tw=max(float(tr.zhi-tr.zlo),STEP);t0=float(tr.zlo-ct);t1=float(tr.zhi-ct);tcen=float(tr.center-ct);vs=max(float(rr.vseg),float(tr.vseg),STEP)
                cd=abs(rcen-tcen);ov=iou(r0,r1,t0,t1);good=(cd<=vs) or (ov>0)
                if good:okm[a,b]=True;cost[a,b]=cd/vs+.5*(1-ov)+.1*abs(math.log(tw/rw))
        aa,bb=linear_sum_assignment(cost)
        for a,b in zip(aa,bb):
            if not okm[a,b] or cost[a,b]>=1e8:continue
            ridx=int(ri[a]);tidx=int(ti[b]);rr=R.loc[ridx];tr=T.loc[tidx];vs=max(float(rr.vseg),float(tr.vseg),STEP)
            r0=float(rr.zlo-cr);r1=float(rr.zhi-cr);t0=float(tr.zlo-ct);t1=float(tr.zhi-ct)
            relov=iou(r0,r1,t0,t1);absov=iou(float(rr.zlo),float(rr.zhi),float(tr.zlo),float(tr.zhi))
            rec={'time':str(tm),'side':int(key[1]),'ridx':ridx,'tidx':tidx,'rel_iou':relov,'abs_iou':absov,
                 'rel_center_err_vseg':abs((float(rr.center)-cr)-(float(tr.center)-ct))/vs,'abs_center_err_vseg':abs(float(rr.center)-float(tr.center))/vs,
                 'score_ref':float(rr.score_raw),'score_tgt':float(tr.score_raw),'score_abs_err':abs(float(rr.score_raw)-float(tr.score_raw)),
                 'r_ref':float(rr.r_float),'r_tgt':float(tr.r_float),'rd_ref':int(rr.r_display),'rd_tgt':int(tr.r_display)}
            pairs.append(rec);matched_r.add(ridx);matched_t.add(tidx);map_rt[ridx]=tidx
    M=pd.DataFrame(pairs)
    if len(M)<100:return {'status':'INSUFFICIENT','label':label,'reason':f'too few matched mature zones: {len(M)}','reference_rows':len(R),'target_rows':len(T)}
    top=[]
    for tm in sorted(set(R.time)&set(T.time)):
        er=R[R.time==tm];et=T[T.time==tm]
        if not len(er) or not len(et):continue
        rtop=int(er.score_raw.idxmax());ttop=int(et.score_raw.idxmax());top.append(map_rt.get(rtop,-1)==ttop)
    rd=np.abs(M.rd_ref.to_numpy(int)-M.rd_tgt.to_numpy(int));rf=np.abs(M.r_ref-M.r_tgt)
    metrics={
      'reference_rows':int(len(R)),'target_rows':int(len(T)),'matched_pairs':int(len(M)),
      'reference_zone_match_rate':float(len(matched_r)/len(R)) if len(R) else 0.0,'target_zone_match_rate':float(len(matched_t)/len(T)) if len(T) else 0.0,
      'relative_iou_quantiles':q(M.rel_iou,(.1,.25,.5,.75,.9,.95)),'absolute_iou_quantiles':q(M.abs_iou,(.1,.5,.9,.95)),
      'relative_center_err_vseg_quantiles':q(M.rel_center_err_vseg,(.5,.9,.95,.99)),'absolute_center_err_vseg_quantiles':q(M.abs_center_err_vseg,(.5,.9,.95,.99)),
      'score_pearson':safe_corr(M.score_ref,M.score_tgt,'pearson'),'score_spearman':safe_corr(M.score_ref,M.score_tgt,'spearman'),'score_abs_err_quantiles':q(M.score_abs_err,(.5,.9,.95,.99)),
      'r_pearson':safe_corr(M.r_ref,M.r_tgt,'pearson'),'r_spearman':safe_corr(M.r_ref,M.r_tgt,'spearman'),'r_float_abs_err_quantiles':q(rf,(.5,.9,.95,.99)),
      'share_display_r_within_5':float(np.mean(rd<=5)),'share_display_r_within_10':float(np.mean(rd<=10)),'share_display_r_within_20':float(np.mean(rd<=20)),
      'top1_zone_agreement':float(np.mean(top)) if top else None,'top1_landmarks':int(len(top)),'eval_start_utc':str(eval_start),'common_mature_c5_times':int(len(valid_times))
    }
    checks={
      'reference_zone_match_ge_080':metrics['reference_zone_match_rate']>=.80,
      'target_zone_match_ge_080':metrics['target_zone_match_rate']>=.80,
      'median_relative_iou_ge_070':metrics['relative_iou_quantiles']['0.5']>=.70,
      'p10_relative_iou_ge_030':metrics['relative_iou_quantiles']['0.1']>=.30,
      'median_relative_center_err_le_025_vseg':metrics['relative_center_err_vseg_quantiles']['0.5']<=.25,
      'p95_relative_center_err_le_075_vseg':metrics['relative_center_err_vseg_quantiles']['0.95']<=.75,
      'score_spearman_ge_090':metrics['score_spearman'] is not None and metrics['score_spearman']>=.90,
      'median_score_abs_err_le_007':metrics['score_abs_err_quantiles']['0.5']<=.07,
      'p95_score_abs_err_le_020':metrics['score_abs_err_quantiles']['0.95']<=.20,
      'top1_ge_070':metrics['top1_zone_agreement'] is not None and metrics['top1_zone_agreement']>=.70,
      'r_spearman_ge_090':metrics['r_spearman'] is not None and metrics['r_spearman']>=.90,
      'share_display_within10_ge_080':metrics['share_display_r_within_10']>=.80,
      'share_display_within20_ge_095':metrics['share_display_r_within_20']>=.95,
    }
    return {'status':'PASS' if all(checks.values()) else 'FAIL','label':label,'metrics':metrics,'checks':checks,'matched_records':pairs}


def strip_records(x):
    y=dict(x);y.pop('matched_records',None);return y


def main():
    a=parse();F=load_forex(a.forex_csv);DM=load_duka(a.duka_csv,'mid');DB=load_duka(a.duka_csv,'bid')
    # Match the civil window to the FOREXCOM depth sample; do not give Dukascopy extra prehistory.
    lo=F.time.min();hi=F.time.max();DM=DM[(DM.time>=lo)&(DM.time<=hi)].reset_index(drop=True);DB=DB[(DB.time>=lo)&(DB.time<=hi)].reset_index(drop=True)
    raw_mid,common_mid=raw_metrics(DM,F);raw_bid,common_bid=raw_metrics(DB,F)
    freeze=json.load(open(a.frozen_json));params=freeze['feeds']['BID']['M0GL'];rmap=json.load(open(a.rmap_json));thr=[x['raw_threshold'] for x in rmap['percentile_thresholds']]
    mt_mid=mature_time(DM);mt_bid=mature_time(DB);mt_f=mature_time(F)
    if mt_mid is None or mt_bid is None or mt_f is None:
        out={'status':'PILOT_INSUFFICIENT_DATA','future_outcomes_used':False,'raw_mid_vs_forex':raw_mid,'raw_bid_vs_forex':raw_bid,'mature_times':{'duka_mid':str(mt_mid),'duka_bid':str(mt_bid),'forex':str(mt_f)}}
        Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));return
    primary_start=max(mt_mid,mt_f);control_start=max(mt_bid,mt_f)
    primary=match_pair(a.duka_mid_pkl,a.forex_pkl,DM,F,common_mid,primary_start,params,thr,'DUKASCOPY_SYNTH_MID__FOREXCOM_MID')
    control=match_pair(a.duka_bid_pkl,a.forex_pkl,DB,F,common_bid,control_start,params,thr,'DUKASCOPY_BID__FOREXCOM_MID')
    raw_checks={'target_timestamp_coverage_ge_097':raw_mid['target_timestamp_coverage']>=.97,'return_pearson_ge_095':raw_mid['return_pearson'] is not None and raw_mid['return_pearson']>=.95,'return_spearman_ge_095':raw_mid['return_spearman'] is not None and raw_mid['return_spearman']>=.95}
    if primary.get('status')=='INSUFFICIENT':status='PILOT_INSUFFICIENT_DATA'
    else: status='PILOT_PASS_TRANSFER_VIABLE' if all(raw_checks.values()) and primary['status']=='PASS' else 'PILOT_FAIL_TRANSFER_NOT_SUPPORTED'
    out={'status':status,'scope':'OUTCOME_BLIND_FOREXCOM_FEED_TRANSFER_PILOT','future_outcomes_used':False,'no_model_refit':True,'no_r_remap':True,
         'forex_window_utc':[str(lo),str(hi)],'mature_times_utc':{'duka_mid':str(mt_mid),'duka_bid':str(mt_bid),'forex':str(mt_f)},
         'raw_primary_mid_vs_forex':raw_mid,'raw_primary_checks':raw_checks,'raw_control_bid_vs_forex':raw_bid,
         'primary_mid_vs_forex':strip_records(primary),'control_bid_vs_forex':strip_records(control),
         'limitations':['Pilot window limited by unauthenticated TradingView chart-history depth.','Dukascopy synthetic MID OHLC is barwise (BID OHLC + ASK OHLC)/2, not tick-synchronous reconstructed midpoint OHLC.','Pilot PASS cannot promote FOREXCOM to validated scientific feed without deeper temporal evidence.']}
    Path(a.output).write_text(json.dumps(out,indent=2))
    if primary.get('matched_records'):
        pd.DataFrame(primary['matched_records']).to_csv(Path(a.output).with_name('XAUUSD_Z4_FOREXCOM_TRANSFER_PILOT_PRIMARY_MATCHED_v0_1.csv'),index=False)
    if control.get('matched_records'):
        pd.DataFrame(control['matched_records']).to_csv(Path(a.output).with_name('XAUUSD_Z4_FOREXCOM_TRANSFER_PILOT_CONTROL_MATCHED_v0_1.csv'),index=False)
    print(json.dumps(out,indent=2),flush=True)

if __name__=='__main__':main()
