#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / 'entry-research'
CAD = ROOT / 'cadence-sensitivity'


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


reaction = load_module('c1_reaction_final', ENTRY / 'xau_ebuy_reaction_dev_v1_0_3_final_preoutcome.py')
base = reaction.base
loc = load_module('c1_reaction_loc', CAD / 'xau_ebuy_c1_refresh_outcome_blind_gate_v1_0.py')
Zone = base.v01.Zone

WINDOWS = {
    'H1': (pd.Timestamp('2024-08-01T00:00:00Z'), pd.Timestamp('2025-08-01T00:00:00Z'), 'OOS_H1'),
    'H2': (pd.Timestamp('2025-08-01T00:00:00Z'), pd.Timestamp('2026-08-01T00:00:00Z'), 'OOS_H2'),
}
AMBIG = {'AMBIGUOUS', 'AMBIGUOUS_CONTACT_BAR'}
BOOT_SEED = 20260826
BOOT_N = 10000


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--window', choices=sorted(WINDOWS), required=True)
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--c1-pkl', required=True)
    p.add_argument('--c5-pkl', required=True)
    p.add_argument('--candidates-gz', required=True)
    p.add_argument('--coverage-result', required=True)
    p.add_argument('--frozen-h1-result', required=True)
    p.add_argument('--frozen-h2-result', required=True)
    p.add_argument('--evidence-dir', required=True)
    p.add_argument('--detector-c1-sec', type=float, default=None)
    p.add_argument('--detector-c5-sec', type=float, default=None)
    p.add_argument('--output', required=True)
    return p.parse_args()


def qpack(values):
    a = np.asarray([float(x) for x in values if x is not None and np.isfinite(float(x))], float)
    return {'median': float(np.median(a)) if len(a) else None,
            'p90': float(np.quantile(a, .9)) if len(a) else None}


def clean_z4(p):
    d = pd.read_pickle(p).copy(); d['time'] = pd.to_datetime(d.time, utc=True)
    need = ['time', 'side', 'center', 'zlo', 'zhi']
    miss = [c for c in need if c not in d.columns]
    if miss: raise RuntimeError(f'missing geometry columns: {miss}')
    # Outcome/label columns produced by the research detector are never consumed.
    return d[need].copy()


def select_window(seq, lo, hi):
    return [x for x in seq if lo <= pd.Timestamp(x['time']) < hi]


def filter_parallel(snaps, displays, pools, lo, hi):
    idx = [i for i, s in enumerate(snaps) if lo <= pd.Timestamp(s['time']) < hi]
    return [snaps[i] for i in idx], [displays[i] for i in idx], [pools[i] for i in idx]


def frozen_c5_states(active, z4, cand, cov, window, lo, hi, cov_key):
    snaps = select_window(loc.make_eval_times(active, z4, 5, 96), lo, hi)
    c = cand[cand.window.astype(str) == cov_key].copy(); c['time'] = pd.to_datetime(c.time, utc=True)
    c = c[(c.time >= lo) & (c.time < hi)].copy()
    by = {pd.Timestamp(t): g.sort_values('entry_rank') for t, g in c.groupby('time', sort=True)}
    displays = []
    for s in snaps:
        g = by.get(pd.Timestamp(s['time'])); zs = []
        if g is not None:
            if not np.allclose(g.close.to_numpy(float), float(s['close']), rtol=0, atol=1e-9):
                raise RuntimeError(f'{window}: frozen candidate close mismatch at {s["time"]}')
            if not np.allclose(g.v60.to_numpy(float), float(s['v']), rtol=0, atol=1e-9):
                raise RuntimeError(f'{window}: frozen candidate v60 mismatch at {s["time"]}')
            for _, r in g.iterrows():
                zs.append(Zone(float(r.center), float(r.zlo), float(r.zhi), str(r.family), 0.0))
        if len(zs) > 3: raise RuntimeError(f'{window}: >3 frozen zones at {s["time"]}')
        displays.append(zs)
    exp = cov['results'][cov_key]
    if len(snaps) != int(exp['eligible_snapshot_count']):
        raise RuntimeError(f'{window}: frozen eligible snapshots {len(snaps)} != {exp["eligible_snapshot_count"]}')
    got = base.v01.metrics(snaps, displays); em = exp['metrics']
    for b in ('0.5', '1.0', '1.5', '2.0'):
        if abs(float(got['coverage'][b]) - float(em['coverage'][b])) > 1e-12:
            raise RuntimeError(f'{window}: frozen coverage parity {b} failed')
    for k in ('candidate_count_median', 'candidate_count_p90', 'nearest_distance_v_median', 'nearest_distance_v_p90'):
        if abs(float(got[k]) - float(em[k])) > 1e-12:
            raise RuntimeError(f'{window}: frozen metric parity {k} failed')
    return snaps, displays, {'eligible_snapshot_count': len(snaps), 'candidate_rows': int(len(c)), 'coverage_parity': True}


