#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd

EF={'ESM_BOTH_G120M','EPM_M1_R2_A8H','EWM_G60M','ES_M1_8H_R2_T0.50'}
FORB=('primary_binary','primary_class','favorable','adverse_level','event_bar','outcome','mfe','mae','success','reaction')

def args():
 p=argparse.ArgumentParser();
 for x in ['features','display-all','full-pool','context','placebos','matching','instrument-manifest']:p.add_argument('--'+x,required=True)
 p.add_argument('--output',required=True);return p.parse_args()
def read(p):
 d=pd.read_csv(p,compression='infer',float_precision='round_trip')
 for c in ['time','snapshot_time_utc','feature_available_time_utc']:
  if c in d.columns:d[c]=pd.to_datetime(d[c],utc=True)
 return d
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 a=args();f=read(a.features);da=read(a.display_all);pool=read(a.full_pool);ctx=read(a.context);pl=read(a.placebos);m=read(a.matching);im=json.load(open(a.instrument_manifest));checks={}
 checks['instrument_status_pass']=im.get('status')=='E_ZONE_V2_INSTRUMENT_OUTCOME_BLIND_PASS'
 checks['v04_parity_pass']=im.get('geometry_parity') is None or bool(im['geometry_parity'].get('pass'))
 checks['features_nonempty']=len(f)>0;checks['features_only_E']=set(f.current_family.astype(str)).issubset(EF);checks['slot_original_1_3']=set(f.display_slot_rank.astype(int)).issubset({1,2,3})
 checks['feature_available_t_plus_1']=bool((pd.to_datetime(f.feature_available_time_utc,utc=True)==pd.to_datetime(f.snapshot_time_utc,utc=True)+pd.Timedelta(minutes=1)).all())
 checks['valid_geometry']=bool(((f.zlo<=f.center)&(f.center<=f.zhi)&(f.v_snapshot>0)&(f.zone_width_v>=0)).all())
 checks['no_outcome_columns_features']=not any(any(t in c.lower() for t in FORB) for c in f.columns)
 checks['no_outcome_columns_placebo_paths']=not any(any(t in c.lower() for t in FORB) for c in pl.columns)
 checks['placebo_feature_available_t_plus_1']=bool((pd.to_datetime(pl.feature_available_time_utc,utc=True)==pd.to_datetime(pl.snapshot_time_utc,utc=True)+pd.Timedelta(minutes=1)).all())
 checks['matching_same_minute']=bool((m.donor_minute_of_session.astype(int)==m.recipient_minute_of_session.astype(int)).all())
 checks['matching_width_exact']=bool(np.allclose(m.donor_zone_width_v,m.recipient_transplanted_zone_width_v,rtol=0,atol=2e-12))
 checks['matching_distance_exact']=bool(np.allclose(m.donor_distance_v,m.recipient_distance_v,rtol=0,atol=2e-12))
 checks['matching_logv_caliper']=bool((np.abs(m.donor_log_v_snapshot-m.recipient_log_v_snapshot)<=.20+1e-12).all())
 checks['matching_z4_caliper']=bool((np.abs(m.donor_nearest_upper_z4_dist_v-m.recipient_nearest_upper_z4_dist_v)<=.25+1e-12).all())
 # Recompute neutrality for every retained placebo snapshot.
 pb={pd.Timestamp(t):g for t,g in pool.groupby('time',sort=False)};bad=0
 for _,r in pl.iterrows():
  g=pb.get(pd.Timestamp(r.snapshot_time_utc));
  if g is None or not len(g):continue
  ov=np.minimum(float(r.zhi),g.zhi.to_numpy(float))>=np.maximum(float(r.zlo),g.zlo.to_numpy(float));near=np.abs(g.center.to_numpy(float)-float(r.center))<=.20*float(r.v_snapshot)+1e-12
  if bool(np.any(ov|near)):bad+=1
 checks['placebo_neutrality_recompute']=bad==0
 # Row hashes are immutable audit fields, not outcome fields.
 checks['row_hash_unique_within_snapshot_slot']=not f.duplicated(['snapshot_time_utc','display_slot_rank']).any()
 out={'status':'E_ZONE_SCORE_BUY_US_V2_PREOUTCOME_QA_PASS' if all(checks.values()) else 'E_ZONE_SCORE_BUY_US_V2_PREOUTCOME_QA_FAIL','checks':checks,'counts':{'features':len(f),'display_all':len(da),'pool':len(pool),'context':len(ctx),'placebo_rows':len(pl),'matching_rows':len(m)},'sha256':{k:sha(getattr(a,k.replace('-','_'))) for k in ['features','display_all','full_pool','context','placebos','matching','instrument_manifest']}}
 Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,indent=2,sort_keys=True))
 if not all(checks.values()):raise RuntimeError('PREOUTCOME_QA_FAIL')
if __name__=='__main__':main()
