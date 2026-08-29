#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
ROOT = PKG.parents[2]
ENTRY = ROOT / 'entry-research'
ENGINE = ENTRY / 'geometry-shifted-grid-parity' / 'xau_z4_c5_geometry_shifted_grid_equivalent.py'
PROV = PKG / 'xau_ebuy_provenance_instrument_v1.py'
SNAP = PKG / 'xau_e_display_episode_snapshot_v1.py'
MODEL = PKG / 'xau_e_display_episode_model_eval_v1.py'
LABELER = PKG / 'xau_e_display_episode_reaction_labeler_v1.py'
FROZEN_MODEL = PKG / 'dev-freeze-canonical-33264659057' / 'DEV_FROZEN_MODEL.json'
EXPECTED_ENGINE_GIT_BLOB = 'ac2448f448df2b873b482fd74c4eddf031790117'
EXPECTED_FROZEN_MODEL_SHA256 = '72e7548de826e2ae2ba66ddcaaf6b2fa7cd35ada0f5f2cd9db585d9734fd48e1'
EXPECTED_LABELER_SHA256 = '08ed29422ede890c300073789daa4669a22fbe48b74171c68402310c00aebef8'
EXPECTED_MODEL_SHA256 = 'f547853609f16b00080049629f708fc0d4170c54071fd22a99228c807cd6dd2e'
PROSPECTIVE_START = pd.Timestamp('2026-08-31T12:00:00Z')
PROSPECTIVE_START_SESSION = '2026-08-31'
MIN_SESSIONS = 90
MIN_CONTACTS = 1000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()


def loadmod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def session_bounds(session_date: str):
    start = pd.Timestamp(f'{session_date} 08:00:00', tz='America/New_York')
    end = pd.Timestamp(f'{session_date} 17:00:00', tz='America/New_York')
    return start.tz_convert('UTC'), end.tz_convert('UTC')


def session_date_ny(t) -> str:
    return pd.Timestamp(t).tz_convert('America/New_York').date().isoformat()


def normalize_raw_files(files: list[str]):
    frames = []
    for f in files:
        d = pd.read_csv(f, compression='infer')
        if 'time' in d.columns:
            d['time'] = pd.to_datetime(d['time'], utc=True)
        elif 'timestamp' in d.columns:
            d['time'] = pd.to_datetime(d['timestamp'], unit='ms', utc=True)
        else:
            raise RuntimeError(f'{f}: no time/timestamp')
        for c in ['open', 'high', 'low', 'close']:
            d[c] = pd.to_numeric(d[c], errors='raise').astype(float)
        frames.append(d[['time', 'open', 'high', 'low', 'close']])
    if not frames:
        raise RuntimeError('no raw files')
    d = pd.concat(frames, ignore_index=True).sort_values('time').reset_index(drop=True)
    conflicting = 0
    dup = d[d.duplicated('time', keep=False)]
    for _, g in dup.groupby('time'):
        if len(g[['open', 'high', 'low', 'close']].drop_duplicates()) > 1:
            conflicting += 1
    if conflicting:
        raise RuntimeError(f'conflicting duplicate M1 timestamps: {conflicting}')
    exact_dups = int(d.duplicated(['time', 'open', 'high', 'low', 'close']).sum())
    d = d.drop_duplicates('time', keep='first').sort_values('time').reset_index(drop=True)
    return d, {'exact_duplicate_rows_removed': exact_dups, 'conflicting_duplicate_timestamps': conflicting}


def deterministic_gzip_csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = df.to_csv(index=False, lineterminator='\n', float_format='%.17g', na_rep='').encode()
    with path.open('wb') as fh:
        with gzip.GzipFile(fileobj=fh, mode='wb', mtime=0, filename='') as gz:
            gz.write(raw)


def canonical_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


