#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prospective_planning_tool_v1 as core
# Import applies the frozen prospective adapters around untouched historical engines.
import prospective_planning_entry_v1 as entry  # noqa: F401


def ns(**kw):
    return argparse.Namespace(**kw)


def write_raw(path, start, periods):
    path.parent.mkdir(parents=True, exist_ok=True)
    t = pd.date_range(start=start, periods=periods, freq='min', tz='UTC')
    x = np.arange(periods, dtype=float)
    d = pd.DataFrame({
        'timestamp': (t.view('int64') // 1_000_000).astype(np.int64),
        'open': 2000 + x * .001,
        'high': 2000.2 + x * .001,
        'low': 1999.8 + x * .001,
        'close': 2000.05 + x * .001,
    })
    d.to_csv(path, index=False)


def test_ingest_append_only_and_revision_dedup(tmp: Path):
    tmp.mkdir(parents=True, exist_ok=True)
    session = '2026-07-15'
    src = tmp / 'source.csv'
    write_raw(src, pd.Timestamp('2026-07-14T00:00:00Z'), 2700)
    meta = tmp / 'meta.json'
    meta.write_text(json.dumps({'upstream_head_commit': 'dryrun', 'upstream_blob_sha': 'dryrun'}))
    root = tmp / 'archive'
    manifest = tmp / 'm1.json'
    args = ns(
        files=[str(src)], session_date=session, acquired_at='2026-07-15T21:01:00Z',
        archive_root=str(root), manifest=str(manifest), source_meta_json=str(meta),
        historical_dry_run=True,
    )
    r1 = core.ingest_session(args)
    assert r1['status'] == 'PROSPECTIVE_SESSION_FIRST_ACCEPTANCE_PASS'
    assert r1['frozen_z4_lookback_active_m1'] == 1440
    assert r1['frozen_warmup_c5_landmarks'] == 96
    assert r1['eligible_pre_session_c5_landmarks'] == 96
    canonical = (root / 'sessions' / f'{session}.csv.gz').read_bytes()
    warm = (root / 'warmup' / f'{session}.csv.gz').read_bytes()
    r2 = core.ingest_session(args)
    assert r2['status'] == 'PROSPECTIVE_SESSION_ALREADY_ACCEPTED_IDENTICAL'
    assert (root / 'sessions' / f'{session}.csv.gz').read_bytes() == canonical

    d = pd.read_csv(src)
    idx = int(d[(pd.to_datetime(d.timestamp, unit='ms', utc=True) >= pd.Timestamp('2026-07-15T12:00:00Z'))].index[5])
    d.loc[idx, 'close'] += .5
    d.to_csv(src, index=False)
    r3 = core.ingest_session(args)
    assert r3['status'] == 'PROSPECTIVE_SOURCE_REVISION_RECORDED_CANONICAL_UNCHANGED'
    assert (root / 'sessions' / f'{session}.csv.gz').read_bytes() == canonical
    assert (root / 'warmup' / f'{session}.csv.gz').read_bytes() == warm
    chain = (root / 'APPEND_CHAIN.jsonl').read_text().strip().splitlines()
    assert len(chain) == 2
    c1, c2 = json.loads(chain[0]), json.loads(chain[1])
    assert c2['previous_record_sha256'] == c1['record_sha256']

    r4 = core.ingest_session(args)
    assert r4['status'] == 'PROSPECTIVE_SOURCE_REVISION_ALREADY_RECORDED_CANONICAL_UNCHANGED'
    assert len((root / 'APPEND_CHAIN.jsonl').read_text().strip().splitlines()) == 2


def test_contact_only_arm_bar_cannot_contact():
    labeler = core.loadmod('synthetic_labeler', core.LABELER)
    raw = pd.DataFrame([
        {'time': pd.Timestamp('2026-07-15T12:00:00Z'), 'open': 101., 'high': 110., 'low': 99.5, 'close': 105.},
        {'time': pd.Timestamp('2026-07-15T12:01:00Z'), 'open': 105., 'high': 105., 'low': 99.0, 'close': 101.},
    ])
    g = pd.DataFrame([{
        'display_episode_id': 'E1', 'session_date_ny': '2026-07-15',
        'snapshot_time_utc': pd.Timestamp('2026-07-15T11:59:00Z'),
        'feature_available_time_utc': pd.Timestamp('2026-07-15T12:00:00Z'),
        'current_family': 'EPM_M1_R2_A8H', 'center': 99.5, 'zlo': 99., 'zhi': 100.,
        'v_snapshot': 1., 'zone_width_v': 1., 'display_persistence_c5': 1,
        'row_sha256': 'abc', 'continuous_logit': 0.1,
        'E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1': 0.5, 'fixed_quartile': 'Q2',
    }])
    r = core.contact_only_episode(labeler, raw, g, {'EPM_M1_R2_A8H'})
    assert r['selection_status'] == 'PRIMARY_CONTACT'
    assert pd.Timestamp(r['contact_bar_open_time_utc']) == pd.Timestamp('2026-07-15T12:01:00Z')


def test_zero_candidate_session_is_represented(tmp: Path):
    tmp.mkdir(parents=True, exist_ok=True)
    z4 = tmp / 'empty_z4.pkl'
    pd.DataFrame(columns=['time', 'landmark_i', 'center', 'zlo', 'zhi', 'side']).to_pickle(z4)
    candidates = tmp / 'candidates.csv.gz'
    ledger = tmp / 'ledger.csv.gz'
    feature_manifest = tmp / 'feature.json'
    fr = core.prospective_feature_session(ns(
        files=['unused.csv'], z4_pkl=str(z4), session_date='2026-08-31',
        candidates_output=str(candidates), ledger_output=str(ledger), manifest=str(feature_manifest),
    ))
    assert fr['status'] == 'PROSPECTIVE_FEATURE_SESSION_OUTCOME_FREE_PASS'
    assert fr['feature_rows'] == 0 and fr['zero_candidate_session'] is True
    assert len(pd.read_csv(ledger, compression='gzip')) == 0

    contact_file = tmp / 'contact.csv.gz'
    contact_manifest = tmp / '2026-08-31.json'
    cr = core.contact_only(ns(
        files=['unused.csv'], ledger=str(ledger), session_date='2026-08-31',
        output=str(contact_file), manifest=str(contact_manifest),
    ))
    assert cr['status'] == 'PROSPECTIVE_CONTACT_ONLY_PASS'
    assert cr['model_eligible_primary_contacts'] == 0

    live = tmp / 'live'
    (live / 'contacts').mkdir(parents=True)
    (live / 'contacts' / '2026-08-31.json').write_text(contact_manifest.read_text())
    status = core.status_checkpoint(ns(
        live_root=str(live), lock=str(tmp / 'lock.json'), output=str(tmp / 'status.json')
    ))
    assert status['represented_session_count'] == 1
    assert status['model_eligible_primary_contact_count'] == 0


def test_firewall(tmp: Path):
    tmp.mkdir(parents=True, exist_ok=True)
    live = tmp / 'live'
    (live / 'contacts').mkdir(parents=True)
    (live / 'contacts' / '2026-08-31.json').write_text(json.dumps({
        'status': 'PROSPECTIVE_CONTACT_ONLY_PASS',
        'session_date_ny': '2026-08-31',
        'model_eligible_primary_contacts': 12,
    }))
    out = tmp / 'fw.json'
    r = core.firewall(ns(live_root=str(live), output=str(out)))
    assert r['status'] == 'PROSPECTIVE_ANTI_PEEKING_FIREWALL_PASS'
    (live / 'status').mkdir()
    (live / 'status' / 'bad.json').write_text(json.dumps({'auc': 0.6}))
    failed = False
    try:
        core.firewall(ns(live_root=str(live), output=str(out)))
    except RuntimeError:
        failed = True
    assert failed


def test_single_checkpoint_lock_and_session_list(tmp: Path):
    tmp.mkdir(parents=True, exist_ok=True)
    live = tmp / 'live'
    contacts = live / 'contacts'
    contacts.mkdir(parents=True)
    dates = pd.bdate_range('2026-08-31', periods=95).date.astype(str)
    for session in dates:
        (contacts / f'{session}.json').write_text(json.dumps({
            'status': 'PROSPECTIVE_CONTACT_ONLY_PASS',
            'session_date_ny': session,
            'model_eligible_primary_contacts': 12,
        }))
    lock = tmp / 'lock.json'
    out = tmp / 'status.json'
    r = core.status_checkpoint(ns(live_root=str(live), lock=str(lock), output=str(out)))
    cp = r['locked_checkpoint']
    assert r['checkpoint_reached']
    assert cp['represented_sessions'] == 90
    assert cp['represented_session_dates'] == list(dates[:90])
    assert cp['model_eligible_primary_contacts'] == 1080
    assert cp['session_date_ny'] == dates[89]
    old = lock.read_text()
    r2 = core.status_checkpoint(ns(live_root=str(live), lock=str(lock), output=str(out)))
    assert lock.read_text() == old and r2['locked_checkpoint'] == cp


def test_prestart_contact_manifest_fails_closed(tmp: Path):
    live = tmp / 'live'
    contacts = live / 'contacts'
    contacts.mkdir(parents=True)
    (contacts / '2026-08-28.json').write_text(json.dumps({
        'status': 'PROSPECTIVE_CONTACT_ONLY_PASS',
        'session_date_ny': '2026-08-28',
        'model_eligible_primary_contacts': 1,
    }))
    failed = False
    try:
        core.status_checkpoint(ns(
            live_root=str(live), lock=str(tmp / 'lock.json'), output=str(tmp / 'status.json')
        ))
    except RuntimeError:
        failed = True
    assert failed


def test_engine_guard():
    with tempfile.TemporaryDirectory() as td:
        g = core.patched_geometry_engine(Path(td) / 'g.py')
        assert g['git_blob'] == core.EXPECTED_ENGINE_GIT_BLOB
        assert len(g['sha256']) == 64


def main():
    with tempfile.TemporaryDirectory(prefix='pros_tests_') as td:
        tmp = Path(td)
        test_ingest_append_only_and_revision_dedup(tmp / 'ingest')
        test_contact_only_arm_bar_cannot_contact()
        test_zero_candidate_session_is_represented(tmp / 'zero')
        test_firewall(tmp / 'fw')
        test_single_checkpoint_lock_and_session_list(tmp / 'status')
        test_prestart_contact_manifest_fails_closed(tmp / 'prestart')
        test_engine_guard()
    out = {
        'status': 'PROSPECTIVE_PLANNING_SYNTHETIC_TESTS_PASS',
        'tests': [
            'append_only_first_acceptance_revision_hash_chain_and_revision_dedup',
            'frozen_1440_active_plus_96_C5_warmup_contract',
            'arming_bar_cannot_contact',
            'valid_zero_candidate_session_is_represented',
            'anti_peeking_firewall',
            'single_checkpoint_first_qualifying_session_lock_with_session_list',
            'prestart_contact_manifest_fails_closed',
            'frozen_Z4_engine_guard',
        ],
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return out


if __name__ == '__main__':
    main()