def historical_frozen_baseline(raw, active, z4, snaps, displays, lo, hi):
    old_lo, old_hi, old_triggers = base.DEV_LO, base.DEV_HI, base.TRIGGERS
    try:
        base.DEV_LO, base.DEV_HI = lo, hi; base.TRIGGERS = ('BULL_REJECTION',)
        states = base.assign_episode_states(snaps, displays)
        contacts, trades = base.detect_contacts(raw, active, z4, snaps, displays, states)
    finally:
        base.DEV_LO, base.DEV_HI, base.TRIGGERS = old_lo, old_hi, old_triggers
    br = [r for r in trades if r.get('trigger') == 'BULL_REJECTION']
    return contacts, br, base.summarize_trigger(br, len(contacts))


def expected_frozen(window, h1, h2):
    if window == 'H1':
        s = h1['trigger_summaries']['BULL_REJECTION']['tp1_invalidation']
        return {'contact_episode_count': int(h1['contact_episode_count']),
                'fired_count': int(h1['trigger_summaries']['BULL_REJECTION']['fired_count']),
                'tp1_resolved_rate': float(s['tp1_resolved_rate'])}
    return {'contact_episode_count': int(h2['contact_episode_count']),
            'fired_count': int(h2['bull_rejection_fired_count']),
            'tp1_resolved_rate': float(h2['metrics']['baseline_positive_rate'])}


def parity_frozen(got_contacts, got_summ, exp):
    got = {'contact_episode_count': int(len(got_contacts)), 'fired_count': int(got_summ['fired_count']),
           'tp1_resolved_rate': float(got_summ['tp1_invalidation']['tp1_resolved_rate'])}
    checks = {'contact_episode_count_exact': got['contact_episode_count'] == exp['contact_episode_count'],
              'fired_count_exact': got['fired_count'] == exp['fired_count'],
              'tp1_resolved_rate_exact_1e12': abs(got['tp1_resolved_rate'] - exp['tp1_resolved_rate']) <= 1e-12}
    return got, checks, bool(all(checks.values()))


def episode_match(old_states, z, tol, used):
    cand = []
    for j, st in enumerate(old_states):
        if j in used: continue
        if base.match(st['zone'], z, tol):
            cand.append((abs(float(st['zone'].center) - float(z.center)), j, st))
    return min(cand, key=lambda x: (x[0], x[1])) if cand else None


