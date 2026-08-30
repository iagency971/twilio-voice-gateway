#!/usr/bin/env python3
from __future__ import annotations

import argparse, gzip, json
from pathlib import Path

import numpy as np
import pandas as pd

TOKEN='GO_E_ZONE_SCORE_BUY_US_V2_SEQUENTIAL_HISTORICAL_EXECUTION'
WINDOWS={
 'DEVELOPMENT_V2':(pd.Timestamp('2020-01-01T00:00:00Z'),pd.Timestamp('2022-01-01T00:00:00Z')),
 'VALIDATION_V2':(pd.Timestamp('2022-01-01T00:00:00Z'),pd.Timestamp('2023-01-01T00:00:00Z')),
 'REPLICATION_V2':(pd.Timestamp('2023-01-01T00:00:00Z'),pd.Timestamp('2024-01-01T00:00:00Z')),
 'ARCHITECTURE_OVERLAP_ROBUSTNESS_ONLY':(pd.Timestamp('2024-01-01T00:00:00Z'),pd.Timestamp('2024-08-01T00:00:00Z')),
}


def parse_args():
 p=argparse.ArgumentParser();p.add_argument('--m1',required=True);p.add_argument('--paths',required=True);p.add_argument('--kind',choices=['REAL','PLACEBO'],required=True)
 p.add_argument('--window',choices=sorted(WINDOWS),required=True);p.add_argument('--authorization-token',default='');p.add_argument('--output',required=True);p.add_argument('--manifest',required=True);return p.parse_args()


def normalize_m1(path):
 d=pd.read_csv(path,compression='infer');
 if 'time' not in d.columns:
  if 'timestamp' not in d.columns:raise RuntimeError('M1 missing timestamp/time')
  d['time']=pd.to_datetime(d.timestamp,unit='ms',utc=True)
 else:d['time']=pd.to_datetime(d.time,utc=True)
 for c in ['open','high','low','close']:d[c]=pd.to_numeric(d[c],errors='raise').astype(float)
 conflicts=0
 for _,g in d[d.duplicated('time',keep=False)].groupby('time'):
  if len(g[['open','high','low','close']].drop_duplicates())>1:conflicts+=1
 if conflicts:raise RuntimeError(f'conflicting duplicate timestamps {conflicts}')
 exact=int(d.duplicated(['time','open','high','low','close']).sum())
 return d.drop_duplicates('time',keep='first').sort_values('time').reset_index(drop=True),{'exact_duplicates_removed':exact,'conflicting_duplicates':conflicts}


def read_paths(path,kind):
 d=pd.read_csv(path,compression='infer',float_precision='round_trip')
 for c in ['snapshot_time_utc','feature_available_time_utc','time']:
  if c in d.columns:d[c]=pd.to_datetime(d[c],utc=True)
 if kind=='REAL':
  req={'display_episode_id','session_date_ny','feature_available_time_utc','center','zlo','zhi','v_snapshot'}
 else:req={'placebo_id','donor_episode_id','recipient_session_date_ny','feature_available_time_utc','center','zlo','zhi','v_snapshot'}
 miss=sorted(req-set(d.columns));
 if miss:raise RuntimeError(f'path missing {miss}')
 return d


def us_bar_ok(t,session):
 ny=pd.Timestamp(t).tz_convert('America/New_York')
 return ny.date().isoformat()==str(session) and 8<=ny.hour<17


def valid_row_at(g,t):
 q=g[(g.feature_available_time_utc<=t)&(t<g.feature_available_time_utc+pd.Timedelta(minutes=5))]
 return None if not len(q) else q.iloc[-1]


def base_real(r):
 keep=['current_family','family','display_slot_rank','zone_width_v','display_persistence_c5','native_evidence_raw','confluence_count_e_families','center_stability_3_c5',
       'distance_v','log1p_zone_width_v','log1p_zone_width_v_squared','distance_v_squared','log_v_snapshot','minute_of_session','minute_bin_30m',
       'upper_z4_count','upper_z4_count_bucket','nearest_upper_z4_dist_v','trend15_v','trend60_v','trend240_v','weekday_ny','row_sha256']
 return {k:r[k] for k in keep if k in r.index}