def append_hash_chain(path: Path, event: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    prev = None
    if path.exists() and path.stat().st_size:
        lines = [x for x in path.read_text().splitlines() if x.strip()]
        if lines:
            prev = json.loads(lines[-1])['record_sha256']
    rec = dict(event)
    rec['previous_record_sha256'] = prev
    payload = json.dumps(rec, sort_keys=True, separators=(',', ':')).encode()
    rec['record_sha256'] = hashlib.sha256(payload).hexdigest()
    with path.open('a') as f:
        f.write(json.dumps(rec, sort_keys=True, separators=(',', ':')) + '\n')
    return rec


def ingest_session(args):
    acquired = pd.Timestamp(args.acquired_at)
    if acquired.tzinfo is None:
        acquired = acquired.tz_localize('UTC')
    else:
        acquired = acquired.tz_convert('UTC')
    start, end = session_bounds(args.session_date)
    if acquired < end:
        raise RuntimeError(f'acquisition before completed session: {acquired} < {end}')
    if pd.Timestamp(start) < PROSPECTIVE_START and not args.historical_dry_run:
        raise RuntimeError('session predates prospective start')
    raw, qa = normalize_raw_files(args.files)
    sess = raw[(raw.time >= start) & (raw.time < end)].copy()
    if not len(sess):
        raise RuntimeError('no usable US-session M1 rows')
    expected = pd.date_range(start=start, periods=540, freq='min')
    actual = set(sess.time.tolist())
    missing = [t for t in expected if t not in actual]
    active_prior = raw[(raw.time < start) & (raw.high > raw.low)]
    if len(active_prior) < 1440:
        raise RuntimeError(f'insufficient active warmup: {len(active_prior)} < 1440')
    warm_start = pd.Timestamp(active_prior.iloc[-1440].time)
    warm = raw[(raw.time >= warm_start) & (raw.time < end)].copy()
    root = Path(args.archive_root)
    session_path = root / 'sessions' / f'{args.session_date}.csv.gz'
    warm_path = root / 'warmup' / f'{args.session_date}.csv.gz'
    candidate_dir = Path(tempfile.mkdtemp(prefix='pros_ingest_'))
    cand_session = candidate_dir / 'session.csv.gz'
    cand_warm = candidate_dir / 'warmup.csv.gz'
    deterministic_gzip_csv(sess, cand_session)
    deterministic_gzip_csv(warm, cand_warm)
    ssha, wsha = sha256_file(cand_session), sha256_file(cand_warm)
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
        **qa,
    }
    if session_path.exists() or warm_path.exists():
        if not (session_path.exists() and warm_path.exists()):
            raise RuntimeError('partial canonical archive state')
        same = sha256_file(session_path) == ssha and sha256_file(warm_path) == wsha
        if same:
            shutil.rmtree(candidate_dir)
            out = {'status': 'PROSPECTIVE_SESSION_ALREADY_ACCEPTED_IDENTICAL', **event_base, 'canonical_unchanged': True}
            canonical_json(Path(args.manifest), out)
            return out
        stamp = acquired.strftime('%Y%m%dT%H%M%SZ')
        revdir = root / 'revisions' / args.session_date
        revdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cand_session, revdir / f'{stamp}_{ssha[:16]}_session.csv.gz')
        shutil.copy2(cand_warm, revdir / f'{stamp}_{wsha[:16]}_warmup.csv.gz')
        event = append_hash_chain(root / 'APPEND_CHAIN.jsonl', {'event_type': 'REVISION_DETECTED_CANONICAL_UNCHANGED', **event_base})
        shutil.rmtree(candidate_dir)
        out = {'status': 'PROSPECTIVE_SOURCE_REVISION_RECORDED_CANONICAL_UNCHANGED', **event_base, 'canonical_unchanged': True, 'chain_record_sha256': event['record_sha256']}
        canonical_json(Path(args.manifest), out)
        return out
    session_path.parent.mkdir(parents=True, exist_ok=True)
    warm_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(cand_session), session_path)
    shutil.move(str(cand_warm), warm_path)
    shutil.rmtree(candidate_dir)
    session_manifest = root / 'manifests' / f'{args.session_date}.json'
    event = append_hash_chain(root / 'APPEND_CHAIN.jsonl', {'event_type': 'FIRST_ACCEPTANCE', **event_base})
    accepted = {
        'status': 'PROSPECTIVE_SESSION_FIRST_ACCEPTANCE_PASS',
        **event_base,
        'canonical_session_path': str(session_path),
        'canonical_warmup_path': str(warm_path),
        'chain_record_sha256': event['record_sha256'],
        'canonical_overwrite_allowed': False,
    }
    canonical_json(session_manifest, accepted)
    canonical_json(Path(args.manifest), accepted)
    return accepted


