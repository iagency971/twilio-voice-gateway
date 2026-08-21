#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, json
from pathlib import Path
import pandas as pd
import requests

YAHOO_FILE=Path('mnq-12model-yahoo/results/v1/yahoo_nq_1m.csv')
GET_URL='https://raw.githubusercontent.com/getdata-finance/nq-1m-ohlcv-stocks-historical-data/main/NQ_1m.csv'
GET_SHA='232fbc18375e6475dbe3b99e6e1504da69c58a962aa7a358b14f4e2b61cf229d'
TZ='America/New_York'
START=pd.Timestamp('2026-07-28 09:30:00'); END=pd.Timestamp('2026-07-31 15:59:59')

y=pd.read_csv(YAHOO_FILE)
y['datetime']=pd.to_datetime(y['datetime'],errors='coerce')
for c in ['open','high','low','close','volume']: y[c]=pd.to_numeric(y[c],errors='coerce')
y=y.dropna(subset=['datetime','open','high','low','close'])
rr=requests.get(GET_URL,timeout=180);rr.raise_for_status()
sha=hashlib.sha256(rr.content).hexdigest()
if sha!=GET_SHA: raise RuntimeError(f'GetData snapshot changed: {sha}')
g=pd.read_csv(io.BytesIO(rr.content));g['datetime']=pd.to_datetime(g['datetime'],utc=True,errors='coerce').dt.tz_convert(TZ).dt.tz_localize(None)
for c in ['open','high','low','close','volume']:g[c]=pd.to_numeric(g[c],errors='coerce')
g=g.dropna(subset=['datetime','open','high','low','close'])
y=y[(y.datetime>=START)&(y.datetime<=END)].copy();g=g[(g.datetime>=START)&(g.datetime<=END)].copy()
lo,hi=pd.Timestamp('09:30').time(),pd.Timestamp('15:59').time()
y=y[(y.datetime.dt.time>=lo)&(y.datetime.dt.time<=hi)];g=g[(g.datetime.dt.time>=lo)&(g.datetime.dt.time<=hi)]
m=y.merge(g,on='datetime',suffixes=('_yahoo','_get'))
for c in ['open','high','low','close']:m[c+'_abs_diff']=(m[c+'_yahoo']-m[c+'_get']).abs()
m['max_ohlc_abs_diff']=m[[c+'_abs_diff' for c in ['open','high','low','close']]].max(axis=1)
qa={
 'mode':'V1.1 bridged QA only on exact archived Yahoo snapshot',
 'overlap_days':int(m.datetime.dt.normalize().nunique()),
 'overlap_bars':int(len(m)),
 'median_abs_close_diff':float(m.close_abs_diff.median()) if len(m) else None,
 'pct_close_within_1pt':float((m.close_abs_diff<=1).mean()) if len(m) else None,
 'median_max_ohlc_abs_diff':float(m.max_ohlc_abs_diff.median()) if len(m) else None,
 'pct_max_ohlc_within_2pt':float((m.max_ohlc_abs_diff<=2).mean()) if len(m) else None,
 'prior_bridge_true_mnq':{'overlap_days':39,'median_entry_diff':0.25,'median_exit_diff':0.25,'entry_within1':0.9743589744,'exit_within2':0.9743589744,'direction_agreement':0.9743589744,'known_anomaly':'2026-06-16'}
}
qa['pass']=bool(qa['overlap_days']>=4 and qa['overlap_bars']>=1200 and qa['median_abs_close_diff']<=.5 and qa['pct_close_within_1pt']>=.95 and qa['median_max_ohlc_abs_diff']<=.5 and qa['pct_max_ohlc_within_2pt']>=.95)
out=Path('mnq-12model-yahoo/results/qa_v1_1_only');out.mkdir(parents=True,exist_ok=True)
(out/'RESULT.json').write_text(json.dumps(qa,indent=2,allow_nan=False));m.to_csv(out/'parity.csv',index=False)
print(json.dumps(qa,indent=2,allow_nan=False))
