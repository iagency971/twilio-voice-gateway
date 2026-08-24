import argparse, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
from xau_wick_zone_greedy_lineage_audit import eligible_from_files, greedy_states
from xau_wick_zone_lineage_cap_audit_fast import capped

p=argparse.ArgumentParser();p.add_argument('--pkl',required=True);p.add_argument('--files',nargs='+',required=True);p.add_argument('--output',required=True);a=p.parse_args()
Z=pd.read_pickle(a.pkl).reset_index(drop=True);Z['time']=pd.to_datetime(Z.time,utc=True)
eligible=eligible_from_files(a.files)
G,_=greedy_states(Z,eligible)
G['lineage_id']=G['lineage_id_greedy'].astype('int64')
C=capped(G,96)
C.to_pickle(a.output)
print({'rows':len(C),'landmarks':int(C.landmark_i.nunique()),'lineages_greedy':int(C.lineage_id.nunique()),'cap':96},flush=True)
