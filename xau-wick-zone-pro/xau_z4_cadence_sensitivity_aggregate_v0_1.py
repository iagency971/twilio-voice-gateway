import argparse, glob, json
from pathlib import Path

CAD=[1,5,15]
KNOWN_15={
 'BID': {'delta_brier':0.0014727645192173233,'delta_logloss':0.004095136286836887},
 'ASK': {'delta_brier':0.0017428441286502505,'delta_logloss':0.004777601966964029},
}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--inputs',required=True)
    p.add_argument('--output-json',required=True)
    p.add_argument('--output-md',required=True)
    a=p.parse_args()
    files=sorted(glob.glob(a.inputs))
    R={}
    for f in files:
        x=json.load(open(f)); c=int(x['cadence_min'])
        if c in R: raise RuntimeError('duplicate cadence')
        R[c]=x
    if set(R)!=set(CAD): raise RuntimeError(f'missing cadences {set(CAD)-set(R)}')

    geom={}
    for feed in ('BID','ASK'):
        hs={c:R[c][feed]['geometry_common15']['sha256'] for c in CAD}
        counts={c:(R[c][feed]['geometry_common15']['rows'],R[c][feed]['geometry_common15']['landmarks']) for c in CAD}
        geom[feed]={
            'hashes':hs,'counts':counts,
            'hash_parity_pass':len(set(hs.values()))==1,
            'count_parity_pass':len(set(counts.values()))==1
        }
    c15=R[15]
    repro={}
    for feed in ('BID','ASK'):
        p15=c15[feed]['pooled_all_cadence']
        repro[feed]={
            'delta_brier_abs_error':abs(p15['delta_brier']-KNOWN_15[feed]['delta_brier']),
            'delta_logloss_abs_error':abs(p15['delta_logloss']-KNOWN_15[feed]['delta_logloss'])
        }
        repro[feed]['pass']=repro[feed]['delta_brier_abs_error']<=1e-12 and repro[feed]['delta_logloss_abs_error']<=1e-12
    provenance=bool(all(geom[f]['hash_parity_pass'] and geom[f]['count_parity_pass'] for f in ('BID','ASK')) and all(repro[f]['pass'] for f in ('BID','ASK')))

    shortlist=[]
    for c in (1,5):
        fl=R[c]['preregistered_flags']
        if fl['DUAL_FEED_STRONG_PASS'] and fl['COMMON15_DUAL_FEED_STRONG_PASS'] and provenance:
            shortlist.append(c)

    out={
        'status':'DEV_CADENCE_SENSITIVITY_COMPLETE_NO_PRODUCTION_CHANGE',
        'candidates_min':CAD,
        'lookback_active_m1':1440,
        'endpoint':'REVISIT_240',
        'geometry_common15_parity':geom,
        'incumbent_c15_reproduction':repro,
        'provenance_gate_pass':provenance,
        'shorter_cadence_pro_review_shortlist_min':shortlist,
        'candidates':{str(c):R[c] for c in CAD},
        'decision_rule_result':(
            'NO_SHORTER_CADENCE_ELIGIBLE_RETAIN_C15'
            if len(shortlist)==0 else
            'SHORTER_CADENCE_ELIGIBLE_FOR_TARGETED_PRO_REVIEW_NO_WINNER_YET'
        ),
        'limits':[
            'DEV Jan-Jul 2024 only.',
            'No Validation/OOS data used.',
            'No production/Pine/R change is authorized by this result alone.'
        ]
    }
    Path(a.output_json).write_text(json.dumps(out,indent=2,allow_nan=False))

    lines=[
        '# XAUUSD Z4 — Landmark Cadence DEV Sensitivity Results v0.1','',
        '**Status:** DEV COMPLETE — NO PRODUCTION CHANGE','',
        'Lookback fixed at **1,440 active M1**. Endpoint fixed at **REVISIT_240**.','',
        '| Cadence | BID ΔBrier all | BID weekly95 all | ASK ΔBrier all | ASK weekly95 all | BID ΔBrier common15 | ASK ΔBrier common15 | Dual-feed all | Dual-feed common15 |',
        '|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|'
    ]
    for c in CAD:
        x=R[c]; B=x['BID']; A=x['ASK']; f=x['preregistered_flags']
        bw=B['pooled_all_cadence']['weekly']['bootstrap_95']; aw=A['pooled_all_cadence']['weekly']['bootstrap_95']
        lines.append(
            f"| {c} | {B['pooled_all_cadence']['delta_brier']:.8f} | [{bw[0]:.8f}, {bw[1]:.8f}] | "
            f"{A['pooled_all_cadence']['delta_brier']:.8f} | [{aw[0]:.8f}, {aw[1]:.8f}] | "
            f"{B['pooled_common15']['delta_brier']:.8f} | {A['pooled_common15']['delta_brier']:.8f} | "
            f"{'PASS' if f['DUAL_FEED_STRONG_PASS'] else 'FAIL'} | {'PASS' if f['COMMON15_DUAL_FEED_STRONG_PASS'] else 'FAIL'} |"
        )
    lines += ['','## Fold-by-fold BID ΔBrier — all cadence snapshots','',
              '| Cadence | APR | MAY | JUN | JUL |','|---:|---:|---:|---:|---:|']
    for c in CAD:
        B=R[c]['BID']['folds']
        lines.append(f"| {c} | {B['APR']['all_cadence']['delta_brier']:.8f} | {B['MAY']['all_cadence']['delta_brier']:.8f} | {B['JUN']['all_cadence']['delta_brier']:.8f} | {B['JUL']['all_cadence']['delta_brier']:.8f} |")
    lines += ['','## Common-15 geometry/provenance','']
    for feed in ('BID','ASK'):
        g=geom[feed]
        lines.append(f"- {feed}: geometry hash parity = **{'PASS' if g['hash_parity_pass'] and g['count_parity_pass'] else 'FAIL'}**; hash `{g['hashes'][15]}`.")
    lines.append(f"- C15 exact pooled reproduction vs frozen DEV = **{'PASS' if all(repro[f]['pass'] for f in ('BID','ASK')) else 'FAIL'}**.")
    lines += ['','## Stability diagnostics','',
              '| Cadence | BID per-update drop | BID median lineage max age (active M1) | BID p95 lineage max age | BID common15 drop |',
              '|---:|---:|---:|---:|---:|']
    for c in CAD:
        B=R[c]['BID']; s=B['stability_per_update']; q=B['stability_common15']
        lines.append(f"| {c} | {s['per_update_drop_rate']:.6f} | {s['lineage_max_age_active_m1']['median']:.2f} | {s['lineage_max_age_active_m1']['p95']:.2f} | {q['per_update_drop_rate']:.6f} |")
    lines += ['','## Preregistered result','',
              f"- Provenance/geometry parity gate: **{'PASS' if provenance else 'FAIL'}**.",
              f"- Shorter cadences eligible for targeted Pro review: **{shortlist}**.",
              f"- Decision-rule result: **{out['decision_rule_result']}**.",
              '- C15 remains the validated incumbent until an explicit later decision.',
              '- No Validation/OOS or production/Pine/R change is authorized by this DEV run.'
             ]
    Path(a.output_md).write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    main()
