#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pandas as pd
import requests

OUT=Path('mgc-macro/event_manifest'); OUT.mkdir(parents=True,exist_ok=True)
START=pd.Timestamp('2021-09-01'); END=pd.Timestamp('2026-08-19')
UA={'User-Agent':'Mozilla/5.0 research-calendar-freeze/1.0'}

# Regular FOMC policy-decision dates only, transcribed from the Federal Reserve
# Meeting Calendars and Information page before any MGC outcome is opened.
FOMC_DATES=[
'2021-09-22','2021-11-03','2021-12-15',
'2022-01-26','2022-03-16','2022-05-04','2022-06-15','2022-07-27','2022-09-21','2022-11-02','2022-12-14',
'2023-02-01','2023-03-22','2023-05-03','2023-06-14','2023-07-26','2023-09-20','2023-11-01','2023-12-13',
'2024-01-31','2024-03-20','2024-05-01','2024-06-12','2024-07-31','2024-09-18','2024-11-07','2024-12-18',
'2025-01-29','2025-03-19','2025-05-07','2025-06-18','2025-07-30','2025-09-17','2025-10-29','2025-12-10',
'2026-01-28','2026-03-18','2026-04-29','2026-06-17','2026-07-29',
]
FED_SOURCE='https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'

# Explicit actual-date overrides/cancellations documented by BLS after the
# 2025/2026 lapses in appropriations. These are applied after scraping annual
# schedule pages, to ensure actual releases rather than superseded schedules.
# Key = (release_type, reference identity or originally expected month where needed)
# Here we handle by deleting known superseded/canceled calendar dates and adding actual releases.
BLS_LAPSE_SOURCE='https://www.bls.gov/bls/2025-lapse-revised-release-dates.htm'
DELETE_EVENTS={
    ('NFP','2025-10-03'),   # Sep 2025 Employment Situation superseded -> Nov20
    ('CPI','2025-11-13'),   # Oct 2025 CPI canceled
    ('CPI','2025-12-10'),   # Nov 2025 CPI superseded -> Dec18
    ('NFP','2026-02-06'),   # Jan 2026 Employment Situation superseded -> Feb11
    ('CPI','2026-02-11'),   # Jan 2026 CPI superseded -> Feb13
}
ADD_EVENTS=[
    ('NFP','2025-11-20','08:30','BLS lapse actual release: Sep 2025 Employment Situation'),
    ('CPI','2025-12-18','08:30','BLS lapse actual release: Nov 2025 CPI'),
    ('NFP','2026-02-11','08:30','BLS lapse actual release: Jan 2026 Employment Situation'),
    ('CPI','2026-02-13','08:30','BLS lapse actual release: Jan 2026 CPI'),
]


def parse_date_cell(x):
    s=str(x).strip()
    # BLS list pages generally use e.g. "Friday, August 07, 2026".
    s=re.sub(r'\s+',' ',s)
    for fmt in ['%A, %B %d, %Y','%B %d, %Y','%b. %d, %Y','%b %d, %Y']:
        try:return pd.Timestamp(pd.to_datetime(s,format=fmt))
        except Exception:pass
    try:return pd.Timestamp(pd.to_datetime(s,errors='raise'))
    except Exception:return None


def scrape_bls():
    rows=[]; pages=[]
    for year in range(2021,2027):
        for month in range(1,13):
            url=f'https://www.bls.gov/schedule/{year}/{month:02d}_sched_list.htm'
            r=requests.get(url,headers=UA,timeout=30)
            if r.status_code!=200:
                pages.append({'url':url,'status':r.status_code,'events':0});continue
            n0=len(rows)
            try:tables=pd.read_html(io.StringIO(r.text))
            except Exception:
                pages.append({'url':url,'status':200,'events':0,'parse':'no_tables'});continue
            for tab in tables:
                # flatten columns and inspect each row as strings; robust across BLS table layout changes.
                tab.columns=[' '.join(map(str,c)).strip() if isinstance(c,tuple) else str(c).strip() for c in tab.columns]
                for _,rr in tab.iterrows():
                    vals=[str(v).strip() for v in rr.tolist()]
                    joined=' | '.join(vals)
                    typ=None
                    if 'Consumer Price Index' in joined: typ='CPI'
                    elif 'Employment Situation' in joined: typ='NFP'
                    if typ is None or '08:30' not in joined: continue
                    dt=None
                    for v in vals:
                        q=parse_date_cell(v)
                        if q is not None and 2000<=q.year<=2100:
                            dt=q.normalize();break
                    if dt is None: continue
                    if not (START<=dt<=END): continue
                    rows.append({'date':dt.strftime('%Y-%m-%d'),'event_type':typ,'time_et':'08:30','source':url,'notes':'BLS official schedule page'})
            pages.append({'url':url,'status':200,'events':len(rows)-n0})
    return rows,pages


def main():
    bls,pages=scrape_bls()
    # Deduplicate scraped events.
    ev={(x['event_type'],x['date']):x for x in bls}
    # Apply documented lapse deletions and actual additions.
    for key in DELETE_EVENTS:ev.pop(key,None)
    for typ,date,tim,note in ADD_EVENTS:
        dt=pd.Timestamp(date)
        if START<=dt<=END:
            ev[(typ,date)]={'date':date,'event_type':typ,'time_et':tim,'source':BLS_LAPSE_SOURCE,'notes':note}
    # FOMC regular decisions.
    for date in FOMC_DATES:
        dt=pd.Timestamp(date)
        if START<=dt<=END:
            ev[('FOMC',date)]={'date':date,'event_type':'FOMC','time_et':'14:00','source':FED_SOURCE,'notes':'Regular FOMC policy decision; notation votes excluded'}
    df=pd.DataFrame(ev.values()).sort_values(['date','time_et','event_type']).reset_index(drop=True)
    # Hard QA counts and uniqueness only; no market outcomes.
    counts=df.event_type.value_counts().to_dict()
    qa={
        'status':'EVENT_MANIFEST_V1_FROZEN_NO_MARKET_OUTCOMES',
        'start':str(START.date()),'end':str(END.date()),
        'rows':int(len(df)),'counts':{k:int(v) for k,v in counts.items()},
        'duplicate_event_type_date':int(df.duplicated(['event_type','date']).sum()),
        'fomc_expected_count':len(FOMC_DATES),
        'fomc_actual_count':int((df.event_type=='FOMC').sum()),
        'bls_scrape_pages':pages,
        'lapse_overrides_applied':True,
        'market_outcomes_opened':False,
    }
    if qa['duplicate_event_type_date']!=0 or qa['fomc_actual_count']!=qa['fomc_expected_count']:
        raise RuntimeError(f'Manifest QA failed: {qa}')
    df.to_csv(OUT/'EVENT_MANIFEST_V1.csv',index=False)
    (OUT/'MANIFEST_QA.json').write_text(json.dumps(qa,indent=2))
    print(json.dumps({k:v for k,v in qa.items() if k!='bls_scrape_pages'},indent=2))

if __name__=='__main__':main()
