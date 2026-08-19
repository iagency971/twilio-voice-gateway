#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import databento as db

HARD_CAP_USD = 0.45
AUTH_VERSION = "COMEX_DEV_RANK1_NATIVE_N1_AUTHORIZATION_V1"
REQ_VERSION = "COMEX_DEV_RANK1_NATIVE_N1_REQUEST_FILE_V1"
PARTIAL_VERSION = "COMEX_DEV_RANK1_NATIVE_N1_ACQUISITION_PARTIAL_V1"
COMPLETE_VERSION = "COMEX_DEV_RANK1_NATIVE_N1_ACQUISITION_COMPLETE_V1"
EXPECTED_AUTH = "OK NATIVE N1, plafond 0,45 $"


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def req_kwargs(r: dict) -> dict:
    return dict(dataset=str(r['dataset']), symbols=str(r['symbols']), stype_in=str(r['stype_in']), schema=str(r['schema']), start=str(r['start']), end=str(r['end']))


def retry_meta(fn, **kw):
    err=None
    for k in range(7):
        try:return fn(**kw)
        except Exception as e:err=e;time.sleep(min(20,2**k))
    raise RuntimeError(err)


def load_markers(root: Path):
    out={}
    for p in root.glob('*.json'):
        try:z=json.loads(p.read_text())
        except Exception:continue
        if z.get('version')==REQ_VERSION:out[str(z['market_request_id'])]=z
    return out


def validate_existing(root: Path, rows: list[dict], auth: dict):
    partial_path=root/'ACQUISITION_PARTIAL.json'
    if not partial_path.exists():raise SystemExit('recovery requires ACQUISITION_PARTIAL.json')
    partial=json.loads(partial_path.read_text())
    if partial.get('version')!=PARTIAL_VERSION or partial.get('complete') is not False:raise SystemExit('invalid partial marker')
    markers=load_markers(root)
    if len(markers)!=int(partial.get('completed_markers',-1)):raise SystemExit('partial marker count mismatch')
    if int(partial.get('paid_market_requests_performed',-1))!=len(markers):raise SystemExit('expected every existing marker to be paid/full')
    rowmap={str(r['market_request_id']):r for r in rows}
    for rid,z in markers.items():
        if rid not in rowmap:raise SystemExit(f'unexpected completed request {rid}')
        raw=root/str(z.get('raw_file'))
        if not raw.exists():raise SystemExit(f'missing existing raw {rid}')
        if sha256_file(raw)!=z.get('sha256'):raise SystemExit(f'existing raw SHA mismatch {rid}')
        if int(z.get('records_downloaded',-1))!=int(z.get('current_records',-2)):raise SystemExit(f'existing record mismatch {rid}')
    success_cost=sum(float(z['immediate_pre_download_cost_usd']) for z in markers.values())
    if abs(success_cost-float(partial.get('paid_cost_upper_bound_usd',-1)))>1e-10:raise SystemExit('existing success cost mismatch')
    ordered=[str(r['market_request_id']) for r in rows]
    missing=[rid for rid in ordered if rid not in markers]
    if not missing:raise SystemExit('nothing missing')
    first_missing=missing[0]
    failed_reserve=float(rowmap[first_missing]['gate_cost_usd'])
    frozen_missing=sum(float(rowmap[rid]['gate_cost_usd']) for rid in missing)
    worst=success_cost+failed_reserve+frozen_missing
    if worst>HARD_CAP_USD+1e-12:
        raise SystemExit(f'recovery worst-case {worst:.12f} exceeds cap')
    return partial,markers,success_cost,missing,first_missing,failed_reserve,worst


