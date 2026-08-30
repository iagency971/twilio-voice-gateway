#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import xau_e_zone_v2_r4_matching_ladder as r4
import xau_e_zone_v2_r4_pro_audit_diagnostics as dg

EF={'ESM_BOTH_G120M','EPM_M1_R2_A8H','EWM_G60M','ES_M1_8H_R2_T0.50'}
FORB=('primary_binary','primary_class','favorable','adverse_level','event_bar','outcome','mfe','mae','success','reaction','target_hit','stop_hit')
DESIGN=r4.DESIGNS[0]
FP_BOUND_FACTOR=64.0


def args():
    p=argparse.ArgumentParser()
    for x in ['features','display-all','full-pool','context','placebos','matching','instrument-manifest','placebo-manifest']:
        p.add_argument('--'+x,required=True)
    p.add_argument('--output',required=True);return p.parse_args()


def read(p):
    d=pd.read_csv(p,compression='infer',float_precision='round_trip')
    for c in ['time','snapshot_time_utc','feature_available_time_utc']:
        if c in d.columns:d[c]=pd.to_datetime(d[c],utc=True)
    return d


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    a=args();f=read(a.features);da=read(a.display_all);pool=read(a.full_pool);ctx=read(a.context);pl=read(a.placebos);m=read(a.matching)
    im=json.load(open(a.instrument_manifest));pm=json.load(open(a.placebo_manifest));checks={};report={}
    checks['instrument_status_pass']=im.get('status')=='E_ZONE_V2_INSTRUMENT_OUTCOME_BLIND_PASS'
    checks['v04_parity_pass']=im.get('geometry_parity') is None or bool(im['geometry_parity'].get('pass'))
    checks['placebo_manifest_status_pass']=pm.get('status')=='E_ZONE_V2_R4_PLACEBO_GENERATION_OUTCOME_BLIND_PASS'
    checks['r4_design_exact']=pm.get('design',{}).get('id')=='R4_D5_MINIMAL_DENSE' and pm.get('D6_D7_D8_used') is False
    checks['features_nonempty']=len(f)>0;checks['features_only_E']=set(f.current_family.astype(str)).issubset(EF);checks['slot_original_1_3']=set(f.display_slot_rank.astype(int)).issubset({1,2,3})
    checks['feature_available_t_plus_1']=bool((pd.to_datetime(f.feature_available_time_utc,utc=True)==pd.to_datetime(f.snapshot_time_utc,utc=True)+pd.Timedelta(minutes=1)).all())
    checks['placebo_feature_available_t_plus_1']=bool((pd.to_datetime(pl.feature_available_time_utc,utc=True)==pd.to_datetime(pl.snapshot_time_utc,utc=True)+pd.Timedelta(minutes=1)).all())
    checks['valid_geometry']=bool(((f.zlo<=f.center)&(f.center<=f.zhi)&(f.v_snapshot>0)&(f.zone_width_v>=0)).all()) and bool(((pl.zlo<=pl.center)&(pl.center<=pl.zhi)&(pl.v_snapshot>0)&(pl.zone_width_v>=0)).all())
    checks['no_outcome_columns_features']=not any(any(t in c.lower() for t in FORB) for c in f.columns)
    checks['no_outcome_columns_placebos']=not any(any(t in c.lower() for t in FORB) for c in pl.columns)
    checks['matching_same_start_minute']=bool((m.donor_minute_of_session.astype(int)==m.recipient_minute_of_session.astype(int)).all())
    checks['matching_min_session_gap_10']=bool((m.session_index_gap.astype(int)>=10).all())

    # Verify the mathematically exact normalized-width preservation using a
    # deterministic IEEE-754 error bound scaled by the actual price/v
    # cancellation condition, rather than a fixed absolute tolerance.
    donor_first=(f.sort_values(['display_episode_id','snapshot_time_utc'])
                   .groupby('display_episode_id',sort=False).first().reset_index()
                   [['display_episode_id','center','zlo','zhi','v_snapshot']]
                   .rename(columns={'display_episode_id':'donor_episode_id','center':'donor_geom_center','zlo':'donor_geom_zlo','zhi':'donor_geom_zhi','v_snapshot':'donor_geom_v'}))
    placebo_first=(pl.sort_values(['placebo_id','snapshot_time_utc'])
                     .groupby('placebo_id',sort=False).first().reset_index()
                     [['placebo_id','center','zlo','zhi','v_snapshot']]
                     .rename(columns={'center':'recipient_geom_center','zlo':'recipient_geom_zlo','zhi':'recipient_geom_zhi','v_snapshot':'recipient_geom_v'}))
    wm=(m.merge(donor_first,on='donor_episode_id',how='left',validate='many_to_one')
          .merge(placebo_first,on='placebo_id',how='left',validate='one_to_one'))
    width_inputs_complete=not wm[['donor_geom_center','donor_geom_zlo','donor_geom_zhi','donor_geom_v','recipient_geom_center','recipient_geom_zlo','recipient_geom_zhi','recipient_geom_v']].isna().any().any()
    checks['matching_width_geometry_inputs_complete']=bool(width_inputs_complete)
    if width_inputs_complete:
        eps=np.finfo(float).eps;tiny=np.finfo(float).tiny
        donor_scale=np.maximum.reduce([np.ones(len(wm)),np.abs(wm.donor_geom_center.to_numpy(float)),np.abs(wm.donor_geom_zlo.to_numpy(float)),np.abs(wm.donor_geom_zhi.to_numpy(float))])/np.maximum(wm.donor_geom_v.to_numpy(float),tiny)
        rec_scale=np.maximum.reduce([np.ones(len(wm)),np.abs(wm.recipient_geom_center.to_numpy(float)),np.abs(wm.recipient_geom_zlo.to_numpy(float)),np.abs(wm.recipient_geom_zhi.to_numpy(float))])/np.maximum(wm.recipient_geom_v.to_numpy(float),tiny)
        wd=wm.donor_zone_width_v.to_numpy(float);wr=wm.recipient_transplanted_zone_width_v.to_numpy(float)
        magnitude=np.maximum.reduce([np.ones(len(wm)),np.abs(wd),np.abs(wr)])
        bound=FP_BOUND_FACTOR*eps*(donor_scale+rec_scale+magnitude)
        delta=np.abs(wd-wr)
        donor_from_geom=(wm.donor_geom_zhi.to_numpy(float)-wm.donor_geom_zlo.to_numpy(float))/wm.donor_geom_v.to_numpy(float)
        recipient_from_geom=(wm.recipient_geom_zhi.to_numpy(float)-wm.recipient_geom_zlo.to_numpy(float))/wm.recipient_geom_v.to_numpy(float)
        donor_serial_delta=np.abs(wd-donor_from_geom);recipient_serial_delta=np.abs(wr-recipient_from_geom)
        checks['matching_width_float_roundtrip_bounded']=bool(np.all(delta<=bound))
        checks['matching_width_donor_geometry_consistent']=bool(np.all(donor_serial_delta<=bound))
        checks['matching_width_recipient_geometry_consistent']=bool(np.all(recipient_serial_delta<=bound))
        nz=delta>0
        report['width_roundtrip']={
            'authority_rule':'abs(donor_width_v-recipient_width_v) <= 64*eps*(donor_price_scale/v + recipient_price_scale/v + width_scale)',
            'fp_bound_factor':FP_BOUND_FACTOR,
            'float64_epsilon':float(eps),
            'old_fixed_atol_2e12_pass_report_only':bool(np.allclose(wd,wr,rtol=0,atol=2e-12)),
            'rows_abs_delta_gt_2e12_report_only':int(np.sum(delta>2e-12)),
            'max_abs_delta':float(delta.max()) if len(delta) else None,
            'max_relative_delta':float(np.max(delta/np.maximum(np.maximum(np.abs(wd),np.abs(wr)),tiny))) if len(delta) else None,
            'min_machine_bound':float(bound.min()) if len(bound) else None,
            'max_machine_bound':float(bound.max()) if len(bound) else None,
            'minimum_bound_to_delta_ratio_nonzero':float(np.min(bound[nz]/delta[nz])) if np.any(nz) else None,
            'donor_geometry_max_delta':float(donor_serial_delta.max()) if len(donor_serial_delta) else None,
            'recipient_geometry_max_delta':float(recipient_serial_delta.max()) if len(recipient_serial_delta) else None,
            'frozen_repair_evidence':'R4_REP_WIDTH_FLOAT_DIAGNOSTIC_2026-08-30.json',
            'repair_memo':'PREOUTCOME_IMPLEMENTATION_REPAIR_R4_WIDTH_FLOAT.md'
        }
    else:
        checks['matching_width_float_roundtrip_bounded']=False
        checks['matching_width_donor_geometry_consistent']=False
        checks['matching_width_recipient_geometry_consistent']=False

    checks['matching_distance_exact']=bool(np.allclose(m.donor_distance_v,m.recipient_distance_v,rtol=0,atol=2e-12))
    checks['matching_logv_caliper_065']=bool((np.abs(m.donor_log_v_snapshot-m.recipient_log_v_snapshot)<=.65+1e-12).all())
    checks['matching_z4_caliper_125']=bool((np.abs(m.donor_nearest_upper_z4_dist_v-m.recipient_nearest_upper_z4_dist_v)<=1.25+1e-12).all())
    checks['control_rank_1_to_5']=bool((m.control_rank.astype(int).between(1,5)).all())
    rank_ok=True
    for _,g in m.groupby('donor_episode_id',sort=False):
        z=g.sort_values('control_rank');ranks=z.control_rank.astype(int).tolist()
        if ranks!=list(range(1,len(ranks)+1)) or np.any(np.diff(z.match_distance.to_numpy(float))<0):rank_ok=False;break
        vals=z.match_distance.to_numpy(float);rs=z.recipient_session_date_ny.astype(str).tolist();i=0
        while i<len(vals):
            j=i+1
            while j<len(vals) and vals[j]==vals[i]:j+=1
            if j-i>1:
                hs=[r4.tie_hash(str(z.donor_episode_id.iloc[0]),s,DESIGN['id']) for s in rs[i:j]]
                if hs!=sorted(hs):rank_ok=False;break
            i=j
        if not rank_ok:break
    checks['deterministic_rank_order']=rank_ok

    ctx2=ctx.copy();ctx2['log_v_snapshot']=np.log(ctx2.v_snapshot.astype(float));ctx2=ctx2.sort_values(['session_date_ny','minute_of_session','time']).drop_duplicates(['session_date_ny','minute_of_session'],keep='last').reset_index(drop=True)
    stats={c:float(ctx2[c].astype(float).std(ddof=0)) or 1.0 for c in r4.MATCH}
    expected=np.zeros(len(m),float)
    for c in r4.MATCH:expected+=((m['recipient_'+c].to_numpy(float)-m['donor_'+c].to_numpy(float))/stats[c])**2
    expected+=(m.recipient_upper_z4_count_bucket.astype(str).to_numpy()!=m.donor_upper_z4_count_bucket.astype(str).to_numpy())*r4.BUCKET_MISMATCH_PENALTY
    expected+=(m.recipient_weekday_ny.astype(str).to_numpy()!=m.donor_weekday_ny.astype(str).to_numpy())*r4.WEEKDAY_MISMATCH_PENALTY
    checks['match_distance_recomputed']=bool(np.allclose(expected,m.match_distance.to_numpy(float),rtol=0,atol=2e-12))

    # Authority is the exact frozen neutrality rule used by the generator:
    # overlap OR center distance <= 0.20*v. No epsilon is added to the gate.
    pb={pd.Timestamp(t):g for t,g in pool.groupby('time',sort=False)}
    strict_bad_rows=0;overlap_bad_rows=0;near_exact_bad_rows=0;epsilon_only_near_rows=0;examples=[]
    for _,z in pl.iterrows():
        g=pb.get(pd.Timestamp(z.snapshot_time_utc))
        if g is None or not len(g):continue
        ov=np.minimum(float(z.zhi),g.zhi.to_numpy(float))>=np.maximum(float(z.zlo),g.zlo.to_numpy(float))
        dd=np.abs(g.center.to_numpy(float)-float(z.center));thr=.20*float(z.v_snapshot)
        near_exact=dd<=thr;near_eps=(dd<=thr+1e-12)&(~near_exact);bad=ov|near_exact
        if bool(np.any(ov)):overlap_bad_rows+=1
        if bool(np.any(near_exact)):near_exact_bad_rows+=1
        if bool(np.any(near_eps)):epsilon_only_near_rows+=1
        if bool(np.any(bad)):
            strict_bad_rows+=1
            if len(examples)<20:examples.append({'placebo_id':str(z.placebo_id),'snapshot_time_utc':pd.Timestamp(z.snapshot_time_utc).isoformat(),'overlap':bool(np.any(ov)),'near_exact':bool(np.any(near_exact)),'min_center_distance':float(np.min(dd)),'threshold_0_20v':float(thr)})
    checks['placebo_neutrality_recompute']=strict_bad_rows==0
    report['neutrality_recompute']={'authority_rule':'overlap OR abs(real_center-placebo_center) <= 0.20*v; exact float64 comparison, no epsilon','strict_bad_rows':strict_bad_rows,'overlap_bad_rows':overlap_bad_rows,'near_exact_bad_rows':near_exact_bad_rows,'epsilon_only_near_rows_report_only':epsilon_only_near_rows,'strict_bad_examples':examples}
    checks['row_hash_unique_within_snapshot_slot']=not f.duplicated(['snapshot_time_utc','display_slot_rank']).any()

    starts=f.sort_values(['display_episode_id','snapshot_time_utc']).groupby('display_episode_id',sort=False).first().reset_index()
    counts=m.groupby('donor_episode_id').size();starts['_n']=starts.display_episode_id.astype(str).map(counts).fillna(0).astype(int)
    overall=float((starts._n>=2).mean());report['fraction_donors_ge2']=overall;checks['coverage_overall_ge_080']=overall>=.80
    slot={}
    for k,g in starts.groupby('display_slot_rank',sort=True):slot[str(int(k))]=float((g._n>=2).mean())
    report['coverage_by_slot']=slot;checks['coverage_each_slot_ge_070']=all(v>=.70 for v in slot.values()) and set(slot)=={'1','2','3'}

    eligible=set(starts.loc[starts._n>=2,'display_episode_id'].astype(str));me=m[m.donor_episode_id.astype(str).isin(eligible)].copy();n=me.groupby('donor_episode_id').size();me['_w']=1.0/me.donor_episode_id.astype(str).map(n).astype(float);w=me._w.to_numpy(float)
    numeric={}
    for c in r4.MATCH:numeric[c]={'smd':dg.wsmd(me['donor_'+c],me['recipient_'+c],w),'ks':dg.weighted_ks(me['donor_'+c],me['recipient_'+c],w)}
    report['donor_equal_numeric_balance']=numeric;checks['numeric_abs_smd_le_010']=all(abs(x['smd'])<=.10 for x in numeric.values());checks['numeric_weighted_ks_le_010']=all(x['ks']<=.10 for x in numeric.values())
    cats={'weekday_ny':dg.weighted_cat(me.donor_weekday_ny,me.recipient_weekday_ny,w),'upper_z4_count_bucket':dg.weighted_cat(me.donor_upper_z4_count_bucket,me.recipient_upper_z4_count_bucket,w)}
    report['donor_equal_categorical_balance']=cats;checks['categorical_tvd_le_010']=all(x['total_variation_distance']<=.10 for x in cats.values());checks['categorical_max_abs_prop_diff_le_010']=all(x['max_abs_proportion_difference']<=.10 for x in cats.values())

    support=[]
    for eid,g in me.groupby('donor_episode_id',sort=False):
        dl=int(g.donor_path_snapshots.iloc[0]);need=max(1,int(np.ceil(.5*dl)));support.append(int((g.path_snapshots.astype(int)>=need).sum())>=2)
    path_frac=float(np.mean(support)) if support else 0.0;report['eligible_donors_two_half_paths_fraction']=path_frac;checks['path_support_ge_070']=path_frac>=.70
    fam={}
    for k,g in starts.groupby('current_family',sort=True):fam[str(k)]={'donors':int(len(g)),'fraction_ge2':float((g._n>=2).mean())}
    report['coverage_by_family_report_only']=fam

    out={'status':'E_ZONE_SCORE_BUY_US_V2_R4_PREOUTCOME_QA_PASS' if all(checks.values()) else 'E_ZONE_SCORE_BUY_US_V2_R4_PREOUTCOME_QA_FAIL','future_price_outcomes_used':False,'checks':checks,'diagnostics':report,'counts':{'features':int(len(f)),'display_all':int(len(da)),'pool':int(len(pool)),'context':int(len(ctx)),'placebo_rows':int(len(pl)),'matching_rows':int(len(m)),'donor_episodes':int(len(starts))},'sha256':{k:sha(getattr(a,k.replace('-','_'))) for k in ['features','display_all','full_pool','context','placebos','matching','instrument_manifest','placebo_manifest']}}
    Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,indent=2,sort_keys=True))
    if not all(checks.values()):raise RuntimeError('R4_PREOUTCOME_QA_FAIL')


if __name__=='__main__':main()
