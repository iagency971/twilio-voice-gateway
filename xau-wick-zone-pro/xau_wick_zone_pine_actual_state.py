import argparse,sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
from xau_wick_zone_greedy_lineage_audit import eligible_from_files,greedy_states
p=argparse.ArgumentParser();p.add_argument('--pkl',required=True);p.add_argument('--files',nargs='+',required=True);p.add_argument('--output',required=True);a=p.parse_args()
Z=pd.read_pickle(a.pkl).reset_index(drop=True);Z['time']=pd.to_datetime(Z.time,utc=True)
G,_=greedy_states(Z,eligible_from_files(a.files));G['lineage_id']=G['lineage_id_greedy'].astype('int64');G.to_pickle(a.output)
print({'rows':len(G),'landmarks':int(G.landmark_i.nunique()),'lineages_greedy':int(G.lineage_id.nunique()),'state':'full carried from available sequence'},flush=True)
