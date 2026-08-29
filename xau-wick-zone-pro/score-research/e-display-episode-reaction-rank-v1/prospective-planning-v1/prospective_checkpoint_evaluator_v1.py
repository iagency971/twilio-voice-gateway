#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
LABELER = PKG / 'xau_e_display_episode_reaction_labeler_v1.py'
MODEL = PKG / 'xau_e_display_episode_model_eval_v1.py'
FROZEN_MODEL = PKG / 'dev-freeze-canonical-33264659057' / 'DEV_FROZEN_MODEL.json'
EXPECTED_FROZEN_MODEL_SHA256 = '72e7548de826e2ae2ba66ddcaaf6b2fa7cd35ada0f5f2cd9db585d9734fd48e1'
EXPECTED_LABELER_SHA256 = '08ed29422ede890c300073789daa4669a22fbe48b74171c68402310c00aebef8'
EXPECTED_MODEL_SHA256 = 'f547853609f16b00080049629f708fc0d4170c54071fd22a99228c807cd6dd2e'
GO_EXECUTION_TOKEN = 'GO_PROSPECTIVE_CONFIRMATION_EXECUTION'
START_SESSION = '2026-08-31'
MIN_SESSIONS = 90
MIN_CONTACTS = 1000
SEED = 20260829
BOOT_N = 5000
MIN_VALID_BOOT = 4750


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def loadmod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def session_end_utc(session: str) -> pd.Timestamp:
    return pd.Timestamp(f'{session} 17:00:00', tz='America/New_York').tz_convert('UTC')


def q4_q1(d: pd.DataFrame):
    q1 = d[d.fixed_quartile == 'Q1']
    q4 = d[d.fixed_quartile == 'Q4']
    if not len(q1) or not len(q4):
        return None
    return float(q4.primary_binary_label.mean() - q1.primary_binary_label.mean())


def represented_session_blocks(d: pd.DataFrame, represented_dates: list[str]):
    parts = np.array_split(np.asarray(represented_dates, dtype=object), 3)
    out = []
    for i, part in enumerate(parts, 1):
        dates = part.tolist()
        g = d[d.session_date_ny.astype(str).isin(dates)]
        out.append({
            'block': i,
            'sessions': dates,
            'session_n': len(dates),
            'episode_n': int(len(g)),
            'q4_minus_q1': q4_q1(g),
        })
    return out


def paired_bootstrap_auc_difference(d: pd.DataFrame):
    sessions = np.array(sorted(d.session_date_ny.astype(str).unique()), dtype=object)
    groups = {s: d[d.session_date_ny.astype(str) == s] for s in sessions}
    rng = np.random.default_rng(SEED)
    vals = []
    invalid = 0
    for _ in range(BOOT_N):
        picks = rng.choice(sessions, size=len(sessions), replace=True)
        q = pd.concat([groups[s] for s in picks], ignore_index=True)
        if q.primary_binary_label.nunique() != 2:
            invalid += 1
            continue
        y = q.primary_binary_label.to_numpy(int)
        full = float(roc_auc_score(y, q.continuous_logit.to_numpy(float)))
        width = float(roc_auc_score(y, q.zone_width_v.to_numpy(float)))
        vals.append(full - width)
    ok = len(vals) >= MIN_VALID_BOOT
    ci = [float(np.quantile(vals, .025)), float(np.quantile(vals, .975))] if ok else [None, None]
    return {
        'requested': BOOT_N,
        'valid': len(vals),
        'invalid': invalid,
        'minimum_valid_required': MIN_VALID_BOOT,
        'ci95_percentile': ci,
        'ci_available': ok,
    }


