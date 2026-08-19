#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

PRIMARY="S11_C6_PRIMARY"; STRESS="S18_C9_STRESS"; RRS=(0.5,1.0,1.5,2.0,2.5,3.0)
REF=("DOZ_OBJECTIVE_ONLY","CLEAN_REJECTION","STRUCTURAL")


def pf(pos,neg):
    if neg<=0: return float("inf") if pos>0 else float("nan")
    return float(pos/neg)


def aggregate_annual(df, group_cols):
    rows=[]
    for key,g in df.groupby(group_cols,dropna=False,sort=True):
        if not isinstance(key,tuple): key=(key,)
        d=dict(zip(group_cols,key)); n=int(g.trades.sum()); sn=float(g.sum_net_R.sum()); pos=float(g.pos_R.sum()); neg=float(g.neg_R.sum())
        d.update({"trades":n,"sum_net_R":sn,"mean_net_R":sn/n if n else np.nan,"pos_R":pos,"neg_R":neg,"pf_net":pf(pos,neg),
                  "positive_years":int(((g.trades>0)&(g.sum_net_R>0)).sum()),"active_years":int((g.trades>0).sum())})
        rows.append(d)
    return pd.DataFrame(rows)


def architecture_classes(multiyear):
    m=pd.read_csv(multiyear)
    rows=[]
    for (sample,model,risk),g in m.groupby(["sample","entry_model","risk_rule"],dropna=False,sort=True):
        surv=int(g.survives_vantage_gate.astype(bool).sum()); key=(str(sample),str(model),str(risk))
        if key==REF: status="VALIDATED_REFERENCE"
        elif surv==0: status="FULLY_REJECTED"
        else: status="PARTIALLY_SURVIVING"
        rows.append({"sample":sample,"entry_model":model,"risk_rule":risk,"architecture_status":status,"surviving_rr_cells":surv,
                     "rr_cells":int(len(g)),"max_primary_mean":float(g.weighted_avg_net_R_primary.max()),"max_stress_mean":float(g.weighted_avg_net_R_stress.max())})
    return pd.DataFrame(rows)


def metric_row(df, scenario, rr):
    g=df[(df.scenario==scenario)&np.isclose(df.target_r.astype(float),rr)]
    if len(g)!=1: return None
    return g.iloc[0]


def candidate_table(agg, classes):
    a=agg.merge(classes[["sample","entry_model","risk_rule","architecture_status"]],on=["sample","entry_model","risk_rule"],how="left")
    arch_cols=["sample","entry_model","risk_rule","dimension","group","architecture_status"]
    rows=[]
    for key,g in a.groupby(arch_cols,dropna=False,sort=True):
        d=dict(zip(arch_cols,key))
        if d["architecture_status"]!="FULLY_REJECTED": continue
        p15=metric_row(g,PRIMARY,1.5); s15=metric_row(g,STRESS,1.5)
        if p15 is None or s15 is None: continue
        pos_both=0; outperform_both=0
        # architecture means are added by caller as arch_mean_net_R
        for rr in RRS:
            p=metric_row(g,PRIMARY,rr); s=metric_row(g,STRESS,rr)
            if p is None or s is None: continue
            if p.sum_net_R>0 and s.sum_net_R>0: pos_both+=1
            if p.mean_net_R>p.arch_mean_net_R and s.mean_net_R>s.arch_mean_net_R: outperform_both+=1
        repeated=(int(p15.trades)>=50 and int(p15.active_years)>=10 and p15.mean_net_R>0 and s15.mean_net_R>0 and
                  p15.pf_net>1.10 and s15.pf_net>=1.00 and pos_both>=4 and outperform_both>=4)
        robust=(repeated and int(p15.trades)>=100 and int(p15.positive_years)>=8 and int(s15.positive_years)>=7 and pos_both>=5)
        label="ROBUST_HYPOTHESIS_SIGNAL" if robust else "REPEATED_HYPOTHESIS_SIGNAL" if repeated else "NO_FROZEN_SIGNAL"
        rows.append({**d,"signal_label":label,"rr15_trades":int(p15.trades),"rr15_primary_mean":float(p15.mean_net_R),"rr15_primary_pf":float(p15.pf_net),
                     "rr15_primary_positive_years":int(p15.positive_years),"rr15_stress_mean":float(s15.mean_net_R),"rr15_stress_pf":float(s15.pf_net),
                     "rr15_stress_positive_years":int(s15.positive_years),"rr_positive_primary_and_stress":pos_both,"rr_outperform_architecture_primary_and_stress":outperform_both,
                     "rr15_primary_delta_vs_arch":float(p15.mean_net_R-p15.arch_mean_net_R),"rr15_stress_delta_vs_arch":float(s15.mean_net_R-s15.arch_mean_net_R)})
    return pd.DataFrame(rows)


