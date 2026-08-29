#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

import prospective_planning_tool_v1 as core

# Canonical repository path repair: PKG.parents[1] is xau-wick-zone-pro.
core.ENTRY = core.PKG.parents[1] / 'entry-research'
core.ENGINE = core.ENTRY / 'geometry-shifted-grid-parity' / 'xau_z4_c5_geometry_shifted_grid_equivalent.py'

# Frozen source constants from xau_ebuy_coverage_v0_1.py.
FROZEN_Z4_LOOKBACK_ACTIVE_M1 = 1440
FROZEN_WARMUP_C5_LANDMARKS = 96


def _resolved_time_frame(path: str) -> pd.DataFrame:
    d = pd.read_csv(path, compression='infer')
    if 'time' in d.columns:
        t = pd.to_datetime(d['time'], utc=True, errors='coerce')
    else:
        t = pd.Series(pd.NaT, index=d.index, dtype='datetime64[ns, UTC]')
    if 'timestamp' in d.columns:
        ts = pd.to_datetime(
            pd.to_numeric(d['timestamp'], errors='coerce'),
            unit='ms', utc=True, errors='coerce'
        )
        t = t.fillna(ts)
    if t.isna().any():
        raise RuntimeError(f'{path}: unresolved M1 timestamps after time/timestamp bridge')
    for c in ['open', 'high', 'low', 'close']:
        if c not in d.columns:
            raise RuntimeError(f'{path}: missing {c}')
        d[c] = pd.to_numeric(d[c], errors='raise').astype(float)
    q = pd.DataFrame({
        'timestamp': (t.astype('int64') // 1_000_000).astype('int64'),
        'open': d['open'].to_numpy(float),
        'high': d['high'].to_numpy(float),
        'low': d['low'].to_numpy(float),
        'close': d['close'].to_numpy(float),
    }).sort_values('timestamp').reset_index(drop=True)
    dup = q[q.duplicated('timestamp', keep=False)]
    if len(dup):
        for ts_value, g in dup.groupby('timestamp'):
            if len(g[['open', 'high', 'low', 'close']].drop_duplicates()) > 1:
                raise RuntimeError(f'{path}: conflicting duplicate timestamp {ts_value}')
    return q.drop_duplicates('timestamp', keep='first').reset_index(drop=True)


@contextmanager
def timestamp_schema_bridge(files: list[str], prefix: str):
    with tempfile.TemporaryDirectory(prefix=prefix) as td:
        td = Path(td)
        compat = []
        for i, f in enumerate(files):
            q = _resolved_time_frame(f)
            p = td / f'input_{i:02d}.csv'
            q.to_csv(p, index=False)
            compat.append(str(p))
        yield compat


def _prospective_warm_start(raw: pd.DataFrame, session_start: pd.Timestamp):
    active_prior = raw[(raw.time < session_start) & (raw.high > raw.low)].copy().reset_index(drop=True)
    if len(active_prior) < FROZEN_Z4_LOOKBACK_ACTIVE_M1:
        raise RuntimeError(f'insufficient active warmup: {len(active_prior)} < {FROZEN_Z4_LOOKBACK_ACTIVE_M1}')
    landmark_mask = (active_prior.time.dt.minute % 5 == 0) & (active_prior.time.dt.second == 0)
    landmark_positions = active_prior.index[landmark_mask].to_numpy()
    if len(landmark_positions) < FROZEN_WARMUP_C5_LANDMARKS:
        raise RuntimeError(f'insufficient pre-session C5 landmarks: {len(landmark_positions)} < {FROZEN_WARMUP_C5_LANDMARKS}')
    p96 = int(landmark_positions[-FROZEN_WARMUP_C5_LANDMARKS])
    start_active_pos = p96 - (FROZEN_Z4_LOOKBACK_ACTIVE_M1 - 1)
    if start_active_pos < 0:
        raise RuntimeError('insufficient active history before the 96th pre-session C5 warmup landmark')
    sl = active_prior.iloc[start_active_pos:].reset_index(drop=True)
    eligible = sl.index[
        (sl.index >= FROZEN_Z4_LOOKBACK_ACTIVE_M1 - 1)
        & (sl.time.dt.minute % 5 == 0)
        & (sl.time.dt.second == 0)
    ].to_numpy()
    if len(eligible) != FROZEN_WARMUP_C5_LANDMARKS:
        raise RuntimeError(
            f'warmup contract construction drift: expected exactly 96 eligible pre-session landmarks, got {len(eligible)}'
        )
    return pd.Timestamp(sl.iloc[0].time), {
        'frozen_z4_lookback_active_m1': FROZEN_Z4_LOOKBACK_ACTIVE_M1,
        'frozen_warmup_c5_landmarks': FROZEN_WARMUP_C5_LANDMARKS,
        'eligible_pre_session_c5_landmarks': int(len(eligible)),
        'warm_start_active_position_in_available_history': int(start_active_pos),
        'warmup_contract': (
            'latest causal start that leaves exactly 96 pre-session C5 landmarks '
            'after the 1440-active-M1 Z4 lookback'
        ),
    }


_ORIGINAL_Z4_SESSION = core.z4_session
_ORIGINAL_FEATURE_SESSION = core.prospective_feature_session
_ORIGINAL_CONTACT_ONLY = core.contact_only


def ingest_session_frozen_warmup(args):
    acquired = pd.Timestamp(args.acquired_at)
    if acquired.tzinfo is None:
        acquired = acquired.tz_localize('UTC')
    else:
        acquired = acquired.tz_convert('UTC')
    start, end = core.session_bounds(args.session_date)
    if acquired < end:
        raise RuntimeError(f'acquisition before completed session: {acquired} < {end}')
    if pd.Timestamp(start) < core.PROSPECTIVE_START and not args.historical_dry_run:
        raise RuntimeError('session predates prospective start')
    raw, qa = core.normalize_raw_files(args.files)
    sess = raw[(raw.time >= start) & (raw.time < end)].copy()
    if not len(sess):
        raise RuntimeError('no usable US-session M1 rows')
    expected = pd.date_range(start=start, periods=540, freq='min')
    actual = set(sess.time.tolist())
    missing = [t for t in expected if t not in actual]
    warm_start, warm_contract = _prospective_warm_start(raw, start)
    warm = raw[(raw.time >= warm_start) & (raw.time < end)].copy()

    root = Path(args.archive_root)
    session_path = root / 'sessions' / f'{args.session_date}.csv.gz'
    warm_path = root / 'warmup' / f'{args.session_date}.csv.gz'
    candidate_dir = Path(tempfile.mkdtemp(prefix='pros_ingest_'))
    cand_session = candidate_dir / 'session.csv.gz'
    cand_warm = candidate_dir / 'warmup.csv.gz'
    core.deterministic_gzip_csv(sess, cand_session)
    core.deterministic_gzip_csv(warm, cand_warm)
    ssha, wsha = core.sha256_file(cand_session), core.sha256_file(cand_warm)
    source_meta = json.loads(Path(args.source_meta_json).read_text()) if args.source_meta_json else {}
    event_base = {
        'session_date_ny': args.session_date,
        'acquired_at_utc': acquired.isoformat(),
        'session_sha256': ssha,
        'warmup_sha256': wsha,
        'session_rows': int(len(sess)),
        'warmup_rows': int(len(warm)),
        'missing_m1': int(len(missing)),
        'first_missing_utc': missing[0].isoformat() if missing else None,
        'last_missing_utc': missing[-1].isoformat() if missing else None,
        'warmup_first_utc': pd.Timestamp(warm.time.min()).isoformat(),
        'source_metadata': source_meta,
        **warm_contract,
        **qa,
    }
    if session_path.exists() or warm_path.exists():
        if not (session_path.exists() and warm_path.exists()):
            raise RuntimeError('partial canonical archive state')
        same = core.sha256_file(session_path) == ssha and core.sha256_file(warm_path) == wsha
        if same:
            shutil.rmtree(candidate_dir)
            out = {
                'status': 'PROSPECTIVE_SESSION_ALREADY_ACCEPTED_IDENTICAL',
                **event_base,
                'canonical_unchanged': True,
            }
            core.canonical_json(Path(args.manifest), out)
            return out
        stamp = acquired.strftime('%Y%m%dT%H%M%SZ')
        revdir = root / 'revisions' / args.session_date
        revdir.mkdir(parents=True, exist_ok=True)
        rev_session = revdir / f'{stamp}_{ssha[:16]}_session.csv.gz'
        rev_warm = revdir / f'{stamp}_{wsha[:16]}_warmup.csv.gz'
        # Avoid duplicating the same source revision on every later collector run.
        prior_same = list(revdir.glob(f'*_{ssha[:16]}_session.csv.gz')) and list(
            revdir.glob(f'*_{wsha[:16]}_warmup.csv.gz')
        )
        if prior_same:
            shutil.rmtree(candidate_dir)
            out = {
                'status': 'PROSPECTIVE_SOURCE_REVISION_ALREADY_RECORDED_CANONICAL_UNCHANGED',
                **event_base,
                'canonical_unchanged': True,
            }
            core.canonical_json(Path(args.manifest), out)
            return out
        shutil.copy2(cand_session, rev_session)
        shutil.copy2(cand_warm, rev_warm)
        event = core.append_hash_chain(
            root / 'APPEND_CHAIN.jsonl',
            {'event_type': 'REVISION_DETECTED_CANONICAL_UNCHANGED', **event_base},
        )
        shutil.rmtree(candidate_dir)
        out = {
            'status': 'PROSPECTIVE_SOURCE_REVISION_RECORDED_CANONICAL_UNCHANGED',
            **event_base,
            'canonical_unchanged': True,
            'chain_record_sha256': event['record_sha256'],
        }
        core.canonical_json(Path(args.manifest), out)
        return out
    session_path.parent.mkdir(parents=True, exist_ok=True)
    warm_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(cand_session), session_path)
    shutil.move(str(cand_warm), warm_path)
    shutil.rmtree(candidate_dir)
    session_manifest = root / 'manifests' / f'{args.session_date}.json'
    event = core.append_hash_chain(root / 'APPEND_CHAIN.jsonl', {'event_type': 'FIRST_ACCEPTANCE', **event_base})
    accepted = {
        'status': 'PROSPECTIVE_SESSION_FIRST_ACCEPTANCE_PASS',
        **event_base,
        'canonical_session_path': str(session_path),
        'canonical_warmup_path': str(warm_path),
        'chain_record_sha256': event['record_sha256'],
        'canonical_overwrite_allowed': False,
    }
    core.canonical_json(session_manifest, accepted)
    core.canonical_json(Path(args.manifest), accepted)
    return accepted