def patched_geometry_engine(temp_path: Path):
    data = ENGINE.read_bytes()
    got = git_blob_sha(data)
    if got != EXPECTED_ENGINE_GIT_BLOB:
        raise RuntimeError(f'Z4 engine git blob drift: {got} != {EXPECTED_ENGINE_GIT_BLOB}')
    src = data.decode()
    anchor = '    m=len(Z)\n'
    if src.count(anchor) != 1:
        raise RuntimeError('geometry cut anchor changed')
    insert = "    keep=['time','landmark_i','center','zlo','zhi','side']\n    Z[keep].to_pickle(args.output)\n    return\n\n"
    temp_path.write_text(src.replace(anchor, insert + anchor))
    return {'git_blob': got, 'sha256': hashlib.sha256(data).hexdigest()}


def z4_session(args):
    session = args.session_date
    start, end = session_bounds(session)
    with tempfile.TemporaryDirectory(prefix='pros_z4_') as td:
        td = Path(td)
        script = td / 'geom.py'
        guard = patched_geometry_engine(script)
        allp = td / 'all.pkl'
        cmd = [sys.executable, str(script), '--files', *args.files, '--output', str(allp), '--tag', f'PROSPECTIVE_{session}']
        subprocess.run(cmd, check=True)
        z = pd.read_pickle(allp)
    z['time'] = pd.to_datetime(z.time, utc=True)
    ny = z.time.dt.tz_convert('America/New_York')
    q = z[(ny.dt.date.astype(str) == session) & (ny.dt.hour >= 8) & (ny.dt.hour < 17)].copy()
    q = q.sort_values(['time', 'side', 'center']).reset_index(drop=True)
    if not len(q):
        raise RuntimeError(f'no Z4 geometry rows for {session}')
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    q.to_pickle(out)
    m = {
        'status': 'PROSPECTIVE_Z4_SESSION_GEOMETRY_PASS',
        'session_date_ny': session,
        'rows': int(len(q)),
        'snapshots_with_zones': int(q.time.nunique()),
        'first_time_utc': pd.Timestamp(q.time.min()).isoformat(),
        'last_time_utc': pd.Timestamp(q.time.max()).isoformat(),
        'engine_guard': guard,
        'geometry_only': True,
        'future_outcomes_used': False,
        'output_sha256': sha256_file(out),
    }
    canonical_json(Path(args.manifest), m)
    return m


