#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, importlib.util, json, sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

HERE=Path(__file__).resolve().parent
MODEL_SHA='ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342'
GRID=[('BASELINE',None),('G010',0.10),('G020',0.20),('G025',0.25),('G030',0.30),('G040',0.40),('G050',0.50)]
WINDOWS={
 'H1':(pd.Timestamp('2024-08-01T00:00:00Z'),pd.Timestamp('2025-08-01T00:00:00Z'),'OOS_H1'),
 'H2':(pd.Timestamp('2025-08-01T00:00:00Z'),pd.Timestamp('2026-08-01T00:00:00Z'),'OOS_H2'),
}

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

reaction=load_module('fused_reaction_final',HERE/'xau_ebuy_reaction_dev_v1_0_3_final_preoutcome.py')
base=reaction.base
score=load_module('fused_score_schema',HERE/'xau_ebuy_score_dev_v1_0.py')
Zone=base.v01.Zone

def args():
    p=argparse.ArgumentParser()
    p.add_argument('--files',nargs='+',required=True)
    p.add_argument('--z4-pkl',required=True)
    p.add_argument('--candidates-gz',required=True)
    p.add_argument('--model-pkl',required=True)
    p.add_argument('--coverage-result',required=True)
    p.add_argument('--h2-reference',required=True)
    p.add_argument('--output-json',required=True)
    p.add_argument('--output-csv',required=True)
    return p.parse_args()

def ny_us(t):
    q=pd.Timestamp(t).tz_convert('America/New_York');return 8<=q.hour<17

def build_states(active,z4,cand,lo,hi,window,cov):
    z=z4[(z4.time>=lo)&(z4.time<hi)].copy();zby={pd.Timestamp(t):g for t,g in z.groupby('time',sort=True)}
    c=cand[cand.window.astype(str)==window].copy();cby={pd.Timestamp(t):g.sort_values('entry_rank') for t,g in c.groupby('time',sort=True)}
    snaps=[];displays=[]
    for i,r in active.iterrows():
        t=pd.Timestamp(r.time)
        if not(lo<=t<hi) or t.minute%5!=0 or t.second!=0 or not ny_us(t):continue
        v=float(r.v60)
        if not np.isfinite(v) or v<=0:continue
        g=zby.get(t)
        if g is None or not (g.side==1).any():continue
        close=float(r.close);upper=g[g.side==1]
        s={'active_i':int(i),'time':t,'close':close,'v':v,'upper_z4_count':int(len(upper)),'nearest_upper_z4_dist_v':float(((upper.center-close)/v).min()),'z4_below':[]}
        gg=cby.get(t);zs=[]
        if gg is not None:
            assert np.allclose(gg.close.to_numpy(float),close,rtol=0,atol=1e-9),(window,t,'close')
            assert np.allclose(gg.v60.to_numpy(float),v,rtol=0,atol=1e-9),(window,t,'v60')
            for _,q in gg.iterrows():zs.append(Zone(float(q.center),float(q.zlo),float(q.zhi),str(q.family),0.0))
        assert len(zs)<=3
        snaps.append(s);displays.append(zs)
    exp=cov['results'][window]
    assert len(snaps)==int(exp['eligible_snapshot_count']),(window,len(snaps),exp['eligible_snapshot_count'])
    got=base.v01.metrics(snaps,displays);em=exp['metrics']
    for b in ('0.5','1.0','1.5','2.0'):assert abs(got['coverage'][b]-em['coverage'][b])<=1e-12,(window,b,got['coverage'][b],em['coverage'][b])
    for k in ('candidate_count_median','candidate_count_p90','nearest_distance_v_median','nearest_distance_v_p90'):
        assert abs(float(got[k])-float(em[k]))<=1e-12,(window,k,got[k],em[k])
    return snaps,displays

