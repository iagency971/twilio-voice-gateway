from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ResearchConfig
from .features import approach_state_arrays, quote_activity_mask, session_bucket


class _KnownZonePrefixTree:
    def __init__(self,zones:pd.DataFrame):
        if zones.empty:
            self.n=0; self.size=1; self.known_ns=np.empty(0,dtype=np.int64); self.min_lower=np.full(2,np.inf); self.max_upper=np.full(2,-np.inf); return
        z=zones[["known_time","lower","upper"]].copy(); z["known_time"]=pd.to_datetime(z["known_time"],utc=True); z=z.sort_values("known_time",kind="mergesort").reset_index(drop=True); self.n=len(z); self.known_ns=z["known_time"].astype("int64").to_numpy(); lo=pd.to_numeric(z["lower"],errors="coerce").to_numpy(float); up=pd.to_numeric(z["upper"],errors="coerce").to_numpy(float); valid=np.isfinite(lo)&np.isfinite(up); size=1
        while size<self.n:size<<=1
        self.size=size; self.min_lower=np.full(2*size,np.inf); self.max_upper=np.full(2*size,-np.inf); self.min_lower[size:size+self.n]=np.where(valid,lo,np.inf); self.max_upper[size:size+self.n]=np.where(valid,up,-np.inf)
        for node in range(size-1,0,-1):self.min_lower[node]=min(self.min_lower[node*2],self.min_lower[node*2+1]); self.max_upper[node]=max(self.max_upper[node*2],self.max_upper[node*2+1])
    def any_near(self,ts_ns:int,price:float,margin:float)->bool:
        if self.n==0:return False
        end=int(np.searchsorted(self.known_ns,ts_ns,side="right"));
        if end<=0:return False
        target_lo=price-margin; target_up=price+margin; stack=[(1,0,self.size)]
        while stack:
            node,lo,hi=stack.pop()
            if lo>=end or lo>=self.n:continue
            if self.min_lower[node]>target_up or self.max_upper[node]<target_lo:continue
            if hi-lo==1:return True
            mid=(lo+hi)//2; stack.append((node*2+1,mid,hi)); stack.append((node*2,lo,mid))
        return False


def _batch_near_known_zone(rows:pd.DataFrame,zones:pd.DataFrame)->np.ndarray:
    if rows.empty:return np.zeros(0,dtype=bool)
    if zones.empty:return np.zeros(len(rows),dtype=bool)
    z=zones[["known_time","lower","upper"]].copy(); z["known_time"]=pd.to_datetime(z["known_time"],utc=True); zlo=pd.to_numeric(z["lower"],errors="coerce").to_numpy(float); zup=pd.to_numeric(z["upper"],errors="coerce").to_numpy(float); zt=z["known_time"].astype("int64").to_numpy(np.int64); valid=np.isfinite(zlo)&np.isfinite(zup); zlo=zlo[valid]; zup=zup[valid]; zt=zt[valid]
    if not len(zlo):return np.zeros(len(rows),dtype=bool)
    order=np.argsort(zt,kind="mergesort"); zlo=zlo[order]; zup=zup[order]; zt=zt[order]; coords=np.unique(zlo); bit=np.full(len(coords)+1,-np.inf,dtype=float)
    def update(pos0:int,value:float):
        i=pos0+1
        while i<len(bit):
            if value>bit[i]:bit[i]=value
            i+=i&-i
    def prefix_max(count:int)->float:
        m=-np.inf; i=count
        while i>0:
            if bit[i]>m:m=bit[i]
            i-=i&-i
        return m
    rt=pd.to_datetime(rows["contact_time"],utc=True).astype("int64").to_numpy(np.int64); px=pd.to_numeric(rows["center"],errors="coerce").to_numpy(float); margin=pd.to_numeric(rows["_near_margin"],errors="coerce").to_numpy(float); rorder=np.argsort(rt,kind="mergesort"); near=np.zeros(len(rows),dtype=bool); zi=0
    for ri in rorder:
        t=int(rt[ri])
        while zi<len(zt) and int(zt[zi])<=t:
            pos=int(np.searchsorted(coords,zlo[zi],side="left")); update(pos,float(zup[zi])); zi+=1
        if not np.isfinite(px[ri]) or not np.isfinite(margin[ri]):continue
        target_lo=float(px[ri]-margin[ri]); target_up=float(px[ri]+margin[ri]); count=int(np.searchsorted(coords,target_up,side="right")); near[ri]=prefix_max(count)>=target_lo
    return near


