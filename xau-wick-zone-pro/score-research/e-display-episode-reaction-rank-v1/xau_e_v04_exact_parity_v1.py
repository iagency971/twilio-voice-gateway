#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--instrumented',required=True);p.add_argument('--output',required=True);a=p.parse_args()
r=pd.read_csv(a.reference,compression='infer');g=pd.read_csv(a.instrumented,compression='infer')
cols=['time','entry_rank','family','center','zlo','zhi'];bad={}
if len(r)!=len(g):bad['row_count']=[len(r),len(g)]
if len(r)==len(g):
    for c in cols:
        if c=='time':x=pd.to_datetime(r[c],utc=True).astype('int64').to_numpy();y=pd.to_datetime(g[c],utc=True).astype('int64').to_numpy();neq=x!=y
        elif c=='family':neq=r[c].astype(str).to_numpy()!=g[c].astype(str).to_numpy()
        elif c=='entry_rank':neq=r[c].to_numpy(dtype=np.int64)!=g[c].to_numpy(dtype=np.int64)
        else:
            x=r[c].to_numpy(dtype=np.float64);y=g[c].to_numpy(dtype=np.float64);neq=~((x==y)|(np.isnan(x)&np.isnan(y)))
        n=int(np.sum(neq))
        if n:bad[c]=n
out={'status':'E_V04_EXACT_DISPLAY_PARITY_PASS' if not bad else 'E_V04_EXACT_DISPLAY_PARITY_FAIL','future_price_outcomes_used':False,'rows':int(len(g)),'checked_columns':cols,'mismatches':bad}
Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,indent=2,sort_keys=True))
if bad:raise SystemExit(4)
