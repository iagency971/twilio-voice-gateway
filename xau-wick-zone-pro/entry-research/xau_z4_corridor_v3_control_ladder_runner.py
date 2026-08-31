#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
V2=HERE.parent/'score-research'/'e-zone-score-buy-us-v2'
LADDER=json.load(open(HERE/'XAUUSD_Z4_CORRIDOR_V3_CONTROL_LADDER_PREDECL_2026-08-31.json'))
WINDOWS={
 'DEV':('2019-11','2021-12','2020-01-01T00:00:00Z','2022-01-01T00:00:00Z'),
 'VAL':('2021-11','2022-12','2022-01-01T00:00:00Z','2023-01-01T00:00:00Z'),
 'REP':('2022-11','2023-12','2023-01-01T00:00:00Z','2024-01-01T00:00:00Z'),
}

def args():
 p=argparse.ArgumentParser();p.add_argument('--data-dir',required=True);p.add_argument('--work-dir',required=True);return p.parse_args()
def run(cmd,check=True):
 print('+',' '.join(map(str,cmd)),flush=True);return subprocess.run(list(map(str,cmd)),check=check)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def files_for(data,a,b):return [Path(data)/f'xauusd_bid_m1_{p.year:04d}_{p.month:02d}.csv' for p in pd.period_range(a,b,freq='M')]

def build_z4(data,root,key):
 a,b,_,_=WINDOWS[key];o=root/'Z4'/key;o.mkdir(parents=True,exist_ok=True);fs=files_for(data,a,b)
 z=o/'z4.pkl';run([sys.executable,V2/'xau_z4_geometry_only_v2.py','--files',*fs,'--output-pkl',z,'--output-csv',o/'z4.csv','--manifest',o/'z4_manifest.json','--tag',f'CORRIDOR_V3_LADDER_{key}']);return fs,z,o

def eval_design(data,root,design,z4map):
 droot=root/'DESIGNS'/design;droot.mkdir(parents=True,exist_ok=True);summary={'design':design,'windows':{},'future_v3_reaction_outcomes_used':False}
 allpass=True
 for key in ['DEV','VAL','REP']:
  _,_,start,end=WINDOWS[key];fs,z4,_=z4map[key];o=droot/key;o.mkdir(parents=True,exist_ok=True)
  run([sys.executable,HERE/'xau_z4_corridor_v3_preoutcome_control_ladder.py','--control-design',design,'--files',*fs,'--z4-pkl',z4,'--target-start',start,'--target-end',end,'--episodes-out',o/'episodes.csv.gz','--candidates-out',o/'candidates.csv.gz','--controls-out',o/'controls.csv.gz','--candidate-contacts-out',o/'candidate_contacts.csv.gz','--control-contacts-out',o/'control_contacts.csv.gz','--manifest',o/'manifest.json','--tag',f'{key}_{design}'])
  rc=run([sys.executable,HERE/'xau_z4_corridor_v3_preoutcome_qa.py','--phase',key,'--episodes',o/'episodes.csv.gz','--candidates',o/'candidates.csv.gz','--controls',o/'controls.csv.gz','--candidate-contacts',o/'candidate_contacts.csv.gz','--control-contacts',o/'control_contacts.csv.gz','--manifest',o/'manifest.json','--output',o/'preoutcome_qa.json'],check=False).returncode
  q=json.load(open(o/'preoutcome_qa.json'));passed=(rc==0 and q.get('status')=='Z4_CORRIDOR_V3_PREOUTCOME_QA_PASS');allpass=allpass and passed
  summary['windows'][key]={'pass':passed,'candidate_contacts':q.get('candidate_contacts'),'matched_ge2':q.get('matched_candidate_contacts_ge2_controls'),'matched_fraction':q.get('matched_fraction'),'matched_sessions':q.get('matched_sessions'),'max_abs_smd':q.get('max_abs_smd'),'checks':q.get('checks',{})}
 (droot/'design_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');summary['all_windows_pass']=allpass;return allpass,summary

