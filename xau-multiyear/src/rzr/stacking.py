from __future__ import annotations

import json
import numpy as np
import pandas as pd


def assign_stack_ids(zones: pd.DataFrame, overlap_threshold: float = 0.5) -> pd.DataFrame:
    if zones.empty:
        out=zones.copy(); out["geometry_stack_hint"]=pd.Series(dtype=str); return out
    z=zones.sort_values(["known_time","lower","upper"]).reset_index(drop=True).copy(); hints=[None]*len(z); counter=0
    for known_time,idxs in z.groupby("known_time",sort=False).groups.items():
        stacks=[]
        for idx in idxs:
            row=z.loc[idx]; width=row.upper-row.lower; assigned=None
            for si,s in enumerate(stacks):
                overlap=max(0.0,min(row.upper,s["upper"])-max(row.lower,s["lower"])); denom=min(width,s["upper"]-s["lower"]); rel=overlap/denom if denom>0 else 0.0
                if rel>=overlap_threshold:
                    assigned=si; s["lower"]=min(s["lower"],row.lower); s["upper"]=max(s["upper"],row.upper); break
            if assigned is None:
                assigned=len(stacks); stacks.append({"lower":row.lower,"upper":row.upper,"global":counter}); counter+=1
            hints[idx]=f"GSTACK_{stacks[assigned]['global']:08d}"
    z["geometry_stack_hint"]=hints; return z


def _relative_overlap(a_lo:float,a_up:float,b_lo:float,b_up:float)->float:
    overlap=max(0.0,min(a_up,b_up)-max(a_lo,b_lo)); denom=min(a_up-a_lo,b_up-b_lo); return overlap/denom if denom>0 else 0.0


def collapse_contact_events(contacts: pd.DataFrame, overlap_threshold: float = 0.5, time_tolerance_minutes: int = 2) -> pd.DataFrame:
    if contacts.empty:
        out=contacts.copy(); out["stack_id"]=pd.Series(dtype=str); return out
    x=contacts.sort_values(["contact_time","lower","upper","zone_id"]).reset_index(drop=True).copy(); n=len(x)
    lo=pd.to_numeric(x["lower"],errors="raise").to_numpy(float); up=pd.to_numeric(x["upper"],errors="raise").to_numpy(float); width=up-lo; times_ns=pd.to_datetime(x["contact_time"],utc=True).astype("int64").to_numpy(np.int64)
    g_lo=np.empty(n); g_up=np.empty(n); g_last=np.empty(n,dtype=np.int64); g_start=np.empty(n,dtype=np.int64); g_rep=np.empty(n,dtype=np.int64); g_rep_width=np.empty(n); g_count=np.zeros(n,dtype=np.int64); g_families=[]; g_variants=[]
    active=np.empty(n,dtype=np.int64); active_count=0; group_count=0; tol_ns=int(pd.Timedelta(minutes=time_tolerance_minutes).value); last_now=None
    families=x["family"].astype(str).to_numpy(object); variants=x["variant"].astype(str).to_numpy(object)
    for idx in range(n):
        now=int(times_ns[idx])
        if now!=last_now and active_count:
            cur=active[:active_count]; kept=cur[(now-g_last[cur])<=tol_ns]; active[:len(kept)]=kept; active_count=len(kept)
        last_now=now; row_lo=float(lo[idx]); row_up=float(up[idx]); row_w=float(width[idx]); chosen=-1
        if active_count:
            cand_groups=active[:active_count]; a_lo=g_lo[cand_groups]; a_up=g_up[cand_groups]
            if abs(overlap_threshold-0.5)<=1e-15 and row_w>0:
                a_w=a_up-a_lo; a_c=(a_lo+a_up)*0.5; row_c=(row_lo+row_up)*0.5; eps=np.finfo(float).eps*np.maximum(1.0,np.abs(row_c))*8.0; possible=np.abs(a_c-row_c)<=(np.maximum(a_w,row_w)*0.5+eps)
            else: possible=(a_up>=row_lo)&(a_lo<=row_up)
            for gi in cand_groups[possible]:
                gii=int(gi)
                if _relative_overlap(row_lo,row_up,float(g_lo[gii]),float(g_up[gii]))>=overlap_threshold: chosen=gii; break
        if chosen<0:
            gi=group_count; group_count+=1; g_lo[gi]=row_lo; g_up[gi]=row_up; g_start[gi]=now; g_last[gi]=now; g_rep[gi]=idx; g_rep_width[gi]=row_w; g_count[gi]=1; g_families.append({str(families[idx])}); g_variants.append({str(variants[idx])}); active[active_count]=gi; active_count+=1
        else:
            gi=chosen; g_last[gi]=now; g_lo[gi]=min(g_lo[gi],row_lo); g_up[gi]=max(g_up[gi],row_up); g_count[gi]+=1; g_families[gi].add(str(families[idx])); g_variants[gi].add(str(variants[idx]))
            if row_w<g_rep_width[gi]:g_rep_width[gi]=row_w; g_rep[gi]=idx
    rows=[]
    for gi in range(group_count):
        rep=x.iloc[int(g_rep[gi])].to_dict(); rep["stack_id"]=f"STACK_{gi:08d}"; rep["constituent_count"]=int(g_count[gi]); rep["constituent_families"]=json.dumps(sorted(g_families[gi])); rep["constituent_variants"]=json.dumps(sorted(g_variants[gi])); rep["stack_contact_start"]=pd.Timestamp(int(g_start[gi]),tz="UTC"); rep["stack_contact_end"]=pd.Timestamp(int(g_last[gi]),tz="UTC"); rows.append(rep)
    return pd.DataFrame(rows)
