#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location('corridor_v3', HERE / 'xau_z4_corridor_v3_preoutcome.py')
    m = importlib.util.module_from_spec(spec)
    sys.modules['corridor_v3'] = m
    spec.loader.exec_module(m)
    return m


v3 = load()


def unit_tests():
    # Connected-components rule is intentionally transitive.
    raws = [
        v3.candidate_raw('BROKEN_PIVOT_HIGH', 'a', 100.00, 10, pd.Timestamp('2026-08-10T12:00:00Z'), 1.0),
        v3.candidate_raw('POST_BREAK_PIVOT_LOW', 'b', 100.08, 11, pd.Timestamp('2026-08-10T12:01:00Z'), 1.0),
        v3.candidate_raw('BULL_FVG_MID', 'c', 100.17, 12, pd.Timestamp('2026-08-10T12:02:00Z'), 1.0),
    ]
    comps = v3.connected_components(raws)
    assert len(comps) == 1 and len(comps[0]) == 3

    eps = [
        {'episode_id': 7, 'main_zhi': 101.0, 'breakout_time': pd.Timestamp('2026-08-10T12:05:00Z')},
        {'episode_id': 8, 'main_zhi': 102.0, 'breakout_time': pd.Timestamp('2026-08-10T12:03:00Z')},
        {'episode_id': 9, 'main_zhi': 102.0, 'breakout_time': pd.Timestamp('2026-08-10T12:04:00Z')},
    ]
    assert v3.authority_episode(eps)['episode_id'] == 9

    # Pivot confirmation is causal: two right bars are required.
    t = pd.date_range('2026-08-10T11:50:00Z', periods=10, freq='1min')
    raw = pd.DataFrame({'time': t, 'open': 100., 'close': 100.,
                        'high': [100, 101, 102, 105, 102, 101, 102, 101, 100, 99],
                        'low':  [99, 99, 99, 99, 99, 98, 96, 98, 99, 99]})
    highs, lows, _, _ = v3.pivot_maps(raw)
    assert any(x['pivot_idx'] == 3 and x['confirm_idx'] == 5 and x['level'] == 105 for x in highs)
    assert any(x['pivot_idx'] == 6 and x['confirm_idx'] == 8 and x['level'] == 96 for x in lows)


