#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / 'entry-research'
HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


final = load_module('asia_final_preoutcome_chain', ENTRY / 'xau_ebuy_reaction_dev_v1_0_3_final_preoutcome.py')
asia = load_module('asia_session_plumbing_v1', HERE / 'xau_ebuy_asia_reaction_v1_0.py')

# Freeze the Asia session/state/contact plumbing, but replace its old raw v1.0
# reaction base with the project's final repaired pre-outcome chain.
asia.base = final.base


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

    # Adapt only the legacy v1 gate-token expected by the Asia plumbing. The
    # selected v2 candidate table and all reaction semantics stay unchanged.
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
        asia.main()
    finally:
        sys.argv = old
        tmp.unlink(missing_ok=True)

    out = json.load(open(a.output))
    out['architecture_source'] = 'ASIA_V2_SELECTED_OUTCOME_BLIND_ARCHITECTURE'
    out['selected_architecture'] = gate['selected_architecture']
    out['v2_gate_status'] = gate['status']
    out['reaction_engine'] = 'xau_ebuy_reaction_dev_v1_0_3_final_preoutcome'
    out['final_preoutcome_repairs_applied'] = True
    out['legacy_raw_v1_reaction_artifacts_authoritative'] = False
    Path(a.output).write_text(json.dumps(out, indent=2, default=str))


if __name__ == '__main__':
    main()
