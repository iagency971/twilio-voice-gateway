#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from rzr.config import ResearchConfig
from rzr.io import load_ohlc_csv
from rzr.features import quote_activity_mask, robust_sigma60, session_bucket
from rzr.zones import generate_baseline_zones
from rzr.contacts import find_first_contacts
from rzr.stacking import collapse_contact_events
from rzr.labels import label_contacts
from rzr.behavior_v2 import classify_behavior_v2
from rzr.entries_v2 import build_entry
from rzr.entries_v1 import simulate_one
from rzr.entries_s1 import apply_volatility_floor
from rzr.vantage_overlay import apply_fixed_spread_overlay
from run_xau_core_audit_annual_v1 import collapse_with_membership, assert_stack_parity, sha256_file

FAMILIES = ["DISPLACEMENT_ORIGIN", "OBJECTIVE_LIQUIDITY", "MEMORY", "FVG"]
SAMPLES = {
    "DISPLACEMENT_ORIGIN_ONLY": ["DISPLACEMENT_ORIGIN"],
    "OBJECTIVE_LIQUIDITY_ONLY": ["OBJECTIVE_LIQUIDITY"],
    "MEMORY_ONLY": ["MEMORY"],
    "DOZ_OBJECTIVE_ONLY": ["DISPLACEMENT_ORIGIN", "OBJECTIVE_LIQUIDITY"],
}
STRUCTURAL_MODELS = ["PASSIVE_TOUCH", "CLEAN_REJECTION", "FAILED_AUCTION", "ACCEPTANCE_RETEST", "RECLAIM_PULLBACK"]
TNO_K = (0.25, 0.50, 0.75, 1.00)
TARGET_RS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
SCENARIOS = {
    "S10_C6": {"spread_usd": 0.10, "commission_rt_usd": 6.0, "role": "sensitivity"},
    "S11_C6_PRIMARY": {"spread_usd": 0.11, "commission_rt_usd": 6.0, "role": "primary"},
    "S12_C6": {"spread_usd": 0.12, "commission_rt_usd": 6.0, "role": "sensitivity"},
    "S18_C9_STRESS": {"spread_usd": 0.18, "commission_rt_usd": 9.0, "role": "stress"},
}


def safe_num(x):
    x = float(x)
    if np.isnan(x): return None
    if np.isposinf(x): return "INF"
    if np.isneginf(x): return "-INF"
    return x


def pf_from_sums(pos, neg):
    if neg <= 0:
        return float("inf") if pos > 0 else float("nan")
    return float(pos / neg)


def age_bucket(hours):
    if not np.isfinite(hours): return "UNKNOWN"
    if hours < 1: return "<1h"
    if hours < 4: return "1-4h"
    if hours < 12: return "4-12h"
    if hours < 24: return "12-24h"
    if hours < 72: return "1-3d"
    if hours < 168: return "3-7d"
    if hours < 720: return "7-30d"
    return ">=30d"


def sess(ts, tz):
    if ts is None or pd.isna(ts): return "UNKNOWN"
    return session_bucket(pd.Timestamp(ts), tz)


def anchor(member_df, family, entry_time=None, causal_only=False):
    g = member_df[member_df["family"].astype(str).eq(family)].copy()
    if causal_only and entry_time is not None:
        kt = pd.to_datetime(g["known_time"], utc=True)
        g = g[kt <= pd.Timestamp(entry_time)]
    if g.empty: return None
    g["_width"] = pd.to_numeric(g["upper"], errors="coerce") - pd.to_numeric(g["lower"], errors="coerce")
    g["_known"] = pd.to_datetime(g["known_time"], utc=True)
    g["_origin"] = pd.to_datetime(g["origin_time"], utc=True)
    return g.sort_values(["_width", "_known", "_origin", "zone_id"], kind="mergesort").iloc[0]


