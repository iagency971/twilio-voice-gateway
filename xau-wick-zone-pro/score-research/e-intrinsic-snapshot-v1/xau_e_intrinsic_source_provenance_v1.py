#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main():
    p=argparse.ArgumentParser(description='Outcome-blind provenance QA for frozen v0.4 E candidate source')
    p.add_argument('--source',required=True)
    p.add_argument('--legacy-expected-sha256',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()

    src=Path(a.source)
    binary=src.read_bytes()
    try:
        payload=gzip.decompress(binary)
    except Exception as e:
        raise SystemExit(f'gzip decode failed: {e}')
    try:
        text=payload.decode('utf-8')
    except UnicodeDecodeError as e:
        raise SystemExit(f'payload is not utf-8 CSV: {e}')

    normalized_lf=text.replace('\r\n','\n').replace('\r','\n').encode('utf-8')
    normalized_lf_final=(text.replace('\r\n','\n').replace('\r','\n').rstrip('\n')+'\n').encode('utf-8')
    first_line=text.splitlines()[0] if text.splitlines() else ''
    rows=max(0,len(text.splitlines())-1)
    variants={
      'compressed_gzip_binary_sha256':h(binary),
      'decompressed_payload_sha256':h(payload),
      'normalized_lf_payload_sha256':h(normalized_lf),
      'normalized_lf_single_final_newline_sha256':h(normalized_lf_final),
    }
    matches=[k for k,v in variants.items() if v==a.legacy_expected_sha256]
    out={
      'status':'E_V04_SOURCE_PROVENANCE_LEGACY_HASH_RESOLVED' if matches else 'E_V04_SOURCE_PROVENANCE_LEGACY_HASH_UNRESOLVED',
      'future_price_outcomes_used':False,
      'source_path':str(src),
      'source_size_bytes':len(binary),
      'decompressed_size_bytes':len(payload),
      'csv_data_row_count':rows,
      'csv_header':first_line,
      'legacy_manifest_expected_sha256':a.legacy_expected_sha256,
      'sha256_variants':variants,
      'legacy_hash_match_modes':matches,
      'note':'This tool hashes source representations only. It does not inspect any future reaction or trading outcome.'
    }
    Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=='__main__': main()
