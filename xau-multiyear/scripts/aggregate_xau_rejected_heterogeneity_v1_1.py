#!/usr/bin/env python3
"""Strict classification adapter for rejected heterogeneity aggregation."""
from __future__ import annotations
import pandas as pd
import aggregate_xau_rejected_heterogeneity_v1 as agg


def architecture_classes_strict(multiyear):
    m=pd.read_csv(multiyear)
    surv=m["survives_vantage_gate"]
    if surv.dtype != bool:
        m["_surv"] = surv.astype(str).str.strip().str.lower().eq("true")
    else:
        m["_surv"] = surv
    rows=[]
    for (sample,model,risk),g in m.groupby(["sample","entry_model","risk_rule"],dropna=False,sort=True):
        n=int(g["_surv"].sum()); key=(str(sample),str(model),str(risk))
        if key==agg.REF: status="VALIDATED_REFERENCE"
        elif n==0: status="FULLY_REJECTED"
        else: status="PARTIALLY_SURVIVING"
        rows.append({"sample":sample,"entry_model":model,"risk_rule":risk,"architecture_status":status,"surviving_rr_cells":n,
                     "rr_cells":int(len(g)),"max_primary_mean":float(g.weighted_avg_net_R_primary.max()),"max_stress_mean":float(g.weighted_avg_net_R_stress.max())})
    return pd.DataFrame(rows)

agg.architecture_classes = architecture_classes_strict

if __name__ == "__main__":
    agg.main()