def build_runtime_states(prev_states, prev_s, s, zs, cadence, next_id):
    contig = prev_s is not None and pd.Timestamp(s['time']) - pd.Timestamp(prev_s['time']) == pd.Timedelta(minutes=cadence)
    tol = .25 * max(float(prev_s['v']), float(s['v'])) if contig else 0.0
    used = set(); cur = []
    for slot, z in enumerate(zs, 1):
        m = episode_match(prev_states, z, tol, used) if contig else None
        if m is not None:
            _, j, old = m; used.add(j)
            st = {'id': old['id'], 'age': old['age'] + 1, 'zone': z, 'slot': slot,
                  'armed': bool(old['armed']), 'arm_time': old['arm_time'], 'arm_close': old['arm_close'],
                  'consumed': bool(old['consumed']), 'origin_family': old['origin_family']}
        else:
            st = {'id': next_id, 'age': 1, 'zone': z, 'slot': slot, 'armed': False,
                  'arm_time': None, 'arm_close': None, 'consumed': False, 'origin_family': z.family}
            next_id += 1
        cur.append(st)
    return cur, next_id


def raw_bounds_inclusive(raw, t, cadence):
    start = base.raw_index(raw, t, 'right') + 1
    end_t = min(pd.Timestamp(t) + pd.Timedelta(minutes=cadence), base.ny_end(t) - pd.Timedelta(nanoseconds=1))
    return start, base.raw_index(raw, end_t, 'right')


def causal_contacts(raw, active, z4, snaps, displays, cadence, lo, hi):
    targets = base.target_map(z4, snaps); contacts = []; trades = []
    prev_states = []; prev_s = None; next_id = 1
    trading_days = sorted({pd.Timestamp(s['time']).tz_convert('America/New_York').date().isoformat() for s in snaps})
    for s, zs in zip(snaps, displays):
        t = pd.Timestamp(s['time'])
        if not (lo <= t < hi): continue
        states, next_id = build_runtime_states(prev_states, prev_s, s, zs, cadence, next_id)
        for st in states:
            z = st['zone']
            if not st['armed'] and float(s['close']) > float(z.zhi):
                st['armed'] = True; st['arm_time'] = t; st['arm_close'] = float(s['close'])
        tp = targets.get(t); i0, i1 = raw_bounds_inclusive(raw, t, cadence)
        if tp is not None and i1 >= i0:
            for st in states:
                if st['consumed']: continue
                z = st['zone']; contact_idx = None
                for j in range(max(0, i0), min(len(raw) - 1, i1) + 1):
                    r = raw.loc[j]
                    if not st['armed']:
                        if float(r.close) > float(z.zhi):
                            st['armed'] = True; st['arm_time'] = pd.Timestamp(r.time); st['arm_close'] = float(r.close)
                        continue
                    if float(r.high) >= float(z.zlo) and float(r.low) <= float(z.zhi):
                        contact_idx = j; break
                if contact_idx is None: continue
                st['consumed'] = True
                ct = pd.Timestamp(raw.at[contact_idx, 'time']); v = float(s['v']); rr = raw.loc[contact_idx]
                width = max(float(z.zhi) - float(z.zlo), 1e-12)
                contact = {'episode_id': int(st['id']), 'state_time': t, 'contact_time': ct,
                           'cadence_min': int(cadence), 'family': z.family,
                           'episode_origin_family': st['origin_family'], 'slot_rank': int(st['slot']),
                           'episode_age_states': int(st['age']), 'episode_age_active_min': int(st['age'] * cadence),
                           'zlo': float(z.zlo), 'center': float(z.center), 'zhi': float(z.zhi),
                           'zone_width_v': float(width / v), 'v_contact': v,
                           'arm_time': st['arm_time'], 'arm_close': st['arm_close'],
                           'tp1_zlo': float(tp['zlo']), 'tp1_center': float(tp['center']), 'tp1_zhi': float(tp['zhi']),
                           'tp1_distance_from_touch_ref_v': float((float(tp['zlo']) - float(z.zhi)) / v),
                           'minutes_to_us_end': float((base.ny_end(ct) - ct).total_seconds() / 60.0),
                           'us_subperiod': base.subperiod(ct),
                           'ny_day': ct.tz_convert('America/New_York').date().isoformat(),
                           'contact_bull': int(float(rr.close) > float(rr.open))}
                contacts.append(contact)
                ej = base.raw_index(raw, base.ny_end(ct) - pd.Timedelta(nanoseconds=1), 'right')
                rec = base.trigger_outcome(raw, contact_idx, ej, z, tp, v, 'BULL_REJECTION')
                trades.append({**contact, **rec})
        prev_states = states; prev_s = s
    return contacts, trades, trading_days