def sample_masks(contacts):
    sf = contacts.get("constituent_families", pd.Series("", index=contacts.index)).fillna("")
    masks = {f: sf.str.contains(f'\"{f}\"', regex=False) for f in FAMILIES}
    return {
        "DISPLACEMENT_ORIGIN_ONLY": masks["DISPLACEMENT_ORIGIN"] & ~masks["OBJECTIVE_LIQUIDITY"] & ~masks["MEMORY"] & ~masks["FVG"],
        "OBJECTIVE_LIQUIDITY_ONLY": masks["OBJECTIVE_LIQUIDITY"] & ~masks["DISPLACEMENT_ORIGIN"] & ~masks["MEMORY"] & ~masks["FVG"],
        "MEMORY_ONLY": masks["MEMORY"] & ~masks["DISPLACEMENT_ORIGIN"] & ~masks["OBJECTIVE_LIQUIDITY"] & ~masks["FVG"],
        "DOZ_OBJECTIVE_ONLY": masks["DISPLACEMENT_ORIGIN"] & masks["OBJECTIVE_LIQUIDITY"] & ~masks["MEMORY"] & ~masks["FVG"],
    }


class Stats:
    __slots__ = ("n","sum_net","sum_gross","pos","neg","tp","sl","time","risk","delay")
    def __init__(self):
        self.n=0; self.sum_net=0.0; self.sum_gross=0.0; self.pos=0.0; self.neg=0.0
        self.tp=0; self.sl=0; self.time=0; self.risk=[]; self.delay=[]
    def add(self, net, gross, result, risk=None, delay=None):
        net=float(net); gross=float(gross); self.n += 1; self.sum_net += net; self.sum_gross += gross
        if net > 0: self.pos += net
        elif net < 0: self.neg += -net
        if result == "TP": self.tp += 1
        elif result == "SL": self.sl += 1
        else: self.time += 1
        if risk is not None: self.risk.append(float(risk))
        if delay is not None: self.delay.append(float(delay))
    def row(self):
        n=self.n
        return {
            "trades": n,
            "sum_net_R": self.sum_net,
            "mean_net_R": self.sum_net/n if n else np.nan,
            "sum_gross_R": self.sum_gross,
            "mean_gross_R": self.sum_gross/n if n else np.nan,
            "pos_R": self.pos,
            "neg_R": self.neg,
            "pf_net": pf_from_sums(self.pos,self.neg),
            "tp_pct": 100*self.tp/n if n else np.nan,
            "sl_pct": 100*self.sl/n if n else np.nan,
            "time_pct": 100*self.time/n if n else np.nan,
            "median_risk_price": float(np.median(self.risk)) if self.risk else np.nan,
            "median_entry_delay_minutes": float(np.median(self.delay)) if self.delay else np.nan,
        }


def add_stat(store, key, sim, entry):
    store[key].add(sim["net_R_legacy22"], sim["gross_R"], sim["result"], entry.get("risk_price"), entry.get("entry_delay_minutes"))


