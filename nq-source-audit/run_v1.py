#!/usr/bin/env python3
from __future__ import annotations

import hashlib, io, json
from pathlib import Path
import numpy as np
import pandas as pd
import requests

GETDATA_URL='https://raw.githubusercontent.com/getdata-finance/nq-1m-ohlcv-stocks-historical-data/main/NQ_1m.csv'
TRUE_URL='https://raw.githubusercontent.com/dng-nguyn/mnq-intraday-momentum-backtest/main/results/trade_log.csv'
EXPECTED_GETDATA_SHA='232fbc18375e6475dbe3b99e6e1504da69c58a962aa7a358b14f4e2b61cf229d'
TZ='America/New_York'
START=pd.Timestamp('2026-06-01')
END=pd.Timestamp('2026-07-27')


def load_getdata():
    rr=requests.get(GETDATA_URL,timeout=180);rr.raise_for_status();raw=rr.content
    sha=hashlib.sha256(raw).hexdigest()
    d=pd.read_csv(io.BytesIO(raw));d['datetime']=pd.to_datetime(d['datetime'],utc=True,errors='coerce')
    for c in ['open','high','low','close','volume']:d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna(subset=['datetime','open','high','low','close']).sort_values('datetime').drop_duplicates('datetime',keep='last')
    d.index=d['datetime'].dt.tz_convert(TZ)
    d=d[['open','high','low','close','volume']].between_time('09:30','15:59');d=d[d.index.weekday<5]
    rows=[];prev_close=None
    for day,g in d.groupby(d.index.normalize(),sort=True):
        m={ts.hour*60+ts.minute:ts for ts in g.index};sig=m.get(599);ent=m.get(930);ex=m.get(959)
        if prev_close is not None and sig is not None and ent is not None and ex is not None:
            sp=float(g.loc[sig,'close']);direction=1 if sp>prev_close else (-1 if sp<prev_close else 0)
            rows.append({'date':day.tz_localize(None).normalize(),'get_direction':direction,'get_signal':sp,'get_prev_close':prev_close,
                         'get_entry':float(g.loc[ent,'open']),'get_exit':float(g.loc[ex,'close'])})
        if ex is not None:prev_close=float(g.loc[ex,'close'])
    return pd.DataFrame(rows), sha, len(raw)


def load_true():
    rr=requests.get(TRUE_URL,timeout=180);rr.raise_for_status();raw=rr.content
    d=pd.read_csv(io.BytesIO(raw))
    d['date']=pd.to_datetime(d['date'],errors='coerce').dt.normalize()
    d=d[(d['variant']=='eta_r1') & (pd.to_numeric(d['k'],errors='coerce')==300)].copy()
    d=d[(d.date>=START)&(d.date<=END)].copy()
    d['true_direction']=pd.to_numeric(d['direction'],errors='coerce').astype('Int64')
    d['true_entry']=pd.to_numeric(d['entry_price'],errors='coerce')
    d['true_exit']=pd.to_numeric(d['exit_price'],errors='coerce')
    return d[['date','true_direction','true_entry','true_exit']], hashlib.sha256(raw).hexdigest(), len(raw)


def frac(s,thr):
    return float((s<=thr).mean()) if len(s) else None


def main():
    out=Path('nq-source-audit/results/v1');out.mkdir(parents=True,exist_ok=True)
    g,gsha,gbytes=load_getdata();t,tsha,tbytes=load_true()
    g=g[(g.date>=START)&(g.date<=END)].copy()
    x=t.merge(g,on='date',how='inner').sort_values('date')
    x['entry_abs_diff']=(x.true_entry-x.get_entry).abs();x['exit_abs_diff']=(x.true_exit-x.get_exit).abs()
    x['direction_match']=x.true_direction.astype(float)==x.get_direction.astype(float)
    x['entry_signed_diff']=x.get_entry-x.true_entry;x['exit_signed_diff']=x.get_exit-x.true_exit
    x.to_csv(out/'parity_days.csv',index=False)
    result={
      'status':'',
      'source_integrity':{
        'getdata_sha_current':gsha,'getdata_sha_expected_from_original_test':EXPECTED_GETDATA_SHA,'getdata_same_snapshot':gsha==EXPECTED_GETDATA_SHA,'getdata_bytes':gbytes,
        'true_mnq_trade_log_sha':tsha,'true_mnq_trade_log_bytes':tbytes,
      },
      'coverage':{'getdata_days':int(len(g)),'true_mnq_days':int(len(t)),'overlap_days':int(len(x)),'start':str(START.date()),'end':str(END.date())},
      'price_parity':{},
      'direction_parity':{},
    }
    if len(x):
        result['price_parity']={
          'median_abs_entry_diff':float(x.entry_abs_diff.median()),'median_abs_exit_diff':float(x.exit_abs_diff.median()),
          'entry_within_0_5pt':frac(x.entry_abs_diff,0.5),'entry_within_1pt':frac(x.entry_abs_diff,1.0),'entry_within_2pt':frac(x.entry_abs_diff,2.0),
          'exit_within_0_5pt':frac(x.exit_abs_diff,0.5),'exit_within_1pt':frac(x.exit_abs_diff,1.0),'exit_within_2pt':frac(x.exit_abs_diff,2.0),
          'median_signed_entry_diff':float(x.entry_signed_diff.median()),'median_signed_exit_diff':float(x.exit_signed_diff.median()),
          'p95_abs_entry_diff':float(x.entry_abs_diff.quantile(.95)),'p95_abs_exit_diff':float(x.exit_abs_diff.quantile(.95)),
        }
        result['direction_parity']={'agreement':float(x.direction_match.mean()),'matches':int(x.direction_match.sum()),'mismatches':int((~x.direction_match).sum())}
        price_good=(result['price_parity']['entry_within_1pt']>=.95 and result['price_parity']['exit_within_1pt']>=.95)
        dir_good=result['direction_parity']['agreement']>=.95
        if result['source_integrity']['getdata_same_snapshot'] and price_good and dir_good:
            result['status']='GETDATA_PRICE_AND_SIGNAL_PARITY_PASS'
            result['interpretation']='GetData is a usable NQ/MNQ price proxy for this Jun-Jul window under this exact timing convention; further model-specific field requirements still need audit.'
        elif result['source_integrity']['getdata_same_snapshot'] and price_good and not dir_good:
            result['status']='GETDATA_PRICE_PARITY_PASS_SIGNAL_CONVENTION_FAIL'
            result['interpretation']='Prices match the true MNQ ledger, but signal directions do not. Previous-close/session/continuous-contract signal convention must be reconciled before model validation.'
        else:
            result['status']='GETDATA_FUTURES_PARITY_FAIL'
            result['interpretation']='Price parity is insufficient for futures validation; do not use GetData as a holdout source.'
    else:
        result['status']='SOURCE_AUDIT_INVALID_NO_OVERLAP';result['interpretation']='No overlapping dates.'
    (out/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False));print(json.dumps(result,indent=2,allow_nan=False))

if __name__=='__main__':main()