def stratify(contacts, trades, field):
    vals = sorted({str(r.get(field)) for r in contacts}); out = {}
    for val in vals:
        cc = [r for r in contacts if str(r.get(field)) == val]
        tt = [r for r in trades if str(r.get(field)) == val and bool(r.get('fired'))]
        if len(cc) < 100:
            out[val] = {'sparse': True, 'contact_count': len(cc)}; continue
        c = Counter(str(r.get('tp1_invalidation_status')) for r in tt); amb = sum(c[k] for k in AMBIG); res = len(tt) - amb
        out[val] = {'sparse': False, 'contact_count': len(cc), 'fired_count': len(tt),
                    'tp1_resolved_rate': float(c['TP1_FIRST'] / res) if res else None}
    return out


def summarize_causal(contacts, trades, trading_days):
    fired = [r for r in trades if bool(r.get('fired'))]
    c = Counter(str(r.get('tp1_invalidation_status')) for r in fired); amb = sum(c[k] for k in AMBIG)
    resolved_n = len(fired) - amb; tp = c['TP1_FIRST']; inv = c['INVALIDATION_FIRST']; nei = c['NEITHER']
    def elapsed(field):
        vals = []
        for r in fired:
            if not r.get(field) or not r.get('exec_time'): continue
            vals.append((pd.Timestamp(r[field]) - pd.Timestamp(r['exec_time'])).total_seconds() / 60.0)
        return qpack(vals)
    return {'contact_episode_count': int(len(contacts)),
            'unique_contact_episode_ids': int(len({int(r['episode_id']) for r in contacts})),
            'trading_day_count': int(len(trading_days)),
            'contacts_per_trading_day': float(len(contacts) / len(trading_days)) if trading_days else None,
            'bull_rejection_fired_count': int(len(fired)),
            'bull_rejection_fired_share': float(len(fired) / len(contacts)) if contacts else None,
            'bull_rejection_fired_per_trading_day': float(len(fired) / len(trading_days)) if trading_days else None,
            'TP1_FIRST': int(tp), 'INVALIDATION_FIRST': int(inv), 'NEITHER': int(nei),
            'AMBIGUOUS': int(amb), 'AMBIGUOUS_CONTACT_BAR': int(c['AMBIGUOUS_CONTACT_BAR']),
            'resolved_denominator': int(resolved_n),
            'tp1_resolved_rate': float(tp / resolved_n) if resolved_n else None,
            'invalidation_resolved_rate': float(inv / resolved_n) if resolved_n else None,
            'neither_resolved_rate': float(nei / resolved_n) if resolved_n else None,
            'time_to_tp1_min': elapsed('tp1_time'), 'time_to_invalidation_min': elapsed('invalidation_time'),
            'contact_zone_width_v': qpack([r['zone_width_v'] for r in contacts]),
            'contact_tp_distance_v': qpack([r['tp1_distance_from_touch_ref_v'] for r in contacts]),
            'fired_tp_distance_v': qpack([r.get('tp_distance_v') for r in fired]),
            'by_origin_family': stratify(contacts, trades, 'episode_origin_family'),
            'by_us_subperiod': stratify(contacts, trades, 'us_subperiod')}


def day_counts(trades):
    out = {}
    for r in trades:
        if not bool(r.get('fired')): continue
        q = out.setdefault(str(r['ny_day']), {'tp': 0, 'resolved': 0}); st = str(r.get('tp1_invalidation_status'))
        if st in AMBIG: continue
        q['resolved'] += 1
        if st == 'TP1_FIRST': q['tp'] += 1
    return out