def prospective_feature_session(args):
    if sha256_file(FROZEN_MODEL) != EXPECTED_FROZEN_MODEL_SHA256:
        raise RuntimeError('frozen DEV model SHA drift')
    prov = loadmod('pros_prov', PROV)
    snap = loadmod('pros_snap', SNAP)
    me = loadmod('pros_model', MODEL)
    raw = prov.v01.load_raw(args.files)
    active = prov.v01.active_m1(raw)
    z4 = pd.read_pickle(args.z4_pkl).copy()
    z4['time'] = pd.to_datetime(z4.time, utc=True)
    snaps, displays = prov.build(raw, active, z4)
    cand = prov.rows_from(snaps, displays)
    if not len(cand):
        raise RuntimeError('no prospective candidate rows')
    cand['time'] = pd.to_datetime(cand.time, utc=True)
    ny = cand.time.dt.tz_convert('America/New_York')
    cand = cand[(ny.dt.date.astype(str) == args.session_date) & (ny.dt.hour >= 8) & (ny.dt.hour < 17)].copy().reset_index(drop=True)
    if not len(cand):
        raise RuntimeError('no candidates in target session')
    ledger = snap.build(cand)
    ledger['feature_window'] = 'PROSPECTIVE_CONFIRMATION'
    ledger['row_sha256'] = [snap.row_hash(r) for r in ledger.drop(columns=['row_sha256']).to_dict('records')]
    m = me.load_model(str(FROZEN_MODEL))
    scored, qa = me.transform_score(ledger, m)
    add = scored[['row_sha256', 'continuous_logit', 'E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1', 'fixed_quartile']].copy()
    ledger = ledger.merge(add, on='row_sha256', how='left', validate='one_to_one')
    ledger['width_only_score'] = ledger.zone_width_v.astype(float)
    outc = Path(args.candidates_output); outl = Path(args.ledger_output)
    snap.write_gzip_csv(cand, str(outc))
    snap.write_gzip_csv(ledger, str(outl))
    man = {
        'status': 'PROSPECTIVE_FEATURE_SESSION_OUTCOME_FREE_PASS',
        'session_date_ny': args.session_date,
        'candidate_rows': int(len(cand)),
        'feature_rows': int(len(ledger)),
        'display_episodes': int(ledger.display_episode_id.nunique()),
        'snapshots': int(ledger.snapshot_time_utc.nunique()),
        'model_feature_exclusion_rows': int(qa['feature_excluded_rows']),
        'model_feature_exclusion_rate': qa['feature_exclusion_rate'],
        'unseen_family_rows': int(qa['unseen_family_rows']),
        'unseen_family_rate': qa['unseen_family_rate'],
        'frozen_dev_model_sha256': EXPECTED_FROZEN_MODEL_SHA256,
        'prospective_outcomes_used': False,
        'candidate_sha256': sha256_file(outc),
        'ledger_sha256': sha256_file(outl),
    }
    canonical_json(Path(args.manifest), man)
    return man


def contact_only_episode(labeler, raw: pd.DataFrame, g: pd.DataFrame, frozen_categories: set[str]):
    g = g.sort_values('feature_available_time_utc').reset_index(drop=True)
    eid = str(g.display_episode_id.iloc[0]); session = str(g.session_date_ny.iloc[0])
    start = g.feature_available_time_utc.min(); end = (g.feature_available_time_utc + pd.Timedelta(minutes=5)).max()
    bars = raw[(raw.time >= start) & (raw.time < end)].copy()
    bars = bars[bars.time.map(lambda t: labeler.us_bar_ok(pd.Timestamp(t), session))]
    armed = False; arm_effective = None; arm_bar = None
    for _, b in bars.iterrows():
        bt = pd.Timestamp(b.time); r = labeler.valid_row_at(g, bt)
        if r is None:
            if armed:
                return {'display_episode_id': eid, 'session_date_ny': session, 'selection_status': 'NO_CONTACT_BEFORE_EPISODE_END', 'arm_bar_open_time_utc': arm_bar, 'arm_effective_time_utc': arm_effective}
            continue
        if not armed:
            if float(b['close']) > float(r.zhi):
                armed = True; arm_bar = bt; arm_effective = bt + pd.Timedelta(minutes=1)
            continue
        if bt < arm_effective:
            continue
        if float(b['high']) >= float(r.zlo) and float(b['low']) <= float(r.zhi):
            ok = np.isfinite(float(r.zone_width_v)) and int(r.display_persistence_c5) >= 1 and str(r.current_family) in frozen_categories
            return {
                'display_episode_id': eid,
                'session_date_ny': session,
                'selection_status': 'PRIMARY_CONTACT',
                'arm_bar_open_time_utc': arm_bar,
                'arm_effective_time_utc': arm_effective,
                'contact_bar_open_time_utc': bt,
                'feature_snapshot_time_utc': pd.Timestamp(r.snapshot_time_utc),
                'feature_available_time_utc': pd.Timestamp(r.feature_available_time_utc),
                'feature_row_sha256': str(r.row_sha256),
                'current_family': str(r.current_family),
                'zone_width_v': float(r.zone_width_v),
                'display_persistence_c5': int(r.display_persistence_c5),
                'frozen_continuous_logit': float(r.continuous_logit) if 'continuous_logit' in r and pd.notna(r.continuous_logit) else np.nan,
                'frozen_rank': float(r.E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1) if 'E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1' in r and pd.notna(r.E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1) else np.nan,
                'fixed_quartile': str(r.fixed_quartile) if 'fixed_quartile' in r and pd.notna(r.fixed_quartile) else '',
                'width_only_score': float(r.zone_width_v),
                'model_eligible_contact': bool(ok),
            }
    if not armed:
        return {'display_episode_id': eid, 'session_date_ny': session, 'selection_status': 'NEVER_ARMED'}
    return {'display_episode_id': eid, 'session_date_ny': session, 'selection_status': 'NO_CONTACT_BEFORE_EPISODE_END', 'arm_bar_open_time_utc': arm_bar, 'arm_effective_time_utc': arm_effective}


