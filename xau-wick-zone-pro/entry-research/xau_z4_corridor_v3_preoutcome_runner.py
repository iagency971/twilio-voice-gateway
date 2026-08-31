#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
V2 = HERE.parent / 'score-research' / 'e-zone-score-buy-us-v2'
WINDOWS = {
    'DEV': ('2019-11', '2021-12', '2020-01-01T00:00:00Z', '2022-01-01T00:00:00Z'),
    'VAL': ('2021-11', '2022-12', '2022-01-01T00:00:00Z', '2023-01-01T00:00:00Z'),
    'REP': ('2022-11', '2023-12', '2023-01-01T00:00:00Z', '2024-01-01T00:00:00Z'),
}
CODE_FILES = [
    'XAUUSD_Z4_CORRIDOR_RETRACE_LEVEL_REACTION_V3_PREREG_2026-08-31.md',
    'XAUUSD_Z4_CORRIDOR_RETRACE_LEVEL_REACTION_V3_PREREG_ADDENDUM_A_EXACT_CAUSAL_RULES_2026-08-31.md',
    'XAUUSD_Z4_CORRIDOR_RETRACE_LEVEL_REACTION_V3_PREREG_ADDENDUM_B_DYNAMIC_CONTROL_NEUTRALITY_2026-08-31.md',
    'XAUUSD_Z4_CORRIDOR_RETRACE_LEVEL_REACTION_V3_PREREG_ADDENDUM_C_GAP_PASS_RULE_2026-08-31.md',
    'XAUUSD_Z4_CORRIDOR_RETRACE_LEVEL_REACTION_V3_PRO_GATE.json',
    'xau_z4_corridor_v3_preoutcome.py',
    'xau_z4_corridor_v3_preoutcome_qa.py',
    'xau_z4_corridor_v3_preoutcome_runner.py',
    'test_xau_z4_corridor_v3_preoutcome.py',
]


def args():
    p = argparse.ArgumentParser()
    p.add_argument('--data-dir', required=True)
    p.add_argument('--work-dir', required=True)
    return p.parse_args()


def run(cmd):
    print('+', ' '.join(map(str, cmd)), flush=True)
    subprocess.run(list(map(str, cmd)), check=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def files_for(data, a, b):
    return [Path(data) / f'xauusd_bid_m1_{p.year:04d}_{p.month:02d}.csv' for p in pd.period_range(a, b, freq='M')]


def prepare(data, work, key):
    a, b, start, end = WINDOWS[key]
    out = Path(work) / key
    out.mkdir(parents=True, exist_ok=True)
    fs = files_for(data, a, b)
    missing = [str(x) for x in fs if not x.is_file()]
    if missing:
        raise RuntimeError(f'missing M1 {missing[:3]}')
    z4 = out / 'z4.pkl'
    run([sys.executable, V2 / 'xau_z4_geometry_only_v2.py', '--files', *fs,
         '--output-pkl', z4, '--output-csv', out / 'z4.csv', '--manifest', out / 'z4_manifest.json', '--tag', f'CORRIDOR_V3_{key}'])
    run([sys.executable, HERE / 'xau_z4_corridor_v3_preoutcome.py', '--files', *fs, '--z4-pkl', z4,
         '--target-start', start, '--target-end', end,
         '--episodes-out', out / 'episodes.csv.gz', '--candidates-out', out / 'candidates.csv.gz',
         '--controls-out', out / 'controls.csv.gz', '--candidate-contacts-out', out / 'candidate_contacts.csv.gz',
         '--control-contacts-out', out / 'control_contacts.csv.gz', '--manifest', out / 'manifest.json', '--tag', key])
    run([sys.executable, HERE / 'xau_z4_corridor_v3_preoutcome_qa.py', '--phase', key,
         '--episodes', out / 'episodes.csv.gz', '--candidates', out / 'candidates.csv.gz', '--controls', out / 'controls.csv.gz',
         '--candidate-contacts', out / 'candidate_contacts.csv.gz', '--control-contacts', out / 'control_contacts.csv.gz',
         '--manifest', out / 'manifest.json', '--output', out / 'preoutcome_qa.json'])
    return out


def main():
    a = args()
    data, work = Path(a.data_dir), Path(a.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    gate = json.load(open(HERE / 'XAUUSD_Z4_CORRIDOR_RETRACE_LEVEL_REACTION_V3_PRO_GATE.json'))
    if gate.get('decision') != 'GO_V3_PREOUTCOME_IMPLEMENTATION' or gate.get('v3_reaction_outcomes_opened') is not False:
        raise RuntimeError('V3_PRO_PREOUTCOME_GATE_MISSING')
    run([sys.executable, HERE / 'test_xau_z4_corridor_v3_preoutcome.py'])
    outs = {k: prepare(data, work, k) for k in ['DEV', 'VAL', 'REP']}
    for k, o in outs.items():
        q = json.load(open(o / 'preoutcome_qa.json'))
        if q.get('status') != 'Z4_CORRIDOR_V3_PREOUTCOME_QA_PASS':
            raise RuntimeError(f'{k}_PREOUTCOME_QA_FAIL')

    forbidden = []
    for pat in ['*reaction*label*', '*outcome*', '*score_report*', '*model*', '*mfe*', '*mae*']:
        forbidden.extend(work.rglob(pat))
    if forbidden:
        raise RuntimeError(f'V3_OUTCOME_ARTIFACT_BEFORE_AUTHORIZATION {[str(x) for x in forbidden]}')

    evidence = {}
    for k, o in outs.items():
        for name in ['z4_manifest.json', 'manifest.json', 'preoutcome_qa.json', 'episodes.csv.gz', 'candidates.csv.gz',
                     'controls.csv.gz', 'candidate_contacts.csv.gz', 'control_contacts.csv.gz']:
            evidence[str(o / name)] = sha(o / name)
    code = {name: sha(HERE / name) for name in CODE_FILES}
    data_manifest = data / 'DATA_INPUT_MANIFEST.json'
    if not data_manifest.is_file():
        raise RuntimeError('DATA_INPUT_MANIFEST missing')
    freeze = {
        'status': 'Z4_CORRIDOR_V3_COMPLETE_PREOUTCOME_FREEZE_PASS',
        'authorization': 'GO_Z4_CORRIDOR_RETRACE_LEVEL_REACTION_V3_PREOUTCOME_ONLY',
        'v3_reaction_outcomes_opened': False,
        'rep_2023_reaction_outcomes_opened': False,
        'windows': WINDOWS,
        'data_input_manifest_sha256': sha(data_manifest),
        'code_sha256': code,
        'evidence_sha256': evidence,
        'upstream_data_manifest': json.load(open(data_manifest)),
        'next_action': 'RETURN_TO_PRO_IF_ANY_PREOUTCOME_GATE_FAILS; OTHERWISE AUTHORIZE DEV_REACTION_OPENING_WITH_FROZEN_PACKAGE'
    }
    (work / 'V3_PREOUTCOME_FREEZE.json').write_text(json.dumps(freeze, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': freeze['status'], 'data_manifest_sha256': freeze['data_input_manifest_sha256']}, indent=2))


if __name__ == '__main__':
    main()
