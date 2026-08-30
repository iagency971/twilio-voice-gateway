#!/usr/bin/env python3
from __future__ import annotations

"""Pro-authorized R4 runner for E-zone score BUY-US V2.

PREOUTCOME remains outcome-blind and must pass every R4 transport/support gate,
exact V0.4 parity and prefix invariance before DEV can be opened.
"""

import json
import os
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import xau_e_zone_v2_pipeline as p

TOKEN='GO_E_ZONE_SCORE_BUY_US_V2_R4_SEQUENTIAL_HISTORICAL_EXECUTION'
ORIGINAL_PY=p.py


def py_r4(name):
    mp={
        'xau_e_zone_v2_placebos.py':'xau_e_zone_v2_placebos_r4.py',
        'xau_e_zone_v2_preoutcome_qa.py':'xau_e_zone_v2_preoutcome_qa_r4.py',
        'xau_e_zone_v2_labeler.py':'xau_e_zone_v2_labeler_r4.py',
        'xau_e_zone_v2_score_model.py':'xau_e_zone_v2_score_model_r4.py',
    }
    return HERE/mp[name] if name in mp else ORIGINAL_PY(name)


p.py=py_r4
p.TOKEN=TOKEN
for extra in [
    'xau_e_zone_v2_placebos_r4.py','xau_e_zone_v2_preoutcome_qa_r4.py',
    'xau_e_zone_v2_labeler_r4.py','xau_e_zone_v2_score_model_r4.py',
    'xau_e_zone_v2_runner_r4.py','xau_e_zone_v2_r4_matching_ladder.py',
    'xau_e_zone_v2_r4_pro_audit_diagnostics.py','E_ZONE_SCORE_BUY_US_V2_R4_PRO_GATE.json',
    'R4_MATCHING_LADDER_VAL.json','R4_PREOUTCOME_CONTROL_FREEZE.md',
    'R4_PRO_AUDIT_PREDECLARED_DIAGNOSTIC_GATES_2026-08-30.json',
    'R4_PRO_AUDIT_DIAGNOSTICS_VAL_2026-08-30.json','R4_PRO_AUDIT_GATE_RESULT_2026-08-30.json',
    'V04_PARITY_REPRODUCIBILITY_DIAGNOSTIC_2026-08-30.json'
]:
    if extra not in p.CODE_FILES:p.CODE_FILES.append(extra)


def prepare_window_r4(data,work,k):
    a,b,start,end,decl=p.WINDOWS[k];o=p.outdir(work,k);fs=p.files_for(data,a,b)
    z4=o/'z4.pkl';p.run([sys.executable,p.py('xau_z4_geometry_only_v2.py'),'--files',*fs,'--output-pkl',z4,'--output-csv',o/'z4.csv','--manifest',o/'z4_manifest.json','--tag',k])
    p.run([sys.executable,p.py('xau_e_zone_v2_instrument.py'),'--files',*fs,'--z4-pkl',z4,'--output-features',o/'features.csv.gz','--output-display-all',o/'display_all.csv.gz','--output-full-pool',o/'full_pool.csv.gz','--output-context',o/'context.csv.gz','--manifest',o/'instrument_manifest.json','--target-start',start,'--target-end',end])
    p.run([sys.executable,p.py('xau_e_zone_v2_placebos.py'),'--features',o/'features.csv.gz','--full-pool',o/'full_pool.csv.gz','--context',o/'context.csv.gz','--output',o/'placebos.csv.gz','--matching-table',o/'matching.csv.gz','--manifest',o/'placebo_manifest.json'])
    p.run([sys.executable,p.py('xau_e_zone_v2_preoutcome_qa.py'),'--features',o/'features.csv.gz','--display-all',o/'display_all.csv.gz','--full-pool',o/'full_pool.csv.gz','--context',o/'context.csv.gz','--placebos',o/'placebos.csv.gz','--matching',o/'matching.csv.gz','--instrument-manifest',o/'instrument_manifest.json','--placebo-manifest',o/'placebo_manifest.json','--output',o/'preoutcome_qa.json'])
    p.merge_m1(fs,o/'m1.csv.gz');return o


def parity_r4(data,work):
    o=p.outdir(work,'PARITY');frozen=Path(os.environ.get('V2_FROZEN_Z4_PKL',''))
    if not frozen.is_file():raise RuntimeError(f'R4_PARITY_FROZEN_Z4_MISSING {frozen}')
    fs=p.files_for(data,'2024-01','2026-07');ref=p.V1/'E_DISPLAY_PROVENANCE_V1_24M.csv.gz'
    p.run([sys.executable,p.py('xau_e_zone_v2_instrument.py'),'--files',*fs,'--z4-pkl',frozen,'--output-features',o/'features.csv.gz','--output-display-all',o/'display_all.csv.gz','--output-full-pool',o/'full_pool.csv.gz','--output-context',o/'context.csv.gz','--manifest',o/'instrument_manifest.json','--target-start','2024-08-01T00:00:00Z','--target-end','2026-08-01T00:00:00Z','--reference-v04-csv',ref])
    m=json.load(open(o/'instrument_manifest.json'))
    if not m.get('geometry_parity',{}).get('pass'):raise RuntimeError(f'R4_PARITY_FAIL {m.get("geometry_parity")}')
    m['r4_exact_parity_gate']={'bid_window':'2024-01 through 2026-07','frozen_z4_source':str(frozen),'canonical_v1_reference':str(ref),'outcomes_used':False,'approximate_tolerance_authorized':False}
    (o/'instrument_manifest.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n');return o


def freeze_pre_r4(data,work):
    gate=json.load(open(HERE/'E_ZONE_SCORE_BUY_US_V2_R4_PRO_GATE.json'))
    if gate.get('decision')!='GO_R4' or gate.get('new_r4_execution_authorization_token')!=TOKEN:raise RuntimeError('R4_PRO_AUTHORIZATION_MISSING')
    for k in ['DEV','VAL','REP']:
        q=json.load(open(Path(work)/k/'preoutcome_qa.json'))
        if q.get('status')!='E_ZONE_SCORE_BUY_US_V2_R4_PREOUTCOME_QA_PASS':raise RuntimeError(f'R4_{k}_PREOUTCOME_GATE_FAIL')
    forbidden=[]
    for pattern in ['*_labels.csv.gz','zone_test.json','matched_sets.csv','score_report.json','scored.csv.gz','DEV_FROZEN_MODEL.json','DEV_FREEZE.json']:
        forbidden.extend(Path(work).rglob(pattern))
    if forbidden:raise RuntimeError(f'R4_OUTCOME_ARTIFACT_EXISTS_BEFORE_DEV {[str(x) for x in forbidden]}')
    p.freeze_pre(data,work)
    fp=Path(work)/'PRE_OUTCOME_FREEZE.json';x=json.load(open(fp));x['status']='E_ZONE_SCORE_BUY_US_V2_R4_PREOUTCOME_FREEZE_PASS';x['authorization_token']=TOKEN;x['r4_design']='R4_D5_MINIMAL_DENSE';x['r2_authorization_superseded']=True;x['future_v2_reaction_outcomes_opened']=False
    x['r4_preoutcome_qa_sha256']={k:p.sha(Path(work)/k/'preoutcome_qa.json') for k in ['DEV','VAL','REP']}
    fp.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')


p.prepare_window=prepare_window_r4
p.parity=parity_r4
p.freeze_pre=freeze_pre_r4
p.main()
