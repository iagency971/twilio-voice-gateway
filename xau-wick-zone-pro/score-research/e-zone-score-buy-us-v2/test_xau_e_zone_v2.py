#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,sys
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent

def load(name,fn):
 s=importlib.util.spec_from_file_location(name,HERE/fn);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
lab=load('v2lab','xau_e_zone_v2_labeler.py')

def path(zlo,zhi):
 t=pd.Timestamp('2024-01-02T13:00:00Z')
 return pd.DataFrame([{'display_episode_id':'X','session_date_ny':'2024-01-02','snapshot_time_utc':t,'feature_available_time_utc':t+pd.Timedelta(minutes=1),'center':100.0,'zlo':zlo,'zhi':zhi,'v_snapshot':2.0,'current_family':'EWM_G60M','display_slot_rank':1,'zone_width_v':(zhi-zlo)/2,'display_persistence_c5':1,'native_evidence_raw':2.0,'confluence_count_e_families':1,'center_stability_3_c5':0.0,'distance_v':1.0,'log1p_zone_width_v':0.1,'log1p_zone_width_v_squared':0.01,'distance_v_squared':1.0,'log_v_snapshot':0.693,'minute_of_session':0,'minute_bin_30m':'0','upper_z4_count':1,'upper_z4_count_bucket':'1','nearest_upper_z4_dist_v':1.0,'trend15_v':0.0,'trend60_v':0.0,'trend240_v':0.0,'weekday_ny':'1','row_sha256':'x'}])

def placebo_path(zlo,zhi):
 p=path(zlo,zhi).drop(columns=['display_episode_id','session_date_ny']).copy()
 p['placebo_id']='P';p['donor_episode_id']='D';p['control_rank']=1;p['donor_session_date_ny']='2023-12-01';p['recipient_session_date_ny']='2024-01-02'
 return p

def bars(next_high=102.0,next_low=100.0):
 times=pd.date_range('2024-01-02T13:01:00Z',periods=5,freq='1min')
 # 13:01 arms above zhi, 13:02 contacts; contact-bar high deliberately exceeds future favorable level and must be ignored.
 return pd.DataFrame({'time':times,'open':[103,102,101,101,101],'high':[103.5,104.0,next_high,101.5,101.5],'low':[102.5,99.5,next_low,100.5,100.5],'close':[103,101,101,101,101]})

def noisy(raw):
 extra=pd.DataFrame({
  'time':[pd.Timestamp('2024-01-01T13:02:00Z'),pd.Timestamp('2024-01-02T12:59:00Z'),pd.Timestamp('2024-01-02T22:00:00Z'),pd.Timestamp('2024-01-03T13:02:00Z')],
  'open':[999,999,999,999],'high':[1000,1000,1000,1000],'low':[0,0,0,0],'close':[999,999,999,999]})
 return pd.concat([raw,extra],ignore_index=True).sort_values('time').reset_index(drop=True)

def same(a,b):
 assert set(a)==set(b),(set(a)-set(b),set(b)-set(a))
 for k in a:
  x,y=a[k],b[k]
  if pd.isna(x) and pd.isna(y):continue
  assert x==y,(k,x,y)

def parity(raw,p,kind):
 legacy=lab.label_one(raw,p,kind);idx=lab.build_us_session_index(raw);fast=lab.label_one_indexed(idx,p,kind);same(legacy,fast);return legacy

def main():
 # Width-independent threshold: both geometries freeze the same v and contact close, so favorable/adverse levels are identical.
 r=noisy(bars(102.2,100.8));a=parity(r,path(99.5,100.5),'REAL');b=parity(r,path(98.5,100.5),'REAL')
 assert a['selection_status']=='PRIMARY_CONTACT' and b['selection_status']=='PRIMARY_CONTACT'
 assert a['favorable_level']==b['favorable_level'] and a['adverse_level']==b['adverse_level']
 # Contact bar high is 104, but classification starts after contact bar; next bar is the event authority.
 assert a['event_bar_open_time_utc']>a['contact_bar_open_time_utc']
 # Arming bar cannot be contact bar.
 assert a['arm_bar_open_time_utc']<a['contact_bar_open_time_utc']
 # Same-bar future favorable+adverse is conservative failure.
 c=parity(noisy(bars(102.2,99.8)),path(99.5,100.5),'REAL');assert c['primary_class']=='AMBIGUOUS_SAME_BAR' and c['primary_binary_label']==0
 # PLACEBO identity and session filtering must also be identical.
 p=parity(noisy(bars(102.2,100.8)),placebo_path(99.5,100.5),'PLACEBO');assert p['placebo_id']=='P' and p['donor_episode_id']=='D' and p['control_rank']==1
 print('E_ZONE_V2_SYNTHETIC_CAUSAL_TESTS_PASS')
 print('E_ZONE_V2_LEGACY_INDEXED_LABEL_PARITY_PASS')
if __name__=='__main__':main()
