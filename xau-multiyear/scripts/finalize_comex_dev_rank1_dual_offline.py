#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import pandas as pd

EXPECTED=103

def sha256_file(path: Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--requests',required=True);ap.add_argument('--root',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    requests_path=Path(a.requests);root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    expected=pd.read_csv(requests_path,dtype={'symbols':str});exp=set(expected.request_id.astype(str))
    qa=[]
    for p in sorted(root.rglob('*.json')):
        try:obj=json.loads(p.read_text())
        except Exception:continue
        if obj.get('version')=='COMEX_DEV_RANK1_DUAL_REQUEST_FILE_V1':qa.append(obj)
    by_id={x['request_id']:x for x in qa};got=set(by_id);missing=sorted(exp-got);extra=sorted(got-exp)
    rows=[by_id[k] for k in sorted(got)]
    complete=(not missing and not extra and len(got)==EXPECTED)
    result={
      'version':'COMEX_DEV_RANK1_DUAL_ACQUISITION_SUMMARY_OFFLINE_V1',
      'source_run_id':32179377819,
      'expected_requests':EXPECTED,
      'completed_request_markers':len(got),
      'missing_request_ids':missing,
      'extra_request_ids':extra,
      'complete':complete,
      'paid_market_requests_performed_in_successful_markers':int(sum(bool(x.get('market_data_request_performed')) for x in rows)),
      'zero_record_metadata_only_requests':int(sum(bool(x.get('zero_record_metadata_only')) for x in rows)),
      'records_downloaded_total':int(sum(int(x.get('records_downloaded',0)) for x in rows)),
      'raw_bytes_total':int(sum(int(x.get('raw_file_bytes',0)) for x in rows)),
      'note':'Does not include any potentially billable failed request that produced no success marker. Databento portal is accounting source of truth.',
      'files':rows,
    }
    (out/'acquisition_summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    missing_rows=expected[expected.request_id.astype(str).isin(missing)].copy();missing_rows.to_csv(out/'missing_requests.csv',index=False)
    if complete:
        marker={'version':'COMEX_DEV_RANK1_DUAL_ACQUISITION_COMPLETE_V1','complete':True,'request_csv_sha256':sha256_file(requests_path),'requests':EXPECTED,'summary_sha256':sha256_file(out/'acquisition_summary.json')}
        (out/'ACQUISITION_COMPLETE.json').write_text(json.dumps(marker,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))

if __name__=='__main__':main()
