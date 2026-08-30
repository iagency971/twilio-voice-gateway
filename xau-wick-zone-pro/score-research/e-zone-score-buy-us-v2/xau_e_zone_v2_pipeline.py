#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
import numpy as np,pandas as pd

HERE=Path(__file__).resolve().parent
V1=HERE.parent/'e-display-episode-reaction-rank-v1'
TOKEN='GO_E_ZONE_SCORE_BUY_US_V2_SEQUENTIAL_HISTORICAL_EXECUTION'
WINDOWS={
 'DEV':('2019-11','2021-12','2020-01-01T00:00:00Z','2022-01-01T00:00:00Z','DEVELOPMENT_V2'),
 'VAL':('2021-11','2022-12','2022-01-01T00:00:00Z','2023-01-01T00:00:00Z','VALIDATION_V2'),
 'REP':('2022-11','2023-12','2023-01-01T00:00:00Z','2024-01-01T00:00:00Z','REPLICATION_V2'),
}
CODE_FILES=['xau_z4_geometry_only_v2.py','xau_e_zone_v2_instrument.py','xau_e_zone_v2_placebos.py','xau_e_zone_v2_labeler.py','xau_e_zone_v2_stats.py','xau_e_zone_v2_zone_test.py','xau_e_zone_v2_score_model.py','xau_e_zone_v2_preoutcome_qa.py','test_xau_e_zone_v2.py','requirements-lock.txt','E_ZONE_SCORE_BUY_US_V2_PRO_GATE.json','E_ZONE_SCORE_BUY_US_V2_FEATURE_REGISTRY.json','XAUUSD_E_ZONE_SCORE_BUY_US_PRO_PROTOCOL_V2_2026-08-29.md']