def fuse_display(zs,v,g):
    if g is None or len(zs)<2:return list(zs)
    ordered=sorted(zs,key=lambda z:(-z.center,-z.zhi,-z.zlo))
    groups=[];cur=[ordered[0]];group_zlo=float(ordered[0].zlo)
    for z in ordered[1:]:
        gap=group_zlo-float(z.zhi)
        if gap<=g*v:
            cur.append(z);group_zlo=min(group_zlo,float(z.zlo))
        else:
            groups.append(cur);cur=[z];group_zlo=float(z.zlo)
    groups.append(cur)
    out=[]
    for q in groups:
        zlo=min(float(z.zlo) for z in q);zhi=max(float(z.zhi) for z in q);fam=q[0].family
        out.append(Zone((zlo+zhi)/2.0,zlo,zhi,fam,0.0))
    return out

def geom_metrics(snaps,displays,baseline):
    counts=np.array([len(z) for z in displays],float);basecounts=np.array([len(z) for z in baseline],float)
    widths=[]
    for s,zs in zip(snaps,displays):
        widths.extend([(float(z.zhi)-float(z.zlo))/float(s['v']) for z in zs])
    widths=np.asarray(widths,float)
    cov=base.v01.metrics(snaps,displays)
    return {
      'snapshot_count':len(snaps),'zone_count_mean':float(counts.mean()),'zone_count_median':float(np.median(counts)),'zone_count_p90':float(np.quantile(counts,.9)),
      'share_snapshots_count_reduced_vs_baseline':float(np.mean(counts<basecounts)),
      'width_v_median':float(np.median(widths)) if len(widths) else None,'width_v_p90':float(np.quantile(widths,.9)) if len(widths) else None,
      'coverage':{k:float(cov['coverage'][k]) for k in ('1.0','1.5','2.0')}
    }

def raw_pos(arr,t):
    q=np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None));i=int(np.searchsorted(arr,q,side='left'))
    if i>=len(arr) or arr[i]!=q:raise RuntimeError(f'raw timestamp missing {t}')
    return i

def enrich(tr,raw,snaps):
    upper={pd.Timestamp(s['time']):float(s['upper_z4_count']) for s in snaps};arr=raw.time.to_numpy(dtype='datetime64[ns]');rows=[]
    for _,r in tr.iterrows():
        tt=pd.Timestamp(r.trigger_time);ct=pd.Timestamp(r.contact_time);et=pd.Timestamp(r.exec_time);ti=raw_pos(arr,tt);ci=raw_pos(arr,ct);raw_pos(arr,et)
        rr=raw.iloc[ti];v=float(r.v_contact);width=max(float(r.zhi)-float(r.zlo),1e-12);o,h,l,cl=map(float,[rr.open,rr.high,rr.low,rr.close]);rng=h-l
        lo=float(raw.low.iloc[min(ci,ti):max(ci,ti)+1].min());c5=pd.Timestamp(r.c5_time);x=r.to_dict()
        x.update({'upper_z4_count':upper[c5],'minutes_contact_to_trigger':float((tt-ct).total_seconds()/60.),'trigger_body_v':float((cl-o)/v),'trigger_range_v':float(rng/v),'trigger_lower_wick_v':float((min(o,cl)-l)/v),'trigger_upper_wick_v':float((h-max(o,cl))/v),'trigger_close_position':float((cl-l)/rng) if rng>0 else 0.0,'trigger_close_minus_zhi_v':float((cl-float(r.zhi))/v),'trigger_close_minus_center_v':float((cl-float(r.center))/v),'exec_gap_v':float((float(r.exec_price)-cl)/v),'max_penetration_to_trigger_width':float((float(r.zhi)-lo)/width),'observation_time':et});rows.append(x)
    d=pd.DataFrame(rows)
    if len(d):
        for k in score.NUMERIC:d[k]=pd.to_numeric(d[k],errors='coerce')
        for k in score.CATEGORICAL:d[k]=d[k].astype(str).fillna('NA')
    return d