def validate_execution_authority(gate_path: Path, seal_path: Path):
    gate = json.loads(gate_path.read_text())
    seal = json.loads(seal_path.read_text())
    if gate.get('status') != 'PRO_PRE_PROSPECTIVE_EXECUTION_GATE_PASS':
        raise RuntimeError('invalid prospective execution gate status')
    if gate.get('decision') != GO_EXECUTION_TOKEN:
        raise RuntimeError('prospective execution gate decision mismatch')
    if gate.get('authorization_scope') != 'OUTCOME_BLIND_COLLECTION_UNTIL_LOCKED_SINGLE_CHECKPOINT':
        raise RuntimeError('prospective execution authorization scope mismatch')
    if seal.get('status') != 'E_DISPLAY_EPISODE_V1_PROSPECTIVE_PLANNING_CANONICAL_SEAL_PASS':
        raise RuntimeError('invalid prospective planning seal status')
    if seal.get('decision') != 'READY_FOR_PRO_PRE_PROSPECTIVE_EXECUTION_GATE':
        raise RuntimeError('prospective planning seal decision mismatch')
    expected_seal_sha = gate.get('planning_seal_sha256')
    if not expected_seal_sha or sha256(seal_path) != expected_seal_sha:
        raise RuntimeError('prospective planning seal SHA drift')
    expected_eval_sha = gate.get('checkpoint_evaluator_sha256')
    if not expected_eval_sha or sha256(Path(__file__)) != expected_eval_sha:
        raise RuntimeError('prospective checkpoint evaluator SHA drift')
    return gate, seal


def validate_checkpoint(checkpoint: dict):
    dates = [str(x) for x in checkpoint.get('represented_session_dates', [])]
    if dates != sorted(set(dates)):
        raise RuntimeError('checkpoint represented session list is not sorted unique')
    if len(dates) != int(checkpoint.get('represented_sessions', -1)):
        raise RuntimeError('checkpoint represented session count/list mismatch')
    if len(dates) < MIN_SESSIONS:
        raise RuntimeError('checkpoint session threshold not met')
    if dates[0] < START_SESSION:
        raise RuntimeError('checkpoint contains pre-start session')
    if dates[-1] != str(checkpoint.get('session_date_ny')):
        raise RuntimeError('checkpoint end session/list mismatch')
    if int(checkpoint.get('model_eligible_primary_contacts', -1)) < MIN_CONTACTS:
        raise RuntimeError('checkpoint contact threshold not met')
    return dates


def load_contact_counter(files: list[str], represented_dates: list[str]):
    if not files:
        raise RuntimeError('contact-only files required for final exact-parity QA')
    frames = []
    for f in files:
        d = pd.read_csv(f, compression='infer', float_precision='round_trip')
        if len(d):
            frames.append(d)
    if not frames:
        return pd.DataFrame(columns=[
            'display_episode_id', 'session_date_ny', 'selection_status',
            'contact_bar_open_time_utc', 'feature_row_sha256', 'model_eligible_contact'
        ])
    out = pd.concat(frames, ignore_index=True)
    if not set(out.session_date_ny.astype(str).unique()).issubset(set(represented_dates)):
        raise RuntimeError('contact-only rows outside represented checkpoint dates')
    if out.display_episode_id.astype(str).duplicated().any():
        raise RuntimeError('duplicate contact-only display episode id')
    return out


def exact_contact_parity(labels: pd.DataFrame, contact: pd.DataFrame, checkpoint_count: int):
    l = labels.copy()
    c = contact.copy()
    keys = ['display_episode_id', 'selection_status']
    l = l.sort_values('display_episode_id').reset_index(drop=True)
    c = c.sort_values('display_episode_id').reset_index(drop=True)
    if len(l) != len(c):
        raise RuntimeError(f'final label/contact counter row count mismatch: {len(l)} != {len(c)}')
    if len(l) and not np.array_equal(l[keys].astype(str).to_numpy(), c[keys].astype(str).to_numpy()):
        raise RuntimeError('final label/contact counter selection mismatch')
    lp = l[l.selection_status == 'PRIMARY_CONTACT'].sort_values('display_episode_id').reset_index(drop=True)
    cp = c[c.selection_status == 'PRIMARY_CONTACT'].sort_values('display_episode_id').reset_index(drop=True)
    if len(lp) != len(cp):
        raise RuntimeError('final primary contact count mismatch')
    for col in ['contact_bar_open_time_utc', 'feature_row_sha256']:
        if len(lp) and not np.array_equal(lp[col].astype(str).to_numpy(), cp[col].astype(str).to_numpy()):
            raise RuntimeError(f'final contact parity mismatch: {col}')
    eligible = cp[cp.model_eligible_contact.fillna(False).astype(bool)] if len(cp) else cp
    if len(eligible) != checkpoint_count:
        raise RuntimeError(
            f'checkpoint eligible contact count drift: counter={len(eligible)} lock={checkpoint_count}'
        )
    return {
        'status': 'PROSPECTIVE_FINAL_CONTACT_COUNTER_EXACT_PARITY_PASS',
        'episodes': int(len(l)),
        'primary_contacts': int(len(lp)),
        'model_eligible_primary_contacts': int(len(eligible)),
    }