def args():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=['PREOUTCOME','DEV','FORWARD'],required=True);p.add_argument('--data-dir',required=True);p.add_argument('--work-dir',required=True);return p.parse_args()
def run(cmd):
 print('+',' '.join(map(str,cmd)),flush=True);subprocess.run(list(map(str,cmd)),check=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def files_for(data,a,b):
 ps=pd.period_range(a,b,freq='M');return [Path(data)/f'xauusd_bid_m1_{p.year:04d}_{p.month:02d}.csv' for p in ps]
def merge_m1(fs,out):
 frames=[]
 for f in fs:frames.append(pd.read_csv(f))
 d=pd.concat(frames,ignore_index=True).sort_values('timestamp').drop_duplicates('timestamp');d.to_csv(out,index=False,compression={'method':'gzip','mtime':0})
def py(name):return HERE/name
def outdir(work,k):p=Path(work)/k;p.mkdir(parents=True,exist_ok=True);return p

def prepare_window(data,work,k):
 a,b,start,end,decl=WINDOWS[k];o=outdir(work,k);fs=files_for(data,a,b)
 z4=o/'z4.pkl';run([sys.executable,py('xau_z4_geometry_only_v2.py'),'--files',*fs,'--output-pkl',z4,'--output-csv',o/'z4.csv','--manifest',o/'z4_manifest.json','--tag',k])
 run([sys.executable,py('xau_e_zone_v2_instrument.py'),'--files',*fs,'--z4-pkl',z4,'--output-features',o/'features.csv.gz','--output-display-all',o/'display_all.csv.gz','--output-full-pool',o/'full_pool.csv.gz','--output-context',o/'context.csv.gz','--manifest',o/'instrument_manifest.json','--target-start',start,'--target-end',end])
 run([sys.executable,py('xau_e_zone_v2_placebos.py'),'--features',o/'features.csv.gz','--full-pool',o/'full_pool.csv.gz','--context',o/'context.csv.gz','--output',o/'placebos.csv.gz','--matching-table',o/'matching.csv.gz','--manifest',o/'placebo_manifest.json'])
 run([sys.executable,py('xau_e_zone_v2_preoutcome_qa.py'),'--features',o/'features.csv.gz','--display-all',o/'display_all.csv.gz','--full-pool',o/'full_pool.csv.gz','--context',o/'context.csv.gz','--placebos',o/'placebos.csv.gz','--matching',o/'matching.csv.gz','--instrument-manifest',o/'instrument_manifest.json','--output',o/'preoutcome_qa.json'])
 merge_m1(fs,o/'m1.csv.gz')
 return o

def parity(data,work):
 o=outdir(work,'PARITY');fs=files_for(data,'2024-06','2026-07');run([sys.executable,py('xau_z4_geometry_only_v2.py'),'--files',*fs,'--output-pkl',o/'z4.pkl','--output-csv',o/'z4.csv','--manifest',o/'z4_manifest.json','--tag','PARITY'])
 ref=V1/'E_DISPLAY_PROVENANCE_V1_24M.csv.gz'
 run([sys.executable,py('xau_e_zone_v2_instrument.py'),'--files',*fs,'--z4-pkl',o/'z4.pkl','--output-features',o/'features.csv.gz','--output-display-all',o/'display_all.csv.gz','--output-full-pool',o/'full_pool.csv.gz','--output-context',o/'context.csv.gz','--manifest',o/'instrument_manifest.json','--target-start','2024-08-01T00:00:00Z','--target-end','2026-08-01T00:00:00Z','--reference-v04-csv',ref])
 m=json.load(open(o/'instrument_manifest.json'))
 if not m['geometry_parity']['pass']:raise RuntimeError('PARITY_FAIL')
 return o

def prefix_invariance(data,work):
 o=outdir(work,'PREFIX');fs=files_for(data,'2021-11','2022-02');run([sys.executable,py('xau_z4_geometry_only_v2.py'),'--files',*fs,'--output-pkl',o/'z4.pkl','--output-csv',o/'z4.csv','--manifest',o/'z4_manifest.json','--tag','PREFIX'])
 run([sys.executable,py('xau_e_zone_v2_instrument.py'),'--files',*fs,'--z4-pkl',o/'z4.pkl','--output-features',o/'features.csv.gz','--output-display-all',o/'display_all.csv.gz','--output-full-pool',o/'full_pool.csv.gz','--output-context',o/'context.csv.gz','--manifest',o/'instrument_manifest.json','--target-start','2022-01-01T00:00:00Z','--target-end','2022-02-01T00:00:00Z'])
 pre=pd.read_csv(o/'features.csv.gz',float_precision='round_trip');full=pd.read_csv(Path(work)/'VAL/features.csv.gz',float_precision='round_trip');pre['snapshot_time_utc']=pd.to_datetime(pre.snapshot_time_utc,utc=True);full['snapshot_time_utc']=pd.to_datetime(full.snapshot_time_utc,utc=True);full=full[(full.snapshot_time_utc>=pd.Timestamp('2022-01-01T00:00:00Z'))&(full.snapshot_time_utc<pd.Timestamp('2022-02-01T00:00:00Z'))]
 cols=['snapshot_time_utc','display_slot_rank','current_family','center','zlo','zhi','zone_width_v','display_persistence_c5','native_evidence_raw','confluence_count_e_families','center_stability_3_c5','distance_v','trend15_v','trend60_v','trend240_v']
 pre=pre[cols].sort_values(cols[:2]).reset_index(drop=True);full=full[cols].sort_values(cols[:2]).reset_index(drop=True);bad={}
 if len(pre)!=len(full):bad['row_count']=[len(pre),len(full)]
 else:
  for c in cols:
   if c in {'snapshot_time_utc','current_family'}:neq=pre[c].astype(str).to_numpy()!=full[c].astype(str).to_numpy()
   elif c=='display_slot_rank':neq=pre[c].to_numpy()!=full[c].to_numpy()
   else:neq=pre[c].to_numpy(float)!=full[c].to_numpy(float)
   if np.any(neq):bad[c]=int(np.sum(neq))
 r={'status':'E_ZONE_V2_PREFIX_INVARIANCE_PASS' if not bad else 'E_ZONE_V2_PREFIX_INVARIANCE_FAIL','rows':len(pre),'mismatches':bad};(o/'prefix_invariance.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
 if bad:raise RuntimeError(r)

def freeze_pre(data,work):
 paths=[]
 for k in ['DEV','VAL','REP']:
  o=Path(work)/k
  for n in ['features.csv.gz','display_all.csv.gz','full_pool.csv.gz','context.csv.gz','placebos.csv.gz','matching.csv.gz','preoutcome_qa.json','instrument_manifest.json','placebo_manifest.json','z4_manifest.json']:paths.append(o/n)
 paths += [Path(work)/'PARITY/instrument_manifest.json',Path(work)/'PREFIX/prefix_invariance.json',Path(data)/'DATA_INPUT_MANIFEST.json']
 codes={n:sha(HERE/n) for n in CODE_FILES};files={str(p):sha(p) for p in paths}
 m={'status':'E_ZONE_SCORE_BUY_US_V2_PREOUTCOME_FREEZE_PASS','authorization_token':TOKEN,'outcomes_opened':False,'code_sha256':codes,'evidence_sha256':files,'windows':WINDOWS,'v1_overlap_reference':str(V1/'E_DISPLAY_PROVENANCE_V1_24M.csv.gz'),'v1_overlap_reference_sha256':sha(V1/'E_DISPLAY_PROVENANCE_V1_24M.csv.gz')}
 Path(work,'PRE_OUTCOME_FREEZE.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')

def label(k,work):
 o=Path(work)/k;decl=WINDOWS[k][4]
 for kind,path,name in [('REAL',o/'features.csv.gz','real'),('PLACEBO',o/'placebos.csv.gz','placebo')]:
  run([sys.executable,py('xau_e_zone_v2_labeler.py'),'--m1',o/'m1.csv.gz','--paths',path,'--kind',kind,'--window',decl,'--authorization-token',TOKEN,'--output',o/f'{name}_labels.csv.gz','--manifest',o/f'{name}_label_manifest.json'])
 run([sys.executable,py('xau_e_zone_v2_zone_test.py'),'--real-labels',o/'real_labels.csv.gz','--placebo-labels',o/'placebo_labels.csv.gz','--matching-table',o/'matching.csv.gz','--phase',decl,'--report',o/'zone_test.json','--matched-output',o/'matched_sets.csv'])

def dev_stage(work):
 label('DEV',work);o=Path(work)/'DEV';run([sys.executable,py('xau_e_zone_v2_score_model.py'),'--phase','DEV_FIT','--labels',o/'real_labels.csv.gz','--model-json',Path(work)/'DEV_FROZEN_MODEL.json','--report-json',o/'score_report.json','--scored-output',o/'scored.csv.gz','--authorization-token',TOKEN])
 paths=[o/x for x in ['real_labels.csv.gz','placebo_labels.csv.gz','zone_test.json','matched_sets.csv','score_report.json','scored.csv.gz']]+[Path(work)/'DEV_FROZEN_MODEL.json',Path(work)/'PRE_OUTCOME_FREEZE.json']
 m={'status':'E_ZONE_SCORE_BUY_US_V2_DEV_FREEZE_PASS','model_refit_later':'FORBIDDEN','sha256':{str(p):sha(p) for p in paths}};Path(work,'DEV_FREEZE.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')

def evaluate(k,work):
 label(k,work);o=Path(work)/k;run([sys.executable,py('xau_e_zone_v2_score_model.py'),'--phase','EVALUATE','--labels',o/'real_labels.csv.gz','--model-json',Path(work)/'DEV_FROZEN_MODEL.json','--report-json',o/'score_report.json','--scored-output',o/'scored.csv.gz','--authorization-token',TOKEN])
 z=json.load(open(o/'zone_test.json'));s=json.load(open(o/'score_report.json'));return bool(z['pooled_zone_pass'] and s['evaluation']['score_pass'])
def final(work,validation_pass,rep_opened):
 evidence=[]
 for k in ['DEV','VAL']+(['REP'] if rep_opened else []):
  o=Path(work)/k
  for n in ['real_labels.csv.gz','placebo_labels.csv.gz','real_label_manifest.json','placebo_label_manifest.json','zone_test.json','matched_sets.csv','score_report.json','scored.csv.gz']:evidence.append(o/n)
 evidence += [Path(work)/'PRE_OUTCOME_FREEZE.json',Path(work)/'DEV_FREEZE.json',Path(work)/'DEV_FROZEN_MODEL.json']
 status='READY_FOR_PRO_E_ZONE_SCORE_BUY_US_V2_FINAL_GATE' if validation_pass else 'READY_FOR_PRO_E_ZONE_SCORE_BUY_US_V2_FINAL_GATE_VALIDATION_FAILED_REPLICATION_CLOSED'
 m={'status':status,'validation_continuation_pass':validation_pass,'replication_outcomes_opened':rep_opened,'model_refit_after_DEV':False,'evidence_sha256':{str(p):sha(p) for p in evidence},'pine_modification':'FORBIDDEN_PENDING_FINAL_PRO_GATE','production_authorization':'NONE'}
 Path(work,'FINAL_FREEZE.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n');(HERE/'FINAL_PRO_GATE_REQUEST.json').write_text(json.dumps({'status':status,'request':'Final Pro adjudication of pooled E zones, E1, E2, E3 and width-neutral score','final_freeze_path':'FINAL_FREEZE.json','pine_modification':'FORBIDDEN_PENDING_FINAL_PRO_GATE'},indent=2,sort_keys=True)+'\n')
 (HERE/'STATUS.md').write_text(f'# E-zone validity and width-neutral score V2 — status\n\n**Scope:** XAUUSD M1 / BUY / US / E1-E2-E3\n\n- Current status: `{status}`\n- Validation continuation gate: `{validation_pass}`\n- Replication outcomes opened: `{rep_opened}`\n- Model refit after DEV: `False`\n- Pine modification: `FORBIDDEN_PENDING_FINAL_PRO_GATE`\n- Production: `NONE`\n\nReturn to **Pro** for the final scientific gate.\n')
def main():
 a=args();data=Path(a.data_dir);work=Path(a.work_dir);work.mkdir(parents=True,exist_ok=True)
 if a.stage=='PREOUTCOME':
  run([sys.executable,py('test_xau_e_zone_v2.py')])
  for k in ['DEV','VAL','REP']:prepare_window(data,work,k)
  parity(data,work);prefix_invariance(data,work);freeze_pre(data,work);print('E_ZONE_V2_PREOUTCOME_STAGE_PASS')
 elif a.stage=='DEV':dev_stage(work);print('E_ZONE_V2_DEV_STAGE_PASS')
 else:
  vp=evaluate('VAL',work);rep=False
  if vp:rep=True;evaluate('REP',work)
  final(work,vp,rep);print(json.dumps({'validation_continuation_pass':vp,'replication_opened':rep},indent=2))
if __name__=='__main__':main()
