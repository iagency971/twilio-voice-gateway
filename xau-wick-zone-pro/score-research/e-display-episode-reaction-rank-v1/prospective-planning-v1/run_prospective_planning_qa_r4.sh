#!/usr/bin/env bash
set -euo pipefail

PKG="${PKG:-xau-wick-zone-pro/score-research/e-display-episode-reaction-rank-v1}"
PLAN="${PLAN:-$PKG/prospective-planning-v1}"
SOURCE_MANIFEST="${SOURCE_MANIFEST:-xau-wick-zone-pro/cadence-sensitivity/c5-replication-v0-2/XAUUSD_Z4_C5_HISTORICAL_SOURCE_MANIFEST_v0_2.json}"
DRY_SESSION="${DRY_SESSION:-2026-07-15}"
METHOD_COMMIT="${METHOD_COMMIT:?METHOD_COMMIT required}"
RUN_ID="${RUN_ID:?RUN_ID required}"
RUN_ATTEMPT="${RUN_ATTEMPT:-1}"
JOB_NAME="${JOB_NAME:-planning-qa-r4}"
EXPECTED_MODEL_SHA256="72e7548de826e2ae2ba66ddcaaf6b2fa7cd35ada0f5f2cd9db585d9734fd48e1"
EXPECTED_LABELER_SHA256="08ed29422ede890c300073789daa4669a22fbe48b74171c68402310c00aebef8"
EXPECTED_MODEL_EVAL_SHA256="f547853609f16b00080049629f708fc0d4170c54071fd22a99228c807cd6dd2e"

rm -rf /tmp/pros-r4
mkdir -p /tmp/pros-r4/results /tmp/pros-r4/raw /tmp/pros-r4/ref /tmp/pros-r4/dry
R=/tmp/pros-r4/results
RAW=/tmp/pros-r4/raw
REF=/tmp/pros-r4/ref
DRY=/tmp/pros-r4/dry
TOOL="$PLAN/prospective_planning_entry_v1.py"

python - <<'PY'
import hashlib,json,os
from pathlib import Path
pkg=Path(os.environ.get('PKG','xau-wick-zone-pro/score-research/e-display-episode-reaction-rank-v1'))
plan=Path(os.environ.get('PLAN',str(pkg/'prospective-planning-v1')))
gate=json.loads((pkg/'E_DISPLAY_EPISODE_V1_PRO_POST_REPLICATION_GATE.json').read_text())
assert gate['status']=='PRO_POST_REPLICATION_SCIENTIFIC_GATE_PASS'
assert gate['decision']=='GO_PROSPECTIVE_CONFIRMATION_PLANNING'
assert gate['authorization_scope']=='PLANNING_AND_FREEZE_ONLY_NO_PROSPECTIVE_OUTCOME_EXECUTION'
assert gate['next_checkpoint']['current_prospective_execution_authorization']=='NOT_GRANTED'
h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert h(pkg/'dev-freeze-canonical-33264659057/DEV_FROZEN_MODEL.json')=='72e7548de826e2ae2ba66ddcaaf6b2fa7cd35ada0f5f2cd9db585d9734fd48e1'
assert h(pkg/'xau_e_display_episode_reaction_labeler_v1.py')=='08ed29422ede890c300073789daa4669a22fbe48b74171c68402310c00aebef8'
assert h(pkg/'xau_e_display_episode_model_eval_v1.py')=='f547853609f16b00080049629f708fc0d4170c54071fd22a99228c807cd6dd2e'
required=[
 'XAUUSD_E_DISPLAY_EPISODE_PROSPECTIVE_CONFIRMATION_PREREG_v1_0_2026-08-29.md',
 'PROSPECTIVE_CONFIRMATION_POLICY_v1.json',
 'XAUUSD_E_DISPLAY_EPISODE_PROSPECTIVE_PLANNING_QA_ADDENDUM_A_WARMUP_AND_NUMERICAL_TOLERANCE_2026-08-29.md',
 'XAUUSD_E_DISPLAY_EPISODE_PROSPECTIVE_PLANNING_QA_ADDENDUM_B_OPERATIONAL_ATOMICity_AND_ZERO_CONTACT_SESSIONS_2026-08-29.md'.replace('ATOMICity','ATOMICITY'),
 'prospective_planning_tool_v1.py','prospective_planning_entry_v1.py',
 'prospective_checkpoint_evaluator_v1.py','test_prospective_planning_v1.py',
 'prospective_collection_workflow_TEMPLATE_v1.yml','run_prospective_planning_qa_r4.sh'
]
for f in required: assert (plan/f).is_file(),f
assert not (pkg/'prospective-live-v1').exists()
print('R4_AUTHORIZATION_FROZEN_AUTHORITIES_NO_LIVE_STORE_PASS')
PY

