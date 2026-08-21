#!/usr/bin/env python3
from __future__ import annotations
import json, os, time
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import databento as db

MANIFEST=Path('mgc-macro/event_manifest/EVENT_MANIFEST_V1.csv')
OUT=Path('mgc-macro/results/event_window_cost_probe'); OUT.mkdir(parents=True,exist_ok=True)
ET=ZoneInfo('America/New_York')
client=db.Historical(os.environ['DATABENTO_API_KEY'])
df=pd.read_csv(MANIFEST)
rows=[]; total=0.0
for i,r in df.iterrows():
    d=pd.Timestamp(r['date'])
    typ=str(r['event_type'])
    if typ=='FOMC':
        start_h,start_m,end_h,end_m=13,55,14,20
    else:
        start_h,start_m,end_h,end_m=8,25,8,45
    start=pd.Timestamp(year=d.year,month=d.month,day=d.day,hour=start_h,minute=start_m,tz=ET).tz_convert('UTC')
    end=pd.Timestamp(year=d.year,month=d.month,day=d.day,hour=end_h,minute=end_m,tz=ET).tz_convert('UTC')
    params={'dataset':'GLBX.MDP3','symbols':['MGC.v.0'],'schema':'ohlcv-1m','stype_in':'continuous','start':start.isoformat(),'end':end.isoformat()}
    try:
        c=float(client.metadata.get_cost(**params))
        total+=c
        rows.append({'date':r['date'],'event_type':typ,'start_utc':start.isoformat(),'end_utc':end.isoformat(),'estimated_cost_usd':c,'ok':True})
    except Exception as e:
        rows.append({'date':r['date'],'event_type':typ,'start_utc':start.isoformat(),'end_utc':end.isoformat(),'estimated_cost_usd':None,'ok':False,'error':str(e)})
    # Gentle pacing for the free metadata endpoint.
    time.sleep(0.02)
out=pd.DataFrame(rows); out.to_csv(OUT/'cost_by_event.csv',index=False)
fail=int((~out.ok).sum())
by_type=out[out.ok].groupby('event_type').estimated_cost_usd.sum().to_dict()
obj={'status':'MGC_EVENT_WINDOW_COST_ESTIMATE_OK' if fail==0 else 'MGC_EVENT_WINDOW_COST_ESTIMATE_PARTIAL',
     'events_requested':int(len(out)),'events_ok':int(out.ok.sum()),'events_failed':fail,
     'estimated_total_cost_usd':float(total),'estimated_by_type_usd':{k:float(v) for k,v in by_type.items()},
     'full_range_previous_estimate_usd':6.254315897822,'data_downloaded':False,'secret_exposed':False,
     'window_policy':{'FOMC':'13:55-14:20 ET','CPI_NFP':'08:25-08:45 ET'}}
(OUT/'RESULT.json').write_text(json.dumps(obj,indent=2)); print(json.dumps(obj,indent=2))
