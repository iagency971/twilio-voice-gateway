#!/usr/bin/env python3
from __future__ import annotations

import argparse,importlib.util,json,sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score,brier_score_loss,roc_auc_score

HERE=Path(__file__).resolve().parent

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

reaction=load_module('h2_reaction_final',HERE/'xau_ebuy_reaction_dev_v1_0_3_final_preoutcome.py')
base=reaction.base
score=load_module('h2_score_schema',HERE/'xau_ebuy_score_dev_v1_0.py')
Zone=base.v01.Zone
H2_LO=pd.Timestamp('2025-08-01T00:00:00Z');H2_HI=pd.Timestamp('2026-08-01T00:00:00Z')
MODEL_SHA='ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342'


def args():
    p=argparse.ArgumentParser();p.add_argument('--files',nargs='+',required=True);p.add_argument('--z4-pkl',required=True);p.add_argument('--candidates-gz',required=True);p.add_argument('--model-pkl',required=True);p.add_argument('--coverage-result',required=True);p.add_argument('--contacts-csv',required=True);p.add_argument('--triggers-csv',required=True);p.add_argument('--scored-csv',required=True);p.add_argument('--output',required=True);return p.parse_args()


def ny_us(t):
    q=pd.Timestamp(t).tz_convert('America/New_York');return 8<=q.hour<17


def build_h2_states(raw,z4,cand,cov):
    active=base.v01.active_m1(raw);z4=z4.copy();z4['time']=pd.to_datetime(z4.time,utc=True)
    zby={pd.Timestamp(t):g.copy() for t,g in z4.groupby('time',sort=True)}
    c=cand[cand.window.astype(str)=='OOS_H2'].copy();c['time']=pd.to_datetime(c.time,utc=True)
    cby={pd.Timestamp(t):g.sort_values('entry_rank') for t,g in c.groupby('time',sort=True)}
    snaps=[];displays=[]
    for i,r in active.iterrows():
        t=pd.Timestamp(r.time)
        if not (H2_LO<=t<H2_HI):continue
        if t.minute%5!=0 or t.second!=0 or not ny_us(t):continue
        v=float(r.v60)
        if not np.isfinite(v) or v<=0:continue
        g=zby.get(t)
        if g is None or not (g.side==1).any():continue
        close=float(r.close);upper=g[g.side==1]
        s={'active_i':int(i),'time':t,'close':close,'v':v,'upper_z4_count':int(len(upper)),'nearest_upper_z4_dist_v':float(((upper.center-close)/v).min()),'z4_below':[]}
        gg=cby.get(t);zs=[]
        if gg is not None:
            assert np.allclose(gg.close.to_numpy(float),close,rtol=0,atol=1e-9)
            assert np.allclose(gg.v60.to_numpy(float),v,rtol=0,atol=1e-9)
            for _,q in gg.iterrows():zs.append(Zone(float(q.center),float(q.zlo),float(q.zhi),str(q.family),0.0))
        assert len(zs)<=3
        snaps.append(s);displays.append(zs)
    exp=cov['results']['OOS_H2'];assert len(snaps)==int(exp['eligible_snapshot_count']),(len(snaps),exp['eligible_snapshot_count'])
    got=base.v01.metrics(snaps,displays);em=exp['metrics']
    for b in ('0.5','1.0','1.5','2.0'):assert abs(got['coverage'][b]-em['coverage'][b])<=1e-12,(b,got['coverage'][b],em['coverage'][b])
    for k in ('candidate_count_median','candidate_count_p90','nearest_distance_v_median','nearest_distance_v_p90'):assert abs(float(got[k])-float(em[k]))<=1e-12,(k,got[k],em[k])
    print('H2_FROZEN_LOCATION_PARITY_PASS',len(snaps),sum(len(x) for x in displays),flush=True)
    return active,snaps,displays


def raw_pos(arr,t):
    q=np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None));i=int(np.searchsorted(arr,q,side='left'))
    if i>=len(arr) or arr[i]!=q:raise RuntimeError(f'raw time missing {t}')
    return i


