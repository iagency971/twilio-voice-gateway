from __future__ import annotations

import json
import numpy as np
import pandas as pd

_REACTION_COLS=("reaction_0_25sigma","reaction_0_5sigma","reaction_1_0sigma","reaction_1_5sigma")


def families_present(contacts:pd.DataFrame)->list[str]:
    fams=set()
    if "constituent_families" in contacts.columns:
        for v in contacts["constituent_families"].dropna().astype(str):
            try:fams.update(json.loads(v))
            except Exception:pass
    if not fams and "family" in contacts.columns:fams.update(contacts["family"].dropna().astype(str))
    return sorted(fams)


def family_mask(contacts:pd.DataFrame,family:str)->pd.Series:
    if "constituent_families" not in contacts.columns:return contacts["family"].astype(str).eq(family)
    def has(v):
        try:return family in json.loads(str(v))
        except Exception:return False
    return contacts["constituent_families"].map(has)


def pair_contacts_to_controls(contacts:pd.DataFrame,controls:pd.DataFrame)->pd.DataFrame:
    c=contacts.copy()
    if c.empty:return c
    if controls.empty:
        c["n_controls"]=0
        for col in _REACTION_COLS:c[f"control_{col}"]=np.nan;c[f"paired_diff_{col}"]=np.nan
        return c
    key="matched_to_stack_id" if "matched_to_stack_id" in controls.columns else "matched_to_zone_id"; real_key="stack_id" if key=="matched_to_stack_id" else "zone_id"; agg_spec={"n_controls":("zone_id","size")}
    for col in _REACTION_COLS:
        if col in controls.columns:agg_spec[f"control_{col}"]=(col,"mean")
    ctrl=controls.groupby(key,dropna=True).agg(**agg_spec); c=c.merge(ctrl,how="left",left_on=real_key,right_index=True); c["n_controls"]=c["n_controls"].fillna(0).astype(int)
    for col in _REACTION_COLS:
        cc=f"control_{col}"
        if col in c.columns and cc in c.columns:c[f"paired_diff_{col}"]=pd.to_numeric(c[col],errors="coerce")-pd.to_numeric(c[cc],errors="coerce")
    return c


def paired_family_summary(contacts:pd.DataFrame,controls:pd.DataFrame,controls_per_contact:int=5)->pd.DataFrame:
    paired=pair_contacts_to_controls(contacts,controls); rows=[]
    if paired.empty:return pd.DataFrame()
    for family in families_present(paired):
        g=paired[family_mask(paired,family)].copy()
        for mode,mask in (("ANY_CONTROL",g["n_controls"].gt(0)),("FULL_CONTROLS",g["n_controls"].eq(int(controls_per_contact)))):
            h=g[mask].copy(); row={"family":family,"mode":mode,"events_all":int(len(g)),"events_paired":int(len(h)),"control_coverage_pct":float(100*len(h)/len(g)) if len(g) else np.nan,"mean_controls_per_paired_event":float(h["n_controls"].mean()) if len(h) else np.nan,"median_mfe_sigma":float(pd.to_numeric(h.get("mfe_sigma"),errors="coerce").median()) if len(h) and "mfe_sigma" in h else np.nan,"median_mae_sigma":float(pd.to_numeric(h.get("mae_sigma"),errors="coerce").median()) if len(h) and "mae_sigma" in h else np.nan}
            for col in _REACTION_COLS:
                if col not in h.columns or f"control_{col}" not in h.columns:continue
                suffix=col.replace("reaction_",""); row[f"actual_{suffix}_pct"]=float(100*pd.to_numeric(h[col],errors="coerce").mean()) if len(h) else np.nan; row[f"control_{suffix}_pct"]=float(100*pd.to_numeric(h[f"control_{col}"],errors="coerce").mean()) if len(h) else np.nan; row[f"paired_lift_{suffix}_pp"]=float(100*pd.to_numeric(h[f"paired_diff_{col}"],errors="coerce").mean()) if len(h) else np.nan
            unmatched=g[g["n_controls"].eq(0)]; row["unmatched_events"]=int(len(unmatched)); row["unmatched_actual_0_5sigma_pct"]=float(100*unmatched["reaction_0_5sigma"].mean()) if len(unmatched) else np.nan; rows.append(row)
    return pd.DataFrame(rows)
