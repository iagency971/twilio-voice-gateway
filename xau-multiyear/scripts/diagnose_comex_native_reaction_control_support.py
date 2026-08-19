#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def ratio_mask(series: pd.Series, ref: float, lo: float, hi: float) -> pd.Series:
    x = series.astype(float) / float(ref)
    return x.between(lo, hi, inclusive="both")


def count_distinct_dates(c: pd.DataFrame) -> int:
    return int(c.control_source_research_date.astype(str).nunique())


def candidate_set(c: pd.DataFrame, e, time_mode: str, time_value: int, cal_lo: float, cal_hi: float) -> pd.DataFrame:
    z = c[
        (c.year.astype(int) == int(e.year)) &
        (c.away_sign.astype(int) == int(e.away_sign)) &
        (c.control_source_research_date.astype(str) != str(e.source_research_date))
    ].copy()
    if time_mode == "same_bin":
        bins = (z.anchor_minute_of_session.astype(int) // int(time_value))
        eb = int(e.anchor_minute_of_session) // int(time_value)
        z = z[bins == eb]
    elif time_mode == "minute_caliper":
        z = z[np.abs(z.anchor_minute_of_session.astype(int) - int(e.anchor_minute_of_session)) <= int(time_value)]
    else:
        raise ValueError(time_mode)
    if len(z):
        z = z[ratio_mask(z.source_range_ticks, float(e.source_range_ticks), cal_lo, cal_hi)]
    if len(z):
        z = z[ratio_mask(z.pre30_range_ticks, float(e.pre30_range_ticks), cal_lo, cal_hi)]
    return z


def support_for_variant(events: pd.DataFrame, controls: pd.DataFrame, name: str, k: int, time_mode: str, time_value: int, cal_lo: float, cal_hi: float):
    rows=[]
    for e in events.itertuples(index=False):
        eligible = bool(e.primary_eligible)
        n=0
        if eligible:
            z=candidate_set(controls,e,time_mode,time_value,cal_lo,cal_hi)
            n=count_distinct_dates(z)
        rows.append({"level_id":str(e.level_id),"date":str(e.source_research_date),"year":int(e.year),"eligible":eligible,"distinct_dates":n,"matched":bool(eligible and n>=k)})
    d=pd.DataFrame(rows)
    defined=events[events.away_sign.astype(int).isin([-1,1])]
    m=d[d.matched]
    by=[]
    for year in range(2011,2019):
        dy=d[(d.year==year) & d.level_id.isin(defined.level_id.astype(str))]
        my=dy[dy.matched]
        by.append({"year":year,"defined":int(len(dy)),"matched":int(len(my)),"rate":float(len(my)/len(dy)) if len(dy) else 0.0,"matched_dates":int(my.date.nunique())})
    bydf=pd.DataFrame(by)
    return {
        "variant":name,"K":k,"time_mode":time_mode,"time_value":time_value,"range_caliper":[cal_lo,cal_hi],
        "matched_events":int(len(m)),"matched_dates":int(m.date.nunique()),
        "defined_contacts":int(len(defined)),"match_rate_vs_defined":float(len(m)/len(defined)) if len(defined) else 0.0,
        "every_year_ge5_dates":bool((bydf.matched_dates>=5).all()),
        "min_year_match_rate":float(bydf.rate.min()),"all_year_ge75pct":bool((bydf.rate>=0.75).all()),
        "by_year":bydf.to_dict("records")
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--events",required=True);ap.add_argument("--controls",required=True);ap.add_argument("--support",required=True);ap.add_argument("--out",required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    e=pd.read_csv(a.events,dtype={"level_id":str,"source_research_date":str})
    c=pd.read_csv(a.controls,dtype={"control_candidate_id":str,"control_source_research_date":str})
    s=pd.read_csv(a.support,dtype={"level_id":str,"source_research_date":str})
    if len(e)!=238 or len(s)!=238:raise SystemExit("expected 238 treated rows")
    e=e.merge(s[["level_id","primary_eligible","causal_covariates_ok","w15_complete"]],on="level_id",how="left",validate="one_to_one")
    defined=e[e.away_sign.astype(int).isin([-1,1])].copy()
    loss={
      "contacts_total":int(len(e)),
      "approach_defined":int(len(defined)),
      "approach_undefined":int(len(e)-len(defined)),
      "defined_pre30_incomplete":int(((defined.pre30_complete.astype(str).str.lower()!='true')).sum()),
      "defined_w15_incomplete":int(((defined.w15_complete.astype(str).str.lower()!='true')).sum()),
      "defined_causal_covariates_fail":int(((defined.causal_covariates_ok.astype(str).str.lower()!='true')).sum()),
      "primary_eligible":int((e.primary_eligible.astype(str).str.lower()=='true').sum()),
    }
    loss["max_possible_match_rate_vs_defined_under_current_eligibility"] = loss["primary_eligible"] / loss["approach_defined"]

    # Baseline waterfall among primary-eligible contacts.
    water=[]
    for ev in e[e.primary_eligible.astype(str).str.lower()=='true'].itertuples(index=False):
        z0=c[(c.year.astype(int)==int(ev.year)) & (c.away_sign.astype(int)==int(ev.away_sign)) & (c.control_source_research_date.astype(str)!=str(ev.source_research_date))].copy()
        z1=z0[(z0.anchor_minute_of_session.astype(int)//30)==(int(ev.anchor_minute_of_session)//30)].copy()
        z2=z1[ratio_mask(z1.source_range_ticks,float(ev.source_range_ticks),0.5,2.0)].copy() if len(z1) else z1
        z3=z2[ratio_mask(z2.pre30_range_ticks,float(ev.pre30_range_ticks),0.5,2.0)].copy() if len(z2) else z2
        water.append({"level_id":str(ev.level_id),"year":int(ev.year),"same_year_sign_other_date":count_distinct_dates(z0),"plus_same_30m_bin":count_distinct_dates(z1),"plus_source_range_caliper":count_distinct_dates(z2),"plus_pre30_range_caliper":count_distinct_dates(z3)})
    wf=pd.DataFrame(water)
    waterfall_summary={}
    for col in ["same_year_sign_other_date","plus_same_30m_bin","plus_source_range_caliper","plus_pre30_range_caliper"]:
        waterfall_summary[col]={"ge5":int((wf[col]>=5).sum()),"ge3":int((wf[col]>=3).sum()),"median_distinct_dates":float(wf[col].median()),"zero":int((wf[col]==0).sum())}

    specs=[
      ("PRO_BASELINE_K5_BIN30_CAL2",5,"same_bin",30,0.5,2.0),
      ("K3_BIN30_CAL2",3,"same_bin",30,0.5,2.0),
      ("K5_BIN60_CAL2",5,"same_bin",60,0.5,2.0),
      ("K3_BIN60_CAL2",3,"same_bin",60,0.5,2.0),
      ("K5_TIME30_CAL2",5,"minute_caliper",30,0.5,2.0),
      ("K3_TIME30_CAL2",3,"minute_caliper",30,0.5,2.0),
      ("K5_TIME60_CAL2",5,"minute_caliper",60,0.5,2.0),
      ("K3_TIME60_CAL2",3,"minute_caliper",60,0.5,2.0),
      ("K5_TIME60_CAL2_5",5,"minute_caliper",60,0.4,2.5),
      ("K3_TIME60_CAL2_5",3,"minute_caliper",60,0.4,2.5),
      ("K5_TIME60_CAL3",5,"minute_caliper",60,1/3,3.0),
      ("K3_TIME60_CAL3",3,"minute_caliper",60,1/3,3.0),
      ("K5_TIME120_CAL3",5,"minute_caliper",120,1/3,3.0),
      ("K3_TIME120_CAL3",3,"minute_caliper",120,1/3,3.0),
    ]
    variants=[support_for_variant(e,c,*sp) for sp in specs]
    # Strip detailed per-year from compact summary and persist separately.
    byrows=[]
    compact=[]
    for v in variants:
        q=dict(v); by=q.pop("by_year"); compact.append(q)
        for r in by: byrows.append({"variant":v["variant"],**r})
    pd.DataFrame(compact).to_csv(out/"support_variant_grid.csv",index=False)
    pd.DataFrame(byrows).to_csv(out/"support_variant_by_year.csv",index=False)
    wf.to_csv(out/"baseline_support_waterfall_events.csv",index=False)
    summary={"version":"COMEX_NATIVE_REACTION_CONTROL_SUPPORT_DIAGNOSTIC_V1","outcome_blind":True,"reaction_outcomes_computed":False,"market_data_api_called":False,"eligibility_loss":loss,"baseline_waterfall":waterfall_summary,"variants":compact,"notes":["Variants change matching support only; no post-anchor reaction value is read.","This diagnostic does not authorize a protocol change. Any material repair must be frozen before outcomes and revalidated methodologically."]}
    (out/"support_diagnostic.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))

if __name__=="__main__":main()
