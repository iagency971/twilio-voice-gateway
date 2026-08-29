#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab',HERE/'xau_e_display_episode_reaction_labeler_v1.py')
lab=importlib.util.module_from_spec(spec);sys.modules[spec.name]=lab;spec.loader.exec_module(lab)

BASE=pd.Timestamp('2026-01-05T13:00:00Z')  # 08:00 New York


def L(eid='E1',snap=BASE,zlo=99.,zhi=100.,v=2.,pers=1):
    return {
      'display_episode_id':eid,'snapshot_time_utc':snap,'feature_available_time_utc':snap+pd.Timedelta(minutes=1),
      'session_date_ny':'2026-01-05','current_family':'EPM_M1_R2_A8H','center':99.5,'zlo':zlo,'zhi':zhi,'v_snapshot':v,
      'zone_width_v':(zhi-zlo)/v,'display_persistence_c5':pers,'row_sha256':eid+str(snap)
    }


def B(minute,o=101.,h=101.2,l=100.5,c=101.):
    return {'time':BASE+pd.Timedelta(minutes=minute),'open':o,'high':h,'low':l,'close':c}


def one(bars,led):
    out,_=lab.label_all(pd.DataFrame(bars),pd.DataFrame(led));return out.iloc[0].to_dict()


def run():
    checks={}
    # Snapshot at 13:00 uses its close and is only available 13:01. 13:00 cannot arm; 13:01 can.
    r=one([B(0,c=102),B(1,c=102),B(2,h=101,l=99.5,c=100.5),B(3,h=101.2,l=100,c=101)], [L()])
    checks['feature_not_available_on_snapshot_open']=pd.Timestamp(r['arm_bar_open_time_utc'])==BASE+pd.Timedelta(minutes=1)
    checks['arming_bar_not_contact']=pd.Timestamp(r['contact_bar_open_time_utc'])==BASE+pd.Timedelta(minutes=2)

    # Contact-bar high is above F=101, but must not be favorable; next bar determines the result.
    r=one([B(1,c=102),B(2,h=103,l=99.5,c=100.5),B(3,h=101.2,l=100,c=101)], [L()])
    checks['contact_bar_favorable_high_ignored']=r['primary_class']=='FAVORABLE_FIRST' and pd.Timestamp(r['event_bar_open_time_utc'])==BASE+pd.Timedelta(minutes=3)

    # Contact bar closes below frozen zlo => immediate invalidation.
    r=one([B(1,c=102),B(2,h=103,l=98.5,c=98.9)], [L()])
    checks['contact_bar_close_below_invalidates']=r['primary_class']=='INVALIDATION_FIRST' and int(r['completed_post_contact_bars'])==0

    # Both post-contact favorable high and invalidating close => conservative ambiguity / binary 0.
    r=one([B(1,c=102),B(2,h=100.5,l=99.5,c=100),B(3,h=102,l=98.5,c=98.9)], [L()])
    checks['same_bar_ambiguity_binary_zero']=r['primary_class']=='AMBIGUOUS_SAME_BAR' and int(r['primary_binary_label'])==0

    # No continuation: display interval is [13:01,13:06). Arm at 13:05 close -> effective 13:06, then episode is expired.
    r=one([B(5,c=102),B(6,h=100,l=99.5,c=100)], [L()])
    checks['episode_expiry_discards_arm']=r['selection_status']=='NO_CONTACT_BEFORE_EPISODE_END'

    # Continuation snapshot at 13:05 becomes available at 13:06; exact 13:06 contact uses new geometry.
    led=[L(),L(snap=BASE+pd.Timedelta(minutes=5),zlo=98.,zhi=99.,pers=2)]
    r=one([B(1,c=102),B(6,h=99.5,l=98.5,c=99.2),B(7,h=101,l=99,c=100)],led)
    checks['exact_update_time_uses_continuation_geometry']=pd.Timestamp(r['contact_bar_open_time_utc'])==BASE+pd.Timedelta(minutes=6) and float(r['zhi0'])==99.

    # Missing minutes do not consume the 30-bar horizon: only available completed bars count.
    bars=[B(1,c=102),B(2,h=100.5,l=99.5,c=100)]
    # Keep episode alive using multiple snapshots, then post-contact available bars at sparse timestamps.
    led=[L(snap=BASE+pd.Timedelta(minutes=5*k),pers=k+1) for k in range(12)]
    for j in range(3,30):bars.append(B(j,h=100.5,l=99.5,c=100))
    bars.append(B(35,h=101.5,l=100,c=101))
    r=one(bars,led)
    checks['available_bar_count_not_wall_clock']=r['primary_class']=='FAVORABLE_FIRST' and int(r['completed_post_contact_bars'])==28

    # Conflicting duplicate OHLC must fail closed.
    failed=False
    try:lab.label_all(pd.DataFrame([B(1,c=102),{**B(1,c=102),'close':103}]),pd.DataFrame([L()]))
    except RuntimeError:failed=True
    checks['conflicting_duplicates_fail_closed']=failed

    passed=all(checks.values())
    out={'status':'SYNTHETIC_REACTION_LABELER_V1_PASS' if passed else 'SYNTHETIC_REACTION_LABELER_V1_FAIL','checks':checks,'real_outcomes_used':False}
    print(json.dumps(out,indent=2,sort_keys=True))
    if not passed:raise SystemExit(2)

if __name__=='__main__':run()