python -m pip freeze | sort > "$R/PIP_FREEZE_PROSPECTIVE_PLANNING.txt"
python - <<'PY' > "$R/ENVIRONMENT_PROSPECTIVE_PLANNING.json"
import json,platform,numpy,pandas,scipy,sklearn
out={'python':platform.python_version(),'numpy':numpy.__version__,'pandas':pandas.__version__,'scipy':scipy.__version__,'scikit_learn':sklearn.__version__}
assert out=={'python':'3.11.16','numpy':'2.3.2','pandas':'2.3.1','scipy':'1.16.1','scikit_learn':'1.7.1'},out
print(json.dumps(out,indent=2,sort_keys=True))
PY

python -m py_compile "$PLAN/prospective_planning_tool_v1.py" "$PLAN/prospective_planning_entry_v1.py" "$PLAN/prospective_checkpoint_evaluator_v1.py" "$PLAN/test_prospective_planning_v1.py"
python "$PLAN/test_prospective_planning_v1.py" | tee "$R/SYNTHETIC_PROSPECTIVE_PLANNING_TESTS.json"
if python "$PLAN/prospective_checkpoint_evaluator_v1.py" --raw-files /tmp/no.csv --ledger-files /tmp/no.csv --checkpoint-lock /tmp/no.json --output-labels /tmp/no.gz --output-report /tmp/no-report.json --output-manifest /tmp/no-manifest.json 2>/tmp/pros-r4-blocked.txt; then
  echo 'unauthorized prospective evaluator unexpectedly opened' >&2
  exit 1
fi
grep -q 'PROSPECTIVE_OUTCOME_OPENING_BLOCKED' /tmp/pros-r4-blocked.txt
python - <<'PY'
import importlib.util,json,sys
from pathlib import Path
import pandas as pd
p=Path('xau-wick-zone-pro/score-research/e-display-episode-reaction-rank-v1/prospective-planning-v1/prospective_checkpoint_evaluator_v1.py')
s=importlib.util.spec_from_file_location('pros_r4_ev',p);m=importlib.util.module_from_spec(s);sys.modules['pros_r4_ev']=m;s.loader.exec_module(m)
dates=pd.bdate_range('2026-08-31',periods=90).date.astype(str).tolist()
cp={'session_date_ny':dates[-1],'represented_sessions':90,'represented_session_dates':dates,'model_eligible_primary_contacts':1080}
assert m.validate_checkpoint(cp)==dates
Path('/tmp/pros-r4/results/FUTURE_OUTCOME_OPENING_GUARD_QA.json').write_text(json.dumps({'status':'FUTURE_OUTCOME_OPENING_GUARD_PASS','prospective_outcome_execution_authorized':False,'unauthorized_evaluator_blocked':True,'checkpoint_session_list_validation':True},indent=2,sort_keys=True)+'\n')
PY

python - <<'PY'
import hashlib,json,os,subprocess
from pathlib import Path
manifest=json.load(open(os.environ.get('SOURCE_MANIFEST','xau-wick-zone-pro/cadence-sensitivity/c5-replication-v0-2/XAUUSD_Z4_C5_HISTORICAL_SOURCE_MANIFEST_v0_2.json')))
ix={f"{int(x['year']):04d}-{int(x['month']):02d}":x for x in manifest['files'] if x['side']=='bid'}
root='https://raw.githubusercontent.com/kevingtlin/Market-Data-Lab/main/xauusd/bid/m1/'
meta=[]
for key in ['2026-06','2026-07']:
    x=ix[key];p=Path('/tmp/pros-r4/raw')/x['file']
    subprocess.run(['curl','--fail','--location','--retry','5',root+x['file'],'-o',str(p)],check=True,stdout=subprocess.DEVNULL)
    got=hashlib.sha256(p.read_bytes()).hexdigest();assert got==x['sha256'],(key,got,x['sha256'])
    meta.append({'month':key,'file':x['file'],'sha256':got,'historical_manifest':True})
Path('/tmp/pros-r4/dry/source_meta.json').write_text(json.dumps({'historical_dry_run':True,'files':meta},indent=2,sort_keys=True)+'\n')
print('R4_HISTORICAL_SOURCE_HASH_PASS')
PY

