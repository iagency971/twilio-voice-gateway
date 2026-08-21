#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
import pandas as pd

REPO='https://github.com/s-k-28/nq-es-trader-5k-payout.git'
SHA='d472d6b442764c2adafbba4bbeb96881c100e3e0'
out=Path('mgc-macro/results/data_probe'); out.mkdir(parents=True,exist_ok=True)
work=Path('/tmp/mgc_probe')
if not work.exists(): subprocess.run(['git','clone','--quiet',REPO,str(work)],check=True)
subprocess.run(['git','checkout','--quiet',SHA],cwd=work,check=True)
p=work/'data'/'MGC_1min.csv'
d=pd.read_csv(p)
d.columns=[str(c).strip().lower().replace(' ','_') for c in d.columns]
dtc='datetime' if 'datetime' in d.columns else ('timestamp' if 'timestamp' in d.columns else d.columns[0])
d['dt']=pd.to_datetime(d[dtc],errors='coerce')
for c in ['open','high','low','close','volume']:
    if c in d.columns:d[c]=pd.to_numeric(d[c],errors='coerce')
res={'status':'MGC_PUBLIC_DATA_PROBE_ONLY','external_commit':SHA,'rows':int(len(d)),'columns':list(d.columns),'min_datetime':str(d.dt.min()),'max_datetime':str(d.dt.max()),'unique_dates':int(d.dt.dt.normalize().nunique()),'price_min':float(d.low.min()) if 'low' in d else None,'price_max':float(d.high.max()) if 'high' in d else None,'median_volume':float(d.volume.median()) if 'volume' in d else None,'outcomes_opened':False}
(out/'RESULT.json').write_text(json.dumps(res,indent=2)); print(json.dumps(res,indent=2))