def build_synthetic(root: Path, target_hit_on_retrace=False):
    times = pd.date_range('2026-08-10T11:55:00Z', periods=31, freq='1min')
    close = np.full(len(times), 100.0); op = close.copy(); high = close + .1; low = close - .1
    ix = {str(t): i for i, t in enumerate(times)}

    def b(ts, o, h, l, c):
        i = ix[str(pd.Timestamp(ts))]
        op[i], high[i], low[i], close[i] = o, h, l, c

    # Prior resistance pivot inside the future corridor, confirmed before MAIN breakout.
    b('2026-08-10T11:55:00Z', 100.0, 100.5, 99.9, 100.2)
    b('2026-08-10T11:56:00Z', 100.2, 101.2, 100.0, 100.4)
    b('2026-08-10T11:57:00Z', 100.4, 102.0, 100.2, 100.5)
    b('2026-08-10T11:58:00Z', 100.5, 101.1, 100.1, 100.4)
    b('2026-08-10T11:59:00Z', 100.4, 100.9, 100.1, 100.3)
    b('2026-08-10T12:00:00Z', 100.3, 100.7, 100.2, 100.6)
    # MAIN zhi=101 breakout.
    b('2026-08-10T12:01:00Z', 100.6, 101.3, 100.5, 101.2)
    b('2026-08-10T12:02:00Z', 101.2, 101.8, 101.1, 101.7)
    # Post-break bullish FVG vs high at 12:01; also closes above prior pivot 102.
    b('2026-08-10T12:03:00Z', 102.1, 102.8, 102.0, 102.6)
    b('2026-08-10T12:04:00Z', 102.6, 103.2, 102.5, 103.0)
    b('2026-08-10T12:05:00Z', 103.0, 103.5, 102.8, 103.3)
    b('2026-08-10T12:06:00Z', 103.3, 103.4, 102.8, 103.0)
    b('2026-08-10T12:07:00Z', 103.0, 103.1, 102.1, 102.3)
    if target_hit_on_retrace:
        b('2026-08-10T12:08:00Z', 102.3, 105.1, 101.5, 101.9)
    else:
        b('2026-08-10T12:08:00Z', 102.3, 102.4, 101.5, 101.9)
    b('2026-08-10T12:09:00Z', 101.9, 102.0, 101.0, 101.4)
    b('2026-08-10T12:10:00Z', 101.4, 102.2, 101.2, 102.0)
    for k, tt in enumerate(times):
        if tt >= pd.Timestamp('2026-08-10T12:11:00Z'):
            op[k], high[k], low[k], close[k] = 102.0, 102.3, 101.8, 102.1

    pd.DataFrame({
        'timestamp': (times.astype('int64') // 10**6).astype('int64'),
        'open': op, 'high': high, 'low': low, 'close': close
    }).to_csv(root / 'xauusd_bid_m1_2026_08.csv', index=False)

    rows = []
    for t in pd.date_range('2026-08-10T12:00:00Z', '2026-08-10T12:20:00Z', freq='5min'):
        if t == pd.Timestamp('2026-08-10T12:00:00Z'):
            rows.append({'time': t, 'center': 100.5, 'zlo': 99.5, 'zhi': 101.0, 'side': 1, 'tr': 1.0})
        rows.append({'time': t, 'center': 105.5, 'zlo': 105.0, 'zhi': 106.0, 'side': 1, 'tr': 1.0})
    pd.DataFrame(rows).to_pickle(root / 'z4.pkl')


def run_engine(root: Path):
    cmd = [sys.executable, str(HERE / 'xau_z4_corridor_v3_preoutcome.py'),
           '--files', str(root / 'xauusd_bid_m1_2026_08.csv'), '--z4-pkl', str(root / 'z4.pkl'),
           '--target-start', '2026-08-10T00:00:00Z', '--target-end', '2026-08-11T00:00:00Z',
           '--episodes-out', str(root / 'episodes.csv.gz'), '--candidates-out', str(root / 'candidates.csv.gz'),
           '--controls-out', str(root / 'controls.csv.gz'), '--candidate-contacts-out', str(root / 'candidate_contacts.csv.gz'),
           '--control-contacts-out', str(root / 'control_contacts.csv.gz'), '--manifest', str(root / 'manifest.json'), '--tag', 'SYNTH']
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    return json.load(open(root / 'manifest.json'))


def integration_tests():
    with tempfile.TemporaryDirectory(prefix='corridor-v3-synth-') as td:
        root = Path(td)
        build_synthetic(root, False)
        m = run_engine(root)
        assert m['future_v3_reaction_outcomes_used'] is False
        assert m['legacy_br70_used'] is False and m['e_zones_or_scores_used'] is False
        ep = pd.read_csv(root / 'episodes.csv.gz')
        cand = pd.read_csv(root / 'candidates.csv.gz')
        ctrl = pd.read_csv(root / 'controls.csv.gz')
        cc = pd.read_csv(root / 'candidate_contacts.csv.gz')
        oc = pd.read_csv(root / 'control_contacts.csv.gz')
        assert len(ep) == 1 and ep.iloc[0].main_zhi == 101.0 and ep.iloc[0].target_zlo == 105.0
        assert cand.candidate_family_set.astype(str).str.contains('BROKEN_PIVOT_HIGH').any()
        assert cand.candidate_family_set.astype(str).str.contains('BULL_FVG_MID').any()
        assert len(cc) >= 1
        # A control generated near the first FVG later becomes structurally non-neutral and must be censored before contact.
        q = ctrl[(np.isclose(ctrl.level.astype(float), 102.15)) & (ctrl.status == 'CENSORED_STRUCTURAL_LEVEL_BORN')]
        assert len(q) >= 1
        assert not oc.control_id.astype(str).isin(q.control_id.astype(str)).any()

    # TARGET precedence: a bar reaching TARGET cannot also create a new candidate contact.
    with tempfile.TemporaryDirectory(prefix='corridor-v3-target-') as td:
        root = Path(td)
        build_synthetic(root, True)
        run_engine(root)
        cc = pd.read_csv(root / 'candidate_contacts.csv.gz')
        if len(cc):
            assert not (pd.to_datetime(cc.contact_time, utc=True) == pd.Timestamp('2026-08-10T12:08:00Z')).any()


def main():
    unit_tests()
    integration_tests()
    print('Z4_CORRIDOR_V3_PREOUTCOME_SYNTHETIC_CAUSAL_TESTS_PASS')


if __name__ == '__main__':
    main()
