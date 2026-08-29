#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

FEATURES = ['zone_width_v','display_persistence_c5','current_family']
EXACT = {'ESM_BOTH_G120M','EPM_M1_R2_A8H','EWM_G60M'}
ES = 'ES_M1_8H_R2_T0.50'


def args():
    p=argparse.ArgumentParser()
    p.add_argument('--ledger',required=True)
    p.add_argument('--dev-ledger',required=True)
    p.add_argument('--replication-ledger',required=True)
    p.add_argument('--builder-manifest',required=True)
    p.add_argument('--provenance-manifest',required=True)
    p.add_argument('--output',required=True)
    return p.parse_args()


def canon(v):
    if isinstance(v,pd.Timestamp): return v.tz_convert('UTC').isoformat()
    if pd.isna(v): return None
    if isinstance(v,(np.integer,int)): return int(v)
    if isinstance(v,(np.floating,float)): return format(float(v),'.17g')
    if isinstance(v,(bool,np.bool_)): return bool(v)
    return str(v)


def rh(row):
    d={k:canon(v) for k,v in sorted(row.items()) if k!='row_sha256'}
    return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def ms(x):
    if pd.isna(x) or str(x)=='': return set()
    return {q for q in str(x).split(';') if q}


def load(p):
    d=pd.read_csv(p,compression='infer')
    for c in ['snapshot_time_utc','bar_open_time_utc','bar_close_time_utc','feature_available_time_utc','prior_snapshot_time_utc']:
        d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    return d


def main():
    a=args();d=load(a.ledger);dev=load(a.dev_ledger);rep=load(a.replication_ledger)
    bm=json.load(open(a.builder_manifest));pm=json.load(open(a.provenance_manifest))
    checks={}
    checks['provenance_geometry_parity_pass']=pm.get('geometry_parity',{}).get('pass') is True
    checks['builder_outcome_blind']=bm.get('future_price_outcomes_used') is False
    checks['feature_whitelist_exact']=bm.get('model_feature_whitelist')==FEATURES
    checks['nonempty']=len(d)>0
    checks['no_z4_rows']=not bool((d.current_family=='Z4').any())
    checks['unique_episode_snapshot']=not bool(d.duplicated(['display_episode_id','snapshot_time_utc']).any())
    checks['unique_slot_snapshot']=not bool(d.duplicated(['snapshot_time_utc','display_slot_rank']).any())
    checks['valid_geometry']=bool(((d.zhi>=d.zlo)&(d.v_snapshot>0)&np.isfinite(d.zone_width_v)&(d.zone_width_v>=0)).all())
    checks['availability_exact_plus_1m']=bool((d.feature_available_time_utc==d.snapshot_time_utc+pd.Timedelta(minutes=1)).all())
    checks['bar_close_exact_plus_1m']=bool((d.bar_close_time_utc==d.bar_open_time_utc+pd.Timedelta(minutes=1)).all())
    checks['bar_open_equals_snapshot']=bool((d.bar_open_time_utc==d.snapshot_time_utc).all())
    checks['dev_nonempty']=len(dev)>0
    checks['replication_nonempty']=len(rep)>0
    checks['dev_window_exact']=bool(((dev.snapshot_time_utc>=pd.Timestamp('2024-08-01T00:00:00Z'))&(dev.snapshot_time_utc<pd.Timestamp('2025-08-01T00:00:00Z'))).all())
    checks['rep_window_exact']=bool(((rep.snapshot_time_utc>=pd.Timestamp('2025-08-01T00:00:00Z'))&(rep.snapshot_time_utc<pd.Timestamp('2026-08-01T00:00:00Z'))).all())
    checks['split_row_parity']=len(dev)==int((d.feature_window=='DEV_HISTORY').sum()) and len(rep)==int((d.feature_window=='HISTORICAL_REPLICATION_DIAGNOSTIC').sum())

    family_ok=True;session_ok=True;age_ok=True;contig_ok=True;prov_ok=True
    for eid,g in d.groupby('display_episode_id',sort=False):
        g=g.sort_values('snapshot_time_utc')
        if g.current_family.nunique()!=1: family_ok=False
        if g.session_date_ny.nunique()!=1: session_ok=False
        ages=g.display_persistence_c5.to_numpy(int)
        if not np.array_equal(ages,np.arange(1,len(g)+1)): age_ok=False
        if len(g)>1 and not bool((g.snapshot_time_utc.diff().iloc[1:]==pd.Timedelta(minutes=5)).all()): contig_ok=False
        fam=str(g.current_family.iloc[0])
        if fam in EXACT and g.source_provenance_id.nunique()!=1: prov_ok=False
        if fam==ES and len(g)>1:
            vals=list(g.source_provenance_members)
            if any(not (ms(vals[i-1]) & ms(vals[i])) for i in range(1,len(vals))): prov_ok=False
    checks['one_family_per_episode']=family_ok
    checks['one_session_per_episode']=session_ok
    checks['persistence_starts_1_increments_1']=age_ok
    checks['episode_c5_contiguous']=contig_ok
    checks['provenance_continuity_rule']=prov_ok

    # Independently recompute row hashes using the serialized ledger values.
    hash_ok=True
    for _,r in d.iterrows():
        x=r.to_dict();exp=str(x.pop('row_sha256'));x['row_sha256']=exp
        if rh(x)!=exp:
            hash_ok=False;break
    checks['row_hashes_recompute']=hash_ok

    forbidden=[c for c in d.columns if any(t in c.lower() for t in ['contact','trigger','mfe','mae','success','outcome','reaction','p&l','return'])]
    checks['no_outcome_columns']=len(forbidden)==0
    passed=all(checks.values())
    lengths=d.groupby('display_episode_id').size()
    out={
      'status':'E_DISPLAY_EPISODE_SNAPSHOT_V1_REAL_QA_PASS' if passed else 'E_DISPLAY_EPISODE_SNAPSHOT_V1_QA_FAIL',
      'future_price_outcomes_used':False,'checks':checks,'forbidden_columns_found':forbidden,
      'rows':int(len(d)),'episodes':int(d.display_episode_id.nunique()),'sessions':int(d.session_date_ny.nunique()),
      'dev_rows':int(len(dev)),'dev_sessions':int(dev.session_date_ny.nunique()),
      'replication_rows':int(len(rep)),'replication_sessions':int(rep.session_date_ny.nunique()),
      'single_snapshot_episode_rate':float((lengths==1).mean()),
      'episode_length_median':float(lengths.median()),'episode_length_p90':float(lengths.quantile(.90)),
      'authorization':'READY_FOR_NEW_PRO_PRE_OUTCOME_GATE' if passed else 'BLOCK_OUTCOME_OPENING',
      'real_outcome_generation':'FORBIDDEN'
    }
    Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True))
    if not passed: raise SystemExit(3)

if __name__=='__main__':main()