def quote_missing(client, rows_by_id, missing):
    def q(rid):
        r=rows_by_id[rid];kw=req_kwargs(r)
        return rid,float(retry_meta(client.metadata.get_cost,**kw)),int(retry_meta(client.metadata.get_record_count,**kw))
    ans={};errs=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        fs={ex.submit(q,rid):rid for rid in missing}
        for f in as_completed(fs):
            rid=fs[f]
            try:
                k,c,n=f.result();ans[k]={'cost':c,'records':n}
            except Exception as e:errs.append({'market_request_id':rid,'error':str(e)})
    if errs:raise SystemExit(f'recovery metadata failures; no new download: {errs[:3]}')
    return ans


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--gate',required=True);ap.add_argument('--authorization',required=True);ap.add_argument('--partial-root',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();key=os.environ.get('DATABENTO_API_KEY')
    if not key:raise SystemExit('DATABENTO_API_KEY missing')
    gate=json.loads(Path(a.gate).read_text());auth=json.loads(Path(a.authorization).read_text())
    if gate.get('version')!='COMEX_DEV_RANK1_NATIVE_N1_PRE_DOWNLOAD_GATE_V1':raise SystemExit('wrong gate')
    if auth.get('version')!=AUTH_VERSION or auth.get('authorization')!=EXPECTED_AUTH or abs(float(auth.get('hard_cap_usd',-1))-HARD_CAP_USD)>1e-12:raise SystemExit('authorization invalid')
    rows=gate.get('rows',[])
    if len(rows)!=92:raise SystemExit('gate must contain 92 requests')
    rows=sorted(rows,key=lambda r:str(r['market_request_id']));rowmap={str(r['market_request_id']):r for r in rows}
    root=Path(a.partial_root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    # Copy/reuse already-acquired files through the workflow before this script. Here partial-root == out is allowed.
    partial,markers,success_cost,missing,first_missing,failed_reserve,frozen_worst=validate_existing(root,rows,auth)
    client=db.Historical(key)
    rq=quote_missing(client,rowmap,missing)
    current_missing=sum(v['cost'] for v in rq.values())
    global_worst=success_cost+failed_reserve+current_missing
    recovery_gate={
      'version':'COMEX_DEV_RANK1_NATIVE_N1_RECOVERY_GATE_V1',
      'original_authorization':auth['authorization'],
      'hard_cap_usd':HARD_CAP_USD,
      'existing_completed_requests':len(markers),
      'existing_success_cost_upper_bound_usd':success_cost,
      'failed_request_id_reserved':first_missing,
      'possible_prior_failed_attempt_reserve_usd':failed_reserve,
      'missing_requests':len(missing),
      'current_missing_exact_quote_usd':current_missing,
      'worst_case_full_completion_usd':global_worst,
      'remaining_margin_after_full_completion_usd':HARD_CAP_USD-global_worst,
      'market_data_download_performed_in_recovery_gate':False,
      'note':'Prior 502 is conservatively reserved at its full quote even though no DBN file/marker was produced. No already-successful request may be replayed.'
    }
    (out/'RECOVERY_GATE.json').write_text(json.dumps(recovery_gate,indent=2))
    if global_worst>HARD_CAP_USD+1e-12:raise SystemExit(f'recovery current worst-case ${global_worst:.12f} exceeds cap; no new download')

    confirmed=success_cost
    remaining_current=dict((rid,rq[rid]['cost']) for rid in missing)
    new_markers=[]
    try:
        for rid in missing:
            r=rowmap[rid];kw=req_kwargs(r)
            current_cost=float(retry_meta(client.metadata.get_cost,**kw));current_records=int(retry_meta(client.metadata.get_record_count,**kw))
            later_sum=sum(remaining_current[x] for x in missing if x!=rid and x not in {z['market_request_id'] for z in new_markers})
            hypothetical=confirmed+failed_reserve+current_cost+later_sum
            if hypothetical>HARD_CAP_USD+1e-12:raise RuntimeError(f'{rid}: immediate price change makes full-completion worst-case ${hypothetical:.12f} > cap; stopped before download')
            if current_records!=int(rq[rid]['records']):raise RuntimeError(f'{rid}: record count changed {rq[rid]["records"]}->{current_records}; stopped before download')
            raw=out/f'{rid}.dbn.zst';marker=out/f'{rid}.json'
            if raw.exists() or marker.exists():raise RuntimeError(f'{rid}: refusing overwrite')
            qa={'version':REQ_VERSION,'market_request_id':rid,'dataset':r['dataset'],'schema':r['schema'],'symbols':str(r['symbols']),'stype_in':r['stype_in'],'start':r['start'],'end':r['end'],'gate_cost_usd':float(r['gate_cost_usd']),'recovery_global_cost_usd':float(rq[rid]['cost']),'immediate_pre_download_cost_usd':current_cost,'gate_records':int(r['gate_records']),'current_records':current_records,'recovery':True}
            if current_records==0:
                qa.update(records_downloaded=0,raw_file=None,raw_file_bytes=0,sha256=None,market_data_request_performed=False,zero_record_metadata_only=True)
                marker.write_text(json.dumps(qa,indent=2));new_markers.append(qa);remaining_current.pop(rid,None);continue
            # One new paid attempt only. No retry on any market-data exception.
            store=client.timeseries.get_range(path=str(raw),**kw)
            df=store.to_df();downloaded=int(len(df))
            if downloaded!=current_records:raise RuntimeError(f'{rid}: downloaded {downloaded}, expected {current_records}')
            confirmed+=current_cost
            qa.update(records_downloaded=downloaded,raw_file=raw.name,raw_file_bytes=int(raw.stat().st_size),sha256=sha256_file(raw),market_data_request_performed=True,zero_record_metadata_only=False)
            marker.write_text(json.dumps(qa,indent=2));new_markers.append(qa);remaining_current.pop(rid,None)
    except Exception as e:
        allmarkers=load_markers(out)
        state={'version':'COMEX_DEV_RANK1_NATIVE_N1_RECOVERY_PARTIAL_V1','complete':False,'total_completed_markers':len(allmarkers),'new_completed_markers':len(new_markers),'confirmed_success_cost_upper_bound_usd':confirmed,'possible_prior_failed_attempt_reserve_usd':failed_reserve,'worst_case_cost_so_far_usd':confirmed+failed_reserve,'hard_cap_usd':HARD_CAP_USD,'error':str(e),'failed_request_retries_beyond_this_run_authorized':False}
        (out/'RECOVERY_PARTIAL.json').write_text(json.dumps(state,indent=2));raise

    final_markers=load_markers(out)
    if len(final_markers)!=92:raise SystemExit(f'completion parity failure {len(final_markers)}/92')
    confirmed_final=sum(float(z.get('immediate_pre_download_cost_usd',0)) for z in final_markers.values() if z.get('market_data_request_performed'))
    worst_final=confirmed_final+failed_reserve
    if worst_final>HARD_CAP_USD+1e-12:raise SystemExit('final worst-case cap failure')
    records=sum(int(z.get('records_downloaded',0)) for z in final_markers.values())
    summary={'version':'COMEX_DEV_RANK1_NATIVE_N1_ACQUISITION_SUMMARY_V1_1_RECOVERY','complete':True,'expected_requests':92,'completed_request_markers':92,'original_run_completed':len(markers),'recovery_completed':len(new_markers),'records_downloaded_total':records,'confirmed_success_cost_upper_bound_usd':confirmed_final,'possible_prior_failed_attempt_reserve_usd':failed_reserve,'worst_case_total_cost_usd':worst_final,'hard_cap_usd':HARD_CAP_USD,'hard_cap_respected':True,'market_data_download_performed':True,'n2_download_performed':False,'original_failure':'502 BentoServerError on first missing request; no raw file or marker produced','failed_request_id_reserved':first_missing}
    (out/'acquisition_summary.json').write_text(json.dumps(summary,indent=2))
    complete={'version':COMPLETE_VERSION,'complete':True,'requests':92,'confirmed_success_cost_upper_bound_usd':confirmed_final,'possible_prior_failed_attempt_reserve_usd':failed_reserve,'worst_case_total_cost_usd':worst_final,'hard_cap_usd':HARD_CAP_USD,'summary_sha256':sha256_file(out/'acquisition_summary.json'),'n2_download_authorized':False,'dev_rank2_opened':False,'retro_confirm_opened':False,'locked_comex_test_opened':False}
    (out/'ACQUISITION_COMPLETE.json').write_text(json.dumps(complete,indent=2));print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
