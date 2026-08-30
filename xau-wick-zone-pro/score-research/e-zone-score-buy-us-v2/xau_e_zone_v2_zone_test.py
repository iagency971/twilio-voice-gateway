#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
import xau_e_zone_v2_stats as st

BAL=[('zone_width_v','donor_zone_width_v','recipient_transplanted_zone_width_v'),('distance_v','donor_distance_v','recipient_distance_v'),('log_v_snapshot','donor_log_v_snapshot','recipient_log_v_snapshot'),('minute_of_session','donor_minute_of_session','recipient_minute_of_session'),('nearest_upper_z4_dist_v','donor_nearest_upper_z4_dist_v','recipient_nearest_upper_z4_dist_v'),('trend15_v','donor_trend15_v','recipient_trend15_v'),('trend60_v','donor_trend60_v','recipient_trend60_v'),('trend240_v','donor_trend240_v','recipient_trend240_v')]

def args():
 p=argparse.ArgumentParser();p.add_argument('--real-labels',required=True);p.add_argument('--placebo-labels',required=True);p.add_argument('--matching-table',required=True);p.add_argument('--phase',required=True);p.add_argument('--report',required=True);p.add_argument('--matched-output',required=True);return p.parse_args()

def read(p):return pd.read_csv(p,compression='infer',float_precision='round_trip')

def sets(real,pl,match):
 rr=real[real.selection_status=='PRIMARY_CONTACT'][['display_episode_id','session_date_ny','display_slot_rank','primary_binary_label']].copy()
 pp=pl[pl.selection_status=='PRIMARY_CONTACT'][['placebo_id','donor_episode_id','recipient_session_date_ny','primary_binary_label']].copy()
 mp=match.merge(pp,on=['placebo_id','donor_episode_id','recipient_session_date_ny'],how='left');by={k:g for k,g in mp.groupby('donor_episode_id',sort=False)};rows=[]
 for _,r in rr.iterrows():
  g=by.get(str(r.display_episode_id));
  if g is None:continue
  v=g[g.primary_binary_label.notna()].copy()
  if len(v)<2:continue
  rows.append({'display_episode_id':str(r.display_episode_id),'donor_session_date_ny':str(r.session_date_ny),'display_slot_rank':int(r.display_slot_rank),'real_y':int(r.primary_binary_label),'placebo_mean':float(v.primary_binary_label.mean()),'effect':float(int(r.primary_binary_label)-v.primary_binary_label.mean()),'control_n':int(len(v)),'controls_json':json.dumps([(str(x.recipient_session_date_ny),int(x.primary_binary_label)) for _,x in v.iterrows()])})
 return rr,mp,pd.DataFrame(rows)

def multiway_boot(d,slot=None):
 x=d if slot is None else d[d.display_slot_rank==slot]
 if not len(x):return {'valid':0,'ci95':[None,None],'p_one_sided':None}
 donors=sorted(x.donor_session_date_ny.unique()); recips=sorted({s for z in x.controls_json for s,_ in json.loads(z)});rng=np.random.default_rng(st.SEED+(0 if slot is None else int(slot)));vals=[]
 for _ in range(st.BOOT_N):
  wd={s:int(rng.poisson(1)) for s in donors};wr={s:int(rng.poisson(1)) for s in recips};num=den=0.0
  for _,r in x.iterrows():
   a=wd[str(r.donor_session_date_ny)]
   if a<=0:continue
   cs=json.loads(r.controls_json);ys=[];ws=[]
   for rs,y in cs:
    w=wr[rs]
    if w>0:ys.append(float(y));ws.append(float(w))
   if not ws:continue
   num+=a*(float(r.real_y)-float(np.average(ys,weights=ws)));den+=a
  if den>0:vals.append(num/den)
 ok=len(vals)>=st.MIN_VALID;arr=np.asarray(vals,float)
 return {'requested':st.BOOT_N,'valid':len(vals),'minimum_valid':st.MIN_VALID,'ci95':[float(np.quantile(arr,.025)),float(np.quantile(arr,.975))] if ok else [None,None],'p_one_sided':float((1+np.sum(arr<=0))/(1+len(arr))) if len(arr) else None}

def main():
 a=args();real=read(a.real_labels);pl=read(a.placebo_labels);match=read(a.matching_table);rr,mp,d=sets(real,pl,match);Path(a.matched_output).parent.mkdir(parents=True,exist_ok=True);d.to_csv(a.matched_output,index=False)
 frac=float(len(d)/len(rr)) if len(rr) else 0.0;bal={}
 for n,dc,rc in BAL:
  v=st.smd(mp[dc],mp[rc]);bal[n]={'smd':v,'abs_smd':abs(v) if v is not None else None}
 q={'minimum_primary_matched_real_contacts':len(d)>=1000,'minimum_donor_sessions':(d.donor_session_date_ny.nunique() if len(d) else 0)>=90,'fraction_real_contacts_with_2plus_controls':frac>=.70,'balance_all_abs_smd_le_010':all(x['abs_smd'] is not None and x['abs_smd']<=.10 for x in bal.values())}
 b=multiway_boot(d);effect=float(d.effect.mean()) if len(d) else None;pooled=bool(effect is not None and effect>0 and b['ci95'][0] is not None and b['ci95'][0]>0 and all(q.values()))
 slots={};ps={}
 for s in (1,2,3):
  g=d[d.display_slot_rank==s];bb=multiway_boot(d,s);e=float(g.effect.mean()) if len(g) else None;slots[str(s)]={'matched_real_contacts':int(len(g)),'donor_sessions':int(g.donor_session_date_ny.nunique()) if len(g) else 0,'effect':e,'bootstrap':bb};ps[str(s)]=bb['p_one_sided']
 adj=st.holm_adjust(ps)
 for s,x in slots.items():x['holm_adjusted_one_sided_p']=adj[s];x['slot_validation_rule_pass']=bool(x['matched_real_contacts']>=300 and x['donor_sessions']>=60 and x['effect'] is not None and x['effect']>0 and adj[s] is not None and adj[s]<.05)
 r={'status':'E_ZONE_V2_MATCHED_PLACEBO_TEST_COMPLETE','phase':a.phase,'real_primary_contacts':int(len(rr)),'primary_matched_real_contacts':int(len(d)),'fraction_real_contacts_with_at_least_two_contacted_controls':frac,'donor_sessions':int(d.donor_session_date_ny.nunique()) if len(d) else 0,'primary_effect':effect,'primary_bootstrap':b,'balance':bal,'quality_checks':q,'pooled_zone_pass':pooled,'slot_diagnostics':slots}
 Path(a.report).write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(r,indent=2,sort_keys=True))
if __name__=='__main__':main()
