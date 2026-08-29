#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

GO_TOKEN = 'GO_DEV_OUTCOME_OPENING'


def normalize_m1(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    d=raw.copy()
    if 'time' not in d.columns:
        if 'timestamp' not in d.columns: raise RuntimeError('M1 requires time or timestamp')
        d['time']=pd.to_datetime(d['timestamp'],unit='ms',utc=True)
    else:d['time']=pd.to_datetime(d['time'],utc=True)
    for c in ['open','high','low','close']:
        d[c]=pd.to_numeric(d[c],errors='raise').astype(float)
    dup=d[d.duplicated('time',keep=False)]
    conflicting=0
    if len(dup):
        for _,g in dup.groupby('time'):
            if len(g[['open','high','low','close']].drop_duplicates())>1:conflicting+=1
    if conflicting: raise RuntimeError(f'conflicting duplicate M1 timestamps: {conflicting}')
    exact_dups=int(d.duplicated(['time','open','high','low','close']).sum())
    d=d.drop_duplicates('time',keep='first').sort_values('time').reset_index(drop=True)
    return d,{'exact_duplicate_rows_removed':exact_dups,'conflicting_duplicate_timestamps':conflicting}


def prep_ledger(ledger: pd.DataFrame) -> pd.DataFrame:
    d=ledger.copy()
    for c in ['snapshot_time_utc','feature_available_time_utc']:
        d[c]=pd.to_datetime(d[c],utc=True)
    req={'display_episode_id','session_date_ny','current_family','center','zlo','zhi','v_snapshot','zone_width_v','display_persistence_c5','feature_available_time_utc'}
    miss=sorted(req-set(d.columns))
    if miss:raise RuntimeError(f'ledger missing {miss}')
    if 'row_sha256' not in d.columns:raise RuntimeError('ledger row hash required')
    return d.sort_values(['display_episode_id','feature_available_time_utc']).reset_index(drop=True)


def valid_row_at(g: pd.DataFrame,t: pd.Timestamp):
    q=g[(g.feature_available_time_utc<=t)&(t<g.feature_available_time_utc+pd.Timedelta(minutes=5))]
    if not len(q):return None
    return q.iloc[-1]


def us_bar_ok(t: pd.Timestamp,session_date: str) -> bool:
    ny=t.tz_convert('America/New_York')
    return ny.date().isoformat()==session_date and ((ny.hour>8 or (ny.hour==8 and ny.minute>=0)) and ny.hour<17)


def label_episode(raw: pd.DataFrame,g: pd.DataFrame) -> dict:
    g=g.sort_values('feature_available_time_utc').reset_index(drop=True)
    eid=str(g.display_episode_id.iloc[0]);session=str(g.session_date_ny.iloc[0])
    start=g.feature_available_time_utc.min();end=(g.feature_available_time_utc+pd.Timedelta(minutes=5)).max()
    bars=raw[(raw.time>=start)&(raw.time<end)].copy()
    bars=bars[bars.time.map(lambda t:us_bar_ok(pd.Timestamp(t),session))]
    armed=False;arm_effective=None;arm_bar=None;contact=None;freeze=None
    for _,b in bars.iterrows():
        bt=pd.Timestamp(b.time);r=valid_row_at(g,bt)
        if r is None:
            if armed:return {'display_episode_id':eid,'session_date_ny':session,'selection_status':'NO_CONTACT_BEFORE_EPISODE_END','arm_bar_open_time_utc':arm_bar,'arm_effective_time_utc':arm_effective}
            continue
        if not armed:
            if float(b['close'])>float(r.zhi):
                armed=True;arm_bar=bt;arm_effective=bt+pd.Timedelta(minutes=1)
            continue
        if bt<arm_effective:continue
        if float(b['high'])>=float(r.zlo) and float(b['low'])<=float(r.zhi):
            contact=b;freeze=r;break
    if not armed:
        return {'display_episode_id':eid,'session_date_ny':session,'selection_status':'NEVER_ARMED'}
    if contact is None:
        return {'display_episode_id':eid,'session_date_ny':session,'selection_status':'NO_CONTACT_BEFORE_EPISODE_END','arm_bar_open_time_utc':arm_bar,'arm_effective_time_utc':arm_effective}

    ct=pd.Timestamp(contact.time);zlo0=float(freeze.zlo);zhi0=float(freeze.zhi);v0=float(freeze.v_snapshot);F=zhi0+.50*v0
    base={
      'display_episode_id':eid,'session_date_ny':session,'selection_status':'PRIMARY_CONTACT',
      'arm_bar_open_time_utc':arm_bar,'arm_effective_time_utc':arm_effective,'contact_bar_open_time_utc':ct,
      'feature_snapshot_time_utc':pd.Timestamp(freeze.snapshot_time_utc),'feature_available_time_utc':pd.Timestamp(freeze.feature_available_time_utc),
      'feature_row_sha256':str(freeze.row_sha256),'current_family':str(freeze.current_family),
      'zone_width_v':float(freeze.zone_width_v),'display_persistence_c5':int(freeze.display_persistence_c5),
      'center0':float(freeze.center),'zlo0':zlo0,'zhi0':zhi0,'v0':v0,'favorable_level':F,
    }
    if float(contact['close'])<zlo0:
        return {**base,'primary_class':'INVALIDATION_FIRST','primary_binary_label':0,'event_bar_open_time_utc':ct,'completed_post_contact_bars':0}

    later=raw[raw.time>ct].copy()
    later=later[later.time.map(lambda t:us_bar_ok(pd.Timestamp(t),session))]
    n=0
    for _,b in later.iterrows():
        if n>=30:break
        n+=1;bt=pd.Timestamp(b.time)
        fav=float(b['high'])>=F;inv=float(b['close'])<zlo0
        if fav and inv:return {**base,'primary_class':'AMBIGUOUS_SAME_BAR','primary_binary_label':0,'event_bar_open_time_utc':bt,'completed_post_contact_bars':n}
        if fav:return {**base,'primary_class':'FAVORABLE_FIRST','primary_binary_label':1,'event_bar_open_time_utc':bt,'completed_post_contact_bars':n}
        if inv:return {**base,'primary_class':'INVALIDATION_FIRST','primary_binary_label':0,'event_bar_open_time_utc':bt,'completed_post_contact_bars':n}
    return {**base,'primary_class':'NEITHER','primary_binary_label':0,'event_bar_open_time_utc':pd.NaT,'completed_post_contact_bars':n}


def label_all(raw: pd.DataFrame,ledger: pd.DataFrame):
    m1,qa=normalize_m1(raw);led=prep_ledger(ledger);rows=[]
    for _,g in led.groupby('display_episode_id',sort=False):rows.append(label_episode(m1,g))
    out=pd.DataFrame(rows)
    return out,qa


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument('--m1',required=True);p.add_argument('--ledger',required=True);p.add_argument('--output',required=True);p.add_argument('--manifest',required=True)
    p.add_argument('--authorization-token',default='')
    return p.parse_args()


def main():
    a=parse_args()
    if a.authorization_token!=GO_TOKEN:
        raise RuntimeError('REAL_OUTCOME_LABELING_BLOCKED: explicit GO_DEV_OUTCOME_OPENING token required; pre-outcome workflows must not supply it')
    raw=pd.read_csv(a.m1,compression='infer');ledger=pd.read_csv(a.ledger,compression='infer')
    out,qa=label_all(raw,ledger);Path(a.output).parent.mkdir(parents=True,exist_ok=True);out.to_csv(a.output,index=False,compression={'method':'gzip','mtime':0})
    m={'status':'E_DISPLAY_EPISODE_REACTION_LABELER_V1_COMPLETE','qa':qa,'episodes':int(len(out)),'primary_contacts':int((out.selection_status=='PRIMARY_CONTACT').sum())}
    Path(a.manifest).write_text(json.dumps(m,indent=2,sort_keys=True)+'\n');print(json.dumps(m,indent=2,sort_keys=True))

if __name__=='__main__':main()