def paired_day_bootstrap(c1_trades, c5_trades):
    a = day_counts(c1_trades); b = day_counts(c5_trades); days = sorted(set(a) | set(b))
    if not days: return {'n_days': 0, 'delta_tp1_rate': None, 'bootstrap_95': [None, None], 'seed': BOOT_SEED, 'replicates': BOOT_N}
    z = np.asarray([(a.get(d, {'tp': 0, 'resolved': 0})['tp'], a.get(d, {'tp': 0, 'resolved': 0})['resolved'],
                     b.get(d, {'tp': 0, 'resolved': 0})['tp'], b.get(d, {'tp': 0, 'resolved': 0})['resolved']) for d in days], int)
    p1 = z[:, 0].sum() / z[:, 1].sum() if z[:, 1].sum() else np.nan
    p5 = z[:, 2].sum() / z[:, 3].sum() if z[:, 3].sum() else np.nan
    rng = np.random.default_rng(BOOT_SEED); vals = []; n = len(days)
    for _ in range(BOOT_N):
        q = z[rng.integers(0, n, size=n)]; d1 = q[:, 1].sum(); d5 = q[:, 3].sum()
        if d1 and d5: vals.append(q[:, 0].sum() / d1 - q[:, 2].sum() / d5)
    return {'n_days': int(n), 'delta_tp1_rate': float(p1 - p5) if np.isfinite(p1) and np.isfinite(p5) else None,
            'bootstrap_95': [float(np.quantile(vals, .025)), float(np.quantile(vals, .975))] if vals else [None, None],
            'seed': BOOT_SEED, 'replicates': BOOT_N}


def corrected_birth_death(snaps, displays, cadence):
    prev = []; prev_s = None; trans = births = deaths = 0
    for s, zs in zip(snaps, displays):
        contig = prev_s is not None and pd.Timestamp(s['time']) - pd.Timestamp(prev_s['time']) == pd.Timedelta(minutes=cadence)
        if contig:
            trans += 1; tol = .25 * max(float(prev_s['v']), float(s['v'])); used = set(); matches = 0
            for z in zs:
                cand = [(abs(float(old.center)-float(z.center)), j) for j, old in enumerate(prev)
                        if j not in used and base.match(old, z, tol)]
                if cand:
                    _, j = min(cand, key=lambda x: (x[0], x[1])); used.add(j); matches += 1
            births += len(zs) - matches; deaths += len(prev) - matches
        prev = list(zs); prev_s = s
    return {'contiguous_state_transitions': int(trans), 'births_on_contiguous_transitions': int(births),
            'deaths_on_contiguous_transitions': int(deaths),
            'births_per_100_state_transitions': float(100*births/trans) if trans else None,
            'deaths_per_100_state_transitions': float(100*deaths/trans) if trans else None}


def stability_threshold_checks(pack):
    m = pack['location']; st = pack['stability']
    c = {'coverage_1v_ge_080': m['coverage']['1.0'] is not None and m['coverage']['1.0'] >= .80,
         'coverage_1p5v_ge_090': m['coverage']['1.5'] is not None and m['coverage']['1.5'] >= .90,
         'coverage_2v_ge_095': m['coverage']['2.0'] is not None and m['coverage']['2.0'] >= .95,
         'zone_count_p90_le_3': m['zone_count_p90'] is not None and m['zone_count_p90'] <= 3.0,
         'nearest_distance_p90_le_1p5v': m['nearest_distance_v_p90'] is not None and m['nearest_distance_v_p90'] <= 1.5,
         'survival_persistence_ge_070': st['survival_aware_display_persistence'] is not None and st['survival_aware_display_persistence'] >= .70,
         'unexplained_survival_share_le_005': st['unexplained_share_of_survival_eligible'] is not None and st['unexplained_share_of_survival_eligible'] <= .05}
    return {'checks': c, 'pass': bool(all(c.values()))}


