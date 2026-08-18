#!/usr/bin/env python3
from __future__ import annotations
import sys,json
from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path("xau-multiyear")
sys.path.insert(0,str(ROOT/"src"))
from rzr.config import ResearchConfig
from rzr.io import load_ohlc_csv
from rzr.features import quote_activity_mask,robust_sigma60
from rzr.zones import generate_baseline_zones
from rzr.contacts import find_first_contacts
from rzr.stacking import collapse_contact_events
from rzr.labels import label_contacts
from rzr.behavior_v2 import classify_behavior_v2
from rzr.entries_v2 import build_entry, simulate_one

def main(csv,out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True); cfg=ResearchConfig()
    bars=load_ohlc_csv(csv).sort_index().copy()
    for c in ["open_bid","high_bid","low_bid","close_bid","open_ask","high_ask","low_ask","close_ask","spread"]: bars[c]=pd.to_numeric(bars[c],errors="raise")
    bars["quote_active"]=quote_activity_mask(bars); bars["sigma60"]=robust_sigma60(bars)
    zones=generate_baseline_zones(bars,cfg); contacts=find_first_contacts(bars,zones,bars.sigma60,cfg); contacts=collapse_contact_events(contacts,cfg.stack_overlap_threshold); contacts=label_contacts(bars,contacts,cfg); contacts=classify_behavior_v2(bars,contacts,cfg)
    ct=pd.to_datetime(contacts.contact_time,utc=True); contacts=contacts[(ct>=pd.Timestamp("2013-01-01",tz="UTC"))&(ct<pd.Timestamp("2014-01-01",tz="UTC"))].copy()
    sf=contacts.constituent_families.fillna(""); obj=sf.eq('["OBJECTIVE_LIQUIDITY"]'); g=contacts[obj]
    rec=[]
    for r in g.to_dict("records"):
        e=build_entry(r,bars,"TOUCH_NEXT_OPEN",acceptance_minutes=cfg.acceptance_minutes)
        if not e: continue
        s=simulate_one(e,bars,1.0,horizon_minutes=120)
        rec.append({**{k:r.get(k) for k in ["stack_id","zone_id","contact_time","variant","side","lower","upper","sigma60"]},**e,**s})
    t=pd.DataFrame(rec).sort_values("gross_R"); t.to_csv(out/"objective_touch_1R_all.csv",index=False)
    worst=t.head(30).copy(); worst.to_csv(out/"worst30.csv",index=False)
    snippets=[]
    for _,r in worst.head(10).iterrows():
        ei=int(r.entry_idx); xi=int(r.exit_idx); lo=max(0,ei-3); hi=min(len(bars),max(ei,xi)+4)
        b=bars.iloc[lo:hi][["timestamp","open_bid","high_bid","low_bid","close_bid","open_ask","high_ask","low_ask","close_ask","spread","quote_active","sigma60"]].copy()
        b.insert(0,"diagnostic_trade_gross_R",float(r.gross_R)); b.insert(1,"diagnostic_zone_id",r.zone_id); snippets.append(b)
    pd.concat(snippets,ignore_index=True).to_csv(out/"worst10_bar_snippets.csv",index=False)
    q={"trades":len(t),"min_gross_R":float(t.gross_R.min()),"p001_gross_R":float(t.gross_R.quantile(.001)),"p01_gross_R":float(t.gross_R.quantile(.01)),"count_below_minus2R":int((t.gross_R<-2).sum()),"count_below_minus5R":int((t.gross_R<-5).sum()),"min_risk_price":float(t.risk_price.min()),"p01_risk_price":float(t.risk_price.quantile(.01)),"max_spread_near_entry":float(max([bars.spread.iloc[int(i)] for i in t.entry_idx]))}
    (out/"diagnostic.json").write_text(json.dumps(q,indent=2)); print(json.dumps(q,indent=2)); print(worst.head(20).to_string(index=False))
if __name__=="__main__": main(sys.argv[1],sys.argv[2])
