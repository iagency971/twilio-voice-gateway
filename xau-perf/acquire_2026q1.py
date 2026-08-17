#!/usr/bin/env python3
from pathlib import Path
import pandas as pd, requests
BASE='https://raw.githubusercontent.com/kevingtlin/dukascopy_XAUUSD_1m_Data/main/xauusd/{side}/m1/xauusd_{side}_m1_2026_{month:02d}.csv'
out=Path('outputs/xau_2026q1'); out.mkdir(parents=True,exist_ok=True)
frames={side:[] for side in ['bid','ask']}
for month in range(1,5):
  for side in ['bid','ask']:
    r=requests.get(BASE.format(side=side,month=month),timeout=90); r.raise_for_status()
    d=pd.read_csv(__import__('io').BytesIO(r.content)); d['timestamp']=pd.to_datetime(d.timestamp,unit='ms',utc=True)
    frames[side].append(d)
b=pd.concat(frames['bid'],ignore_index=True); a=pd.concat(frames['ask'],ignore_index=True)
m=b.merge(a,on='timestamp',suffixes=('_bid','_ask'),how='inner').sort_values('timestamp').drop_duplicates('timestamp')
for c in ['open','high','low','close']:
  m[c]=(m[f'{c}_bid']+m[f'{c}_ask'])/2
m['spread']=m.close_ask-m.close_bid
keep=['timestamp','open','high','low','close','open_bid','high_bid','low_bid','close_bid','open_ask','high_ask','low_ask','close_ask','spread']
m[keep].to_csv(out/'xauusd_bidask_mid_m1_2026-01_2026-04.csv',index=False)
print('ROWS',len(m),'FIRST',m.timestamp.min(),'LAST',m.timestamp.max(),'SPREAD_MED',m.spread.median())
