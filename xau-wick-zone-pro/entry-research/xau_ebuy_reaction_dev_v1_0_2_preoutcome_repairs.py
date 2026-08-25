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


# v1.0.1 already installs the Addendum-B runtime-state repair into base.
repair = load_module('ebuy_reaction_v101_repair', HERE / 'xau_ebuy_reaction_dev_v1_0_1_runtime_repair.py')
base = repair.base
original_trigger_outcome = base.trigger_outcome


def touch_fp_status(raw, start_idx, end_idx, entry, v, up_mult, dn_mult):
    up = entry + up_mult * v
    dn = entry - dn_mult * v
    if start_idx > end_idx:
        return 'NEITHER', None

    # Contact bar: a favorable high can predate the actual first touch/fill.
    r = raw.loc[start_idx]
    hit_up = float(r.high) >= up
    hit_dn = float(r.low) <= dn
    if hit_up:
        return 'AMBIGUOUS_CONTACT_BAR', start_idx
    if hit_dn:
        return 'ADVERSE_FIRST', start_idx

    if start_idx + 1 > end_idx:
        return 'NEITHER', None
    return base.fp_status(raw, start_idx + 1, end_idx, entry, v, up_mult, dn_mult)


def touch_target_status(raw, contact_idx, end_idx, tp_zlo, zlo):
    if contact_idx > end_idx:
        return 'NEITHER', None, None
    r = raw.loc[contact_idx]
    tp = float(r.high) >= tp_zlo
    inv = float(r.close) < zlo
    if tp:
        return 'AMBIGUOUS_CONTACT_BAR', contact_idx, (contact_idx if inv else None)
    if inv:
        return 'INVALIDATION_FIRST', None, contact_idx
    if contact_idx + 1 > end_idx:
        return 'NEITHER', None, None
    return base.target_invalidation_status(raw, contact_idx + 1, end_idx, tp_zlo, zlo)


def trigger_outcome_preoutcome_repaired(raw, contact_idx, end_idx, z, tp, v, kind):
    if kind != 'TOUCH_REF':
        return original_trigger_outcome(raw, contact_idx, end_idx, z, tp, v, kind)

    entry = float(z.zhi)
    info = {
        'fired': True,
        'trigger_idx': contact_idx,
        'exec_idx': contact_idx,
        'exec_price': entry,
        'trigger_time': base.pd.Timestamp(raw.at[contact_idx, 'time']),
        'exec_time': base.pd.Timestamp(raw.at[contact_idx, 'time']),
    }
    rec = {
        'trigger': kind,
        **info,
        'tp_distance_v': (float(tp['zlo']) - entry) / v,
        'touch_gap_through_entry': bool(float(raw.at[contact_idx, 'open']) < entry),
        'touch_contact_bar_favorable_order_unknown': False,
        'mfe_contact_bar_high_excluded': True,
    }

    for nm, up, dn in base.FP_SPECS:
        status, j = touch_fp_status(raw, contact_idx, end_idx, entry, v, up, dn)
        rec[nm] = status
        rec[nm + '_time'] = str(raw.at[j, 'time']) if j is not None else None
        if status == 'AMBIGUOUS_CONTACT_BAR':
            rec['touch_contact_bar_favorable_order_unknown'] = True

    os, tpj, invj = touch_target_status(raw, contact_idx, end_idx, float(tp['zlo']), float(z.zlo))
    rec['tp1_invalidation_status'] = os
    rec['tp1_time'] = str(raw.at[tpj, 'time']) if tpj is not None else None
    rec['invalidation_time'] = str(raw.at[invj, 'time']) if invj is not None else None

    # Conservative TOUCH MFE: exclude the contact-bar high because it can be pre-fill.
    hs = raw.high.iloc[contact_idx + 1:end_idx + 1].to_numpy(float)
    ls = raw.low.iloc[contact_idx:end_idx + 1].to_numpy(float)
    rec['mfe_v'] = float(max(0.0, hs.max() - entry) / v) if len(hs) else 0.0
    rec['mae_v'] = float(max(0.0, entry - ls.min()) / v) if len(ls) else 0.0
    return rec


base.trigger_outcome = trigger_outcome_preoutcome_repaired


if __name__ == '__main__':
    base.main()
