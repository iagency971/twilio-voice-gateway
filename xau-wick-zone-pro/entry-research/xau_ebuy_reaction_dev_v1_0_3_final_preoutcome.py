#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


repairs = load_module('ebuy_reaction_v102_repairs', HERE / 'xau_ebuy_reaction_dev_v1_0_2_preoutcome_repairs.py')
base = repairs.base
AMBIG = {'AMBIGUOUS', 'AMBIGUOUS_CONTACT_BAR'}


def fp_summary_repaired(rows, nm):
    vals = [r.get(nm) for r in rows if r.get('fired')]
    c = base.pd.Series(vals).value_counts().to_dict() if vals else {}
    fav = int(c.get('FAVORABLE_FIRST', 0))
    adv = int(c.get('ADVERSE_FIRST', 0))
    amb = int(sum(c.get(x, 0) for x in AMBIG))
    nei = int(c.get('NEITHER', 0))
    res = fav + adv
    total = fav + adv + amb + nei
    return {
        'favorable_first': fav,
        'adverse_first': adv,
        'ambiguous': amb,
        'ambiguous_contact_bar': int(c.get('AMBIGUOUS_CONTACT_BAR', 0)),
        'neither': nei,
        'resolved_denominator': res,
        'favorable_resolved_rate': float(fav / res) if res else None,
        'ambiguity_rate': float(amb / total) if total else None,
    }


def summarize_trigger_repaired(rows, total_contacts):
    fired = [r for r in rows if r.get('fired')]
    reasons = base.pd.Series([r.get('reason') for r in rows if not r.get('fired')]).value_counts().to_dict() if rows else {}
    statuses = [r.get('tp1_invalidation_status') for r in fired]
    os = base.pd.Series(statuses).value_counts().to_dict() if statuses else {}
    amb = int(sum(os.get(x, 0) for x in AMBIG))
    resolved_n = len(fired) - amb
    tp = int(os.get('TP1_FIRST', 0))
    inv = int(os.get('INVALIDATION_FIRST', 0))
    nei = int(os.get('NEITHER', 0))

    def quant(field):
        a = base.np.asarray([
            float(r[field]) for r in fired
            if r.get(field) is not None and base.np.isfinite(float(r[field]))
        ], float)
        return {
            'median': float(base.np.median(a)) if len(a) else None,
            'p90': float(base.np.quantile(a, .9)) if len(a) else None,
        }

    out = {
        'fired_count': len(fired),
        'fired_share_of_contacts': float(len(fired) / total_contacts) if total_contacts else 0.0,
        'nonfire_reasons': {str(k): int(v) for k, v in reasons.items()},
        'tp1_invalidation': {
            'TP1_FIRST': tp,
            'INVALIDATION_FIRST': inv,
            'NEITHER': nei,
            'AMBIGUOUS': amb,
            'AMBIGUOUS_CONTACT_BAR': int(os.get('AMBIGUOUS_CONTACT_BAR', 0)),
            'resolved_share': float(resolved_n / len(fired)) if fired else None,
            'tp1_resolved_rate': float(tp / resolved_n) if resolved_n else None,
            'invalidation_resolved_rate': float(inv / resolved_n) if resolved_n else None,
            'neither_resolved_rate': float(nei / resolved_n) if resolved_n else None,
        },
        'fp': {nm: fp_summary_repaired(fired, nm) for nm, _, _ in base.FP_SPECS},
        'mfe_v': quant('mfe_v'),
        'mae_v': quant('mae_v'),
        'tp_distance_v': quant('tp_distance_v'),
        'minutes_to_us_end': quant('minutes_to_us_end'),
    }
    out['DEV_ELIGIBLE'] = bool(
        len(fired) >= 1000
        and out['fired_share_of_contacts'] >= .20
        and out['tp1_invalidation']['resolved_share'] is not None
        and out['tp1_invalidation']['resolved_share'] >= .90
    )
    return out


base.fp_summary = fp_summary_repaired
base.summarize_trigger = summarize_trigger_repaired


if __name__ == '__main__':
    base.main()
