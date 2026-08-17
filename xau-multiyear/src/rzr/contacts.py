from __future__ import annotations

from typing import Iterable, List
import numpy as np
import pandas as pd

from .config import ResearchConfig
from .features import approach_state_arrays, quote_activity_mask, session_bucket
from .types import Zone, ZoneSide


class _IntervalContactTree:
    def __init__(self, high: np.ndarray, low: np.ndarray, valid: np.ndarray):
        n=len(high); size=1
        while size<n:size<<=1
        self.n=n; self.size=size
        self.max_high=np.full(2*size,-np.inf,dtype=float); self.min_low=np.full(2*size,np.inf,dtype=float)
        h=np.asarray(high,dtype=float).copy(); l=np.asarray(low,dtype=float).copy(); v=np.asarray(valid,dtype=bool)
        h[~v]=-np.inf; l[~v]=np.inf
        self.max_high[size:size+n]=h; self.min_low[size:size+n]=l
        for node in range(size-1,0,-1):
            self.max_high[node]=max(self.max_high[node*2],self.max_high[node*2+1]); self.min_low[node]=min(self.min_low[node*2],self.min_low[node*2+1])

    def first_intersection(self,start:int,lower:float,upper:float)->int:
        if start>=self.n or lower>upper:return -1
        stack=[(1,0,self.size)]
        while stack:
            node,lo,hi=stack.pop()
            if hi<=start or lo>=self.n:continue
            if self.max_high[node]<lower or self.min_low[node]>upper:continue
            if hi-lo==1:return lo
            mid=(lo+hi)//2; stack.append((node*2+1,mid,hi)); stack.append((node*2,lo,mid))
        return -1


def find_first_contacts(bars: pd.DataFrame, zones: Iterable[Zone], sigma60: pd.Series, config: ResearchConfig) -> pd.DataFrame:
    times=bars.index; high=bars.high.to_numpy(float); low=bars.low.to_numpy(float); sigmas=sigma60.reindex(times).to_numpy(float)
    valid_sigma=np.isfinite(sigmas)&(sigmas>0)
    active=bars["quote_active"].astype(bool).to_numpy() if "quote_active" in bars.columns else quote_activity_mask(bars).to_numpy()
    tree=_IntervalContactTree(high,low,valid_sigma&active); approach_state=approach_state_arrays(bars,sigma60,config.timezone,lookback=5)
    records=[]
    for z in zones:
        start=int(times.searchsorted(z.known_time,side="left")); i=tree.first_intersection(start,float(z.lower),float(z.upper))
        if i<0:continue
        width=float(z.upper-z.lower)
        if width<=0:continue
        if z.side==ZoneSide.SUPPORT:penetration=max(0.0,min(1.5,(z.upper-low[i])/width))
        elif z.side==ZoneSide.RESISTANCE:penetration=max(0.0,min(1.5,(high[i]-z.lower)/width))
        else:penetration=max(0.0,min(1.5,(min(high[i],z.upper)-max(low[i],z.lower))/width))
        records.append({"zone_id":z.zone_id,"family":z.family.value,"variant":z.variant,"side":z.side.value,"zone_known_time":z.known_time,"contact_time":times[i],"contact_idx":i,"lower":z.lower,"upper":z.upper,"center":z.center,"penetration_depth":penetration,"sigma60":float(sigmas[i]),"approach_direction":int(approach_state["approach_direction"][i]),"approach_move":float(approach_state["approach_move"][i]),"approach_move_sigma":float(approach_state["approach_move_sigma"][i]),"approach_abs_sigma":float(approach_state["approach_abs_sigma"][i]),"approach_band":int(approach_state["approach_band"][i]),"local_hour":int(approach_state["local_hour"][i]),"session":session_bucket(times[i],config.timezone)})
    return pd.DataFrame.from_records(records)