def evaluate(raw: pd.DataFrame, ledger: pd.DataFrame, contact: pd.DataFrame, checkpoint: dict):
    if sha256(FROZEN_MODEL) != EXPECTED_FROZEN_MODEL_SHA256:
        raise RuntimeError('frozen model SHA drift')
    if sha256(LABELER) != EXPECTED_LABELER_SHA256:
        raise RuntimeError('labeler SHA drift')
    if sha256(MODEL) != EXPECTED_MODEL_SHA256:
        raise RuntimeError('model evaluator SHA drift')

    represented_dates = validate_checkpoint(checkpoint)
    end_session = str(checkpoint['session_date_ny'])
    checkpoint_count = int(checkpoint['model_eligible_primary_contacts'])

    led = ledger.copy()
    led['session_date_ny'] = led.session_date_ny.astype(str)
    if len(led):
        if led.session_date_ny.min() < START_SESSION or led.session_date_ny.max() > end_session:
            raise RuntimeError('ledger outside locked prospective window')
        if not set(led.session_date_ny.unique()).issubset(set(represented_dates)):
            raise RuntimeError('ledger includes a non-represented prospective session')

    labeler = loadmod('pros_checkpoint_labeler', LABELER)
    me = loadmod('pros_checkpoint_model', MODEL)
    labels, _ = labeler.label_all(raw, led)
    parity = exact_contact_parity(labels, contact, checkpoint_count)

    pri = labels[labels.selection_status == 'PRIMARY_CONTACT'].copy()
    if not len(pri):
        raise RuntimeError('no prospective primary contacts')
    t = pd.to_datetime(pri.contact_bar_open_time_utc, utc=True, errors='raise')
    if (t < pd.Timestamp('2026-08-31T12:00:00Z')).any() or (t >= session_end_utc(end_session)).any():
        raise RuntimeError('contact outside locked prospective window')

    model = me.load_model(str(FROZEN_MODEL))
    scored, qa = me.transform_score(pri, model)
    if len(scored) != checkpoint_count:
        raise RuntimeError(
            f'frozen model eligible count drift: scored={len(scored)} lock={checkpoint_count}'
        )
    ev = me.evaluation(scored)
    gate = me.prospective_gate(scored, qa, ev)

    # The preregistered time-diversity threshold and chronological blocks use
    # every represented accepted session, including valid zero-contact days.
    blocks = represented_session_blocks(scored, represented_dates)
    gate['checks']['threshold_sessions_ge_90'] = len(represented_dates) >= MIN_SESSIONS
    gate['checks']['threshold_episodes_ge_1000'] = len(scored) >= MIN_CONTACTS
    gate['checks']['q4_q1_positive_all_3_blocks'] = all(
        b['q4_minus_q1'] is not None and b['q4_minus_q1'] > 0 for b in blocks
    )
    gate['blocks'] = blocks
    gate['pass'] = all(gate['checks'].values())

    y = scored.primary_binary_label.to_numpy(int)
    full = float(roc_auc_score(y, scored.continuous_logit.to_numpy(float)))
    width = float(roc_auc_score(y, scored.zone_width_v.to_numpy(float)))
    width_control = {
        'status': 'WIDTH_ONLY_INTERPRETATION_CONTROL',
        'gating': False,
        'rescue_allowed': False,
        'width_only_auc': width,
        'full_model_auc': full,
        'full_minus_width_auc': full - width,
        'paired_session_bootstrap_full_minus_width': paired_bootstrap_auc_difference(scored),
    }
    report = {
        'status': 'PROSPECTIVE_CONFIRMATION_SINGLE_CHECKPOINT_EVALUATED',
        'locked_checkpoint': checkpoint,
        'represented_session_count': len(represented_dates),
        'contact_counter_exact_parity': parity,
        'frozen_dev_model_sha256': EXPECTED_FROZEN_MODEL_SHA256,
        'model_refit': False,
        'primary_evaluation': ev,
        'primary_gate': gate,
        'feature_transform_qa': qa,
        'width_interpretation_control': width_control,
        'production_authorization': 'NONE_REQUIRES_POST_PROSPECTIVE_PRO_GATE',
        'pine_modification': 'FORBIDDEN',
    }
    return labels, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw-files', nargs='+', required=True)
    parser.add_argument('--ledger-files', nargs='+', required=True)
    parser.add_argument('--contact-files', nargs='*', default=[])
    parser.add_argument('--checkpoint-lock', required=True)
    parser.add_argument('--planning-seal')
    parser.add_argument('--execution-gate')
    parser.add_argument('--output-labels', required=True)
    parser.add_argument('--output-report', required=True)
    parser.add_argument('--output-manifest', required=True)
    parser.add_argument('--authorization-token', default='')
    args = parser.parse_args()

    # The token guard executes before any outcome-bearing input is opened.
    if args.authorization_token != GO_EXECUTION_TOKEN:
        raise RuntimeError(
            'PROSPECTIVE_OUTCOME_OPENING_BLOCKED: GO_PROSPECTIVE_CONFIRMATION_EXECUTION required'
        )
    if not args.planning_seal or not args.execution_gate:
        raise RuntimeError('prospective planning seal and Pro execution gate are required')
    validate_execution_authority(Path(args.execution_gate), Path(args.planning_seal))

    checkpoint = json.loads(Path(args.checkpoint_lock).read_text())
    represented_dates = validate_checkpoint(checkpoint)
    raw = pd.concat([pd.read_csv(f, compression='infer') for f in args.raw_files], ignore_index=True)
    if 'time' not in raw and 'timestamp' in raw:
        raw['time'] = pd.to_datetime(raw.timestamp, unit='ms', utc=True)
    elif 'time' in raw:
        raw['time'] = pd.to_datetime(raw.time, utc=True)
    else:
        raise RuntimeError('raw M1 input has no time/timestamp')
    ledger_frames = [
        pd.read_csv(f, compression='infer', float_precision='round_trip') for f in args.ledger_files
    ]
    ledger = pd.concat(ledger_frames, ignore_index=True) if ledger_frames else pd.DataFrame()
    contact = load_contact_counter(args.contact_files, represented_dates)
    labels, report = evaluate(raw, ledger, contact, checkpoint)

    output_labels = Path(args.output_labels)
    output_labels.parent.mkdir(parents=True, exist_ok=True)
    labels.to_csv(
        output_labels,
        index=False,
        compression={'method': 'gzip', 'mtime': 0},
        float_format='%.17g',
    )
    output_report = Path(args.output_report)
    output_report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    manifest = {
        'status': 'PROSPECTIVE_CONFIRMATION_CHECKPOINT_PACKAGE_COMPLETE',
        'labels_sha256': sha256(output_labels),
        'report_sha256': sha256(output_report),
        'frozen_dev_model_sha256': EXPECTED_FROZEN_MODEL_SHA256,
        'model_refit': False,
        'contact_counter_exact_parity': True,
        'next_authorization': 'READY_FOR_PRO_POST_PROSPECTIVE_GATE',
        'production_authorization': 'NONE',
    }
    Path(args.output_manifest).write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(json.dumps({
        'status': manifest['status'],
        'primary_gate_pass': report['primary_gate']['pass'],
        'next_authorization': manifest['next_authorization'],
    }, indent=2))


if __name__ == '__main__':
    main()