def z4_session_timestamp_bridge(args):
    old_files = list(args.files)
    with timestamp_schema_bridge(old_files, 'pros_z4_schema_bridge_') as compat:
        args.files = compat
        try:
            try:
                return _ORIGINAL_Z4_SESSION(args)
            except RuntimeError as exc:
                if 'no Z4 geometry rows for' not in str(exc):
                    raise
                empty = pd.DataFrame(columns=['time', 'landmark_i', 'center', 'zlo', 'zhi', 'side'])
                out = Path(args.output)
                out.parent.mkdir(parents=True, exist_ok=True)
                empty.to_pickle(out)
                m = {
                    'status': 'PROSPECTIVE_Z4_SESSION_GEOMETRY_PASS',
                    'session_date_ny': args.session_date,
                    'rows': 0,
                    'snapshots_with_zones': 0,
                    'first_time_utc': None,
                    'last_time_utc': None,
                    'engine_guard': {'git_blob': core.EXPECTED_ENGINE_GIT_BLOB},
                    'geometry_only': True,
                    'zero_zone_session': True,
                    'future_outcomes_used': False,
                    'output_sha256': core.sha256_file(out),
                }
                core.canonical_json(Path(args.manifest), m)
                return m
        finally:
            args.files = old_files


def _empty_feature_outputs(args, reason: str):
    canonical = core.PKG / 'E_DISPLAY_EPISODE_LEDGER_V1_REPLICATION.csv.gz'
    ledger = pd.read_csv(canonical, compression='gzip', nrows=0)
    for c, dtype in [
        ('continuous_logit', 'float64'),
        ('E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1', 'float64'),
        ('fixed_quartile', 'object'),
        ('width_only_score', 'float64'),
    ]:
        if c not in ledger.columns:
            ledger[c] = pd.Series(dtype=dtype)
    candidates = pd.DataFrame(columns=['time'])
    outc, outl = Path(args.candidates_output), Path(args.ledger_output)
    core.deterministic_gzip_csv(candidates, outc)
    core.deterministic_gzip_csv(ledger, outl)
    m = {
        'status': 'PROSPECTIVE_FEATURE_SESSION_OUTCOME_FREE_PASS',
        'session_date_ny': args.session_date,
        'candidate_rows': 0,
        'feature_rows': 0,
        'display_episodes': 0,
        'snapshots': 0,
        'model_feature_exclusion_rows': 0,
        'model_feature_exclusion_rate': 0.0,
        'unseen_family_rows': 0,
        'unseen_family_rate': 0.0,
        'frozen_dev_model_sha256': core.EXPECTED_FROZEN_MODEL_SHA256,
        'prospective_outcomes_used': False,
        'zero_candidate_session': True,
        'zero_candidate_reason': reason,
        'candidate_sha256': core.sha256_file(outc),
        'ledger_sha256': core.sha256_file(outl),
    }
    core.canonical_json(Path(args.manifest), m)
    return m