def enrich_h2(tr,raw,cand):
    c=cand[cand.window.astype(str)=='OOS_H2'].copy();c['time']=pd.to_datetime(c.time,utc=True);upper=c.groupby('time',sort=False)['upper_z4_count'].first().to_dict()
    arr=raw.time.to_numpy(dtype='datetime64[ns]');rows=[]
    for _,r in tr.iterrows():
        tt=pd.Timestamp(r.trigger_time);ct=pd.Timestamp(r.contact_time);et=pd.Timestamp(r.exec_time);ti=raw_pos(arr,tt);ci=raw_pos(arr,ct);raw_pos(arr,et)
        rr=raw.iloc[ti];v=float(r.v_contact);width=max(float(r.zhi)-float(r.zlo),1e-12);o,h,l,cl=map(float,[rr.open,rr.high,rr.low,rr.close]);rng=h-l;lo=float(raw.low.iloc[min(ci,ti):max(ci,ti)+1].min());c5=pd.Timestamp(r.c5_time)
        if c5 not in upper:raise RuntimeError(f'missing H2 candidate for {c5}')
        x=r.to_dict();x.update({'upper_z4_count':float(upper[c5]),'minutes_contact_to_trigger':float((tt-ct).total_seconds()/60.),'trigger_body_v':float((cl-o)/v),'trigger_range_v':float(rng/v),'trigger_lower_wick_v':float((min(o,cl)-l)/v),'trigger_upper_wick_v':float((h-max(o,cl))/v),'trigger_close_position':float((cl-l)/rng) if rng>0 else 0.,'trigger_close_minus_zhi_v':float((cl-float(r.zhi))/v),'trigger_close_minus_center_v':float((cl-float(r.center))/v),'exec_gap_v':float((float(r.exec_price)-cl)/v),'max_penetration_to_trigger_width':float((float(r.zhi)-lo)/width),'observation_time':et});rows.append(x)
    d=pd.DataFrame(rows)
    for k in score.NUMERIC:d[k]=pd.to_numeric(d[k],errors='coerce')
    for k in score.CATEGORICAL:d[k]=d[k].astype(str).fillna('NA')
    return d


def fp_stats(d,mask):
    s=d.loc[mask,'FP_1.00v_vs_0.50v'].astype(str).value_counts().to_dict();fav=int(s.get('FAVORABLE_FIRST',0));adv=int(s.get('ADVERSE_FIRST',0));amb=int(s.get('AMBIGUOUS',0))+int(s.get('AMBIGUOUS_CONTACT_BAR',0));nei=int(s.get('NEITHER',0));return {'favorable':fav,'adverse':adv,'ambiguous':amb,'neither':nei,'favorable_vs_adverse_rate':float(fav/(fav+adv)) if fav+adv else None}


def band(d,cut):
    m=d.E_BUY_US>=cut;n=int(m.sum());rate=float(d.loc[m,'y'].mean()) if n else None;return {'count':n,'positive_rate':rate,'lift_vs_baseline':float(rate-d.y.mean()) if n else None,'fp1':fp_stats(d,m)}


def metrics(d):
    y=d.y.to_numpy(int);p=d.raw_score.to_numpy(float);base=float(y.mean());bb=base*(1-base)
    return {'n':len(d),'baseline_positive_rate':base,'roc_auc':float(roc_auc_score(y,p)),'average_precision':float(average_precision_score(y,p)),'brier':float(brier_score_loss(y,p)),'constant_baseline_brier':float(bb),'E80':band(d,80),'E90':band(d,90),'fp1_all':fp_stats(d,np.ones(len(d),dtype=bool))}