def compact_stability(raw, snaps, displays, pools, cadence):
    ch = loc.churn(snaps, displays, cadence); ch.pop('births_per_100_transitions', None); ch.pop('deaths_per_100_transitions', None)
    out = {'location': loc.metric_pack(snaps, displays, cadence),
           'stability': loc.stability(raw, snaps, displays, pools, cadence), 'churn': ch,
           'corrected_birth_death': corrected_birth_death(snaps, displays, cadence),
           'excluded_metric': 'legacy birth/death per-transition rates replaced by contiguous-state denominator'}
    out['preregistered_thresholds'] = stability_threshold_checks(out)
    return out


def save_rows(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False, compression='gzip')


def main():
    a = parse_args(); lo, hi, cov_key = WINDOWS[a.window]
    evidence = Path(a.evidence_dir); evidence.mkdir(parents=True, exist_ok=True)
    cov = json.load(open(a.coverage_result))
    if cov.get('status') != 'EBUY_COVERAGE_OOS_REPLICATION_PASS': raise RuntimeError('coverage freeze is not PASS')
    h1 = json.load(open(a.frozen_h1_result)); h2 = json.load(open(a.frozen_h2_result))
    cand = pd.read_csv(a.candidates_gz, compression='gzip', low_memory=False)
    raw = base.v01.load_raw(a.files); active = base.v01.active_m1(raw)
    c1 = clean_z4(a.c1_pkl); c5 = clean_z4(a.c5_pkl)

    geom = loc.detector_geometry_parity(c1, c5)
    if not geom['pass']: raise RuntimeError(f'detector geometry parity failed: {geom}')

    frozen_snaps, frozen_displays, frozen_loc = frozen_c5_states(active, c5, cand, cov, a.window, lo, hi, cov_key)
    fcontacts, ftrades, fsumm = historical_frozen_baseline(raw, active, c5, frozen_snaps, frozen_displays, lo, hi)
    exp = expected_frozen(a.window, h1, h2); fgot, fchecks, fpass = parity_frozen(fcontacts, fsumm, exp)
    if not fpass:
        fail = {'status': 'FROZEN_C5_BASELINE_PARITY_FAIL_C1_NOT_OPENED', 'window': a.window,
                'frozen_location': frozen_loc, 'expected': exp, 'reproduced': fgot, 'checks': fchecks,
                'detector_geometry_parity': geom, 'c1_reaction_outcomes_opened': False}
        Path(a.output).write_text(json.dumps(fail, indent=2)); raise RuntimeError(json.dumps(fail))

    t0 = time.perf_counter(); c1_all_s, c1_all_p = loc.build_fixed(raw, active, c1, 1, 480)
    c1_all_d = loc.sticky_display(raw, c1_all_s, c1_all_p, 1); c1_location_sec = time.perf_counter() - t0
    c1_s, c1_d, c1_p = filter_parallel(c1_all_s, c1_all_d, c1_all_p, lo, hi)
    t0 = time.perf_counter(); c5_all_s, c5_all_p = loc.build_fixed(raw, active, c5, 5, 96)
    c5_all_d = loc.sticky_display(raw, c5_all_s, c5_all_p, 5); c5_location_sec = time.perf_counter() - t0
    c5_sci_s, c5_sci_d, c5_sci_p = filter_parallel(c5_all_s, c5_all_d, c5_all_p, lo, hi)

    t0 = time.perf_counter(); c5_contacts, c5_trades, c5_days = causal_contacts(raw, active, c5, frozen_snaps, frozen_displays, 5, lo, hi)
    c5_reaction_sec = time.perf_counter() - t0
    t0 = time.perf_counter(); c1_contacts, c1_trades, c1_days = causal_contacts(raw, active, c1, c1_s, c1_d, 1, lo, hi)
    c1_reaction_sec = time.perf_counter() - t0
    s5 = summarize_causal(c5_contacts, c5_trades, c5_days); s1 = summarize_causal(c1_contacts, c1_trades, c1_days)
    boot = paired_day_bootstrap(c1_trades, c5_trades)
    stab1 = compact_stability(raw, c1_s, c1_d, c1_p, 1); stab5 = compact_stability(raw, c5_sci_s, c5_sci_d, c5_sci_p, 5)

    save_rows(evidence / f'{a.window}_CAUSAL_V1_C5_CONTACTS.csv.gz', c5_contacts)
    save_rows(evidence / f'{a.window}_CAUSAL_V1_C5_BR.csv.gz', c5_trades)
    save_rows(evidence / f'{a.window}_CAUSAL_V1_C1_CONTACTS.csv.gz', c1_contacts)
    save_rows(evidence / f'{a.window}_CAUSAL_V1_C1_BR.csv.gz', c1_trades)

    out = {'status': 'C1_REFRESH_CAUSAL_REACTION_WINDOW_COMPLETE_NO_PROMOTION', 'window': a.window,
           'window_utc': [str(lo), str(hi)], 'study': 'E_BUY_C1_REFRESH_CAUSAL_ACTIVE_INTERVAL_V1',
           'frozen_c5_baseline': {'location_parity': frozen_loc, 'expected': exp, 'reproduced': fgot,
                                  'checks': fchecks, 'pass': True,
                                  'timing': 'historical boundary-exclusion implementation; provenance anchor only'},
           'detector_common_anchor_geometry_parity': geom,
           'outcome_blind_historical_window_diagnostics': {'C1': stab1, 'C5_reconstructed_scientific': stab5,
                                                            'C5_reaction_display_source': 'frozen OOS E-BUY candidate table'},
           'causal_active_interval_v1': {'C5': s5, 'C1': s1,
                                         'C1_minus_C5': {'contact_count': int(s1['contact_episode_count'] - s5['contact_episode_count']),
                                                         'contact_ratio': float(s1['contact_episode_count'] / s5['contact_episode_count']) if s5['contact_episode_count'] else None,
                                                         'fired_count': int(s1['bull_rejection_fired_count'] - s5['bull_rejection_fired_count']),
                                                         'tp1_resolved_rate': float(s1['tp1_resolved_rate'] - s5['tp1_resolved_rate']) if s1['tp1_resolved_rate'] is not None and s5['tp1_resolved_rate'] is not None else None},
                                         'paired_trading_day_bootstrap': boot},
           'compute_burden_seconds': {'detector_C1': a.detector_c1_sec, 'detector_C5': a.detector_c5_sec,
                                      'location_C1': c1_location_sec, 'location_C5_reconstructed': c5_location_sec,
                                      'causal_reaction_C1': c1_reaction_sec, 'causal_reaction_C5': c5_reaction_sec},
           'preregistered_runtime_semantics': {'causal_interval': 'state t governs subsequent M1 through next cadence boundary inclusive; boundary state becomes usable only after that observation completes',
                                               'episode_state': 'armed/consumed propagated sequentially; max one fresh contact per display episode per US session',
                                               'contact_geometry_frozen': True, 'score_used': False, 'trigger': 'BULL_REJECTION_ONLY'},
           'next_gate': 'AGGREGATE_H1_H2_AND_PRO_INTERPRET_COHERENCE_FRAGMENTATION_GEOMETRY_RUNTIME',
           'authorization': 'NONE_RETROSPECTIVE_SENSITIVITY_ONLY'}
    Path(a.output).write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({'window': a.window, 'frozen_parity': True,
                      'C5_contacts': s5['contact_episode_count'], 'C1_contacts': s1['contact_episode_count'],
                      'C5_BR': s5['bull_rejection_fired_count'], 'C1_BR': s1['bull_rejection_fired_count'],
                      'C5_TP': s5['tp1_resolved_rate'], 'C1_TP': s1['tp1_resolved_rate'],
                      'delta': boot['delta_tp1_rate'], 'ci95': boot['bootstrap_95']}, indent=2), flush=True)


if __name__ == '__main__': main()