def recurrence(cand):
    rows=[]
    for (dim,grp),g in cand.groupby(["dimension","group"],sort=True,dropna=False):
        eligible=g[g.rr15_trades>=50]
        rows.append({"dimension":dim,"group":grp,"fully_rejected_architectures_observed":int(len(g)),"eligible_architectures_n50":int(len(eligible)),
                     "repeated_signal_architectures":int(eligible.signal_label.isin(["REPEATED_HYPOTHESIS_SIGNAL","ROBUST_HYPOTHESIS_SIGNAL"]).sum()),
                     "robust_signal_architectures":int((eligible.signal_label=="ROBUST_HYPOTHESIS_SIGNAL").sum()),
                     "median_primary_delta_rr15":float(eligible.rr15_primary_delta_vs_arch.median()) if len(eligible) else np.nan,
                     "median_stress_delta_rr15":float(eligible.rr15_stress_delta_vs_arch.median()) if len(eligible) else np.nan,
                     "primary_and_stress_positive_rr15_architectures":int(((eligible.rr15_primary_mean>0)&(eligible.rr15_stress_mean>0)).sum())})
    return pd.DataFrame(rows).sort_values(["robust_signal_architectures","repeated_signal_architectures","eligible_architectures_n50"],ascending=[False,False,False])


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--annual-dir",required=True); ap.add_argument("--multiyear-summary",required=True); ap.add_argument("--out",required=True); args=ap.parse_args()
    p=Path(args.annual_dir); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    parity_files=sorted(p.glob("parity_*.json")); pars=[json.load(open(x)) for x in parity_files]
    if len(pars)!=15 or not all(x.get("pass") for x in pars): raise RuntimeError(f"annual parity incomplete/fail: {len(pars)}")

    classes=architecture_classes(args.multiyear_summary); classes.to_csv(out/"architecture_classification.csv",index=False)
    class_counts=classes.architecture_status.value_counts().to_dict()

    sub=pd.concat([pd.read_csv(x) for x in sorted(p.glob("subgroups_*.csv"))],ignore_index=True)
    tra=pd.concat([pd.read_csv(x) for x in sorted(p.glob("transitions_*.csv"))],ignore_index=True)
    caus=pd.concat([pd.read_csv(x) for x in sorted(p.glob("causal_architecture_*.csv"))],ignore_index=True)
    qual=pd.concat([pd.read_csv(x) for x in sorted(p.glob("causal_quality_*.csv"))],ignore_index=True)

    # Normalize transitions into the same diagnostic schema.
    tra2=tra.copy(); tra2["dimension"]="transition:"+tra2.transition.astype(str); tra2["group"]=tra2.from_session.astype(str)+"->"+tra2.to_session.astype(str)
    common=["year","scenario","sample","entry_model","risk_rule","target_r","dimension","group","trades","sum_net_R","mean_net_R","pos_R","neg_R","pf_net","positive_years","active_years"]
    # annual source rows already contain annual positive/active flags only implicitly; keep numerical columns needed for aggregate_annual.
    diag=pd.concat([sub,tra2],ignore_index=True,sort=False)
    agg=aggregate_annual(diag,["scenario","sample","entry_model","risk_rule","target_r","dimension","group"])
    arch=aggregate_annual(caus,["scenario","sample","entry_model","risk_rule","target_r"])
    arch=arch.rename(columns={"mean_net_R":"arch_mean_net_R","pf_net":"arch_pf_net","trades":"arch_trades","sum_net_R":"arch_sum_net_R","positive_years":"arch_positive_years","active_years":"arch_active_years","pos_R":"arch_pos_R","neg_R":"arch_neg_R"})
    agg=agg.merge(arch[["scenario","sample","entry_model","risk_rule","target_r","arch_mean_net_R","arch_pf_net","arch_trades","arch_positive_years","arch_active_years"]],on=["scenario","sample","entry_model","risk_rule","target_r"],how="left")
    agg.to_csv(out/"all_causal_clean_subgroup_metrics.csv",index=False)

    cand=candidate_table(agg,classes); cand.to_csv(out/"candidate_signals.csv",index=False)
    rec=recurrence(cand); rec.to_csv(out/"cross_architecture_recurrence.csv",index=False)

    q=qual.groupby(["sample","entry_model","risk_rule"],as_index=False).agg(canonical_entries=("canonical_entries","sum"),causal_clean_entries=("causal_clean_entries","sum"),causal_invalid_entries=("causal_invalid_entries","sum"))
    q["causal_invalid_pct"]=100*q.causal_invalid_entries/q.canonical_entries
    q=q.merge(classes[["sample","entry_model","risk_rule","architecture_status"]],on=["sample","entry_model","risk_rule"],how="left")
    q.to_csv(out/"causal_quality_by_architecture.csv",index=False)

    sig=cand[cand.signal_label!="NO_FROZEN_SIGNAL"].copy()
    summary={
        "version":"XAU_REJECTED_STRATEGY_HETEROGENEITY_V1_RESULT",
        "annual_parity_all_pass":True,
        "architecture_status_counts":{str(k):int(v) for k,v in class_counts.items()},
        "candidate_rows":int(len(cand)),
        "repeated_hypothesis_signals":int((cand.signal_label=="REPEATED_HYPOTHESIS_SIGNAL").sum()),
        "robust_hypothesis_signals":int((cand.signal_label=="ROBUST_HYPOTHESIS_SIGNAL").sum()),
        "architectures_with_any_signal":int(sig[["sample","entry_model","risk_rule"]].drop_duplicates().shape[0]),
        "production_filter_authorized":False,
        "rejected_strategy_rescue_authorized":False,
        "new_paid_market_data_spend":0
    }
    (out/"result_summary.json").write_text(json.dumps(summary,indent=2))

    top=rec.head(20)
    lines=["# CHECKPOINT — XAU REJECTED STRATEGY HETEROGENEITY V1","",f"Annual full-grid parity: **PASS 15/15**","",f"Fully rejected architectures: **{class_counts.get('FULLY_REJECTED',0)}**",f"Partially surviving architectures: **{class_counts.get('PARTIALLY_SURVIVING',0)}**",f"Validated reference architectures: **{class_counts.get('VALIDATED_REFERENCE',0)}**","",f"Repeated hypothesis signals: **{summary['repeated_hypothesis_signals']}**",f"Robust hypothesis signals: **{summary['robust_hypothesis_signals']}**",f"Fully rejected architectures containing at least one frozen signal: **{summary['architectures_with_any_signal']}**","","## Interpretation rule","","All subgroup findings are post-hoc hypothesis generation. They cannot rescue a rejected strategy or become a production filter without independent preregistered replication.","","## Cross-architecture recurrence (top rows)",""]
    for _,r in top.iterrows(): lines.append(f"- {r.dimension} / {r.group}: robust={int(r.robust_signal_architectures)}, repeated={int(r.repeated_signal_architectures)}, eligible N>=50={int(r.eligible_architectures_n50)}, median delta primary={r.median_primary_delta_rr15:+.4f}R, stress={r.median_stress_delta_rr15:+.4f}R")
    (out/"CHECKPOINT_XAU_REJECTED_HETEROGENEITY_V1.md").write_text("\n".join(lines)+"\n")
    print(json.dumps(summary,indent=2))

if __name__=="__main__": main()
