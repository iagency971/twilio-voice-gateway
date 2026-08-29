#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import xau_e_intrinsic_snapshot_v1 as core


def parse_args():
    p = argparse.ArgumentParser(description='Independent QA for E_INTRINSIC_SNAPSHOT_V1')
    p.add_argument('--candidates', required=True)
    p.add_argument('--ledger', required=True)
    p.add_argument('--manifest', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--expected-source-payload-sha256', default=None)
    return p.parse_args()


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def read_ledger(path: Path) -> pd.DataFrame:
    d=pd.read_csv(path)
    if list(d.columns) != list(core.OUTPUT_COLUMNS):
        raise AssertionError(f'ledger schema mismatch: {list(d.columns)}')
    d['snapshot_time_utc']=pd.to_datetime(d['snapshot_time_utc'],utc=True)
    d['prior_snapshot_time_utc']=pd.to_datetime(d['prior_snapshot_time_utc'],utc=True,errors='coerce')
    return d


def independent_reconstruct(candidates: pd.DataFrame) -> pd.DataFrame:
    rows=[]; prev=[]; prev_t=None; nxt=1
    for t,g in candidates.groupby('time',sort=True):
        t=pd.Timestamp(t); g=g.sort_values(['entry_rank','center','family'],kind='mergesort')
        contig=prev_t is not None and t-prev_t==core.SNAPSHOT_STEP
        used=set(); cur=[]
        for _,r in g.iterrows():
            slot=int(r.entry_rank); v=float(r.v60); cen=float(r.center); lo=float(r.zlo); hi=float(r.zhi); fam=str(r.family)
            matches=[]
            if contig:
                for j,p in enumerate(prev):
                    if j in used: continue
                    tol=core.MATCH_TOL_V*max(float(p['v']),v)
                    ok=(min(float(p['zhi']),hi)+core.EPS>=max(float(p['zlo']),lo)) or abs(float(p['center'])-cen)<=tol+core.EPS
                    if ok: matches.append((abs(float(p['center'])-cen),int(p['seq']),j,p))
            if matches:
                _,_,j,p=min(matches,key=lambda x:(x[0],x[1],x[2])); used.add(j)
                seq=int(p['seq']); age=int(p['age'])+1; origin=str(p['origin']); prior_slot=int(p['slot']); prior_time=p['time']
            else:
                seq=nxt; nxt+=1; age=1; origin=fam; prior_slot=None; prior_time=None
            eid=f'EIV1-{seq:08d}'
            rows.append((t,slot,eid,seq,age,origin,prior_slot,prior_time))
            cur.append({'seq':seq,'age':age,'origin':origin,'slot':slot,'center':cen,'zlo':lo,'zhi':hi,'v':v,'time':t})
        prev=cur; prev_t=t
    return pd.DataFrame(rows,columns=['snapshot_time_utc','display_slot_rank','episode_id','episode_seq','episode_age_c5','origin_family','prior_display_slot_rank','prior_snapshot_time_utc'])


def prefix_invariance(candidates: pd.DataFrame, ledger: pd.DataFrame) -> bool:
    times=sorted(candidates['time'].drop_duplicates())
    if len(times)<10: return True
    cut=times[max(1,int(len(times)*0.67))-1]
    pref=candidates[candidates['time']<=cut].copy()
    rec=core.assign_episodes(pref)
    a=ledger[ledger['snapshot_time_utc']<=cut].copy().reset_index(drop=True)
    b=rec.copy(); b['snapshot_time_utc']=pd.to_datetime(b['snapshot_time_utc'],utc=True)
    cols=['episode_id','episode_seq','snapshot_time_utc','display_slot_rank','current_family','origin_family','center','zlo','zhi','v_snapshot','zone_width_v','episode_age_c5']
    a=a[cols].reset_index(drop=True); b=b[cols].reset_index(drop=True)
    for c in cols:
        if c in {'center','zlo','zhi','v_snapshot','zone_width_v'}:
            if not np.allclose(pd.to_numeric(a[c]),pd.to_numeric(b[c]),rtol=0,atol=1e-9,equal_nan=True): return False
        elif c=='snapshot_time_utc':
            if not pd.to_datetime(a[c],utc=True).equals(pd.to_datetime(b[c],utc=True)): return False
        else:
            if a[c].astype(str).tolist()!=b[c].astype(str).tolist(): return False
    return True


def main():
    a=parse_args(); cand_path=Path(a.candidates); led_path=Path(a.ledger); man_path=Path(a.manifest)
    hashes=core.source_hashes(cand_path)
    binary_sha=hashes['compressed_binary_sha256']; payload_sha=hashes['decompressed_payload_sha256']
    if a.expected_source_payload_sha256 and payload_sha != a.expected_source_payload_sha256:
        raise AssertionError(f'source payload SHA mismatch before QA: got {payload_sha}, expected {a.expected_source_payload_sha256}')

    cand=core.read_candidates(cand_path); led=read_ledger(led_path); man=json.loads(man_path.read_text())
    checks={}
    checks['source_payload_sha_matches_expected']= (a.expected_source_payload_sha256 is None or payload_sha==a.expected_source_payload_sha256)
    checks['manifest_source_payload_sha_matches']= man['source']['decompressed_payload_sha256']==payload_sha
    checks['manifest_source_binary_sha_matches']= man['source']['compressed_binary_sha256']==binary_sha
    checks['manifest_ledger_sha_matches']= man['ledger']['sha256']==sha256_file(led_path)
    checks['row_count_matches']= len(led)==len(cand)
    checks['max_three_per_snapshot']= int(led.groupby('snapshot_time_utc').size().max())<=3
    checks['slot_unique_per_snapshot']= not led.duplicated(['snapshot_time_utc','display_slot_rank']).any()
    checks['geometry_valid']= bool(((led.zlo<=led.center)&(led.center<=led.zhi)&(led.v_snapshot>0)&(led.zone_width_v>=0)).all())
    ny=led['snapshot_time_utc'].dt.tz_convert(core.TZ_NY)
    checks['all_rows_in_us_session']= bool(((ny.dt.hour>=8)&(ny.dt.hour<17)).all())
    checks['origin_family_stable_per_episode']= bool((led.groupby('episode_id')['origin_family'].nunique()<=1).all())
    checks['session_date_stable_per_episode']= bool((led.groupby('episode_id')['session_date_ny'].nunique()<=1).all())
    checks['episode_age_starts_at_one']= bool((led.groupby('episode_id')['episode_age_c5'].min()==1).all())
    age_ok=True
    for _,g in led.sort_values(['episode_seq','snapshot_time_utc']).groupby('episode_id'):
        ages=g.episode_age_c5.to_numpy(int)
        if not np.array_equal(ages,np.arange(1,len(ages)+1)): age_ok=False; break
    checks['episode_age_increments_by_one']=age_ok
    checks['no_forbidden_output_columns']= len(core._forbidden_input_columns(led.columns))==0
    checks['model_feature_whitelist_exact']= tuple(man['model_feature_whitelist'])==core.MODEL_FEATURE_WHITELIST
    checks['z4_separated_from_intrinsic_model']= man.get('intrinsic_model_row_eligibility') == 'current_family != Z4 AND origin_family != Z4'

    indep=independent_reconstruct(cand)
    left=led[['snapshot_time_utc','display_slot_rank','episode_id','episode_seq','episode_age_c5','origin_family','prior_display_slot_rank','prior_snapshot_time_utc']].copy()
    right=indep.copy()
    left['prior_display_slot_rank']=pd.to_numeric(left['prior_display_slot_rank'],errors='coerce')
    right['prior_display_slot_rank']=pd.to_numeric(right['prior_display_slot_rank'],errors='coerce')
    left['prior_snapshot_time_utc']=pd.to_datetime(left['prior_snapshot_time_utc'],utc=True,errors='coerce')
    right['prior_snapshot_time_utc']=pd.to_datetime(right['prior_snapshot_time_utc'],utc=True,errors='coerce')
    checks['independent_identity_parity']=left.reset_index(drop=True).equals(right.reset_index(drop=True))
    checks['prefix_invariance_no_repaint']=prefix_invariance(cand,led)

    hashes_ok=True
    for _,r in led.iterrows():
        rec={k:r[k] for k in core.OUTPUT_COLUMNS if k!='row_sha256'}
        for k,v in list(rec.items()):
            if pd.isna(v): rec[k]=None
            elif isinstance(v,pd.Timestamp): rec[k]=v.isoformat()
            elif hasattr(v,'item'): rec[k]=v.item()
        if core.deterministic_row_hash(rec)!=str(r.row_sha256): hashes_ok=False; break
    checks['row_hashes_recompute']=hashes_ok

    passed=all(checks.values())
    out={
      'status':'E_INTRINSIC_SNAPSHOT_V1_REAL_QA_PASS' if passed else 'E_INTRINSIC_SNAPSHOT_V1_REAL_QA_FAIL',
      'future_price_outcomes_used':False,
      'checks':checks,
      'counts':{'rows':int(len(led)),'episodes':int(led.episode_id.nunique()),'snapshots':int(led.snapshot_time_utc.nunique()),'sessions_ny':int(led.session_date_ny.nunique())},
      'source_compressed_binary_sha256':binary_sha,
      'source_decompressed_payload_sha256':payload_sha,
      'ledger_sha256':sha256_file(led_path),
      'authorization': 'READY_FOR_PRO_PRE_OUTCOME_GATE' if passed else 'BLOCK_OUTCOME_OPENING'
    }
    Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True))
    if not passed: raise SystemExit(2)

if __name__=='__main__': main()
