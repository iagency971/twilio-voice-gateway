import argparse, glob, json
from pathlib import Path


def fmt(x, n=8):
    return 'NA' if x is None else f'{x:.{n}f}'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--inputs', nargs='+', required=True)
    p.add_argument('--output-json', required=True)
    p.add_argument('--output-md', required=True)
    a = p.parse_args()

    files = []
    for pat in a.inputs:
        files.extend(glob.glob(pat, recursive=True))
    rows = [json.load(open(f)) for f in sorted(set(files))]
    if len(rows) != 5:
        raise RuntimeError(f'expected 5 preregistered candidates, got {len(rows)}')
    rows = sorted(rows, key=lambda x: x['lookback_active_m1'])
    if [r['lookback_active_m1'] for r in rows] != [240,360,600,900,1440]:
        raise RuntimeError('candidate set mismatch')

    shortlist = [r['lookback_active_m1'] for r in rows if r['preregistered_flags']['DUAL_FEED_STRONG_PASS']]
    bid_shortlist = [r['lookback_active_m1'] for r in rows if r['preregistered_flags']['BID_ROBUST_PASS']]
    incumbent = next(r for r in rows if r['lookback_active_m1'] == 1440)

    summary = {
        'status': 'DEV_MEMORY_SENSITIVITY_COMPLETE_AWAITING_TARGETED_PRO_GATE',
        'prereg': 'XAUUSD_Z4_MEMORY_LOOKBACK_SENSITIVITY_PREREG_v0_1_2026-08-24.md',
        'candidate_set_active_m1': [240,360,600,900,1440],
        'incumbent_active_m1': 1440,
        'BID_ROBUST_PASS_candidates': bid_shortlist,
        'DUAL_FEED_STRONG_PASS_candidates_for_Pro_review': shortlist,
        'winner_selected': False,
        'production_change_authorized': False,
        'candidates': rows,
        'incumbent_reference': {
            'BID_delta_brier': incumbent['BID']['pooled']['delta_brier'],
            'ASK_delta_brier': incumbent['ASK']['pooled']['delta_brier'],
            'BID_churn': incumbent['geometry_stability']['BID']['one_step_drop_churn_rate'],
            'ASK_churn': incumbent['geometry_stability']['ASK']['one_step_drop_churn_rate'],
        },
        'next_decision': 'Targeted Pro methodological gate: plateau/robustness review before any historical replication or Pine change.',
    }
    Path(a.output_json).write_text(json.dumps(summary, indent=2, allow_nan=False))

    lines = []
    lines.append('# XAUUSD Z4 — Memory Lookback DEV Sensitivity Results v0.1')
    lines.append('')
    lines.append('**Status:** DEV COMPLETE — NO WINNER SELECTED — NO PRODUCTION CHANGE')
    lines.append('')
    lines.append('Preregistered candidates: **240 / 360 / 600 / 900 / 1440 active M1**. The 1440 architecture remains the validated incumbent until a later decision gate.')
    lines.append('')
    lines.append('| L | BID ΔBrier | BID weekly 95% | ASK ΔBrier | ASK weekly 95% | BID robust | Dual-feed strong | BID churn | Median lineage | Median zones/landmark |')
    lines.append('|---:|---:|---:|---:|---:|:---:|:---:|---:|---:|---:|')
    for r in rows:
        b=r['BID']; q=r['ASK']; gs=r['geometry_stability']['BID']; fl=r['preregistered_flags']
        bci=b['weekly']['bootstrap_95']; qci=q['weekly']['bootstrap_95']
        lines.append(
            f"| {r['lookback_active_m1']} | {fmt(b['pooled']['delta_brier'])} | [{fmt(bci[0])}, {fmt(bci[1])}] | "
            f"{fmt(q['pooled']['delta_brier'])} | [{fmt(qci[0])}, {fmt(qci[1])}] | "
            f"{'PASS' if fl['BID_ROBUST_PASS'] else 'FAIL'} | {'PASS' if fl['DUAL_FEED_STRONG_PASS'] else 'FAIL'} | "
            f"{fmt(gs['one_step_drop_churn_rate'],6)} | {fmt(gs['lineage_length_snapshots']['median'],2)} | "
            f"{fmt(gs['zones_per_represented_landmark']['median'],2)} |"
        )
    lines.append('')
    lines.append('## Fold-by-fold BID ΔBrier')
    lines.append('')
    lines.append('| L | APR | MAY | JUN | JUL | Positive folds |')
    lines.append('|---:|---:|---:|---:|---:|---:|')
    for r in rows:
        f=r['BID']['folds']; vals=[f[x]['delta_brier'] for x in ['APR','MAY','JUN','JUL']]
        lines.append(f"| {r['lookback_active_m1']} | {fmt(vals[0])} | {fmt(vals[1])} | {fmt(vals[2])} | {fmt(vals[3])} | {sum(v>0 for v in vals)}/4 |")
    lines.append('')
    lines.append('## Frozen interpretation')
    lines.append('')
    lines.append(f"- BID robust candidates: **{bid_shortlist if bid_shortlist else 'none'}**.")
    lines.append(f"- Dual-feed strong candidates eligible for targeted Pro review: **{shortlist if shortlist else 'none'}**.")
    lines.append('- This run does **not** choose the final memory.')
    lines.append('- Raw Brier levels across memories are not used alone because each memory creates a different zone population/base rate.')
    lines.append('- Geometry stability/churn is secondary and cannot rescue a candidate that loses predictive robustness.')
    lines.append('- No Validation/OOS data was used in this gate.')
    lines.append('- No Pine/R/production modification is authorized from this DEV sensitivity result alone.')
    lines.append('')
    lines.append('## Next step')
    lines.append('')
    lines.append('Run the planned **targeted Pro methodological gate** on this fixed five-candidate result set to decide whether the incumbent 1440 should remain frozen or whether a shorter memory deserves a separately frozen historical replication.')
    Path(a.output_md).write_text('\n'.join(lines) + '\n')
    print(json.dumps({
        'status': summary['status'],
        'BID_ROBUST_PASS_candidates': bid_shortlist,
        'DUAL_FEED_STRONG_PASS_candidates_for_Pro_review': shortlist,
        'winner_selected': False,
    }, indent=2))


if __name__ == '__main__':
    main()