def contact_only(args):
    if sha256_file(LABELER) != EXPECTED_LABELER_SHA256:
        raise RuntimeError('frozen labeler SHA drift')
    labeler = loadmod('pros_labeler', LABELER)
    raw0, rawqa = normalize_raw_files(args.files)
    raw, _ = labeler.normalize_m1(raw0)
    led = pd.read_csv(args.ledger, compression='infer', float_precision='round_trip')
    led = labeler.prep_ledger(led)
    if set(led.session_date_ny.astype(str).unique()) != {args.session_date}:
        raise RuntimeError('contact-only ledger must contain exactly target session')
    fm = json.loads(FROZEN_MODEL.read_text())
    cats = set(str(x) for x in fm['categories'])
    rows = [contact_only_episode(labeler, raw, g, cats) for _, g in led.groupby('display_episode_id', sort=False)]
    out = pd.DataFrame(rows).sort_values('display_episode_id').reset_index(drop=True)
    p = Path(args.output)
    deterministic_gzip_csv(out, p)
    primary = out[out.selection_status == 'PRIMARY_CONTACT']
    eligible = primary[primary.model_eligible_contact.fillna(False).astype(bool)] if len(primary) else primary
    man = {
        'status': 'PROSPECTIVE_CONTACT_ONLY_PASS',
        'session_date_ny': args.session_date,
        'episodes': int(len(out)),
        'primary_contacts': int(len(primary)),
        'model_eligible_primary_contacts': int(len(eligible)),
        'post_contact_bars_read': 0,
        'prospective_outcomes_generated': False,
        'prospective_outcomes_read': False,
        'raw_qa': rawqa,
        'output_sha256': sha256_file(p),
    }
    canonical_json(Path(args.manifest), man)
    return man


def z4_parity(args):
    a = pd.read_pickle(args.a); b = pd.read_pickle(args.b)
    for d in (a, b):
        d['time'] = pd.to_datetime(d.time, utc=True)
    cols = ['time', 'side', 'center', 'zlo', 'zhi']
    aa = a[cols].sort_values(cols).reset_index(drop=True)
    bb = b[cols].sort_values(cols).reset_index(drop=True)
    if len(aa) != len(bb):
        raise RuntimeError(f'Z4 row count mismatch {len(aa)} != {len(bb)}')
    for c in ['time', 'side']:
        if not np.array_equal(aa[c].to_numpy(), bb[c].to_numpy()):
            raise RuntimeError(f'Z4 mismatch {c}')
    for c in ['center', 'zlo', 'zhi']:
        if not np.allclose(aa[c].to_numpy(float), bb[c].to_numpy(float), rtol=0, atol=1e-12):
            raise RuntimeError(f'Z4 mismatch {c}')
    out = {'status': 'PROSPECTIVE_Z4_PARITY_PASS', 'rows': int(len(aa)), 'columns': cols}
    canonical_json(Path(args.output), out); return out