def generate_matched_controls(bars:pd.DataFrame,contacts:pd.DataFrame,zones:pd.DataFrame,config:ResearchConfig,controls_per_contact:int=1,sigma_tolerance:float=0.20,exclude_known_zones:bool|None=None,candidate_start:pd.Timestamp|None=None,candidate_end:pd.Timestamp|None=None)->pd.DataFrame:
    if contacts.empty:return pd.DataFrame()
    if "sigma60" not in bars.columns:raise ValueError("bars must include sigma60 for matched controls")
    if exclude_known_zones is None:exclude_known_zones=bool(config.control_exclude_known_zones)
    rng=np.random.default_rng(config.control_seed); times=bars.index
    if not isinstance(times,pd.DatetimeIndex) or times.tz is None:raise ValueError("bars index must be timezone-aware DatetimeIndex")
    times_ns=times.asi8; close=bars.close.to_numpy(float); sigma=pd.to_numeric(bars.sigma60,errors="coerce").to_numpy(float); valid_sigma=np.isfinite(sigma)&(sigma>0); active=bars["quote_active"].astype(bool).to_numpy() if "quote_active" in bars.columns else quote_activity_mask(bars).to_numpy(); candidate_time=np.ones(len(times),dtype=bool)
    if candidate_start is not None:
        start_ts=pd.Timestamp(candidate_start); start_ts=start_ts.tz_localize("UTC") if start_ts.tzinfo is None else start_ts.tz_convert("UTC"); candidate_time&=times_ns>=int(start_ts.value)
    if candidate_end is not None:
        end_ts=pd.Timestamp(candidate_end); end_ts=end_ts.tz_localize("UTC") if end_ts.tzinfo is None else end_ts.tz_convert("UTC"); candidate_time&=times_ns<int(end_ts.value)
    sessions=np.asarray([session_bucket(ts,config.timezone) for ts in times],dtype=object); approach_state=approach_state_arrays(bars,bars["sigma60"],config.timezone,lookback=5); hours=approach_state["local_hour"]; approach_dirs=approach_state["approach_direction"]; approach_bands=approach_state["approach_band"]; tree=_KnownZonePrefixTree(zones if (exclude_known_zones and not zones.empty) else pd.DataFrame(columns=["known_time","lower","upper"]))
    match_index={}; base_valid=valid_sigma&active&candidate_time&(approach_bands>=0); keys=pd.unique(pd.Series(list(zip(sessions,hours,approach_dirs,approach_bands)),dtype=object))
    for key in keys:
        sess,hour,adir,aband=key; idx=np.flatnonzero(base_valid&(sessions==sess)&(hours==hour)&(approach_dirs==adir)&(approach_bands==aband))
        if not len(idx):continue
        order=np.argsort(sigma[idx],kind="mergesort"); match_index[(sess,int(hour),int(adir),int(aband))]=(sigma[idx][order],idx[order])
    rows=[]; one_hour_ns=3_600_000_000_000
    for c in contacts.itertuples(index=False):
        sig=float(c.sigma60)
        if not np.isfinite(sig) or sig<=0:continue
        session=c.session; source_side=getattr(c,"side","NEUTRAL"); src_idx=int(getattr(c,"contact_idx")); source_hour=int(getattr(c,"local_hour",hours[src_idx])); source_approach_dir=int(getattr(c,"approach_direction",approach_dirs[src_idx])); source_approach_band=int(getattr(c,"approach_band",approach_bands[src_idx])); width=float(c.upper-c.lower); contact_ns=int(pd.Timestamp(c.contact_time).value); margin=max(width,config.point_zone_sigma_mult*sig)*2.0
        if exclude_known_zones:
            mask=(sessions==session)&valid_sigma&candidate_time; mask&=sigma>=sig*(1-sigma_tolerance); mask&=sigma<=sig*(1+sigma_tolerance); mask&=np.abs(times_ns-contact_ns)>=one_hour_ns; pool_idx=np.flatnonzero(mask)
            if len(pool_idx)==0:continue
            candidate_indices=(int(pool_idx[int(pos)]) for pos in rng.permutation(len(pool_idx)))
        else:
            key=(session,source_hour,source_approach_dir,source_approach_band); svals,sidx=match_index.get(key,(np.empty(0),np.empty(0,dtype=int))); lo=int(np.searchsorted(svals,sig*(1-sigma_tolerance),side="left")); hi=int(np.searchsorted(svals,sig*(1+sigma_tolerance),side="right"))
            if hi<=lo:continue
            selected=[]; used=set(); max_draws=max(64,8*controls_per_contact); draws=0
            while len(selected)<controls_per_contact and draws<max_draws:
                p=int(rng.integers(lo,hi)); draws+=1; idx=int(sidx[p])
                if idx in used or abs(int(times_ns[idx])-contact_ns)<one_hour_ns:continue
                used.add(idx); selected.append(idx)
            if len(selected)<controls_per_contact:
                cand=sidx[lo:hi]; cand=cand[np.abs(times_ns[cand]-contact_ns)>=one_hour_ns]
                if used:cand=cand[~np.isin(cand,np.fromiter(used,dtype=int))]
                need=min(controls_per_contact-len(selected),len(cand))
                if need:
                    picks=np.atleast_1d(rng.choice(len(cand),size=need,replace=False)); selected.extend(int(cand[int(p)]) for p in picks)
            candidate_indices=iter(selected)
        made=0
        for idx in candidate_indices:
            ts=times[idx]; px=float(close[idx]); near=tree.any_near(int(times_ns[idx]),px,margin) if exclude_known_zones else False
            if exclude_known_zones and near:continue
            rows.append({"zone_id":f"CTRL_{len(rows):08d}","matched_to_zone_id":c.zone_id,"matched_to_stack_id":getattr(c,"stack_id",None),"matched_constituent_families":getattr(c,"constituent_families",None),"family":"CONTROL","variant":"MATCHED_ARBITRARY_TIME_PRICE","side":"NEUTRAL" if exclude_known_zones else source_side,"control_source_side":source_side,"zone_known_time":ts,"contact_time":ts,"contact_idx":idx,"lower":px-width/2,"upper":px+width/2,"center":px,"penetration_depth":0.5,"sigma60":float(sigma[idx]),"approach_direction":int(approach_dirs[idx]),"approach_move":float(approach_state["approach_move"][idx]),"approach_move_sigma":float(approach_state["approach_move_sigma"][idx]),"approach_abs_sigma":float(approach_state["approach_abs_sigma"][idx]),"approach_band":int(approach_bands[idx]),"local_hour":int(hours[idx]),"quote_active":bool(active[idx]),"session":session,"near_known_zone":bool(near),"_near_margin":float(margin),"control_exclusion_mode":"STRICT_NONZONE" if exclude_known_zones else "PRIMARY_ARBITRARY_MATCHED","control_sampler":"LEGACY_PERMUTATION" if exclude_known_zones else "ACTIVE_SESSION_HOUR_SIGMA_APPROACH_INDEX_V3"}); made+=1
            if made>=controls_per_contact:break
    out=pd.DataFrame.from_records(rows)
    if out.empty:return out
    if not exclude_known_zones:out["near_known_zone"]=_batch_near_known_zone(out,zones)
    return out.drop(columns=["_near_margin"],errors="ignore")
