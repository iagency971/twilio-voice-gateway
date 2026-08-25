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


base = load_module('ebuy_reaction_v10_base', HERE / 'xau_ebuy_reaction_dev_v1_0.py')


def detect_contacts_runtime_repaired(raw, active, z4, snaps, displays, states):
    """Outcome-blind runtime-state repair frozen in Addendum B.

    Display episode identity/geometry are unchanged. Only ARMED/CONSUMED runtime
    state is carried causally by display_episode_id instead of relying on state
    dictionaries that were precomputed before contact detection.
    """
    targets = base.target_map(z4, snaps)
    contacts = []
    trades = []
    runtime = {}

    for s, zs, sts in zip(snaps, displays, states):
        # Never compute reaction outcomes on H2. Location states may have been
        # built causally, but reaction traversal stops at the frozen DEV end.
        if s['time'] >= base.DEV_HI:
            break
        if s['time'] not in targets:
            continue

        next_boundary = s['time'] + base.pd.Timedelta(minutes=5)
        end = min(next_boundary, base.ny_end(s['time']))
        i0 = base.raw_index(raw, s['time'], 'right') + 1
        i1 = base.raw_index(raw, end - base.pd.Timedelta(nanoseconds=1), 'right')
        if i1 < i0:
            continue

        for z, st in zip(zs, sts):
            eid = int(st['id'])
            rt = runtime.setdefault(eid, {
                'armed': False,
                'arm_time': None,
                'arm_close': None,
                'consumed': False,
            })
            if rt['consumed']:
                continue

            # A confirmed C5 close can arm immediately using only known data.
            if not rt['armed'] and float(s['close']) > float(z.zhi):
                rt['armed'] = True
                rt['arm_time'] = s['time']
                rt['arm_close'] = float(s['close'])

            contact_idx = None
            for j in range(i0, i1 + 1):
                r = raw.loc[j]
                if not rt['armed']:
                    if float(r.close) > float(z.zhi):
                        rt['armed'] = True
                        rt['arm_time'] = base.pd.Timestamp(r.time)
                        rt['arm_close'] = float(r.close)
                    continue
                if float(r.high) >= float(z.zlo) and float(r.low) <= float(z.zhi):
                    contact_idx = j
                    break

            if contact_idx is None:
                continue

            # Consume causally even for a pre-DEV contact. This preserves state
            # continuity without recording any pre-DEV outcome.
            rt['consumed'] = True
            ct = base.pd.Timestamp(raw.at[contact_idx, 'time'])
            if not (base.DEV_LO <= ct < base.DEV_HI):
                continue

            v = float(s['v'])
            tp = targets[s['time']]
            ai = base.active_index(active, ct)
            tr = base.trends(active, ai, v) if ai >= 0 else {f'trend{h}_v': None for h in (5, 15, 60, 240)}
            rr = raw.loc[contact_idx]
            width = max(float(z.zhi - z.zlo), 1e-12)
            rng = float(rr.high - rr.low)
            cp = float((rr.close - rr.low) / rng) if rng > 0 else 0.0

            contact = {
                'episode_id': eid,
                'contact_time': ct,
                'c5_time': s['time'],
                'family': z.family,
                'episode_origin_family': st['origin_family'],
                'slot_rank': st['slot'],
                'episode_age_c5': st['age'],
                'zlo': z.zlo,
                'center': z.center,
                'zhi': z.zhi,
                'zone_width_v': width / v,
                'v_contact': v,
                'arm_time': rt['arm_time'],
                'arm_close': rt['arm_close'],
                'arm_center_distance_v': ((float(rt['arm_close']) - float(z.center)) / v if rt['arm_close'] is not None else None),
                'tp1_zlo': tp['zlo'],
                'tp1_center': tp['center'],
                'tp1_zhi': tp['zhi'],
                'tp1_distance_from_touch_ref_v': (float(tp['zlo']) - float(z.zhi)) / v,
                'minutes_to_us_end': (base.ny_end(ct) - ct).total_seconds() / 60.0,
                'us_subperiod': base.subperiod(ct),
                'contact_penetration_width': (float(z.zhi) - float(rr.low)) / width,
                'contact_bull': int(float(rr.close) > float(rr.open)),
                'contact_close_position': cp,
                'approach5_v': tr.get('trend5_v'),
                'approach15_v': tr.get('trend15_v'),
                **tr,
            }
            contacts.append(contact)

            end_session = base.ny_end(ct)
            ej = base.raw_index(raw, end_session - base.pd.Timedelta(nanoseconds=1), 'right')
            for kind in base.TRIGGERS:
                rec = base.trigger_outcome(raw, contact_idx, ej, z, tp, v, kind)
                trades.append({**contact, **rec})

    return contacts, trades


base.detect_contacts = detect_contacts_runtime_repaired


if __name__ == '__main__':
    base.main()