def feature_parity(args):
    a = pd.read_csv(args.got, compression='infer', float_precision='round_trip')
    b = pd.read_csv(args.canonical, compression='infer', float_precision='round_trip')
    b['snapshot_time_utc'] = pd.to_datetime(b.snapshot_time_utc, utc=True)
    ny = b.snapshot_time_utc.dt.tz_convert('America/New_York')
    b = b[(ny.dt.date.astype(str) == args.session_date) & (ny.dt.hour >= 8) & (ny.dt.hour < 17)].copy()
    a['snapshot_time_utc'] = pd.to_datetime(a.snapshot_time_utc, utc=True)
    keys = ['snapshot_time_utc', 'display_slot_rank']
    cols_s = ['current_family']
    cols_f = ['center', 'zlo', 'zhi', 'v_snapshot', 'zone_width_v']
    cols_i = ['display_persistence_c5']
    aa = a.sort_values(keys).reset_index(drop=True); bb = b.sort_values(keys).reset_index(drop=True)
    if len(aa) != len(bb):
        raise RuntimeError(f'feature parity row count {len(aa)} != {len(bb)}')
    if not np.array_equal(aa[keys].astype(str).to_numpy(), bb[keys].astype(str).to_numpy()):
        raise RuntimeError('feature parity keys mismatch')
    for c in cols_s + cols_i:
        if not np.array_equal(aa[c].astype(str).to_numpy(), bb[c].astype(str).to_numpy()):
            raise RuntimeError(f'feature parity mismatch {c}')
    for c in cols_f:
        if not np.allclose(aa[c].to_numpy(float), bb[c].to_numpy(float), rtol=0, atol=1e-12):
            raise RuntimeError(f'feature parity mismatch {c}')
    out = {'status': 'PROSPECTIVE_FEATURE_HISTORICAL_DRYRUN_PARITY_PASS', 'session_date_ny': args.session_date, 'rows': int(len(aa)), 'compared': keys + cols_s + cols_f + cols_i}
    canonical_json(Path(args.output), out); return out


def contact_parity(args):
    got = pd.read_csv(args.got, compression='infer', float_precision='round_trip')
    ref = pd.read_csv(args.frozen_labels, compression='infer', float_precision='round_trip')
    ref = ref[ref.session_date_ny.astype(str) == args.session_date].copy()
    cols = ['display_episode_id', 'selection_status']
    g = got.sort_values('display_episode_id').reset_index(drop=True)
    r = ref.sort_values('display_episode_id').reset_index(drop=True)
    if len(g) != len(r): raise RuntimeError(f'contact parity rows {len(g)} != {len(r)}')
    if not np.array_equal(g[cols].astype(str).to_numpy(), r[cols].astype(str).to_numpy()): raise RuntimeError('selection parity mismatch')
    gp = g[g.selection_status == 'PRIMARY_CONTACT'].copy().sort_values('display_episode_id')
    rp = r[r.selection_status == 'PRIMARY_CONTACT'].copy().sort_values('display_episode_id')
    if len(gp) != len(rp): raise RuntimeError('primary contact count mismatch')
    for c in ['contact_bar_open_time_utc', 'feature_row_sha256']:
        if not np.array_equal(gp[c].astype(str).to_numpy(), rp[c].astype(str).to_numpy()): raise RuntimeError(f'contact parity mismatch {c}')
    out = {'status': 'PROSPECTIVE_CONTACT_ONLY_HISTORICAL_PARITY_PASS', 'session_date_ny': args.session_date, 'episodes': int(len(g)), 'primary_contacts': int(len(gp))}
    canonical_json(Path(args.output), out); return out