def compare_summary(actual_rows, expected_path):
    act = pd.DataFrame(actual_rows)
    exp = pd.read_csv(expected_path)
    keys = ["scenario","sample","entry_model","risk_rule","target_r"]
    act["target_r"] = act["target_r"].astype(float)
    exp["target_r"] = exp["target_r"].astype(float)
    merged = exp.merge(act, on=keys, how="outer", suffixes=("_expected","_actual"), indicator=True)
    failures=[]
    metrics=[
        ("trades",0.0),("avg_gross_R",1e-10),("avg_net_R",1e-10),("pf_net",1e-9),
        ("sum_net_R",1e-9),("median_risk_price",1e-10),("median_entry_delay_minutes",1e-10),
    ]
    for _,r in merged.iterrows():
        if r["_merge"] != "both":
            failures.append({"keys":{k:r.get(k) for k in keys},"reason":str(r["_merge"])})
            continue
        for m,tol in metrics:
            a=float(r[f"{m}_actual"]); e=float(r[f"{m}_expected"])
            if np.isinf(a) and np.isinf(e): continue
            if np.isnan(a) and np.isnan(e): continue
            if not (np.isfinite(a) and np.isfinite(e) and abs(a-e)<=tol):
                failures.append({"keys":{k:r.get(k) for k in keys},"metric":m,"actual":safe_num(a),"expected":safe_num(e),"tol":tol})
                break
    return {"pass":len(failures)==0,"expected_cells":int(len(exp)),"actual_cells":int(len(act)),"failures":failures[:100]}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv"); ap.add_argument("--year",type=int,required=True); ap.add_argument("--expected-annual-summary",required=True); ap.add_argument("--out",required=True)
    args=ap.parse_args()
    year=int(args.year); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    cfg=ResearchConfig(); start=pd.Timestamp(f"{year}-01-01",tz="UTC"); end=pd.Timestamp(f"{year+1}-01-01",tz="UTC")
    input_path=Path(args.csv); input_sha=sha256_file(input_path)

    bars_mid=load_ohlc_csv(input_path).sort_index().copy(); bars_mid["quote_active"]=quote_activity_mask(bars_mid); bars_mid["sigma60"]=robust_sigma60(bars_mid)
    zones=generate_baseline_zones(bars_mid,cfg)
    zdf=pd.DataFrame([{"zone_id":z.zone_id,"family":z.family.value,"variant":z.variant,"origin_time":z.origin_time,"known_time":z.known_time,"lower":z.lower,"upper":z.upper,"source_tf":z.source_tf} for z in zones])
    raw=find_first_contacts(bars_mid,zones,bars_mid["sigma60"],cfg)
    canonical=collapse_contact_events(raw,cfg.stack_overlap_threshold)
    audit,membership=collapse_with_membership(raw,cfg.stack_overlap_threshold)
    stack_parity=assert_stack_parity(canonical,audit)
    if not stack_parity["pass"]: raise RuntimeError(f"stack parity failed {stack_parity}")
    audit=label_contacts(bars_mid,audit,cfg); audit=classify_behavior_v2(bars_mid,audit,cfg)
    ct=pd.to_datetime(audit["contact_time"],utc=True); audit=audit[(ct>=start)&(ct<end)].copy()
    masks=sample_masks(audit)

    members = membership.merge(zdf,on="zone_id",how="left")
    member_map={k:g.copy() for k,g in members.groupby("stack_id",sort=False)}

    baseline=defaultdict(Stats); causal_baseline=defaultdict(Stats); subgroup=defaultdict(Stats); transitions=defaultdict(Stats)
    quality=defaultdict(lambda:{"canonical_entries":0,"causal_clean_entries":0,"causal_invalid_entries":0})

    for scenario,sc in SCENARIOS.items():
        bars_exec=apply_fixed_spread_overlay(bars_mid,sc["spread_usd"]); comm=float(sc["commission_rt_usd"])
        for sample,mask in masks.items():
            recs=audit[mask].to_dict("records"); required=SAMPLES[sample]
            model_specs=[(m,"STRUCTURAL",None) for m in STRUCTURAL_MODELS] + [("TOUCH_NEXT_OPEN",f"VOL_FLOOR_{k:.2f}",k) for k in TNO_K]
            for model,risk_rule,k in model_specs:
                for rec in recs:
                    entry=build_entry(rec,bars_exec,"TOUCH_NEXT_OPEN" if model=="TOUCH_NEXT_OPEN" else model,acceptance_minutes=cfg.acceptance_minutes)
                    if entry is None: continue
                    if k is not None:
                        entry=apply_volatility_floor(entry,float(k))
                        if entry is None: continue
                    stack_id=str(rec.get("stack_id")); mdf=member_map.get(stack_id,pd.DataFrame())
                    et=bars_mid.index[int(entry["entry_idx"])]; contact_t=pd.Timestamp(rec["contact_time"])
                    anchors={fam:anchor(mdf,fam,entry_time=et,causal_only=True) for fam in required}
                    causal_valid=all(anchors.get(fam) is not None for fam in required)
                    qkey=(scenario,sample,model,risk_rule)
                    quality[qkey]["canonical_entries"] += 1
                    if causal_valid: quality[qkey]["causal_clean_entries"] += 1
                    else: quality[qkey]["causal_invalid_entries"] += 1

                    rel_family="DISPLACEMENT_ORIGIN" if "DISPLACEMENT_ORIGIN" in required else required[0]
                    rel=anchors.get(rel_family) if causal_valid else None
                    dims={
                        "direction":str(entry["direction"]),
                        "contact_session":sess(contact_t,cfg.timezone),
                        "entry_session":sess(et,cfg.timezone),
                    }
                    if rel is not None:
                        kt=pd.Timestamp(rel["known_time"]); ot=pd.Timestamp(rel["origin_time"])
                        dims["relevant_source_tf"]=str(rel.get("source_tf","UNKNOWN"))
                        dims["relevant_variant"]=str(rel.get("variant","UNKNOWN"))
                        dims["relevant_age_bucket"]=age_bucket((et-kt).total_seconds()/3600.0)
                    else:
                        dims["relevant_source_tf"]="INVALID"; dims["relevant_variant"]="INVALID"; dims["relevant_age_bucket"]="INVALID"

                    family_transition_values=[]
                    if causal_valid:
                        for fam,a in anchors.items():
                            family_transition_values.append((f"{fam}_origin_to_entry",sess(pd.Timestamp(a["origin_time"]),cfg.timezone),sess(et,cfg.timezone)))
                            family_transition_values.append((f"{fam}_activation_to_entry",sess(pd.Timestamp(a["known_time"]),cfg.timezone),sess(et,cfg.timezone)))

                    for rr in TARGET_RS:
                        sim=simulate_one(entry,bars_exec,rr,horizon_minutes=120,commission_rt_per_lot=comm)
                        bkey=(scenario,sample,model,risk_rule,float(rr)); add_stat(baseline,bkey,sim,entry)
                        if not causal_valid: continue
                        add_stat(causal_baseline,bkey,sim,entry)
                        for dim,grp in dims.items(): add_stat(subgroup,bkey+(dim,str(grp)),sim,entry)
                        for name,frm,to in family_transition_values: add_stat(transitions,bkey+(name,str(frm),str(to)),sim,entry)

    actual=[]
    for (scenario,sample,model,risk_rule,rr),st in baseline.items():
        r=st.row(); actual.append({
            "scenario":scenario,"sample":sample,"entry_model":model,"risk_rule":risk_rule,"target_r":rr,
            "trades":r["trades"],"avg_gross_R":r["mean_gross_R"],"avg_net_R":r["mean_net_R"],"pf_net":r["pf_net"],
            "sum_net_R":r["sum_net_R"],"median_risk_price":r["median_risk_price"],"median_entry_delay_minutes":r["median_entry_delay_minutes"]})
    parity=compare_summary(actual,Path(args.expected_annual_summary)); parity.update({"year":year,"stack_parity":stack_parity,"input_sha256":input_sha})
    (out/f"parity_{year}.json").write_text(json.dumps(parity,indent=2,allow_nan=False))
    if not parity["pass"]: raise RuntimeError(f"annual full-grid parity failed {year}: {parity['failures'][:3]}")

    pd.DataFrame(actual).to_csv(out/f"canonical_architecture_{year}.csv",index=False)
    crows=[]
    for k,st in causal_baseline.items():
        scenario,sample,model,risk_rule,rr=k; crows.append({"year":year,"scenario":scenario,"sample":sample,"entry_model":model,"risk_rule":risk_rule,"target_r":rr,**st.row()})
    pd.DataFrame(crows).to_csv(out/f"causal_architecture_{year}.csv",index=False)

    srows=[]
    for k,st in subgroup.items():
        scenario,sample,model,risk_rule,rr,dim,grp=k; srows.append({"year":year,"scenario":scenario,"sample":sample,"entry_model":model,"risk_rule":risk_rule,"target_r":rr,"dimension":dim,"group":grp,**st.row()})
    pd.DataFrame(srows).to_csv(out/f"subgroups_{year}.csv",index=False)

    trows=[]
    for k,st in transitions.items():
        scenario,sample,model,risk_rule,rr,name,frm,to=k; trows.append({"year":year,"scenario":scenario,"sample":sample,"entry_model":model,"risk_rule":risk_rule,"target_r":rr,"transition":name,"from_session":frm,"to_session":to,**st.row()})
    pd.DataFrame(trows).to_csv(out/f"transitions_{year}.csv",index=False)

    qrows=[]
    for (scenario,sample,model,risk_rule),v in quality.items(): qrows.append({"year":year,"scenario":scenario,"sample":sample,"entry_model":model,"risk_rule":risk_rule,**v})
    pd.DataFrame(qrows).to_csv(out/f"causal_quality_{year}.csv",index=False)
    manifest={"version":"XAU_REJECTED_HETEROGENEITY_ANNUAL_V1","year":year,"parity_pass":True,"input_sha256":input_sha,"new_paid_market_data_spend":0,"runtime_commit":os.getenv("GITHUB_SHA","LOCAL")}
    (out/f"manifest_{year}.json").write_text(json.dumps(manifest,indent=2))
    print(json.dumps({"year":year,"parity_pass":True,"canonical_cells":len(actual),"subgroup_rows":len(srows),"transition_rows":len(trows)},indent=2))

if __name__=="__main__": main()
