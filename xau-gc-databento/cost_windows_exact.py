#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import pandas as pd


def one(client, dataset, symbol, stype, schema, start, end, retries=4):
    kw=dict(dataset=dataset,symbols=symbol,stype_in=stype,schema=schema,start=str(start),end=str(end))
    err=None
    for i in range(retries):
        try:
            return {
                'start':str(start),'end':str(end),
                'cost_usd':float(client.metadata.get_cost(**kw)),
                'records':int(client.metadata.get_record_count(**kw)),
                'billable_bytes':int(client.metadata.get_billable_size(**kw)),
                'status':'OK'
            }
        except Exception as e:
            err=str(e); time.sleep(1.5*(i+1))
    return {'start':str(start),'end':str(end),'status':'ERROR','error':err}


def main():
    ap=argparse.ArgumentParser(description='Exact metadata-only cost of disjoint Databento windows. Never downloads market data.')
    ap.add_argument('windows_csv'); ap.add_argument('--schema',required=True)
    ap.add_argument('--dataset',default='GLBX.MDP3'); ap.add_argument('--symbol',default='GC.v.0'); ap.add_argument('--stype',default='continuous')
    ap.add_argument('--workers',type=int,default=6); ap.add_argument('--out',required=True)
    a=ap.parse_args()
    key=os.getenv('DATABENTO_API_KEY')
    if not key: raise SystemExit('DATABENTO_API_KEY missing')
    import databento as db
    client=db.Historical(key)
    w=pd.read_csv(a.windows_csv)
    if not {'start','end'}.issubset(w.columns): raise SystemExit('windows CSV requires start,end')
    rows=[]
    with ThreadPoolExecutor(max_workers=max(1,a.workers)) as ex:
        futs=[ex.submit(one,client,a.dataset,a.symbol,a.stype,a.schema,r.start,r.end) for r in w.itertuples(index=False)]
        for f in as_completed(futs): rows.append(f.result())
    ok=[r for r in rows if r.get('status')=='OK']; bad=[r for r in rows if r.get('status')!='OK']
    result={
        'dataset':a.dataset,'symbol':a.symbol,'stype_in':a.stype,'schema':a.schema,
        'windows':int(len(w)),'ok_windows':len(ok),'error_windows':len(bad),
        'cost_usd':float(sum(r['cost_usd'] for r in ok)),
        'records':int(sum(r['records'] for r in ok)),
        'billable_bytes':int(sum(r['billable_bytes'] for r in ok)),
        'download_performed':False,'errors':bad,
    }
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    if bad: raise SystemExit(f'{len(bad)} metadata windows failed')

if __name__=='__main__':main()
