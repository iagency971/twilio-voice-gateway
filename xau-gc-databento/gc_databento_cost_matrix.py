#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from pathlib import Path

REQUESTS = [
    {"name":"GC_OHLCV1M_FULL", "schema":"ohlcv-1m", "start":"2010-06-06"},
    {"name":"GC_TRADES_FULL", "schema":"trades", "start":"2010-06-06"},
    {"name":"GC_MBP1_FULL", "schema":"mbp-1", "start":"2010-06-06"},
    {"name":"GC_MBO_MODERN", "schema":"mbo", "start":"2017-05-21"},
]

def main():
    p=argparse.ArgumentParser(description='Databento GC.v.0 cost matrix. Cost check only: no data download.')
    p.add_argument('--end', default='2026-08-17')
    p.add_argument('--out', default='outputs/gc_databento_cost_matrix.json')
    a=p.parse_args()
    key=os.getenv('DATABENTO_API_KEY')
    if not key:
        raise SystemExit('DATABENTO_API_KEY is not set. This script never downloads data.')
    import databento as db
    client=db.Historical(key)
    rows=[]
    for r in REQUESTS:
        kw=dict(dataset='GLBX.MDP3', symbols='GC.v.0', stype_in='continuous', schema=r['schema'], start=r['start'], end=a.end)
        try:
            cost=float(client.metadata.get_cost(**kw))
            count=int(client.metadata.get_record_count(**kw))
            size=int(client.metadata.get_billable_size(**kw))
            rows.append({**r,'end':a.end,'cost_usd':cost,'records':count,'billable_bytes':size,'status':'OK'})
        except Exception as e:
            rows.append({**r,'end':a.end,'status':'ERROR','error':str(e)})
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print(json.dumps(rows,indent=2))
    print('COST_CHECK_ONLY_NO_DOWNLOAD')
if __name__=='__main__': main()