python "$TOOL" ingest-session --files "$RAW"/*.csv --session-date "$DRY_SESSION" --acquired-at 2026-07-15T21:01:00Z --archive-root "$DRY/archive" --manifest "$R/HISTORICAL_DRYRUN_INGEST_QA.json" --source-meta-json "$DRY/source_meta.json" --historical-dry-run
python "$TOOL" z4-session --files "$DRY/archive/warmup/$DRY_SESSION.csv.gz" --session-date "$DRY_SESSION" --output "$DRY/z4_session.pkl" --manifest "$R/HISTORICAL_DRYRUN_Z4_QA.json"

curl --fail --silent --show-error --location -H "Authorization: Bearer ${GH_TOKEN:-}" -H 'Accept: application/vnd.github+json' https://api.github.com/repos/iagency971/twilio-voice-gateway/actions/artifacts/9673431120/zip -o "$REF/july.zip"
echo "7f3d02ddfcff0c00882de7c24d6823d6b652dd915c2886ba0b1d44313aaee6e6  $REF/july.zip" | sha256sum -c -
unzip -q "$REF/july.zip" -d "$REF/july"
python - <<'PY'
import pandas as pd
d=pd.read_pickle('/tmp/pros-r4/ref/july/z4_2026_07.pkl');d['time']=pd.to_datetime(d.time,utc=True);ny=d.time.dt.tz_convert('America/New_York');q=d[(ny.dt.date.astype(str)=='2026-07-15')&(ny.dt.hour>=8)&(ny.dt.hour<17)].copy();q.to_pickle('/tmp/pros-r4/ref/z4_session.pkl')
PY
python "$TOOL" z4-parity --a "$DRY/z4_session.pkl" --b "$REF/z4_session.pkl" --output "$R/HISTORICAL_DRYRUN_Z4_EXACT_PARITY.json"

python - <<'PY'
import pandas as pd
warm=pd.read_csv('/tmp/pros-r4/dry/archive/warmup/2026-07-15.csv.gz');jul=pd.read_csv('/tmp/pros-r4/raw/xauusd_bid_m1_2026_07.csv');jul['time']=pd.to_datetime(jul.timestamp,unit='ms',utc=True);future=jul[(jul.time>=pd.Timestamp('2026-07-15T21:00:00Z'))&(jul.time<pd.Timestamp('2026-07-17T00:00:00Z'))].drop(columns=['time']);pd.concat([warm,future],ignore_index=True).to_csv('/tmp/pros-r4/dry/warmup_plus_future.csv',index=False)
PY
python "$TOOL" z4-session --files "$DRY/warmup_plus_future.csv" --session-date "$DRY_SESSION" --output "$DRY/z4_with_future.pkl" --manifest "$DRY/z4_with_future.json"
python "$TOOL" z4-parity --a "$DRY/z4_session.pkl" --b "$DRY/z4_with_future.pkl" --output "$R/HISTORICAL_DRYRUN_Z4_PREFIX_INVARIANCE.json"

mkdir -p "$DRY/features"
python "$TOOL" feature-session --files "$DRY/archive/warmup/$DRY_SESSION.csv.gz" --z4-pkl "$DRY/z4_session.pkl" --session-date "$DRY_SESSION" --candidates-output "$DRY/features/candidates.csv.gz" --ledger-output "$DRY/features/ledger.csv.gz" --manifest "$R/HISTORICAL_DRYRUN_FEATURE_QA.json"
python "$TOOL" feature-parity --got "$DRY/features/ledger.csv.gz" --canonical "$PKG/E_DISPLAY_EPISODE_LEDGER_V1_REPLICATION.csv.gz" --session-date "$DRY_SESSION" --output "$R/HISTORICAL_DRYRUN_FEATURE_PARITY.json"
python - <<'PY'
import pandas as pd
src=pd.read_csv('xau-wick-zone-pro/score-research/e-display-episode-reaction-rank-v1/E_DISPLAY_EPISODE_LEDGER_V1_REPLICATION.csv.gz',compression='gzip',float_precision='round_trip');t=pd.to_datetime(src.snapshot_time_utc,utc=True);ny=t.dt.tz_convert('America/New_York');q=src[ny.dt.date.astype(str)=='2026-07-15'].copy();q.to_csv('/tmp/pros-r4/dry/canonical_ledger_session.csv.gz',index=False,compression={'method':'gzip','mtime':0},float_format='%.17g')
PY
python "$TOOL" contact-only --files "$RAW/xauusd_bid_m1_2026_07.csv" --ledger "$DRY/canonical_ledger_session.csv.gz" --session-date "$DRY_SESSION" --output "$DRY/contact_only.csv.gz" --manifest "$R/HISTORICAL_DRYRUN_CONTACT_ONLY_QA.json"
python "$TOOL" contact-parity --got "$DRY/contact_only.csv.gz" --frozen-labels "$PKG/replication-freeze-canonical-33266656414/REPLICATION_REACTION_LABELS.csv.gz" --session-date "$DRY_SESSION" --output "$R/HISTORICAL_DRYRUN_CONTACT_ONLY_PARITY.json"

python "$TOOL" width-historical-dryrun --labels "$PKG/replication-freeze-canonical-33266656414/REPLICATION_REACTION_LABELS.csv.gz" --output "$R/HISTORICAL_WIDTH_CONTROL_DRYRUN.json"
python - <<'PY'
import json
from pathlib import Path
d=json.load(open('/tmp/pros-r4/results/HISTORICAL_WIDTH_CONTROL_DRYRUN.json'));ref=json.load(open('xau-wick-zone-pro/score-research/e-display-episode-reaction-rank-v1/POST_REPLICATION_PRO_INTERPRETIVE_DIAGNOSTICS.json'))['REPLICATION']
dw=abs(d['width_only_auc']-ref['width_only_auc']);dfc=abs(d['full_auc']-ref['canonical_full_auc']);dfi=abs(d['full_auc']-ref['independent_recomputed_full_auc'])
assert dfc<1e-12,(dfc,d,ref);assert dw<=5e-7,(dw,d,ref);assert dfi<=5e-7,(dfi,d,ref)
assert d['gating'] is False and d['rescue_allowed'] is False
Path('/tmp/pros-r4/results/HISTORICAL_WIDTH_CONTROL_NUMERICAL_QA.json').write_text(json.dumps({'status':'WIDTH_CONTROL_HISTORICAL_NUMERICAL_QA_PASS','canonical_full_auc_tolerance':1e-12,'historical_cross_serialization_tolerance':5e-7,'canonical_full_auc_delta':dfc,'independent_full_auc_cross_serialization_delta':dfi,'width_auc_cross_serialization_delta':dw,'prospective_gate_tolerance':False},indent=2,sort_keys=True)+'\n')
PY

python - <<'PY'
import json
from pathlib import Path
t=Path('xau-wick-zone-pro/score-research/e-display-episode-reaction-rank-v1/prospective-planning-v1/prospective_collection_workflow_TEMPLATE_v1.yml').read_text()
required=['concurrency:','cancel-in-progress: false','raw.githubusercontent.com/kevingtlin/Market-Data-Lab/{head}/','upstream_blob_sha','source_sha256',"'rows':rows",'append first-seen prospective M1 evidence','PROSPECTIVE_SOURCE_REVISION_RECORDED_CANONICAL_UNCHANGED','contacts/$S.json','planning_seal_sha256','collector_template_sha256']
for x in required:assert x in t,x
assert 'if test -s "$LIVE/archive/manifests/$S.json"; then continue' not in t
assert 'prospective_checkpoint_evaluator_v1.py" --' not in t
assert 'xau_e_display_episode_reaction_labeler_v1.py" --' not in t
assert t.index('append first-seen prospective M1 evidence')<t.index('z4-session --files')
Path('/tmp/pros-r4/results/COLLECTOR_STATIC_FIREWALL_QA.json').write_text(json.dumps({'status':'COLLECTOR_STATIC_FIREWALL_QA_PASS','single_concurrency':True,'exact_commit_source_binding':True,'source_blob_sha256_bytes_rows_recorded':True,'first_acceptance_persisted_before_downstream':True,'incomplete_session_resume':True,'revision_recheck':True,'valid_zero_contact_sessions_represented':True,'reaction_labeler_invocation':False,'checkpoint_evaluator_invocation':False,'collector_outputs_outcome_blind_only':True},indent=2,sort_keys=True)+'\n')
PY

python - <<'PY'
import hashlib,json,os
from pathlib import Path
import pandas as pd
r=Path('/tmp/pros-r4/results');plan=Path(os.environ.get('PLAN','xau-wick-zone-pro/score-research/e-display-episode-reaction-rank-v1/prospective-planning-v1'));pkg=plan.parent
assert pd.Timestamp.now(tz='UTC')<pd.Timestamp('2026-08-31T12:00:00Z')
required=['SYNTHETIC_PROSPECTIVE_PLANNING_TESTS.json','FUTURE_OUTCOME_OPENING_GUARD_QA.json','HISTORICAL_DRYRUN_INGEST_QA.json','HISTORICAL_DRYRUN_Z4_QA.json','HISTORICAL_DRYRUN_Z4_EXACT_PARITY.json','HISTORICAL_DRYRUN_Z4_PREFIX_INVARIANCE.json','HISTORICAL_DRYRUN_FEATURE_QA.json','HISTORICAL_DRYRUN_FEATURE_PARITY.json','HISTORICAL_DRYRUN_CONTACT_ONLY_QA.json','HISTORICAL_DRYRUN_CONTACT_ONLY_PARITY.json','HISTORICAL_WIDTH_CONTROL_DRYRUN.json','HISTORICAL_WIDTH_CONTROL_NUMERICAL_QA.json','COLLECTOR_STATIC_FIREWALL_QA.json']
for f in required:assert (r/f).is_file(),f
methods=['XAUUSD_E_DISPLAY_EPISODE_PROSPECTIVE_CONFIRMATION_PREREG_v1_0_2026-08-29.md','PROSPECTIVE_CONFIRMATION_POLICY_v1.json','XAUUSD_E_DISPLAY_EPISODE_PROSPECTIVE_PLANNING_QA_ADDENDUM_A_WARMUP_AND_NUMERICAL_TOLERANCE_2026-08-29.md','XAUUSD_E_DISPLAY_EPISODE_PROSPECTIVE_PLANNING_QA_ADDENDUM_B_OPERATIONAL_ATOMICITY_AND_ZERO_CONTACT_SESSIONS_2026-08-29.md','prospective_planning_tool_v1.py','prospective_planning_entry_v1.py','prospective_checkpoint_evaluator_v1.py','test_prospective_planning_v1.py','prospective_collection_workflow_TEMPLATE_v1.yml','run_prospective_planning_qa_r4.sh']
h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ing=json.load(open(r/'HISTORICAL_DRYRUN_INGEST_QA.json'));z4=json.load(open(r/'HISTORICAL_DRYRUN_Z4_QA.json'));feat=json.load(open(r/'HISTORICAL_DRYRUN_FEATURE_QA.json'));contact=json.load(open(r/'HISTORICAL_DRYRUN_CONTACT_ONLY_QA.json'))
out={'status':'PROSPECTIVE_PLANNING_QA_R4_PASS','decision':'READY_FOR_PRO_PRE_PROSPECTIVE_EXECUTION_GATE','prospective_start_session_ny':'2026-08-31','prospective_start_utc':'2026-08-31T12:00:00Z','minimum_sessions':90,'minimum_model_eligible_primary_contacts':1000,'single_checkpoint':True,'prospective_outcomes_opened':False,'prospective_outcome_execution_authorized':False,'pine_production_modified':False,'method_commit':os.environ['METHOD_COMMIT'],'workflow_run_id':os.environ['RUN_ID'],'workflow_run_attempt':os.environ.get('RUN_ATTEMPT','1'),'job_name':os.environ.get('JOB_NAME','planning-qa-r4'),'frozen_dev_model_sha256':h(pkg/'dev-freeze-canonical-33264659057/DEV_FROZEN_MODEL.json'),'frozen_reaction_labeler_sha256':h(pkg/'xau_e_display_episode_reaction_labeler_v1.py'),'frozen_model_eval_sha256':h(pkg/'xau_e_display_episode_model_eval_v1.py'),'method_hashes':{f:h(plan/f) for f in methods},'qa_evidence_hashes':{f:h(r/f) for f in required},'historical_dryrun':{'session_date_ny':'2026-07-15','session_rows':ing['session_rows'],'warmup_rows':ing['warmup_rows'],'z4_rows':z4['rows'],'feature_rows':feat['feature_rows'],'episodes':contact['episodes'],'primary_contacts':contact['primary_contacts'],'model_eligible_primary_contacts':contact['model_eligible_primary_contacts']},'operational_hardening':{'atomic_exact_commit_source':True,'immediate_first_acceptance_persistence':True,'resume_after_downstream_failure':True,'revision_monitoring_and_dedup':True,'single_concurrency':True,'valid_zero_contact_sessions_represented':True,'checkpoint_session_list_locked':True,'final_contact_counter_exact_parity_required':True}}
(r/'PROSPECTIVE_PLANNING_QA_R4.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':out['status'],'decision':out['decision']},indent=2))
PY

echo 'PROSPECTIVE_PLANNING_QA_R4_COMPLETE'
