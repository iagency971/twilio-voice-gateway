#!/usr/bin/env python3
import gzip, io, json
from pathlib import Path
import pandas as pd
import requests

SYMS=['NAS100','US30','SPX500','US2000','GER40','GER30','UK100','XAUUSD','GBPUSD','USDJPY']
WEEKS=[(2016,10),(2020,10),(2024,10),(2026,10)]
out=[]
for s in SYMS:
    rec={'symbol':s,'checks':[]}
    for y,w in WEEKS:
        u=f'https://candledata.fxcorporate.com/m1/{s}/{y}/{w}.csv.gz'
        try:
            r=requests.get(u,timeout=20,headers={'User-Agent':'propf-probe/1'})
            x={'year':y,'week':w,'status':r.status_code,'bytes':len(r.content)}
            if r.status_code==200:
                try:
                    df=pd.read_csv(io.BytesIO(gzip.decompress(r.content)),nrows=3)
                    x['columns']=list(map(str,df.columns)); x['rows_sample']=len(df)
                except Exception as e: x['parse_error']=str(e)
            rec['checks'].append(x)
        except Exception as e:
            rec['checks'].append({'year':y,'week':w,'error':str(e)})
    out.append(rec)
Path('eurusd-propf/results/symbol_probe').mkdir(parents=True,exist_ok=True)
Path('eurusd-propf/results/symbol_probe/result.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
