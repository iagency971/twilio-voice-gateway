#!/usr/bin/env python3
from __future__ import annotations
import json, os
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import databento as db

OUT=Path('mgc-macro/results/window_cost_sample_probe');OUT.mkdir(parents=True,exist_ok=True)
ET=ZoneInfo('America/New_York'); client=db.Historical(os.environ['DATABENTO_API_KEY'])
# Representative already-frozen event windows; metadata only.
samples=[
 ('MACRO','2022-03-10',8,25,8,45),('FOMC','2022-03-16',13,55,14,20),
 ('MACRO','2024-03-12',8,25,8,45),('FOMC','2024-03-20',13,55,14,20),
 ('MACRO','2026-03-11',8,25,8,45),('FOMC','2026-03-18',13,55,14,20),
]
rows=[]
for typ,date,h0,m0,h1,m1 in samples:
    d=pd.Timestamp(date)
    start=pd.Timestamp(year=d.year,month=d.month,day=d.day,hour=h0,minute=m0,tz=ET).tz_convert('UTC')
    end=pd.Timestamp(year=d.year,month=d.month,day=d.day,hour=h1,minute=m1,tz=ET).tz_convert('UTC')
    params={'dataset':'GLBX.MDP3','symbols':['MGC.v.0'],'schema':'ohlcv-1m','stype_in':'continuous','start':start.isoformat(),'end':end.isoformat()}
    cost=float(client.metadata.get_cost(**params)); mins=(end-start).total_seconds()/60
    rows.append({'type':typ,'date':date,'minutes':mins,'cost_usd':cost,'cost_per_minute':cost/mins})
per_min=sum(r['cost_usd'] for r in rows)/sum(r['minutes'] for r in rows)
requested_minutes=40*25 + 118*20
estimate=per_min*requested_minutes
obj={'status':'MGC_WINDOW_SAMPLE_COST_ESTIMATE_OK','sample_windows':rows,'weighted_cost_per_minute_usd':per_min,'frozen_event_counts':{'FOMC':40,'CPI_NFP':118},'estimated_requested_minutes':requested_minutes,'extrapolated_total_cost_usd':estimate,'full_range_estimate_usd':6.254315897822,'data_downloaded':False,'secret_exposed':False,'note':'Runtime downloader must exact-cost all frozen windows before any paid time-series request and abort if user-authorized cap would be exceeded.'}
(OUT/'RESULT.json').write_text(json.dumps(obj,indent=2));print(json.dumps(obj,indent=2))
