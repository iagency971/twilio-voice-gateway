#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

HERE=Path(__file__).resolve().parent


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

old=load_module('c1_session_parent_v11',HERE/'xau_ebuy_c1_refresh_causal_reaction_v1_1.py')
base=old.base
loc=old.loc
WINDOWS=old.WINDOWS
FROZEN_ANCHORS=old.FROZEN_ANCHORS
BOOT_SEED=old.BOOT_SEED
BOOT_N=old.BOOT_N
AMBIG=old.AMBIG
summarize_causal=old.summarize_causal
paired_day_bootstrap=old.paired_day_bootstrap
qpack=old.qpack


def episode_match(old_states,z,tol,used):
    cand=[]
    for j,st in enumerate(old_states):
        if j in used: continue
        if base.match(st['zone'],z,tol): cand.append((abs(float(st['zone'].center)-float(z.center)),j,st))
    return min(cand,key=lambda x:(x[0],x[1])) if cand else None


def build_runtime_states(prev_states,prev_s,s,zs,cadence,next_id):
    contig=prev_s is not None and pd.Timestamp(s['time'])-pd.Timestamp(prev_s['time'])==pd.Timedelta(minutes=cadence)
    tol=.25*max(float(prev_s['v']),float(s['v'])) if contig else 0.0
    used=set();cur=[]
    for slot,z in enumerate(zs,1):
        m=episode_match(prev_states,z,tol,used) if contig else None
        if m is not None:
            _,j,prior=m;used.add(j)
            st={'id':prior['id'],'age':prior['age']+1,'zone':z,'slot':slot,
                'armed':bool(prior['armed']),'arm_time':prior['arm_time'],'arm_close':prior['arm_close'],
                'consumed_ny_day':prior.get('consumed_ny_day'),'origin_family':prior['origin_family']}
        else:
            st={'id':next_id,'age':1,'zone':z,'slot':slot,'armed':False,'arm_time':None,'arm_close':None,
                'consumed_ny_day':None,'origin_family':z.family};next_id+=1
        cur.append(st)
    return cur,next_id


def causal_contacts(raw,active,z4,snaps,displays,cadence,lo,hi):
    targets=base.target_map(z4,snaps);contacts=[];trades=[]
    prev_states=[];prev_s=None;next_id=1
    trading_days=sorted({pd.Timestamp(s['time']).tz_convert('America/New_York').date().isoformat() for s in snaps})
    for s,zs in zip(snaps,displays):
        t=pd.Timestamp(s['time'])
        if not (lo<=t<hi): continue
        ny_day=t.tz_convert('America/New_York').date().isoformat()
        states,next_id=build_runtime_states(prev_states,prev_s,s,zs,cadence,next_id)
        for st in states:
            z=st['zone']
            if not st['armed'] and float(s['close'])>float(z.zhi):
                st['armed']=True;st['arm_time']=t;st['arm_close']=float(s['close'])
        tp=targets.get(t);i0,i1=old.raw_bounds_inclusive(raw,t,cadence)
        if tp is not None and i1>=i0:
            for st in states:
                if st.get('consumed_ny_day')==ny_day: continue
                z=st['zone'];contact_idx=None
                for j in range(max(0,i0),min(len(raw)-1,i1)+1):
                    r=raw.loc[j]
                    if not st['armed']:
                        if float(r.close)>float(z.zhi):
                            st['armed']=True;st['arm_time']=pd.Timestamp(r.time);st['arm_close']=float(r.close)
                        continue
                    if float(r.high)>=float(z.zlo) and float(r.low)<=float(z.zhi):
                        contact_idx=j;break
                if contact_idx is None: continue
                ct=pd.Timestamp(raw.at[contact_idx,'time']);contact_day=ct.tz_convert('America/New_York').date().isoformat()
                st['consumed_ny_day']=contact_day
                v=float(s['v']);rr=raw.loc[contact_idx];width=max(float(z.zhi)-float(z.zlo),1e-12)
                contact={'episode_id':int(st['id']),'state_time':t,'contact_time':ct,'cadence_min':int(cadence),
                         'family':z.family,'episode_origin_family':st['origin_family'],'slot_rank':int(st['slot']),
                         'episode_age_states':int(st['age']),'episode_age_active_min':int(st['age']*cadence),
                         'zlo':float(z.zlo),'center':float(z.center),'zhi':float(z.zhi),
                         'zone_width_v':float(width/v),'v_contact':v,'arm_time':st['arm_time'],'arm_close':st['arm_close'],
                         'tp1_zlo':float(tp['zlo']),'tp1_center':float(tp['center']),'tp1_zhi':float(tp['zhi']),
                         'tp1_distance_from_touch_ref_v':float((float(tp['zlo'])-float(z.zhi))/v),
                         'minutes_to_us_end':float((base.ny_end(ct)-ct).total_seconds()/60.0),
                         'us_subperiod':base.subperiod(ct),'ny_day':contact_day,
                         'contact_bull':int(float(rr.close)>float(rr.open))}
                contacts.append(contact)
                ej=base.raw_index(raw,base.ny_end(ct)-pd.Timedelta(nanoseconds=1),'right')
                rec=base.trigger_outcome(raw,contact_idx,ej,z,tp,v,'BULL_REJECTION')
                trades.append({**contact,**rec})
        prev_states=states;prev_s=s
    return contacts,trades,trading_days


# Patch the parent module before delegating to its provenance/stability/main pipeline.
old.build_runtime_states=build_runtime_states
old.causal_contacts=causal_contacts


def main():
    old.main()


if __name__=='__main__':
    main()
