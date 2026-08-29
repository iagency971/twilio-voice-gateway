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

# Frozen source constants from xau_ebuy_coverage_v0_1.py.  They are repeated
# here only to make the prospective warm-up contract explicit and testable.
FROZEN_Z4_LOOKBACK_ACTIVE_M1 = 1440
FROZEN_WARMUP_C5_LANDMARKS = 96

# The prospective archive intentionally stores normalized UTC `time`, while
# the frozen historical Z4/E source engines remain unchanged and expect the
# original Dukascopy-style `timestamp` in milliseconds.  This bridge is
# schema-only: no prices, ordering rules, geometry rules, eligibility rules or
# future information are changed.  Conflicting duplicate timestamps fail
# closed; exact duplicates may be collapsed deterministically.


def _resolved_time_frame(path: str) -> pd.DataFrame:
    d = pd.read_csv(path, compression='infer')
    if 'time' in d.columns:
        t = pd.to_datetime(d['time'], utc=True, errors='coerce')
    else:
        t = pd.Series(pd.NaT, index=d.index, dtype='datetime64[ns, UTC]')
    if 'timestamp' in d.columns:
        ts = pd.to_datetime(pd.to_numeric(d['timestamp'], errors='coerce'), unit='ms', utc=True, errors='coerce')
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
    eligible = sl.index[(sl.index >= FROZEN_Z4_LOOKBACK_ACTIVE_M1 - 1) & (sl.time.dt.minute % 5 == 0) & (sl.time.dt.second == 0)].to_numpy()
    if len(eligible) != FROZEN_WARMUP_C5_LANDMARKS:
        raise RuntimeError(f'warmup contract construction drift: expected exactly 96 eligible pre-session landmarks, got {len(eligible)}')
    return pd.Timestamp(sl.iloc[0].time), {
        'frozen_z4_lookback_active_m1': FROZEN_Z4_LOOKBACK_ACTIVE_M1,
        'frozen_warmup_c5_landmarks': FROZEN_WARMUP_C5_LANDMARKS,
        'eligible_pre_session_c5_landmarks': int(len(eligible)),
        'warm_start_active_position_in_available_history': int(start_active_pos),
        'warmup_contract': 'latest causal start that leaves exactly 96 pre-session C5 landmarks after the 1440-active-M1 Z4 lookback',
    }


_ORIGINAL_Z4_SESSION = core.z4_session
_ORIGINAL_FEATURE_SESSION = core.prospective_feature_session


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
            out = {'status': 'PROSPECTIVE_SESSION_ALREADY_ACCEPTED_IDENTICAL', **event_base, 'canonical_unchanged': True}
            core.canonical_json(Path(args.manifest), out)
            return out
        stamp = acquired.strftime('%Y%m%dT%H%M%SZ')
        revdir = root / 'revisions' / args.session_date
        revdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cand_session, revdir / f'{stamp}_{ssha[:16]}_session.csv.gz')
        shutil.copy2(cand_warm, revdir / f'{stamp}_{wsha[:16]}_warmup.csv.gz')
        event = core.append_hash_chain(root / 'APPEND_CHAIN.jsonl', {'event_type': 'REVISION_DETECTED_CANONICAL_UNCHANGED', **event_base})
        shutil.rmtree(candidate_dir)
        out = {'status': 'PROSPECTIVE_SOURCE_REVISION_RECORDED_CANONICAL_UNCHANGED', **event_base, 'canonical_unchanged': True, 'chain_record_sha256': event['record_sha256']}
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
            return _ORIGINAL_Z4_SESSION(args)
        finally:
            args.files = old_files


def feature_session_timestamp_bridge(args):
    old_files = list(args.files)
    with timestamp_schema_bridge(old_files, 'pros_e_schema_bridge_') as compat:
        args.files = compat
        try:
            return _ORIGINAL_FEATURE_SESSION(args)
        finally:
            args.files = old_files


core.ingest_session = ingest_session_frozen_warmup
core.z4_session = z4_session_timestamp_bridge
core.prospective_feature_session = feature_session_timestamp_bridge

if __name__ == '__main__':
    core.main()
