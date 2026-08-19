#!/usr/bin/env python3
from __future__ import annotations

import argparse, json
from pathlib import Path
import pandas as pd

RR_ORDER = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
COMPARISONS = ['B1_vs_B0', 'B2_vs_B1']


def contiguous3(vals):
    good = {round(float(x), 8) for x in vals}
    for i in range(len(RR_ORDER)-2):
        if all(round(x,8) in good for x in RR_ORDER[i:i+3]):
            return True
    return False


def possible_with_unknown(passing, unknown):
    return len(passing | unknown) >= 4 and contiguous3(passing | unknown)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    root = Path(a.root); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    rows = []
    files = sorted(root.rglob('result.json'))
    if not files:
        raise SystemExit('no net-R cell result.json files found')
    for p in files:
        z = json.loads(p.read_text())
        if z.get('version') != 'COMEX_DEV_RANK1_NET_R_CELL_RESULT_V1':
            continue
        r = z['result']
        base = {
            'entry_model': z['entry_model'],
            'risk_rule': z['risk_rule'],
            'target_r': float(z['target_r']),
            'scenario': z['scenario'],
            'status': r.get('status'),
            'events': int(r.get('events',0)),
            'sessions': int(r.get('sessions',0)),
        }
        comps = {c.get('comparison'):c for c in r.get('comparisons',[])}
        for comp in COMPARISONS:
            c = comps.get(comp)
            row = dict(base, comparison=comp)
            if c is None:
                row.update({
                    'family_balanced_event_mse_improvement':None,
                    'population_event_mse_improvement':None,
                    'session_balanced_mse_improvement':None,
                    'positive_years':None,
                    'bootstrap_lo':None,'bootstrap_median':None,'bootstrap_hi':None,
                    'directional_gate':False,
                })
            else:
                b = c.get('cluster_bootstrap_95',{})
                row.update({
                    'family_balanced_event_mse_improvement':c.get('family_balanced_event_mse_improvement'),
                    'population_event_mse_improvement':c.get('population_event_mse_improvement'),
                    'session_balanced_mse_improvement':c.get('session_balanced_mse_improvement'),
                    'positive_years':c.get('positive_years'),
                    'bootstrap_lo':b.get('lo'),'bootstrap_median':b.get('median'),'bootstrap_hi':b.get('hi'),
                    'directional_gate':bool(c.get('directional_gate',False)),
                })
            rows.append(row)

    df = pd.DataFrame(rows).sort_values(['entry_model','risk_rule','comparison','target_r'])
    df.to_csv(out/'rr_cell_summary.csv', index=False)

    verdicts = []
    for (model,risk,comp), g in df.groupby(['entry_model','risk_rule','comparison'], sort=True):
        modeled = set(round(float(x),8) for x in g.loc[g.status.eq('MODELED'),'target_r'])
        passing = set(round(float(x),8) for x in g.loc[g.status.eq('MODELED') & g.directional_gate.astype(bool),'target_r'])
        unknown = set(round(float(x),8) for x in RR_ORDER) - modeled
        eligible = len(passing) >= 4 and contiguous3(passing)
        if eligible:
            verdict = 'ELIGIBLE_DEV_RANK2'
        elif not unknown:
            verdict = 'NO_GO_DEV_RANK1'
        elif possible_with_unknown(passing, unknown):
            verdict = 'INCONCLUSIVE_DEV_RANK1'
        else:
            verdict = 'NO_GO_DEV_RANK1'
        verdicts.append({
            'entry_model':model,
            'risk_rule':risk,
            'comparison':comp,
            'modeled_rr_count':len(modeled),
            'qualifying_rr_count':len(passing),
            'qualifying_rrs':','.join(f'{x:.1f}' for x in sorted(passing)),
            'unknown_rrs':','.join(f'{x:.1f}' for x in sorted(unknown)),
            'has_contiguous_3':contiguous3(passing),
            'verdict':verdict,
        })
    vd = pd.DataFrame(verdicts).sort_values(['entry_model','risk_rule','comparison'])
    vd.to_csv(out/'plateau_verdicts.csv', index=False)

    payload = {
        'version':'COMEX_DEV_RANK1_NET_R_AGGREGATE_V1',
        'freeze':'COMEX_DEV_RANK1_NET_R_AGGREGATION_FREEZE_v1.md',
        'rr_order':RR_ORDER,
        'cell_results_found':int(len(files)),
        'cell_comparison_rows':int(len(df)),
        'feature_group_verdicts':vd.to_dict('records'),
        'dev_rank2_opened':False,
        'retro_confirm_opened':False,
        'locked_comex_test_opened':False,
    }
    (out/'result.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))

if __name__ == '__main__':
    main()