def band(d,cut):
    m=d.E_BUY_US>=cut;n=int(m.sum());return {'count':n,'positive_rate':float(d.loc[m,'y'].mean()) if n else None}

def score_metrics(d):
    if len(d)==0:return {'n':0}
    y=d.y.to_numpy(int);p=d.raw_score.to_numpy(float)
    return {'n':len(d),'baseline_positive_rate':float(y.mean()),'roc_auc':float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None,'average_precision':float(average_precision_score(y,p)) if len(np.unique(y))==2 else None,'E80':band(d,80),'E90':band(d,90)}

def run_variant(raw,active,z4,snaps,baseline_displays,g,art):
    displays=[fuse_display(zs,float(s['v']),g) for s,zs in zip(snaps,baseline_displays)]
    states=base.assign_episode_states(snaps,displays)
    old_triggers=base.TRIGGERS;base.TRIGGERS=('BULL_REJECTION',)
    contacts,trades=base.detect_contacts(raw,active,z4,snaps,displays,states)
    base.TRIGGERS=old_triggers
    td=pd.DataFrame(trades)
    fired=td[score.as_bool(td.fired)].copy() if len(td) else pd.DataFrame()
    if len(fired):
        for k in ('trigger_time','contact_time','exec_time','c5_time'):fired[k]=pd.to_datetime(fired[k],utc=True)
        status=fired.tp1_invalidation_status.astype(str);amb=status.str.startswith('AMBIGUOUS')
        valid=fired[~amb&status.isin(['TP1_FIRST','INVALIDATION_FIRST','NEITHER'])].copy();valid['y']=(valid.tp1_invalidation_status.astype(str)=='TP1_FIRST').astype(int)
        d=enrich(valid,raw,snaps)
        if len(d):
            p=art['pipeline'].predict_proba(d[score.NUMERIC+score.CATEGORICAL])[:,1];cdf=np.asarray(art['train_score_cdf_sorted'],float);d['raw_score']=p;d['E_BUY_US']=100.*np.searchsorted(cdf,p,side='right')/len(cdf)
        statuses=fired.tp1_invalidation_status.astype(str).value_counts().to_dict()
        ambn=int(sum(v for k,v in statuses.items() if k.startswith('AMBIGUOUS')));resolved=len(fired)-ambn;tp=int(statuses.get('TP1_FIRST',0));inv=int(statuses.get('INVALIDATION_FIRST',0));nei=int(statuses.get('NEITHER',0))
    else:
        d=pd.DataFrame();statuses={};ambn=resolved=tp=inv=nei=0
    return displays,{
      'contact_episode_count':len(contacts),'bull_rejection_fired_count':len(fired),'bull_rejection_fired_share':float(len(fired)/len(contacts)) if contacts else 0.0,
      'reaction':{'TP1_FIRST':tp,'INVALIDATION_FIRST':inv,'NEITHER':nei,'AMBIGUOUS':ambn,'resolved_n':resolved,'tp1_resolved_rate':float(tp/resolved) if resolved else None,'invalidation_resolved_rate':float(inv/resolved) if resolved else None},
      'score':score_metrics(d)
    }

def parity_h2(got,ref):
    gm=got['score'];rm=ref['metrics'];checks={
      'contacts':got['contact_episode_count']==ref['contact_episode_count'],
      'fired':got['bull_rejection_fired_count']==ref['bull_rejection_fired_count'],
      'resolved_n':gm['n']==ref['resolved_scored_n'],
      'baseline_rate':abs(gm['baseline_positive_rate']-rm['baseline_positive_rate'])<=1e-12,
      'auc':abs(gm['roc_auc']-rm['roc_auc'])<=1e-12,
      'ap':abs(gm['average_precision']-rm['average_precision'])<=1e-12,
      'E80_count':gm['E80']['count']==rm['E80']['count'],
      'E80_rate':abs(gm['E80']['positive_rate']-rm['E80']['positive_rate'])<=1e-12,
      'E90_count':gm['E90']['count']==rm['E90']['count'],
      'E90_rate':abs(gm['E90']['positive_rate']-rm['E90']['positive_rate'])<=1e-12,
    };return checks,all(checks.values())

