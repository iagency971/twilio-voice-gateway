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

HERE=Path(__file__).resolve().parent
PKG=HERE.parent
LABELER=PKG/'xau_e_display_episode_reaction_labeler_v1.py'
MODEL=PKG/'xau_e_display_episode_model_eval_v1.py'
FROZEN_MODEL=PKG/'dev-freeze-canonical-33264659057'/'DEV_FROZEN_MODEL.json'
EXPECTED_FROZEN_MODEL_SHA256='72e7548de826e2ae2ba66ddcaaf6b2fa7cd35ada0f5f2cd9db585d9734fd48e1'
EXPECTED_LABELER_SHA256='08ed29422ede890c300073789daa4669a22fbe48b74171c68402310c00aebef8'
EXPECTED_MODEL_SHA256='f547853609f16b00080049629f708fc0d4170c54071fd22a99228c807cd6dd2e'
GO_EXECUTION_TOKEN='GO_PROSPECTIVE_CONFIRMATION_EXECUTION'
START_SESSION='2026-08-31'
MIN_SESSIONS=90
MIN_CONTACTS=1000
SEED=20260829
BOOT_N=5000
MIN_VALID_BOOT=4750


def sha256(path:Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def loadmod(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m


def session_end_utc(s):
    return pd.Timestamp(f'{s} 17:00:00',tz='America/New_York').tz_convert('UTC')


def paired_bootstrap_auc_difference(d):
    sessions=np.array(sorted(d.session_date_ny.astype(str).unique()),dtype=object)
    groups={s:d[d.session_date_ny.astype(str)==s] for s in sessions}
    rng=np.random.default_rng(SEED);vals=[];invalid=0
    for _ in range(BOOT_N):
        picks=rng.choice(sessions,size=len(sessions),replace=True)
        q=pd.concat([groups[s] for s in picks],ignore_index=True)
        if q.primary_binary_label.nunique()!=2:
            invalid+=1;continue
        y=q.primary_binary_label.to_numpy(int)
        full=float(roc_auc_score(y,q.continuous_logit.to_numpy(float)))
        width=float(roc_auc_score(y,q.zone_width_v.to_numpy(float)))
        vals.append(full-width)
    ok=len(vals)>=MIN_VALID_BOOT
    ci=[float(np.quantile(vals,.025)),float(np.quantile(vals,.975))] if ok else [None,None]
    return {'requested':BOOT_N,'valid':len(vals),'invalid':invalid,'minimum_valid_required':MIN_VALID_BOOT,'ci95_percentile':ci,'ci_available':ok}


def evaluate(raw,ledger,checkpoint):
    if sha256(FROZEN_MODEL)!=EXPECTED_FROZEN_MODEL_SHA256:raise RuntimeError('frozen model SHA drift')
    if sha256(LABELER)!=EXPECTED_LABELER_SHA256:raise RuntimeError('labeler SHA drift')
    if sha256(MODEL)!=EXPECTED_MODEL_SHA256:raise RuntimeError('model evaluator SHA drift')
    if int(checkpoint['represented_sessions'])<MIN_SESSIONS or int(checkpoint['model_eligible_primary_contacts'])<MIN_CONTACTS:
        raise RuntimeError('checkpoint thresholds not met')
    end_session=str(checkpoint['session_date_ny'])
    led=ledger.copy();led['session_date_ny']=led.session_date_ny.astype(str)
    if led.session_date_ny.min()<START_SESSION or led.session_date_ny.max()>end_session:
        raise RuntimeError('ledger outside locked prospective window')
    labeler=loadmod('pros_checkpoint_labeler',LABELER);me=loadmod('pros_checkpoint_model',MODEL)
    labels,_=labeler.label_all(raw,led)
    pri=labels[labels.selection_status=='PRIMARY_CONTACT'].copy()
    if not len(pri):raise RuntimeError('no prospective primary contacts')
    t=pd.to_datetime(pri.contact_bar_open_time_utc,utc=True,errors='raise')
    if (t<pd.Timestamp('2026-08-31T12:00:00Z')).any() or (t>=session_end_utc(end_session)).any():
        raise RuntimeError('contact outside locked prospective window')
    m=me.load_model(str(FROZEN_MODEL));scored,qa=me.transform_score(pri,m);ev=me.evaluation(scored);gate=me.prospective_gate(scored,qa,ev)
    y=scored.primary_binary_label.to_numpy(int)
    full=float(roc_auc_score(y,scored.continuous_logit.to_numpy(float)))
    width=float(roc_auc_score(y,scored.zone_width_v.to_numpy(float)))
    width_control={'status':'WIDTH_ONLY_INTERPRETATION_CONTROL','gating':False,'rescue_allowed':False,'width_only_auc':width,'full_model_auc':full,'full_minus_width_auc':full-width,'paired_session_bootstrap_full_minus_width':paired_bootstrap_auc_difference(scored)}
    report={'status':'PROSPECTIVE_CONFIRMATION_SINGLE_CHECKPOINT_EVALUATED','locked_checkpoint':checkpoint,'frozen_dev_model_sha256':EXPECTED_FROZEN_MODEL_SHA256,'model_refit':False,'primary_evaluation':ev,'primary_gate':gate,'feature_transform_qa':qa,'width_interpretation_control':width_control,'production_authorization':'NONE_REQUIRES_POST_PROSPECTIVE_PRO_GATE','pine_modification':'FORBIDDEN'}
    return labels,report


def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-files',nargs='+',required=True);p.add_argument('--ledger-files',nargs='+',required=True);p.add_argument('--checkpoint-lock',required=True);p.add_argument('--output-labels',required=True);p.add_argument('--output-report',required=True);p.add_argument('--output-manifest',required=True);p.add_argument('--authorization-token',default='');a=p.parse_args()
    if a.authorization_token!=GO_EXECUTION_TOKEN:raise RuntimeError('PROSPECTIVE_OUTCOME_OPENING_BLOCKED: GO_PROSPECTIVE_CONFIRMATION_EXECUTION required')
    checkpoint=json.loads(Path(a.checkpoint_lock).read_text())
    raw=pd.concat([pd.read_csv(f,compression='infer') for f in a.raw_files],ignore_index=True)
    if 'time' not in raw and 'timestamp' in raw:raw['time']=pd.to_datetime(raw.timestamp,unit='ms',utc=True)
    elif 'time' in raw:raw['time']=pd.to_datetime(raw.time,utc=True)
    ledger=pd.concat([pd.read_csv(f,compression='infer',float_precision='round_trip') for f in a.ledger_files],ignore_index=True)
    labels,report=evaluate(raw,ledger,checkpoint)
    op=Path(a.output_labels);op.parent.mkdir(parents=True,exist_ok=True);labels.to_csv(op,index=False,compression={'method':'gzip','mtime':0},float_format='%.17g')
    rp=Path(a.output_report);rp.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    man={'status':'PROSPECTIVE_CONFIRMATION_CHECKPOINT_PACKAGE_COMPLETE','labels_sha256':sha256(op),'report_sha256':sha256(rp),'frozen_dev_model_sha256':EXPECTED_FROZEN_MODEL_SHA256,'model_refit':False,'next_authorization':'READY_FOR_PRO_POST_PROSPECTIVE_GATE','production_authorization':'NONE'}
    Path(a.output_manifest).write_text(json.dumps(man,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':man['status'],'primary_gate_pass':report['primary_gate']['pass'],'next_authorization':man['next_authorization']},indent=2))

if __name__=='__main__':main()