def label_one(raw,g,kind):
 g=g.sort_values('feature_available_time_utc').reset_index(drop=True)
 if kind=='REAL':eid=str(g.display_episode_id.iloc[0]);session=str(g.session_date_ny.iloc[0]); baseid={'display_episode_id':eid,'session_date_ny':session}
 else:eid=str(g.placebo_id.iloc[0]);session=str(g.recipient_session_date_ny.iloc[0]);baseid={'placebo_id':eid,'donor_episode_id':str(g.donor_episode_id.iloc[0]),'control_rank':int(g.control_rank.iloc[0]),'donor_session_date_ny':str(g.donor_session_date_ny.iloc[0]),'recipient_session_date_ny':session}
 start=g.feature_available_time_utc.min(); end=(g.feature_available_time_utc+pd.Timedelta(minutes=5)).max()
 bars=raw[(raw.time>=start)&(raw.time<end)].copy(); bars=bars[bars.time.map(lambda t:us_bar_ok(t,session))]
 armed=False;arm_bar=None;arm_effective=None;contact=None;freeze=None
 for _,b in bars.iterrows():
  bt=pd.Timestamp(b.time);r=valid_row_at(g,bt)
  if r is None:
   if armed:return {**baseid,'selection_status':'NO_CONTACT_BEFORE_EPISODE_END','arm_bar_open_time_utc':arm_bar,'arm_effective_time_utc':arm_effective}
   continue
  if not armed:
   if float(b.close)>float(r.zhi):armed=True;arm_bar=bt;arm_effective=bt+pd.Timedelta(minutes=1)
   continue
  if bt<arm_effective:continue
  if float(b.high)>=float(r.zlo) and float(b.low)<=float(r.zhi):contact=b;freeze=r;break
 if not armed:return {**baseid,'selection_status':'NEVER_ARMED'}
 if contact is None:return {**baseid,'selection_status':'NO_CONTACT_BEFORE_EPISODE_END','arm_bar_open_time_utc':arm_bar,'arm_effective_time_utc':arm_effective}
 ct=pd.Timestamp(contact.time);v0=float(freeze.v_snapshot);anchor=float(contact.close);fav=anchor+.50*v0;adv=anchor-.50*v0
 base={**baseid,'selection_status':'PRIMARY_CONTACT','arm_bar_open_time_utc':arm_bar,'arm_effective_time_utc':arm_effective,'contact_bar_open_time_utc':ct,
       'feature_snapshot_time_utc':pd.Timestamp(freeze.get('snapshot_time_utc',freeze.get('time',pd.NaT))),'feature_available_time_utc':pd.Timestamp(freeze.feature_available_time_utc),
       'center0':float(freeze.center),'zlo0':float(freeze.zlo),'zhi0':float(freeze.zhi),'v0':v0,'contact_close':anchor,'favorable_level':fav,'adverse_level':adv}
 if kind=='REAL':base.update(base_real(freeze))
 later=raw[raw.time>ct].copy();later=later[later.time.map(lambda t:us_bar_ok(t,session))]
 n=0
 for _,b in later.iterrows():
  if n>=30:break
  n+=1;bt=pd.Timestamp(b.time);f=float(b.high)>=fav;a=float(b.low)<=adv
  if f and a:return {**base,'primary_class':'AMBIGUOUS_SAME_BAR','primary_binary_label':0,'event_bar_open_time_utc':bt,'completed_post_contact_bars':n}
  if f:return {**base,'primary_class':'FAVORABLE_FIRST','primary_binary_label':1,'event_bar_open_time_utc':bt,'completed_post_contact_bars':n}
  if a:return {**base,'primary_class':'ADVERSE_FIRST','primary_binary_label':0,'event_bar_open_time_utc':bt,'completed_post_contact_bars':n}
 return {**base,'primary_class':'NEITHER','primary_binary_label':0,'event_bar_open_time_utc':pd.NaT,'completed_post_contact_bars':n}


def write_gz(d,path):
 raw=d.to_csv(index=False,lineterminator='\n',float_format='%.17g',na_rep='').encode();Path(path).parent.mkdir(parents=True,exist_ok=True)
 with open(path,'wb') as fh:
  with gzip.GzipFile(fileobj=fh,mode='wb',mtime=0,filename='') as gz:gz.write(raw)


def main():
 a=parse_args()
 if a.authorization_token!=TOKEN:raise RuntimeError('V2_OUTCOME_OPENING_BLOCKED')
 raw,qa=normalize_m1(a.m1);p=read_paths(a.paths,a.kind);idcol='display_episode_id' if a.kind=='REAL' else 'placebo_id'
 rows=[label_one(raw,g,a.kind) for _,g in p.groupby(idcol,sort=False)];out=pd.DataFrame(rows)
 start,end=WINDOWS[a.window]; primary=out[out.selection_status=='PRIMARY_CONTACT'].copy()
 if len(primary):
  t=pd.to_datetime(primary.contact_bar_open_time_utc,utc=True,errors='coerce')
  if t.isna().any() or not bool(((t>=start)&(t<end)).all()):raise RuntimeError('contact outside declared window')
 write_gz(out,a.output)
 cls={str(k):int(v) for k,v in primary.primary_class.value_counts().sort_index().items()} if len(primary) else {}
 m={'status':'E_ZONE_V2_WIDTH_NEUTRAL_LABELER_COMPLETE','kind':a.kind,'declared_window':a.window,'episodes':int(len(out)),'primary_contacts':int(len(primary)),
    'sessions':int((primary.session_date_ny if a.kind=='REAL' else primary.recipient_session_date_ny).nunique()) if len(primary) else 0,
    'class_counts':cls,'m1_qa':qa,'width_in_outcome_thresholds':False,'contact_bar_used_for_outcome':False,'horizon_available_m1':30}
 Path(a.manifest).write_text(json.dumps(m,indent=2,sort_keys=True)+'\n');print(json.dumps(m,indent=2,sort_keys=True))

if __name__=='__main__':main()
