#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

OUT=Path('mgc-macro/event_manifest'); OUT.mkdir(parents=True,exist_ok=True)
START=pd.Timestamp('2021-09-01'); END=pd.Timestamp('2026-08-19')

FED_SOURCE='https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'
BLS_CPI_SOURCE='https://www.bls.gov/schedule/news_release/cpi.htm'
BLS_NFP_SOURCE='https://www.bls.gov/schedule/news_release/empsit.htm'
BLS_LAPSE_SOURCE='https://www.bls.gov/bls/2025-lapse-revised-release-dates.htm'
ALFRED_NFP_SOURCE='https://alfred.stlouisfed.org/release/downloaddates?ff=txt&rid=50'
CPI_VERSIONED_MIRROR='https://github.com/abusadat/CPI-release-dates/blob/main/cpi_releases.csv'

# Regular policy-decision dates transcribed from the Federal Reserve 2021-2026 calendars.
FOMC_DATES='''
2021-09-22 2021-11-03 2021-12-15
2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14
2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13
2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10
2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29
'''.split()

# CPI actual release dates in our research window. 2021-2025 baseline dates are
# transcribed from a versioned BLS-schedule mirror and cross-checked against BLS.
# 2025/2026 lapse effects use the BLS revised-release page: Oct-2025 CPI was
# canceled; Nov-2025 CPI was released 2025-12-18; Jan-2026 CPI 2026-02-13.
CPI_DATES='''
2021-09-14 2021-10-13 2021-11-10 2021-12-10
2022-01-12 2022-02-10 2022-03-10 2022-04-12 2022-05-11 2022-06-10 2022-07-13 2022-08-10 2022-09-13 2022-10-13 2022-11-10 2022-12-13
2023-01-12 2023-02-14 2023-03-14 2023-04-12 2023-05-10 2023-06-13 2023-07-12 2023-08-10 2023-09-13 2023-10-12 2023-11-14 2023-12-12
2024-01-11 2024-02-13 2024-03-12 2024-04-10 2024-05-15 2024-06-12 2024-07-11 2024-08-14 2024-09-11 2024-10-10 2024-11-13 2024-12-11
2025-01-15 2025-02-12 2025-03-12 2025-04-10 2025-05-13 2025-06-11 2025-07-15 2025-08-12 2025-09-11 2025-10-15 2025-12-18
2026-01-13 2026-02-13 2026-03-11 2026-04-10 2026-05-12 2026-06-10 2026-07-14 2026-08-12
'''.split()

# Actual Employment Situation release dates. Baseline dates are the regular BLS
# releases; late-2025/2026 dates use BLS revised dates and are cross-checked against
# the ALFRED release-date history sourced from BLS. Oct-2025 Employment Situation
# was not published. Sep-2025 was released 2025-11-20; Nov-2025 on 2025-12-16.
NFP_DATES='''
2021-09-03 2021-10-08 2021-11-05 2021-12-03
2022-01-07 2022-02-04 2022-03-04 2022-04-01 2022-05-06 2022-06-03 2022-07-08 2022-08-05 2022-09-02 2022-10-07 2022-11-04 2022-12-02
2023-01-06 2023-02-03 2023-03-10 2023-04-07 2023-05-05 2023-06-02 2023-07-07 2023-08-04 2023-09-01 2023-10-06 2023-11-03 2023-12-08
2024-01-05 2024-02-02 2024-03-08 2024-04-05 2024-05-03 2024-06-07 2024-07-05 2024-08-02 2024-09-06 2024-10-04 2024-11-01 2024-12-06
2025-01-10 2025-02-07 2025-03-07 2025-04-04 2025-05-02 2025-06-06 2025-07-03 2025-08-01 2025-09-05 2025-11-20 2025-12-16
2026-01-09 2026-02-11 2026-03-06 2026-04-03 2026-05-08 2026-06-05 2026-07-02 2026-08-07
'''.split()


def rows_for(dates,event_type,time_et,source,notes):
    rows=[]
    for date in dates:
        d=pd.Timestamp(date)
        if START<=d<=END:
            rows.append({'date':date,'event_type':event_type,'time_et':time_et,'source':source,'notes':notes})
    return rows


def main():
    rows=[]
    rows += rows_for(FOMC_DATES,'FOMC','14:00',FED_SOURCE,'Regular FOMC policy decision; notation votes excluded')
    rows += rows_for(CPI_DATES,'CPI','08:30',BLS_CPI_SOURCE,'Actual CPI release date; lapse revisions/cancellation incorporated')
    rows += rows_for(NFP_DATES,'NFP','08:30',BLS_NFP_SOURCE,'Actual Employment Situation release date; lapse revisions/non-publication incorporated')
    df=pd.DataFrame(rows).sort_values(['date','time_et','event_type']).reset_index(drop=True)
    counts={k:int(v) for k,v in df.event_type.value_counts().to_dict().items()}
    # Research-window counts are intentionally hard-gated before any MGC outcomes.
    expected={'FOMC':40,'CPI':59,'NFP':59}
    qa={
        'status':'EVENT_MANIFEST_V1_FROZEN_NO_MARKET_OUTCOMES',
        'start':str(START.date()),'end':str(END.date()),'rows':int(len(df)),
        'counts':counts,'expected_counts':expected,
        'duplicate_event_type_date':int(df.duplicated(['event_type','date']).sum()),
        'same_timestamp_multi_event_rows':int(df.duplicated(['date','time_et'],keep=False).sum()),
        'sources':{
            'fomc':FED_SOURCE,
            'cpi_official':BLS_CPI_SOURCE,
            'nfp_official':BLS_NFP_SOURCE,
            'bls_lapse_revisions':BLS_LAPSE_SOURCE,
            'nfp_release_date_crosscheck':ALFRED_NFP_SOURCE,
            'cpi_versioned_schedule_crosscheck':CPI_VERSIONED_MIRROR,
        },
        'market_outcomes_opened':False,
    }
    if counts!=expected or qa['duplicate_event_type_date']!=0:
        raise RuntimeError(f'Manifest QA failed: {qa}')
    # If two event types ever share a timestamp, preserve both rows in the manifest;
    # the trading runner is already frozen to deduplicate CPI/NFP into one trade.
    df.to_csv(OUT/'EVENT_MANIFEST_V1.csv',index=False)
    (OUT/'MANIFEST_QA.json').write_text(json.dumps(qa,indent=2))
    print(json.dumps(qa,indent=2))

if __name__=='__main__':main()
