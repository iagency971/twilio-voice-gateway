#!/usr/bin/env python3
from __future__ import annotations

import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

import run_comex_dev_rank1_net_r_surface as surf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', required=True)
    ap.add_argument('--outcomes', required=True)
    ap.add_argument('--entry-model', required=True)
    ap.add_argument('--risk-rule', required=True)
    ap.add_argument('--target-r', type=float, required=True)
    ap.add_argument('--scenario', default='S11_C6_PRIMARY')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    f = pd.read_parquet(a.features)
    o = pd.read_parquet(a.outcomes)
    o = o[
        o.entry_model.eq(a.entry_model)
        & o.risk_rule.eq(a.risk_rule)
        & o.scenario.eq(a.scenario)
        & np.isclose(pd.to_numeric(o.target_r, errors='coerce'), float(a.target_r))
    ].copy()
    if o.empty:
        raise SystemExit('no frozen outcomes for requested net-R cell')

    keep = [c for c in o.columns if c not in f.columns or c == 'event_uid']
    x = f.merge(o[keep], on='event_uid', how='inner', validate='one_to_one')
    x['net_R'] = pd.to_numeric(x.net_R, errors='coerce')
    x = x[np.isfinite(x.net_R)].copy()
    if set(x.entry_model.astype(str).unique()) != {a.entry_model}:
        raise SystemExit('entry_model merge parity failure')

    eco = surf.economic(x)
    eco['target_r'] = float(a.target_r)
    eco.to_csv(out/'economic_summary.csv', index=False)
    result = surf.analyze_cell(
        x, a.entry_model, a.risk_rule, float(a.target_r), a.scenario, out
    )
    payload = {
        'version':'COMEX_DEV_RANK1_NET_R_CELL_RESULT_V1',
        'orchestration_only_split':True,
        'scientific_method':'identical to run_comex_dev_rank1_net_r_surface.py',
        'entry_model':a.entry_model,
        'risk_rule':a.risk_rule,
        'target_r':float(a.target_r),
        'scenario':a.scenario,
        'freeze':'COMEX_DEV_RANK1_NET_R_SURFACE_FREEZE_v1.md',
        'trade_selection_threshold_used':False,
        'result':result,
    }
    (out/'result.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))

if __name__ == '__main__':
    main()
