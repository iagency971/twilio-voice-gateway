#!/usr/bin/env python3
from pathlib import Path
import pandas as pd, requests
BASE='https://raw.githubusercontent.com/kevingtlin/dukascopy_XAUUSD_1m_Data/main/xauusd/{side}/m1/xauusd_{side}_m1_2010_01.csv'
out=Path('outputs/xau_jan2010'); out.mkdir(parents=True,exist_ok=True)
frames={}
for side in ['bid','ask']:
    p=out/f'xauusd_{side}_m1_2010_01.csv'
    r=requests.get(BASE.format(side=side),timeout=90); r.raise_for_status(); p.write_bytes(r.content)
    d=pd.read_csv(p); d['timestamp']=pd.to_datetime(d.timestamp,unit='ms',utc=True)
    frames[side]=d
b,a=frames['bid'],frames['ask']
m=b.merge(a,on='timestamp',suffixes=('_bid','_ask'),how='inner')
for c in ['open','high','low','close']:
    m[c]=(m[f'{c}_bid']+m[f'{c}_ask'])/2
m['spread']=m.close_ask-m.close_bid
keep=['timestamp','open','high','low','close','open_bid','high_bid','low_bid','close_bid','open_ask','high_ask','low_ask','close_ask','spread']
m[keep].to_csv(out/'xauusd_bidask_mid_m1_2010-01.csv',index=False)
print('ROWS',len(m),'FIRST',m.timestamp.min(),'LAST',m.timestamp.max(),'SPREAD_MED',m.spread.median())
