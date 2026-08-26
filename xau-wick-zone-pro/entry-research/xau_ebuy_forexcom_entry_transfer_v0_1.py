#!/usr/bin/env python3
from __future__ import annotations

import argparse, importlib.util, json, math, sys, hashlib
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
FEED=ROOT/'feed-parity'


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod

v01=load_module('transfer_v01',HERE/'xau_ebuy_coverage_v0_1.py')
v04=load_module('transfer_v04',HERE/'xau_ebuy_coverage_v0_4_sticky.py')
reaction=load_module('transfer_reaction',HERE/'xau_ebuy_reaction_dev_v1_0.py')
score_schema=load_module('transfer_score_schema',HERE/'xau_ebuy_score_dev_v1_0.py')
rawcmp=load_module('transfer_rawcmp',FEED/'xau_z4_forexcom_transfer_compare_v0_1.py')
Zone=v01.Zone
MODEL_SHA='ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342'


def args():
    p=argparse.ArgumentParser()
    p.add_argument('--forex-csv',required=True)
    p.add_argument('--duka-csv',required=True)
    p.add_argument('--z4-bid-pkl',required=True)
    p.add_argument('--z4-mid-pkl',required=True)
    p.add_argument('--z4-forex-pkl',required=True)
    p.add_argument('--model-pkl',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--matched-bid-csv',required=True)
    p.add_argument('--matched-mid-csv',required=True)
    return p.parse_args()


def load_forex(path):
    d=pd.read_csv(path,compression='infer')
    d['time']=pd.to_datetime(d['timestamp_utc'],utc=True)
    out=d[['time','open','high','low','close']].copy()
    for c in ('open','high','low','close'):out[c]=pd.to_numeric(out[c],errors='coerce')
    return out.dropna().sort_values('time').drop_duplicates('time').reset_index(drop=True)


def load_duka(path,mode):
    d=pd.read_csv(path,compression='infer')
    x=pd.to_numeric(d['timestamp'],errors='coerce')
    d['time']=pd.to_datetime(x,unit='ms',utc=True) if x.notna().all() else pd.to_datetime(d['timestamp'],utc=True)
    cols=['open','high','low','close'] if mode=='mid' else ['open_bid','high_bid','low_bid','close_bid']
    out=pd.DataFrame({'time':d.time})
    for s,t in zip(cols,['open','high','low','close']):out[t]=pd.to_numeric(d[s],errors='coerce')
    return out.dropna().sort_values('time').drop_duplicates('time').reset_index(drop=True)


def q(vals,ps):
    a=np.asarray(vals,float);a=a[np.isfinite(a)]
    return {str(p):(float(np.quantile(a,p)) if len(a) else None) for p in ps}


def sp(a,b):
    x=np.asarray(a,float);y=np.asarray(b,float);m=np.isfinite(x)&np.isfinite(y)
    if m.sum()<3:return None
    return float(spearmanr(x[m],y[m]).statistic)


def iou(a0,a1,b0,b1):
    inter=max(0.,min(a1,b1)-max(a0,b0));union=max(a1,b1)-min(a0,b0)
    return inter/union if union>0 else 0.


def raw_sanity(ref,tgt):
    met,_=rawcmp.raw_metrics(ref,tgt)
    checks={'timestamp_coverage_ge_097':met['target_timestamp_coverage']>=.97,
            'return_spearman_ge_095':met['return_spearman'] is not None and met['return_spearman']>=.95}
    return {'metrics':met,'checks':checks,'pass':all(checks.values())}


def build_feed(raw,z4_path,model_art):
    z4=pd.read_pickle(z4_path).copy();z4['time']=pd.to_datetime(z4.time,utc=True)
    bad=sorted(v01.FORBIDDEN&set(z4.columns))
    if bad:raise RuntimeError(f'future outcome columns in geometry: {bad}')
    active=v01.active_m1(raw)
    snaps,pools=v04.build_fixed_pools(raw,active,z4)
    displays=v04.sticky_display(raw,snaps,pools)
    states=reaction.assign_episode_states(snaps,displays)
    events=detect_events(raw,active,z4,snaps,displays,states)
    if events:
        d=pd.DataFrame(events)
        X=d[score_schema.NUMERIC+score_schema.CATEGORICAL].copy()
        for c in score_schema.NUMERIC:X[c]=pd.to_numeric(X[c],errors='coerce')
        for c in score_schema.CATEGORICAL:X[c]=X[c].astype(str).fillna('NA')
        p=model_art['pipeline'].predict_proba(X)[:,1]
        cdf=np.asarray(model_art['train_score_cdf_sorted'],float)
        e=100.*np.searchsorted(cdf,p,side='right')/len(cdf)
        d['raw_score']=p;d['E_BUY_US']=e
    else:d=pd.DataFrame()
    return {'raw':raw,'active':active,'z4':z4,'snaps':snaps,'displays':displays,'events':d}


def detect_events(raw,active,z4,snaps,displays,states):
    targets=reaction.target_map(z4,snaps)
    runtime={};events=[]
    for s,zs,sts in zip(snaps,displays,states):
        if s['time'] not in targets:continue
        next_boundary=s['time']+pd.Timedelta(minutes=5);end=min(next_boundary,reaction.ny_end(s['time']))
        i0=reaction.raw_index(raw,s['time'],'right')+1;i1=reaction.raw_index(raw,end-pd.Timedelta(nanoseconds=1),'right')
        if i1<i0:continue
        for z,st in zip(zs,sts):
            eid=int(st['id']);rt=runtime.setdefault(eid,{'armed':False,'arm_time':None,'arm_close':None,'consumed':False})
            if rt['consumed']:continue
            if not rt['armed'] and float(s['close'])>float(z.zhi):
                rt['armed']=True;rt['arm_time']=s['time'];rt['arm_close']=float(s['close'])
            contact_idx=None
            for j in range(i0,i1+1):
                r=raw.loc[j]
                if not rt['armed']:
                    if float(r.close)>float(z.zhi):
                        rt['armed']=True;rt['arm_time']=pd.Timestamp(r.time);rt['arm_close']=float(r.close)
                    continue
                if float(r.high)>=float(z.zlo) and float(r.low)<=float(z.zhi):contact_idx=j;break
            if contact_idx is None:continue
            rt['consumed']=True
            ct=pd.Timestamp(raw.at[contact_idx,'time']);v=float(s['v']);tp=targets[s['time']]
            end_session=reaction.ny_end(ct);ej=reaction.raw_index(raw,end_session-pd.Timedelta(nanoseconds=1),'right')
            info=reaction.find_confirmation(raw,contact_idx,ej,z,float(tp['zlo']),'BULL_REJECTION')
            if not info.get('fired'):continue
            tt=pd.Timestamp(info['trigger_time']);et=pd.Timestamp(info['exec_time']);ti=int(info['trigger_idx']);ei=int(info['exec_idx'])
            ai=reaction.active_index(active,ct);tr=reaction.trends(active,ai,v) if ai>=0 else {f'trend{h}_v':np.nan for h in (5,15,60,240)}
            cr=raw.loc[contact_idx];width=max(float(z.zhi-z.zlo),1e-12);rngc=float(cr.high-cr.low);cpc=float((cr.close-cr.low)/rngc) if rngc>0 else 0.
            rr=raw.loc[ti];o,h,l,c=map(float,[rr.open,rr.high,rr.low,rr.close]);rng=h-l
            low_to_trigger=float(raw.low.iloc[min(contact_idx,ti):max(contact_idx,ti)+1].min())
            row={
                'episode_id':eid,'c5_time':s['time'],'contact_time':ct,'trigger_time':tt,'exec_time':et,
                'family':z.family,'episode_origin_family':st['origin_family'],'slot_rank':st['slot'],'episode_age_c5':st['age'],
                'zlo':float(z.zlo),'center':float(z.center),'zhi':float(z.zhi),'zone_width_v':width/v,'v_contact':v,
                'arm_time':rt['arm_time'],'arm_close':rt['arm_close'],'arm_center_distance_v':((float(rt['arm_close'])-float(z.center))/v if rt['arm_close'] is not None else np.nan),
                'tp1_zlo':float(tp['zlo']),'tp1_center':float(tp['center']),'tp1_zhi':float(tp['zhi']),
                'tp_distance_v':(float(tp['zlo'])-float(info['exec_price']))/v,
                'minutes_to_us_end':(reaction.ny_end(ct)-ct).total_seconds()/60.,'us_subperiod':reaction.subperiod(ct),
                'contact_penetration_width':(float(z.zhi)-float(cr.low))/width,'contact_bull':int(float(cr.close)>float(cr.open)),'contact_close_position':cpc,
                'upper_z4_count':float(s['upper_z4_count']),
                'minutes_contact_to_trigger':float((tt-ct).total_seconds()/60.),
                'trigger_body_v':(c-o)/v,'trigger_range_v':rng/v,
                'trigger_lower_wick_v':(min(o,c)-l)/v,'trigger_upper_wick_v':(h-max(o,c))/v,
                'trigger_close_position':((c-l)/rng if rng>0 else 0.),
                'trigger_close_minus_zhi_v':(c-float(z.zhi))/v,'trigger_close_minus_center_v':(c-float(z.center))/v,
                'exec_gap_v':(float(info['exec_price'])-c)/v,
                'max_penetration_to_trigger_width':(float(z.zhi)-low_to_trigger)/width,
                'exec_price':float(info['exec_price']),
                'trend5_v':tr.get('trend5_v'),'trend15_v':tr.get('trend15_v'),'trend60_v':tr.get('trend60_v'),'trend240_v':tr.get('trend240_v'),
            }
            events.append(row)
    return events


def snap_maps(feed):
    return {pd.Timestamp(s['time']):(s,zs) for s,zs in zip(feed['snaps'],feed['displays'])}


def location_compare(ref,tgt):
    R=snap_maps(ref);T=snap_maps(tgt);times=sorted(set(R)&set(T))
    matched_ref=matched_tgt=total_ref=total_tgt=0
    rel_iou=[];center_err=[];exact=[];within1=[];nearest=[];family=[]
    rows=[]
    for tm in times:
        sr,rz=R[tm];st,tz=T[tm];total_ref+=len(rz);total_tgt+=len(tz);exact.append(len(rz)==len(tz));within1.append(abs(len(rz)-len(tz))<=1)
        if not rz or not tz:
            nearest.append(False);continue
        vr=max(float(sr['v']),float(st['v']),1e-9);cr=float(sr['close']);ct=float(st['close'])
        cost=np.full((len(rz),len(tz)),1e6,float);ok=np.zeros_like(cost,bool)
        for i,a in enumerate(rz):
            a0=float(a.zlo-cr);a1=float(a.zhi-cr);ac=float(a.center-cr)
            for j,b in enumerate(tz):
                b0=float(b.zlo-ct);b1=float(b.zhi-ct);bc=float(b.center-ct);ce=abs(ac-bc)/vr;ov=iou(a0,a1,b0,b1)
                if ov>0 or ce<=.75:
                    ok[i,j]=True;cost[i,j]=ce+.5*(1-ov)
        aa,bb=linear_sum_assignment(cost);mapping={}
        for i,j in zip(aa,bb):
            if not ok[i,j]:continue
            a=rz[i];b=tz[j];a0=float(a.zlo-cr);a1=float(a.zhi-cr);b0=float(b.zlo-ct);b1=float(b.zhi-ct);ce=abs((float(a.center)-cr)-(float(b.center)-ct))/vr;ov=iou(a0,a1,b0,b1)
            matched_ref+=1;matched_tgt+=1;mapping[i]=j;rel_iou.append(ov);center_err.append(ce);family.append(a.family==b.family)
            rows.append({'time':tm,'ref_slot':i+1,'tgt_slot':j+1,'ref_family':a.family,'tgt_family':b.family,'rel_iou':ov,'center_err_v':ce})
        nearest.append(mapping.get(0,-1)==0)
    metrics={
      'common_eligible_c5':len(times),'reference_zone_count':total_ref,'target_zone_count':total_tgt,
      'reference_zone_match_rate':matched_ref/total_ref if total_ref else 0.,'target_zone_match_rate':matched_tgt/total_tgt if total_tgt else 0.,
      'relative_iou_quantiles':q(rel_iou,(.1,.5,.9)),'relative_center_err_v_quantiles':q(center_err,(.5,.9,.95)),
      'exact_candidate_count_agreement':float(np.mean(exact)) if exact else 0.,'candidate_count_within1_agreement':float(np.mean(within1)) if within1 else 0.,
      'nearest_top1_agreement':float(np.mean(nearest)) if nearest else 0.,'family_agreement_matched':float(np.mean(family)) if family else None}
    checks={
      'common_c5_ge_250':metrics['common_eligible_c5']>=250,
      'reference_zone_match_ge_075':metrics['reference_zone_match_rate']>=.75,
      'target_zone_match_ge_075':metrics['target_zone_match_rate']>=.75,
      'median_relative_iou_ge_060':metrics['relative_iou_quantiles']['0.5'] is not None and metrics['relative_iou_quantiles']['0.5']>=.60,
      'median_center_err_le_035v':metrics['relative_center_err_v_quantiles']['0.5'] is not None and metrics['relative_center_err_v_quantiles']['0.5']<=.35,
      'p90_center_err_le_075v':metrics['relative_center_err_v_quantiles']['0.9'] is not None and metrics['relative_center_err_v_quantiles']['0.9']<=.75,
      'exact_count_agreement_ge_065':metrics['exact_candidate_count_agreement']>=.65,
      'within1_count_agreement_ge_090':metrics['candidate_count_within1_agreement']>=.90,
      'nearest_top1_ge_070':metrics['nearest_top1_agreement']>=.70,
    }
    return {'pass':all(checks.values()),'metrics':metrics,'checks':checks,'matches':pd.DataFrame(rows),'common_times':set(times)}


def trigger_compare(ref,tgt,common_times):
    R=ref['events'].copy();T=tgt['events'].copy()
    if len(R):R=R[R.c5_time.isin(common_times)].reset_index(drop=True)
    if len(T):T=T[T.c5_time.isin(common_times)].reset_index(drop=True)
    if not len(R) or not len(T):
        met={'reference_triggers':len(R),'target_triggers':len(T),'matched_triggers':0}
        return {'pass':False,'metrics':met,'checks':{},'matches':pd.DataFrame()}
    cost=np.full((len(R),len(T)),1e6,float);ok=np.zeros_like(cost,bool)
    for i,r in R.iterrows():
        for j,t in T.iterrows():
            dt=abs((pd.Timestamp(r.trigger_time)-pd.Timestamp(t.trigger_time)).total_seconds())/60.
            if dt>2:continue
            v=max(float(r.v_contact),float(t.v_contact),1e-9)
            # Relative to the close at the C5 that armed/presented the episode. Approximate operational alignment through absolute zone center gap normalized by local v.
            ce=abs(float(r.center)-float(t.center))/v
            ov=iou(float(r.zlo),float(r.zhi),float(t.zlo),float(t.zhi))
            if ov>0 or ce<=.75:
                ok[i,j]=True;cost[i,j]=dt+.25*min(ce,3.)
    aa,bb=linear_sum_assignment(cost);rows=[];times=[];centers=[];scores_r=[];scores_t=[];es_r=[];es_t=[]
    for i,j in zip(aa,bb):
        if not ok[i,j]:continue
        r=R.iloc[i];t=T.iloc[j];dt=abs((pd.Timestamp(r.trigger_time)-pd.Timestamp(t.trigger_time)).total_seconds())/60.;v=max(float(r.v_contact),float(t.v_contact),1e-9);ce=abs(float(r.center)-float(t.center))/v
        times.append(dt);centers.append(ce);scores_r.append(float(r.raw_score));scores_t.append(float(t.raw_score));es_r.append(float(r.E_BUY_US));es_t.append(float(t.E_BUY_US))
        rows.append({'ref_trigger_time':r.trigger_time,'tgt_trigger_time':t.trigger_time,'time_delta_min':dt,'center_err_v':ce,'ref_family':r.family,'tgt_family':t.family,'ref_score':r.raw_score,'tgt_score':t.raw_score,'ref_E':r.E_BUY_US,'tgt_E':t.E_BUY_US})
    eabs=np.abs(np.asarray(es_r)-np.asarray(es_t)) if es_r else np.array([])
    cls80=[]
    for a,b in zip(es_r,es_t):cls80.append((a>=80)==(b>=80))
    union80=sum((a>=80) or (b>=80) for a,b in zip(es_r,es_t))
    met={
      'reference_triggers':len(R),'target_triggers':len(T),'matched_triggers':len(rows),
      'reference_match_rate':len(rows)/len(R) if len(R) else 0.,'target_match_rate':len(rows)/len(T) if len(T) else 0.,
      'time_delta_min_quantiles':q(times,(.5,.9,.95)),'entry_zone_center_err_v_quantiles':q(centers,(.5,.9)),
      'raw_score_spearman':sp(scores_r,scores_t),'E_spearman':sp(es_r,es_t),'E_abs_diff_quantiles':q(eabs,(.5,.9,.95)),
      'share_E_within15':float(np.mean(eabs<=15)) if len(eabs) else None,'E80_union_count':int(union80),'E80_classification_agreement':float(np.mean(cls80)) if cls80 else None,
      'E90_union_count':int(sum((a>=90) or (b>=90) for a,b in zip(es_r,es_t))),
      'E90_classification_agreement':float(np.mean([(a>=90)==(b>=90) for a,b in zip(es_r,es_t)])) if es_r else None,
    }
    checks={
      'reference_triggers_ge_25':met['reference_triggers']>=25,'target_triggers_ge_25':met['target_triggers']>=25,'matched_ge_20':met['matched_triggers']>=20,
      'reference_match_ge_060':met['reference_match_rate']>=.60,'target_match_ge_060':met['target_match_rate']>=.60,
      'median_time_delta_le_1m':met['time_delta_min_quantiles']['0.5'] is not None and met['time_delta_min_quantiles']['0.5']<=1.,
      'p90_time_delta_le_2m':met['time_delta_min_quantiles']['0.9'] is not None and met['time_delta_min_quantiles']['0.9']<=2.,
      'median_center_err_le_050v':met['entry_zone_center_err_v_quantiles']['0.5'] is not None and met['entry_zone_center_err_v_quantiles']['0.5']<=.50,
      'raw_score_spearman_ge_080':met['raw_score_spearman'] is not None and met['raw_score_spearman']>=.80,
      'E_spearman_ge_080':met['E_spearman'] is not None and met['E_spearman']>=.80,
      'median_E_abs_diff_le_10':met['E_abs_diff_quantiles']['0.5'] is not None and met['E_abs_diff_quantiles']['0.5']<=10.,
      'share_E_within15_ge_080':met['share_E_within15'] is not None and met['share_E_within15']>=.80,
      'E80_agreement_if_n_ge10':True if union80<10 else met['E80_classification_agreement']>=.75,
    }
    return {'pass':all(checks.values()),'metrics':met,'checks':checks,'matches':pd.DataFrame(rows)}


def compare(label,ref,tgt):
    loc=location_compare(ref,tgt);tr=trigger_compare(ref,tgt,loc['common_times'])
    out={'label':label,'status':'PASS' if loc['pass'] and tr['pass'] else 'FAIL','location':{'metrics':loc['metrics'],'checks':loc['checks']},'trigger_score':{'metrics':tr['metrics'],'checks':tr['checks']}}
    return out,tr['matches']


def main():
    a=args();model_bytes=Path(a.model_pkl).read_bytes();assert hashlib.sha256(model_bytes).hexdigest()==MODEL_SHA
    art=joblib.load(a.model_pkl);assert art['model_id']=='M1_LOGISTIC';assert art['numeric_features']==score_schema.NUMERIC and art['categorical_features']==score_schema.CATEGORICAL
    forex=load_forex(a.forex_csv);bid=load_duka(a.duka_csv,'bid');mid=load_duka(a.duka_csv,'mid')
    lo=max(forex.time.min(),bid.time.min(),mid.time.min());hi=min(forex.time.max(),bid.time.max(),mid.time.max())
    forex=forex[(forex.time>=lo)&(forex.time<=hi)].reset_index(drop=True);bid=bid[(bid.time>=lo)&(bid.time<=hi)].reset_index(drop=True);mid=mid[(mid.time>=lo)&(mid.time<=hi)].reset_index(drop=True)
    raw_bid=raw_sanity(bid,forex);raw_mid=raw_sanity(mid,forex)
    feeds={'bid':build_feed(bid,a.z4_bid_pkl,art),'mid':build_feed(mid,a.z4_mid_pkl,art),'forex':build_feed(forex,a.z4_forex_pkl,art)}
    cb,mb=compare('DUKASCOPY_BID__FOREXCOM_MID',feeds['bid'],feeds['forex']);cm,mm=compare('DUKASCOPY_SYNTH_MID__FOREXCOM_MID',feeds['mid'],feeds['forex'])
    mb.to_csv(a.matched_bid_csv,index=False);mm.to_csv(a.matched_mid_csv,index=False)
    passed=raw_bid['pass'] and raw_mid['pass'] and cb['status']=='PASS' and cm['status']=='PASS'
    out={
      'status':'ENTRY_TRANSFER_PILOT_PASS_OPERATIONAL' if passed else 'ENTRY_TRANSFER_PILOT_FAIL_NO_PINE_PROMOTION',
      'scope':'OUTCOME_BLIND_EBUY_BULL_REJECTION_E_SCORE_FOREXCOM_TRANSFER','future_trade_outcomes_used':False,'no_model_refit':True,'no_e_remap':True,
      'common_raw_window_utc':[str(lo),str(hi)],'model_sha256':MODEL_SHA,
      'raw_scientific_reference_bid_vs_forex':raw_bid,'raw_mid_control_vs_forex':raw_mid,
      'scientific_reference_bid_vs_forex':cb,'mid_control_vs_forex':cm,
      'authorization':('AUTHORIZE_PINE_ENTRY_LAYER_ENGINEERING_ON_FOREXCOM_M1' if passed else 'DO_NOT_PROMOTE_ENTRY_LAYER_TO_PINE'),
      'explicit_nonclaims':['No FOREXCOM future-performance validation','No profitability claim','No transaction-cost validation','No R_US route claim','No higher-timeframe E-BUY claim','E_BUY_US is a rank not calibrated probability']}
    Path(a.output).write_text(json.dumps(out,indent=2,default=str));print(json.dumps({'status':out['status'],'authorization':out['authorization'],'bid':cb,'mid':cm},indent=2,default=str))

if __name__=='__main__':main()