def main():
 a=args();data=Path(a.data_dir);root=Path(a.work_dir);root.mkdir(parents=True,exist_ok=True)
 assert LADDER['future_v3_reaction_outcomes_opened'] is False
 run([sys.executable,HERE/'test_xau_z4_corridor_v3_preoutcome.py'])
 z4map={k:build_z4(data,root,k) for k in ['DEV','VAL','REP']}
 trials=[];selected=None
 for rec in LADDER['designs']:
  design=rec['id'];ok,s=eval_design(data,root,design,z4map);s['all_windows_pass']=ok;trials.append(s)
  if ok:selected=design;break
 result={'status':'Z4_CORRIDOR_V3_CONTROL_LADDER_PASS' if selected else 'Z4_CORRIDOR_V3_CONTROL_LADDER_NO_PASS','selected_design':selected,'selection_rule':LADDER['selection_rule'],'future_v3_reaction_outcomes_used':False,'rep_2023_reaction_outcomes_opened':False,'trials':trials}
 (root/'V3_CONTROL_LADDER_SELECTION.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 if not selected:raise RuntimeError(result['status'])
 # Promote selected preoutcome evidence without recomputation.
 sel=root/'DESIGNS'/selected;final=root/'SELECTED';final.mkdir(parents=True,exist_ok=True)
 evidence={}
 for key in ['DEV','VAL','REP']:
  src=sel/key;dst=final/key;shutil.copytree(src,dst,dirs_exist_ok=True)
  shutil.copy2(root/'Z4'/key/'z4_manifest.json',dst/'z4_manifest.json')
  for n in ['z4_manifest.json','manifest.json','preoutcome_qa.json','episodes.csv.gz','candidates.csv.gz','controls.csv.gz','candidate_contacts.csv.gz','control_contacts.csv.gz']:
   evidence[str(dst/n)]=sha(dst/n)
 code_names=['XAUUSD_Z4_CORRIDOR_RETRACE_LEVEL_REACTION_V3_PREREG_2026-08-31.md','XAUUSD_Z4_CORRIDOR_RETRACE_LEVEL_REACTION_V3_PREREG_ADDENDUM_A_EXACT_CAUSAL_RULES_2026-08-31.md','XAUUSD_Z4_CORRIDOR_RETRACE_LEVEL_REACTION_V3_PREREG_ADDENDUM_B_DYNAMIC_CONTROL_NEUTRALITY_2026-08-31.md','XAUUSD_Z4_CORRIDOR_RETRACE_LEVEL_REACTION_V3_PREREG_ADDENDUM_C_GAP_PASS_RULE_2026-08-31.md','XAUUSD_Z4_CORRIDOR_RETRACE_LEVEL_REACTION_V3_PRO_GATE.json','XAUUSD_Z4_CORRIDOR_V3_CONTROL_LADDER_PREDECL_2026-08-31.json','xau_z4_corridor_v3_preoutcome.py','xau_z4_corridor_v3_preoutcome_control_ladder.py','xau_z4_corridor_v3_preoutcome_qa.py','xau_z4_corridor_v3_control_ladder_runner.py','test_xau_z4_corridor_v3_preoutcome.py']
 freeze={'status':'Z4_CORRIDOR_V3_COMPLETE_PREOUTCOME_FREEZE_PASS','selected_control_design':selected,'v3_reaction_outcomes_opened':False,'rep_2023_reaction_outcomes_opened':False,'quality_gates_changed':False,'candidate_geometry_changed':False,'control_ladder_selection_sha256':sha(root/'V3_CONTROL_LADDER_SELECTION.json'),'data_input_manifest_sha256':sha(data/'DATA_INPUT_MANIFEST.json'),'code_sha256':{n:sha(HERE/n) for n in code_names},'evidence_sha256':evidence,'next_action':'PRO_REVIEW_PREOUTCOME_SELECTED_CONTROL_DESIGN_BEFORE_DEV_REACTION_OPENING'}
 (root/'V3_PREOUTCOME_FREEZE.json').write_text(json.dumps(freeze,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':freeze['status'],'selected_control_design':selected,'trials':[{ 'design':t['design'],'all_windows_pass':t['all_windows_pass']} for t in trials]},indent=2))
if __name__=='__main__':main()
