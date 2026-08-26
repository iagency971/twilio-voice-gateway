#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


v1 = load_module('asia_reaction_v1_frozen', HERE / 'xau_ebuy_asia_reaction_v1_0.py')


def parse():
    p = argparse.ArgumentParser()
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--z4-pkl', required=True)
    p.add_argument('--candidates-csv', required=True)
    p.add_argument('--gate-result', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--contacts-csv', required=True)
    p.add_argument('--br-csv', required=True)
    return p.parse_args()


def main():
    a = parse()
    gate = json.load(open(a.gate_result))
    if gate.get('status') != 'ASIA_V2_ARCHITECTURE_GATE_PASS':
        raise RuntimeError(f'Asia v2 architecture gate not pass: {gate.get("status")}')
    if gate.get('reaction_study_authorized') is not True or not gate.get('selected_architecture'):
        raise RuntimeError('Asia v2 reaction not authorized or selected architecture missing')
    # The v1 reaction engine is reused unchanged. Only adapt its gate-token contract
    # to the v2 outcome-blind architecture gate; the candidate table itself is the
    # immutable selected v2 table.
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        tmp = Path(f.name)
        proxy = dict(gate)
        proxy['status'] = 'ASIA_C5_OUTCOME_BLIND_LOCATION_GATE_PASS'
        proxy['reaction_study_authorized'] = True
        json.dump(proxy, f)
    old = list(sys.argv)
    try:
        sys.argv = [
            old[0], '--files', *a.files,
            '--z4-pkl', a.z4_pkl,
            '--candidates-csv', a.candidates_csv,
            '--gate-result', str(tmp),
            '--output', a.output,
            '--contacts-csv', a.contacts_csv,
            '--br-csv', a.br_csv,
        ]
        v1.main()
    finally:
        sys.argv = old
        tmp.unlink(missing_ok=True)

    out = json.load(open(a.output))
    out['architecture_source'] = 'ASIA_V2_SELECTED_OUTCOME_BLIND_ARCHITECTURE'
    out['selected_architecture'] = gate['selected_architecture']
    out['v2_gate_status'] = gate['status']
    out['v1_reaction_semantics_reused_unchanged'] = True
    Path(a.output).write_text(json.dumps(out, indent=2, default=str))


if __name__ == '__main__':
    main()
