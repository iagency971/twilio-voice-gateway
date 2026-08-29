#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd

import xau_e_intrinsic_snapshot_v1 as core


def df(rows):
    d=pd.DataFrame(rows)
    d['time']=pd.to_datetime(d['time'],utc=True)
    return d


def base_row(t,slot,family,center,zlo,zhi,v=1.0):
    return {'time':t,'v60':v,'entry_rank':slot,'family':family,'center':center,'zlo':zlo,'zhi':zhi}


def test_identity_survives_slot_swap():
    c=df([
      base_row('2026-08-03T12:00:00Z',1,'EWM_G60M',100,99.8,100.2),
      base_row('2026-08-03T12:00:00Z',2,'EPM_M1_R2_A8H',98,97.8,98.2),
      base_row('2026-08-03T12:05:00Z',1,'EPM_M1_R2_A8H',98.05,97.8,98.2),
      base_row('2026-08-03T12:05:00Z',2,'EWM_G60M',100.05,99.8,100.2),
    ])
    out=core.assign_episodes(c)
    a=out[out.current_family=='EWM_G60M'].sort_values('snapshot_time_utc')
    b=out[out.current_family=='EPM_M1_R2_A8H'].sort_values('snapshot_time_utc')
    assert a.episode_id.nunique()==1 and b.episode_id.nunique()==1
    assert list(a.display_slot_rank)==[1,2]
    assert list(a.episode_age_c5)==[1,2]


def test_gap_breaks_identity():
    c=df([
      base_row('2026-08-03T12:00:00Z',1,'EWM_G60M',100,99.8,100.2),
      base_row('2026-08-03T12:10:00Z',1,'EWM_G60M',100,99.8,100.2),
    ])
    out=core.assign_episodes(c)
    assert out.episode_id.nunique()==2
    assert list(out.episode_age_c5)==[1,1]


def test_origin_family_stays_with_episode_when_current_family_changes():
    c=df([
      base_row('2026-08-03T12:00:00Z',1,'EWM_G60M',100,99.8,100.2),
      base_row('2026-08-03T12:05:00Z',1,'ESM_BOTH_G120M',100.05,99.85,100.25),
    ])
    out=core.assign_episodes(c)
    assert out.episode_id.nunique()==1
    assert list(out.origin_family)==['EWM_G60M','EWM_G60M']
    assert list(out.family_changed)==[0,1]


def test_non_matching_zone_gets_new_identity():
    c=df([
      base_row('2026-08-03T12:00:00Z',1,'EWM_G60M',100,99.8,100.2,v=1),
      base_row('2026-08-03T12:05:00Z',1,'EWM_G60M',101,100.8,101.2,v=1),
    ])
    out=core.assign_episodes(c)
    assert out.episode_id.nunique()==2


def test_forbidden_future_column_rejected():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'c.csv'
        d=pd.DataFrame([base_row('2026-08-03T12:00:00Z',1,'EWM_G60M',100,99.8,100.2)])
        d['mfe30_v']=1.0; d.to_csv(p,index=False)
        try:
            core.read_candidates(p)
            raise AssertionError('future column should have been rejected')
        except ValueError as e:
            assert 'forbidden' in str(e)


def test_context_columns_are_dropped_not_features():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'c.csv'
        d=pd.DataFrame([base_row('2026-08-03T12:00:00Z',1,'EWM_G60M',100,99.8,100.2)])
        d['upper_z4_count']=3; d['nearest_upper_z4_dist_v']=1.2; d['distance_v']=0.5; d.to_csv(p,index=False)
        x=core.read_candidates(p)
        out=core.assign_episodes(x)
        assert 'upper_z4_count' not in out.columns
        assert 'nearest_upper_z4_dist_v' not in out.columns
        assert 'distance_v' not in out.columns
        assert 'display_slot_rank' not in core.MODEL_FEATURE_WHITELIST


def test_deterministic_gzip_and_manifest():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); src=td/'c.csv'; out1=td/'a.csv.gz'; out2=td/'b.csv.gz'; m1=td/'m1.json'; m2=td/'m2.json'
        pd.DataFrame([
          base_row('2026-08-03T12:00:00Z',1,'EWM_G60M',100,99.8,100.2),
          base_row('2026-08-03T12:05:00Z',1,'EWM_G60M',100.05,99.85,100.25),
        ]).to_csv(src,index=False)
        core.run(src,out1,m1); core.run(src,out2,m2)
        assert out1.read_bytes()==out2.read_bytes()
        a=json.loads(m1.read_text()); b=json.loads(m2.read_text())
        assert a['ledger']['sha256']==b['ledger']['sha256']


def run_all():
    tests=[v for k,v in globals().items() if k.startswith('test_') and callable(v)]
    for t in sorted(tests,key=lambda f:f.__name__): t()
    print(json.dumps({'status':'E_INTRINSIC_SNAPSHOT_V1_SYNTHETIC_TESTS_PASS','tests':len(tests)},indent=2))

if __name__=='__main__': run_all()