def feature_session_timestamp_bridge(args):
    old_files = list(args.files)
    z4 = pd.read_pickle(args.z4_pkl)
    if len(z4) == 0 or ('side' in z4.columns and not (pd.to_numeric(z4.side, errors='coerce') == 1).any()):
        return _empty_feature_outputs(args, 'NO_UPPER_Z4_CONTEXT')
    with timestamp_schema_bridge(old_files, 'pros_e_schema_bridge_') as compat:
        args.files = compat
        try:
            try:
                return _ORIGINAL_FEATURE_SESSION(args)
            except RuntimeError as exc:
                allowed = (
                    'no eligible BUY-context snapshots',
                    'no prospective candidate rows',
                    'no candidates in target session',
                )
                if not any(x in str(exc) for x in allowed):
                    raise
                return _empty_feature_outputs(args, str(exc))
        finally:
            args.files = old_files


def contact_only_empty_bridge(args):
    ledger = pd.read_csv(args.ledger, compression='infer', nrows=1)
    if len(ledger):
        return _ORIGINAL_CONTACT_ONLY(args)
    out = pd.DataFrame(columns=[
        'display_episode_id', 'session_date_ny', 'selection_status', 'model_eligible_contact'
    ])
    p = Path(args.output)
    core.deterministic_gzip_csv(out, p)
    m = {
        'status': 'PROSPECTIVE_CONTACT_ONLY_PASS',
        'session_date_ny': args.session_date,
        'episodes': 0,
        'primary_contacts': 0,
        'model_eligible_primary_contacts': 0,
        'post_contact_bars_read': 0,
        'prospective_outcomes_generated': False,
        'prospective_outcomes_read': False,
        'zero_candidate_session': True,
        'raw_qa': {'exact_duplicate_rows_removed': 0, 'conflicting_duplicate_timestamps': 0},
        'output_sha256': core.sha256_file(p),
    }
    core.canonical_json(Path(args.manifest), m)
    return m