def firewall(args):
    root = Path(args.live_root)
    forbidden_names = ('reaction', 'label', 'outcome', 'performance', 'evaluation', 'mfe', 'mae')
    forbidden_fields = ('primary_binary_label', 'primary_class', 'favorable_level', 'event_bar_open_time_utc', 'success_rate', 'auc', 'q4_minus_q1', 'mfe', 'mae')
    violations = []
    if root.exists():
        for p in root.rglob('*'):
            if not p.is_file(): continue
            rel = str(p.relative_to(root)).lower()
            if any(x in rel for x in forbidden_names): violations.append({'file': rel, 'reason': 'forbidden_filename'})
            if p.suffix.lower() in {'.json', '.jsonl', '.csv'} or p.name.endswith('.csv.gz'):
                try:
                    if p.suffix.lower() in {'.json', '.jsonl'}:
                        txt = p.read_text(errors='ignore').lower()
                        for f in forbidden_fields:
                            if f in txt: violations.append({'file': rel, 'reason': f'forbidden_field:{f}'})
                    else:
                        d = pd.read_csv(p, compression='infer', nrows=2)
                        lc = [str(c).lower() for c in d.columns]
                        for f in forbidden_fields:
                            if f in lc: violations.append({'file': rel, 'reason': f'forbidden_column:{f}'})
                except Exception as e:
                    violations.append({'file': rel, 'reason': f'unreadable:{type(e).__name__}'})
    out = {'status': 'PROSPECTIVE_ANTI_PEEKING_FIREWALL_PASS' if not violations else 'PROSPECTIVE_ANTI_PEEKING_FIREWALL_FAIL', 'violations': violations, 'prospective_performance_visible': False if not violations else None}
    canonical_json(Path(args.output), out)
    if violations: raise RuntimeError(f'anti-peeking violations: {violations[:5]}')
    return out


def status_checkpoint(args):
    root = Path(args.live_root)
    mans = []
    for p in sorted((root / 'contacts').glob('*.json')) if (root / 'contacts').exists() else []:
        d = json.loads(p.read_text())
        if d.get('status') == 'PROSPECTIVE_CONTACT_ONLY_PASS': mans.append(d)
    by = {str(m['session_date_ny']): m for m in mans}
    dates = sorted(by)
    cumulative = 0; checkpoint = None
    for i, s in enumerate(dates, 1):
        cumulative += int(by[s]['model_eligible_primary_contacts'])
        if checkpoint is None and i >= MIN_SESSIONS and cumulative >= MIN_CONTACTS:
            checkpoint = {'session_date_ny': s, 'represented_sessions': i, 'model_eligible_primary_contacts': cumulative}
    total_contacts = sum(int(by[s]['model_eligible_primary_contacts']) for s in dates)
    out = {
        'status': 'PROSPECTIVE_PRECHECKPOINT_STATUS_OUTCOME_BLIND',
        'prospective_start_session': PROSPECTIVE_START_SESSION,
        'represented_session_count': len(dates),
        'model_eligible_primary_contact_count': total_contacts,
        'threshold_sessions': MIN_SESSIONS,
        'threshold_contacts': MIN_CONTACTS,
        'checkpoint_reached': checkpoint is not None,
        'locked_checkpoint': checkpoint,
        'performance_fields_exposed': False,
    }
    lock = Path(args.lock)
    if checkpoint:
        if lock.exists():
            old = json.loads(lock.read_text())
            if old != checkpoint: raise RuntimeError(f'checkpoint lock drift: {old} != {checkpoint}')
        else:
            canonical_json(lock, checkpoint)
    canonical_json(Path(args.output), out)
    return out


