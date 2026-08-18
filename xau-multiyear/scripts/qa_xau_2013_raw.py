#!/usr/bin/env python3
import sys,json
from pathlib import Path
import pandas as pd, numpy as np
p=sys.argv[1]; out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
df=pd.read_csv(p); df['timestamp']=pd.to_datetime(df['timestamp'],utc=True)
num=['open','high','low','close','open_bid','high_bid','low_bid','close_bid','open_ask','high_ask','low_ask','close_ask','spread']
for c in num: df[c]=pd.to_numeric(df[c],errors='coerce')
x=df[(df.timestamp>=pd.Timestamp('2013-01-01',tz='UTC'))&(df.timestamp<pd.Timestamp('2014-01-01',tz='UTC'))].copy().sort_values('timestamp')
x['prev_close']=x.close.shift(1); x['gap_abs']=(x.open-x.prev_close).abs(); x['gap_pct']=x.gap_abs/x.prev_close
x['ret1_abs']=x.close.pct_change(fill_method=None).abs(); x['range']=x.high-x.low
x['bid_gap_abs']=(x.open_bid-x.close_bid.shift(1)).abs(); x['ask_gap_abs']=(x.open_ask-x.close_ask.shift(1)).abs()
cols=['timestamp','open','high','low','close','open_bid','high_bid','low_bid','close_bid','open_ask','high_ask','low_ask','close_ask','spread','gap_abs','gap_pct','ret1_abs','range','bid_gap_abs','ask_gap_abs']
x.nlargest(100,'gap_abs')[cols].to_csv(out/'top_gaps.csv',index=False); x.nlargest(100,'spread')[cols].to_csv(out/'top_spreads.csv',index=False); x.nlargest(100,'range')[cols].to_csv(out/'top_ranges.csv',index=False)
q={'rows':int(len(x)),'price_min':float(x.low.min()),'price_max':float(x.high.max()),'spread_median':float(x.spread.median()),'spread_p99':float(x.spread.quantile(.99)),'spread_max':float(x.spread.max()),'gap_abs_p99':float(x.gap_abs.quantile(.99)),'gap_abs_p999':float(x.gap_abs.quantile(.999)),'gap_abs_max':float(x.gap_abs.max()),'gap_pct_max':float(x.gap_pct.max()),'range_p999':float(x.range.quantile(.999)),'range_max':float(x.range.max()),'count_gap_gt_20':int((x.gap_abs>20).sum()),'count_gap_gt_50':int((x.gap_abs>50).sum()),'count_gap_gt_100':int((x.gap_abs>100).sum()),'count_spread_gt_5':int((x.spread>5).sum()),'count_price_below_500':int((x.low<500).sum())}
(out/'qa.json').write_text(json.dumps(q,indent=2)); print(json.dumps(q,indent=2)); print(x.nlargest(20,'gap_abs')[cols].to_string(index=False))