def status_checkpoint_hardened(args):
    root = Path(args.live_root)
    manifests = []
    contact_dir = root / 'contacts'
    for p in sorted(contact_dir.glob('*.json')) if contact_dir.exists() else []:
        d = json.loads(p.read_text())
        if d.get('status') != 'PROSPECTIVE_CONTACT_ONLY_PASS':
            continue
        session = str(d.get('session_date_ny', ''))
        if p.stem != session:
            raise RuntimeError(f'contact manifest filename/session mismatch: {p.name} != {session}')
        if session < core.PROSPECTIVE_START_SESSION:
            raise RuntimeError(f'pre-start contact manifest forbidden: {session}')
        if int(d.get('model_eligible_primary_contacts', -1)) < 0:
            raise RuntimeError(f'invalid contact count: {session}')
        manifests.append(d)
    by = {str(m['session_date_ny']): m for m in manifests}
    if len(by) != len(manifests):
        raise RuntimeError('duplicate prospective contact session manifest')
    dates = sorted(by)
    cumulative = 0
    checkpoint = None
    for i, session in enumerate(dates, 1):
        cumulative += int(by[session]['model_eligible_primary_contacts'])
        if checkpoint is None and i >= core.MIN_SESSIONS and cumulative >= core.MIN_CONTACTS:
            checkpoint = {
                'session_date_ny': session,
                'represented_sessions': i,
                'represented_session_dates': dates[:i],
                'model_eligible_primary_contacts': cumulative,
            }
    total_contacts = sum(int(by[s]['model_eligible_primary_contacts']) for s in dates)
    out = {
        'status': 'PROSPECTIVE_PRECHECKPOINT_STATUS_OUTCOME_BLIND',
        'prospective_start_session': core.PROSPECTIVE_START_SESSION,
        'represented_session_count': len(dates),
        'represented_session_dates': dates,
        'model_eligible_primary_contact_count': total_contacts,
        'threshold_sessions': core.MIN_SESSIONS,
        'threshold_contacts': core.MIN_CONTACTS,
        'checkpoint_reached': checkpoint is not None,
        'locked_checkpoint': checkpoint,
        'performance_fields_exposed': False,
    }
    lock = Path(args.lock)
    if checkpoint:
        if lock.exists():
            old = json.loads(lock.read_text())
            if old != checkpoint:
                raise RuntimeError(f'checkpoint lock drift: {old} != {checkpoint}')
        else:
            core.canonical_json(lock, checkpoint)
    core.canonical_json(Path(args.output), out)
    return out


core.ingest_session = ingest_session_frozen_warmup
core.z4_session = z4_session_timestamp_bridge
core.prospective_feature_session = feature_session_timestamp_bridge
core.contact_only = contact_only_empty_bridge
core.status_checkpoint = status_checkpoint_hardened

if __name__ == '__main__':
    core.main()