def width_historical_dryrun(args):
    if sha256_file(MODEL) != EXPECTED_MODEL_SHA256: raise RuntimeError('model evaluator SHA drift')
    me = loadmod('pros_width_model', MODEL)
    labels = pd.read_csv(args.labels, compression='infer')
    pri = labels[labels.selection_status == 'PRIMARY_CONTACT'].copy()
    if args.session_date:
        pri = pri[pri.session_date_ny.astype(str) == args.session_date].copy()
    m = me.load_model(str(FROZEN_MODEL)); scored, qa = me.transform_score(pri, m)
    y = scored.primary_binary_label.to_numpy(int)
    full = float(roc_auc_score(y, scored.continuous_logit.to_numpy(float)))
    width = float(roc_auc_score(y, scored.zone_width_v.to_numpy(float)))
    out = {'status': 'WIDTH_ONLY_INTERPRETATION_CONTROL_HISTORICAL_DRY_RUN_PASS', 'n': int(len(scored)), 'full_auc': full, 'width_only_auc': width, 'full_minus_width_auc': full - width, 'gating': False, 'rescue_allowed': False, 'feature_qa': qa}
    canonical_json(Path(args.output), out); return out


def parser():
    p = argparse.ArgumentParser(); sp = p.add_subparsers(dest='cmd', required=True)
    q = sp.add_parser('ingest-session'); q.add_argument('--files', nargs='+', required=True); q.add_argument('--session-date', required=True); q.add_argument('--acquired-at', required=True); q.add_argument('--archive-root', required=True); q.add_argument('--manifest', required=True); q.add_argument('--source-meta-json'); q.add_argument('--historical-dry-run', action='store_true')
    q = sp.add_parser('z4-session'); q.add_argument('--files', nargs='+', required=True); q.add_argument('--session-date', required=True); q.add_argument('--output', required=True); q.add_argument('--manifest', required=True)
    q = sp.add_parser('feature-session'); q.add_argument('--files', nargs='+', required=True); q.add_argument('--z4-pkl', required=True); q.add_argument('--session-date', required=True); q.add_argument('--candidates-output', required=True); q.add_argument('--ledger-output', required=True); q.add_argument('--manifest', required=True)
    q = sp.add_parser('contact-only'); q.add_argument('--files', nargs='+', required=True); q.add_argument('--ledger', required=True); q.add_argument('--session-date', required=True); q.add_argument('--output', required=True); q.add_argument('--manifest', required=True)
    q = sp.add_parser('z4-parity'); q.add_argument('--a', required=True); q.add_argument('--b', required=True); q.add_argument('--output', required=True)
    q = sp.add_parser('feature-parity'); q.add_argument('--got', required=True); q.add_argument('--canonical', required=True); q.add_argument('--session-date', required=True); q.add_argument('--output', required=True)
    q = sp.add_parser('contact-parity'); q.add_argument('--got', required=True); q.add_argument('--frozen-labels', required=True); q.add_argument('--session-date', required=True); q.add_argument('--output', required=True)
    q = sp.add_parser('firewall'); q.add_argument('--live-root', required=True); q.add_argument('--output', required=True)
    q = sp.add_parser('status'); q.add_argument('--live-root', required=True); q.add_argument('--lock', required=True); q.add_argument('--output', required=True)
    q = sp.add_parser('width-historical-dryrun'); q.add_argument('--labels', required=True); q.add_argument('--session-date'); q.add_argument('--output', required=True)
    return p


def main():
    a = parser().parse_args()
    funcs = {'ingest-session': ingest_session, 'z4-session': z4_session, 'feature-session': prospective_feature_session, 'contact-only': contact_only, 'z4-parity': z4_parity, 'feature-parity': feature_parity, 'contact-parity': contact_parity, 'firewall': firewall, 'status': status_checkpoint, 'width-historical-dryrun': width_historical_dryrun}
    out = funcs[a.cmd](a)
    print(json.dumps(out, indent=2, sort_keys=True, default=str))


if __name__ == '__main__':
    main()
