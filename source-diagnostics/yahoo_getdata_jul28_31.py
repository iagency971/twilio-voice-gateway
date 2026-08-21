#!/usr/bin/env python3
from pathlib import Path
import json
import pandas as pd

src=Path('mnq-12model-yahoo/results/qa_v1_1_only/parity.csv')
d=pd.read_csv(src)
d['datetime']=pd.to_datetime(d['datetime'])
d['date']=d.datetime.dt.strftime('%Y-%m-%d')
d['hour']=d.datetime.dt.hour

out={'status':'SOURCE_DIAGNOSTIC_ONLY_NOT_A_QA_RESCUE','overall':{},'by_date':{},'by_hour':{},'largest_close_diffs':[]}
out['overall']={
 'n':int(len(d)),
 'close_diff_p50':float(d.close_abs_diff.quantile(.50)),
 'close_diff_p75':float(d.close_abs_diff.quantile(.75)),
 'close_diff_p90':float(d.close_abs_diff.quantile(.90)),
 'close_diff_p95':float(d.close_abs_diff.quantile(.95)),
 'close_diff_p99':float(d.close_abs_diff.quantile(.99)),
 'max_ohlc_p95':float(d.max_ohlc_abs_diff.quantile(.95)),
 'max_ohlc_p99':float(d.max_ohlc_abs_diff.quantile(.99)),
}
for day,g in d.groupby('date'):
    out['by_date'][day]={
      'n':int(len(g)),
      'median_close_diff':float(g.close_abs_diff.median()),
      'pct_close_within1':float((g.close_abs_diff<=1).mean()),
      'median_max_ohlc_diff':float(g.max_ohlc_abs_diff.median()),
      'pct_max_ohlc_within2':float((g.max_ohlc_abs_diff<=2).mean()),
      'p95_close_diff':float(g.close_abs_diff.quantile(.95)),
      'p95_max_ohlc_diff':float(g.max_ohlc_abs_diff.quantile(.95)),
    }
for h,g in d.groupby('hour'):
    out['by_hour'][str(int(h))]={
      'n':int(len(g)),
      'median_close_diff':float(g.close_abs_diff.median()),
      'pct_close_within1':float((g.close_abs_diff<=1).mean()),
      'p95_close_diff':float(g.close_abs_diff.quantile(.95)),
    }
top=d.nlargest(20,'close_abs_diff')
for _,r in top.iterrows():
    out['largest_close_diffs'].append({'datetime':str(r.datetime),'close_diff':float(r.close_abs_diff),'yahoo_close':float(r.close_yahoo),'getdata_close':float(r.close_get),'max_ohlc_diff':float(r.max_ohlc_abs_diff)})

p=Path('source-diagnostics/results/yahoo_getdata_jul28_31');p.mkdir(parents=True,exist_ok=True)
(p/'RESULT.json').write_text(json.dumps(out,indent=2,allow_nan=False))
print(json.dumps(out,indent=2,allow_nan=False))
