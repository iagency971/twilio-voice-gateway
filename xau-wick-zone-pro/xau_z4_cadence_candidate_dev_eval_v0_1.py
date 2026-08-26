#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FROZEN = ROOT / 'cadence-sensitivity' / 'xau_z4_cadence_candidate_dev_eval_v0_1_frozen_copy.py'
GATE = ROOT / 'cadence-sensitivity' / 'xau_ebuy_c1_refresh_outcome_blind_gate_v1_1.py'
Z4 = ROOT / 'xau_zone_episode_dev_z4.py'
C5_SHA = '7bb47cfc78a26dd7a74965556352114a8e31ca1545ef4d21a987951daf417d24'


def parse_known():
    p=argparse.ArgumentParser(add_help=False)
    p.add_argument('--bid-pkl',required=True)
    p.add_argument('--ask-pkl',required=True)
    p.add_argument('--cadence',required=True,type=int)
    p.add_argument('--engine-patch-json',required=True)
    p.add_argument('--output',required=True)
    return p.parse_args()


def run(cmd):
    print('C1_REFRESH_VEHICLE:', ' '.join(map(str,cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], check=True)


def build_c5(side):
    src=Z4.read_text()
    old='p=utc_ts(ts); return p.minute%15==0 and p.second==0'
    new='p=utc_ts(ts); return p.minute%5==0 and p.second==0'
    assert src.count(old)==1
    patched=src.replace(old,new)
    assert patched.replace(new,old)==src
    eng=Path('/tmp/xau_zone_episode_dev_z4_C5_EBUY_GATE.py')
    eng.write_text(patched)
    got=hashlib.sha256(eng.read_bytes()).hexdigest()
    assert got==C5_SHA,(got,C5_SHA)
    out=Path(f'/tmp/C5_EBUY_{side.upper()}.pkl')
    run([sys.executable,eng,'--files',*sorted(Path('/tmp/xau',side).glob('*.csv')),'--output',out,'--tag',f'C5_EBUY_GATE_{side.upper()}'])
    return out


def inject_summary(side, gate_path):
    p=Path(f'/tmp/C1_{side.upper()}_summary.json')
    x=json.loads(p.read_text()) if p.exists() else {}
    x['c1_refresh_ebuy_outcome_blind_gate_v1_1']=json.loads(Path(gate_path).read_text())
    x['c1_refresh_vehicle_note']='Added only to uploaded summary artifact; cadence DEV result and engine-patch evidence remain unchanged.'
    p.write_text(json.dumps(x,indent=2))


def main():
    a=parse_known()
    # First reproduce the historical evaluator output byte-semantically from the frozen copy.
    run([sys.executable,FROZEN,*sys.argv[1:]])
    if a.cadence!=1:
        return

    print('C1_REFRESH_VEHICLE: starting preregistered outcome-blind E-BUY C1/C5 gate',flush=True)
    for side,c1 in [('bid',a.bid_pkl),('ask',a.ask_pkl)]:
        c5=build_c5(side)
        gout=Path(f'/tmp/C1_REFRESH_{side.upper()}_OUTCOME_BLIND_GATE_v1_1.json')
        run([sys.executable,GATE,
             '--files',*sorted(Path('/tmp/xau',side).glob('*.csv')),
             '--c1-pkl',c1,'--c5-pkl',c5,
             '--side',side,'--output',gout])
        inject_summary(side,gout)
    print('C1_REFRESH_VEHICLE: gate embedded in C1 BID/ASK summary artifacts only',flush=True)


if __name__=='__main__':
    main()