def main():
    a=args()
    import hashlib
    assert hashlib.sha256(Path(a.model_pkl).read_bytes()).hexdigest()==MODEL_SHA
    cov=json.load(open(a.coverage_result));assert cov['status']=='EBUY_COVERAGE_OOS_REPLICATION_PASS' and cov['results']['OOS_H2']['status']=='PASS'
    raw=base.v01.load_raw(a.files);assert raw.time.min()>=H2_LO and raw.time.max()<H2_HI
    z4=pd.read_pickle(a.z4_pkl);bad=sorted(base.v01.FORBIDDEN&set(z4.columns));assert not bad,bad
    cand=pd.read_csv(a.candidates_gz,compression='gzip',low_memory=False)
    active,snaps,displays=build_h2_states(raw,z4,cand,cov)
    states=base.assign_episode_states(snaps,displays)
    base.DEV_LO=H2_LO;base.DEV_HI=H2_HI;base.TRIGGERS=('BULL_REJECTION',)
    contacts,trades=base.detect_contacts(raw,active,z4,snaps,displays,states)
    pd.DataFrame(contacts).to_csv(a.contacts_csv,index=False);td=pd.DataFrame(trades);td.to_csv(a.triggers_csv,index=False)
    assert set(td.trigger.astype(str).unique())<= {'BULL_REJECTION'}
    fired=td[score.as_bool(td.fired)].copy();fired['trigger_time']=pd.to_datetime(fired.trigger_time,utc=True);fired['contact_time']=pd.to_datetime(fired.contact_time,utc=True);fired['exec_time']=pd.to_datetime(fired.exec_time,utc=True);fired['c5_time']=pd.to_datetime(fired.c5_time,utc=True)
    status=fired.tp1_invalidation_status.astype(str);amb=status.str.startswith('AMBIGUOUS');valid=fired[~amb&status.isin(['TP1_FIRST','INVALIDATION_FIRST','NEITHER'])].copy();valid['y']=(valid.tp1_invalidation_status.astype(str)=='TP1_FIRST').astype(int)
    d=enrich_h2(valid,raw,cand)
    art=joblib.load(a.model_pkl);assert art['model_id']=='M1_LOGISTIC';assert art['numeric_features']==score.NUMERIC and art['categorical_features']==score.CATEGORICAL
    p=art['pipeline'].predict_proba(d[score.NUMERIC+score.CATEGORICAL])[:,1];cdf=np.asarray(art['train_score_cdf_sorted'],float);e=100.*np.searchsorted(cdf,p,side='right')/len(cdf);d['raw_score']=p;d['E_BUY_US']=e;d.to_csv(a.scored_csv,index=False)
    met=metrics(d);amb_share=float(amb.mean()) if len(fired) else None;fired_share=float(len(fired)/len(contacts)) if contacts else 0.
    halves={}
    for nm,lo,hi in [('H2A',H2_LO,pd.Timestamp('2026-02-01T00:00:00Z')),('H2B',pd.Timestamp('2026-02-01T00:00:00Z'),H2_HI)]:
        q=d[(d.observation_time>=lo)&(d.observation_time<hi)].copy();halves[nm]=metrics(q) if len(q)>50 and q.y.nunique()==2 else {'n':len(q),'status':'SPARSE'}
    b=met['baseline_positive_rate'];checks={
      'contacts_ge_10000':len(contacts)>=10000,
      'bull_fired_ge_3000':len(fired)>=3000,
      'bull_fired_share_ge_025':fired_share>=.25,
      'ambiguous_share_le_002':amb_share is not None and amb_share<=.02,
      'baseline_positive_rate_ge_020':b>=.20,
      'auc_ge_065':met['roc_auc']>=.65,
      'ap_ge_baseline_plus_010':met['average_precision']>=b+.10,
      'brier_better_than_constant':met['brier']<met['constant_baseline_brier'],
      'E80_n_ge_800':met['E80']['count']>=800,
      'E80_rate_ge_baseline_plus_020':met['E80']['positive_rate'] is not None and met['E80']['positive_rate']>=b+.20,
      'E80_rate_ge_050':met['E80']['positive_rate'] is not None and met['E80']['positive_rate']>=.50,
      'E90_n_ge_350':met['E90']['count']>=350,
      'E90_rate_ge_baseline_plus_025':met['E90']['positive_rate'] is not None and met['E90']['positive_rate']>=b+.25,
      'E90_rate_ge_055':met['E90']['positive_rate'] is not None and met['E90']['positive_rate']>=.55,
      'E90_rate_ge_E80':met['E90']['positive_rate'] is not None and met['E80']['positive_rate'] is not None and met['E90']['positive_rate']>=met['E80']['positive_rate'],
    }
    passed=all(checks.values());out={'status':'E_BUY_US_H2_VALIDATION_PASS' if passed else 'E_BUY_US_H2_VALIDATION_FAIL','scope':'BUY_ONLY_BULL_REJECTION_E_BUY_US_H2','h2_window':[str(H2_LO),str(H2_HI)],'model_sha256':MODEL_SHA,'alternate_trigger_outcomes_computed':False,'contact_episode_count':len(contacts),'bull_rejection_fired_count':len(fired),'bull_rejection_fired_share':fired_share,'ambiguous_count':int(amb.sum()),'ambiguous_share':amb_share,'resolved_scored_n':len(d),'metrics':met,'half_year_diagnostics':halves,'checks':checks,'authorization':('HISTORICAL_H2_ENTRY_RANK_VALIDATED' if passed else 'H2_SPENT_FAIL_NO_POSTHOC_RESCUE'),'explicit_nonclaims':['No live profitability claim','No spread/slippage/commission validation','No FOREXCOM E score transfer validation','No R_US route claim','E_BUY_US is rank not calibrated probability']}
    Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

if __name__=='__main__':main()
