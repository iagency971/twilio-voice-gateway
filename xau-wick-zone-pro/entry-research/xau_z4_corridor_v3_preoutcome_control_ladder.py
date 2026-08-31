#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import xau_z4_corridor_v3_preoutcome as base

LADDER=json.load(open(HERE/'XAUUSD_Z4_CORRIDOR_V3_CONTROL_LADDER_PREDECL_2026-08-31.json'))
DESIGNS={d['id']:tuple(float(x) for x in d['offsets_v_birth']) for d in LADDER['designs']}

def main():
    if '--control-design' not in sys.argv:
        raise RuntimeError('missing --control-design')
    i=sys.argv.index('--control-design')
    design=sys.argv[i+1]
    if design not in DESIGNS:
        raise RuntimeError(f'unknown design {design}')
    del sys.argv[i:i+2]
    base.CONTROL_OFFSETS=DESIGNS[design]
    old_parse=base.parse_args
    def parse_args_with_design():
        a=old_parse()
        setattr(a,'control_design',design)
        return a
    base.parse_args=parse_args_with_design
    base.main()

if __name__=='__main__':
    main()
