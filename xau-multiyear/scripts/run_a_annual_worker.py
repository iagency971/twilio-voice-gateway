#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys,time
from dataclasses import asdict
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rzr.config import ResearchConfig
from rzr.io import load_ohlc_csv
from rzr.features import quote_activity_mask,robust_sigma60
from rzr.zones import generate_baseline_zones
from rzr.stacking import assign_stack_ids,collapse_contact_events
from rzr.contacts import find_first_contacts
from rzr.labels import label_contacts
from rzr.controls import generate_matched_controls
from rzr.reporting import pair_contacts_to_controls,paired_family_summary


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('csv'); ap.add_argument('--target-start',required=True); ap.add_argument('--target-end',required=True); ap.add_argument('--out',required=True); ap.add_argument('--controls',type=int,default=5); a=ap.parse_args()
    target_start=pd.Timestamp(a.target_start); target_start=target_start.tz_localize('UTC') if target_start.tzinfo is None else target_start.tz_convert('UTC'); target_end=pd.Timestamp(a.target_end); target_end=target_end.tz_localize('UTC') if target_end.tzinfo is None else target_end.tz_convert('UTC'); cfg=ResearchConfig(controls_per_contact=int(a.controls)); out=Path(a.out); out.mkdir(parents=True,exist_ok=True); timings={}
    t=time.perf_counter(); bars=load_ohlc_csv(a.csv); timings['load']=time.perf_counter()-t; bars=bars.sort_index().copy(); t=time.perf_counter(); bars['quote_active']=quote_activity_mask(bars); bars['sigma60']=robust_sigma60(bars); timings['features']=time.perf_counter()-t
    t=time.perf_counter(); zones=generate_baseline_zones(bars,cfg); timings['zones']=time.perf_counter()-t; zdf=pd.DataFrame([asdict(z) for z in zones])
    if not zdf.empty:
        zdf['family']=zdf['family'].astype(str).str.replace('ZoneFamily.','',regex=False); zdf['side']=zdf['side'].astype(str).str.replace('ZoneSide.','',regex=False); t=time.perf_counter(); zdf=assign_stack_ids(zdf,cfg.stack_overlap_threshold); timings['zone_stack_hints']=time.perf_counter()-t
    t=time.perf_counter(); contacts=find_first_contacts(bars,zones,bars['sigma60'],cfg); timings['first_contacts']=time.perf_counter()-t; t=time.perf_counter(); contacts=collapse_contact_events(contacts,cfg.stack_overlap_threshold); timings['contact_stacking']=time.perf_counter()-t; t=time.perf_counter(); contacts=label_contacts(bars,contacts,cfg); timings['contact_labels']=time.perf_counter()-t
    if not contacts.empty:
        ct=pd.to_datetime(contacts['contact_time'],utc=True); contacts=contacts[(ct>=target_start)&(ct<target_end)].copy()
    t=time.perf_counter(); controls=generate_matched_controls(bars,contacts,zdf,cfg,controls_per_contact=cfg.controls_per_contact,candidate_start=target_start,candidate_end=target_end); timings['controls']=time.perf_counter()-t; t=time.perf_counter(); controls=label_contacts(bars,controls,cfg) if not controls.empty else controls; timings['control_labels']=time.perf_counter()-t
    paired=pair_contacts_to_controls(contacts,controls)
    if not paired.empty:
        paired['contact_time']=pd.to_datetime(paired['contact_time'],utc=True); paired['zone_known_time']=pd.to_datetime(paired['zone_known_time'],utc=True); paired['representative_zone_age_days']=(paired['contact_time']-paired['zone_known_time']).dt.total_seconds()/86400.0
    summary=paired_family_summary(contacts,controls,cfg.controls_per_contact)
    keep=[c for c in ['stack_id','zone_id','contact_time','zone_known_time','representative_zone_age_days','family','variant','side','constituent_count','constituent_families','constituent_variants','session','local_hour','sigma60','approach_direction','approach_band','mfe_sigma','mae_sigma','accepted_5m','behavior_primary','reaction_0_25sigma','reaction_0_5sigma','reaction_1_0sigma','reaction_1_5sigma','n_controls','control_reaction_0_25sigma','control_reaction_0_5sigma','control_reaction_1_0sigma','control_reaction_1_5sigma','paired_diff_reaction_0_25sigma','paired_diff_reaction_0_5sigma','paired_diff_reaction_1_0sigma','paired_diff_reaction_1_5sigma'] if c in paired.columns]
    paired[keep].to_csv(out/'event_pairs.csv',index=False); summary.to_csv(out/'paired_summary_by_family.csv',index=False)
    manifest={'input_bars':int(len(bars)),'input_start':str(bars.index.min()),'input_end':str(bars.index.max()),'target_start':str(target_start),'target_end':str(target_end),'zones':int(len(zdf)),'target_events':int(len(contacts)),'control_draws':int(len(controls)),'paired_events_any':int((paired.get('n_controls',pd.Series(dtype=int))>0).sum()) if len(paired) else 0,'paired_events_full':int((paired.get('n_controls',pd.Series(dtype=int))==cfg.controls_per_contact).sum()) if len(paired) else 0,'controls_per_contact':cfg.controls_per_contact,'timings_seconds':{k:round(v,6) for k,v in timings.items()},'primary_estimand':'event-level paired reaction difference: actual - equally weighted mean matched controls','control_candidate_window':'restricted to target_start <= control_time < target_end'}
    (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2)); print(json.dumps(manifest,indent=2)); print(summary.to_string(index=False))

if __name__=='__main__':main()