def main():
    a=args();assert hashlib.sha256(Path(a.model_pkl).read_bytes()).hexdigest()==MODEL_SHA
    cov=json.load(open(a.coverage_result));h2ref=json.load(open(a.h2_reference));art=joblib.load(a.model_pkl)
    assert art['model_id']=='M1_LOGISTIC' and art['numeric_features']==score.NUMERIC and art['categorical_features']==score.CATEGORICAL
    raw=base.v01.load_raw(a.files);active=base.v01.active_m1(raw);z4=pd.read_pickle(a.z4_pkl);z4['time']=pd.to_datetime(z4.time,utc=True)
    cand=pd.read_csv(a.candidates_gz,compression='gzip',low_memory=False);cand['time']=pd.to_datetime(cand.time,utc=True)
    out={'status':'RUNNING','study':'RETROSPECTIVE_FUSED_ZONE_SENSITIVITY','model_sha256':MODEL_SHA,'grid':{k:v for k,v in GRID},'windows':{},'baseline_parity':{}}
    flat=[]
    for wn,(lo,hi,cw) in WINDOWS.items():
        snaps,baseline=build_states(active,z4,cand,lo,hi,cw,cov);base.DEV_LO=lo;base.DEV_HI=hi
        wr={}
        for key,g in GRID:
            displays,res=run_variant(raw,active,z4,snaps,baseline,g,art);geom=geom_metrics(snaps,displays,baseline);wr[key]={'gap_v':g,'geometry':geom,**res}
            sm=res['score'];flat.append({'window':wn,'variant':key,'gap_v':g,'zone_count_mean':geom['zone_count_mean'],'count_reduced_share':geom['share_snapshots_count_reduced_vs_baseline'],'width_v_median':geom['width_v_median'],'width_v_p90':geom['width_v_p90'],'contacts':res['contact_episode_count'],'br_fired':res['bull_rejection_fired_count'],'br_share':res['bull_rejection_fired_share'],'tp1_rate':res['reaction']['tp1_resolved_rate'],'invalidation_rate':res['reaction']['invalidation_resolved_rate'],'scored_n':sm.get('n'),'positive_rate':sm.get('baseline_positive_rate'),'auc':sm.get('roc_auc'),'ap':sm.get('average_precision'),'E80_n':sm.get('E80',{}).get('count'),'E80_rate':sm.get('E80',{}).get('positive_rate'),'E90_n':sm.get('E90',{}).get('count'),'E90_rate':sm.get('E90',{}).get('positive_rate')})
            print('DONE',wn,key,res['contact_episode_count'],res['bull_rejection_fired_count'],res['reaction']['tp1_resolved_rate'],sm.get('E80'),flush=True)
        out['windows'][wn]=wr
        if wn=='H1':
            checks={'contacts':wr['BASELINE']['contact_episode_count']==16896,'fired':wr['BASELINE']['bull_rejection_fired_count']==7128}
            out['baseline_parity']['H1']={'checks':checks,'pass':all(checks.values())}
        else:
            checks,ok=parity_h2(wr['BASELINE'],h2ref);out['baseline_parity']['H2']={'checks':checks,'pass':ok}
    parity=all(x['pass'] for x in out['baseline_parity'].values());out['status']='FUSED_ZONE_SENSITIVITY_COMPLETE' if parity else 'NO_INTERPRETATION_PARITY_FAIL'
    out['production_authorization']='NONE_RETROSPECTIVE_SENSITIVITY_ONLY'
    Path(a.output_json).write_text(json.dumps(out,indent=2));pd.DataFrame(flat).to_csv(a.output_csv,index=False)
    print(json.dumps({'status':out['status'],'baseline_parity':out['baseline_parity']},indent=2))
    if not parity:raise SystemExit(3)

if __name__=='__main__':main()
