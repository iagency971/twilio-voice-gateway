from __future__ import annotations

import json
from typing import List
import bisect
import numpy as np
import pandas as pd

from .config import ResearchConfig
from .features import (robust_sigma60, point_half_width, quote_activity_mask,
                       recent_quote_activity_mask, session_instance_key, trading_day_key)
from .resample import resample_ohlc
from .types import Zone, ZoneFamily, ZoneSide


def _make_zone_id(prefix: str, n: int) -> str:
    return f"{prefix}_{n:08d}"


def previous_period_levels(bars: pd.DataFrame, sigma60: pd.Series, config: ResearchConfig) -> List[Zone]:
    out: List[Zone] = []
    widths = point_half_width(bars, sigma60, config)
    active = bars.loc[quote_activity_mask(bars)]
    if active.empty:
        return out
    day_key = pd.Series([trading_day_key(ts, config.timezone) for ts in active.index], index=active.index)
    daily=[]
    for d, idxs in day_key.groupby(day_key, sort=True).groups.items():
        g=active.loc[list(idxs)]
        if not g.empty: daily.append((d,g.index[0],g.index[-1],float(g.high.max()),float(g.low.min())))
    daily.sort(key=lambda x:x[1])
    for i in range(1,len(daily)):
        prev,cur=daily[i-1],daily[i]; known=cur[1]
        if known not in widths.index or pd.isna(widths.loc[known]): continue
        w=float(widths.loc[known])
        for label,px,side in [("PDH",prev[3],ZoneSide.RESISTANCE),("PDL",prev[4],ZoneSide.SUPPORT)]:
            out.append(Zone(_make_zone_id(label,len(out)),ZoneFamily.OBJECTIVE_LIQUIDITY,label,side,prev[2],known,px-w,px+w,px,"D1",json.dumps({"source_trading_date":str(prev[0])})))
    week_keys=pd.Series([pd.Timestamp(d).to_period("W-SUN").start_time.date() for d in day_key],index=active.index)
    weekly=[]
    for key,idxs in week_keys.groupby(week_keys,sort=True).groups.items():
        g=active.loc[list(idxs)]; weekly.append((key,g.index[0],g.index[-1],float(g.high.max()),float(g.low.min())))
    weekly.sort(key=lambda x:x[1])
    for i in range(1,len(weekly)):
        prev,cur=weekly[i-1],weekly[i]; known=cur[1]
        if known not in widths.index or pd.isna(widths.loc[known]): continue
        w=float(widths.loc[known])
        for label,px,side in [("PWH",prev[3],ZoneSide.RESISTANCE),("PWL",prev[4],ZoneSide.SUPPORT)]:
            out.append(Zone(_make_zone_id(label,len(out)),ZoneFamily.OBJECTIVE_LIQUIDITY,label,side,prev[2],known,px-w,px+w,px,"W1",json.dumps({"source_week":str(prev[0])})))
    return out


def completed_session_levels(bars: pd.DataFrame, sigma60: pd.Series, config: ResearchConfig) -> List[Zone]:
    widths=point_half_width(bars,sigma60,config); active=bars.loc[quote_activity_mask(bars)]; out=[]
    if active.empty:return out
    keys=pd.Series([session_instance_key(ts,config.timezone) for ts in active.index],index=active.index,dtype=object)
    instances=[]; seen=set()
    for ts,key in keys.items():
        if key not in seen: seen.add(key); instances.append(key)
    for key in instances:
        idxs=keys.index[keys.map(lambda v:v==key)]; g=active.loc[idxs]
        if g.empty: continue
        pos=active.index.searchsorted(g.index[-1],side="right")
        if pos>=len(active):continue
        known=active.index[pos]
        if pd.isna(widths.loc[known]):continue
        name=key[0]; hi,lo=float(g.high.max()),float(g.low.min()); w=float(widths.loc[known])
        out.append(Zone(_make_zone_id(f"{name}_H",len(out)),ZoneFamily.OBJECTIVE_LIQUIDITY,f"{name}_HIGH",ZoneSide.RESISTANCE,g.index[-1],known,hi-w,hi+w,hi,"SESSION",json.dumps({"session_date":str(key[1])})))
        out.append(Zone(_make_zone_id(f"{name}_L",len(out)),ZoneFamily.OBJECTIVE_LIQUIDITY,f"{name}_LOW",ZoneSide.SUPPORT,g.index[-1],known,lo-w,lo+w,lo,"SESSION",json.dumps({"session_date":str(key[1])})))
    return out


def round_number_levels(bars: pd.DataFrame, sigma60: pd.Series, config: ResearchConfig) -> List[Zone]:
    widths=point_half_width(bars,sigma60,config); out=[]; seen=set(); active=quote_activity_mask(bars)
    for ts,row in bars.loc[active].iterrows():
        if pd.isna(widths.loc[ts]):continue
        c=float(row.close); sig=float(sigma60.loc[ts]) if not pd.isna(sigma60.loc[ts]) else np.nan
        if not np.isfinite(sig) or sig<=0:continue
        w=float(widths.loc[ts])
        for step in config.round_number_steps:
            base=round(c/step)*step
            for px in (base-step,base,base+step):
                key=(step,round(px,6))
                if key in seen:continue
                if abs(c-px)<=3.0*sig:
                    seen.add(key); out.append(Zone(_make_zone_id(f"ROUND_{step:g}",len(out)),ZoneFamily.OBJECTIVE_LIQUIDITY,f"ROUND_{step:g}",ZoneSide.NEUTRAL,ts,ts,px-w,px+w,px,"PRICE",json.dumps({"step":step})))
    return out


def directional_change_turns(bars: pd.DataFrame, sigma60: pd.Series, config: ResearchConfig) -> pd.DataFrame:
    pos=np.flatnonzero(quote_activity_mask(bars).to_numpy(bool))
    if len(pos)==0:return pd.DataFrame()
    times=bars.index; hi=bars.high.to_numpy(float); lo=bars.low.to_numpy(float); close=bars.close.to_numpy(float); sigmas=sigma60.reindex(bars.index).to_numpy(float); records=[]
    for delta_mult in config.directional_change_deltas:
        mode=0; extreme_price=None; extreme_time=None
        for i in pos:
            sig=sigmas[i]
            if not np.isfinite(sig) or sig<=0:continue
            h,l,c=hi[i],lo[i],close[i]; ts=times[i]; threshold=float(delta_mult*sig)
            if extreme_price is None: extreme_price,extreme_time,mode=c,ts,+1; continue
            if mode>=0:
                if h>extreme_price: extreme_price,extreme_time=h,ts
                if extreme_price-l>=threshold:
                    records.append({"delta_mult":delta_mult,"kind":"HIGH","origin_time":extreme_time,"known_time":ts,"price":extreme_price,"reaction_amplitude":extreme_price-l}); mode=-1; extreme_price,extreme_time=l,ts
            else:
                if l<extreme_price: extreme_price,extreme_time=l,ts
                if h-extreme_price>=threshold:
                    records.append({"delta_mult":delta_mult,"kind":"LOW","origin_time":extreme_time,"known_time":ts,"price":extreme_price,"reaction_amplitude":h-extreme_price}); mode=+1; extreme_price,extreme_time=h,ts
    return pd.DataFrame.from_records(records)


def _dedupe_directional_turns(turns: pd.DataFrame) -> pd.DataFrame:
    if turns.empty:return turns
    x=turns.sort_values(["known_time","origin_time","kind","delta_mult"]).copy(); grouped=[]
    for (origin,kind),g in x.groupby(["origin_time","kind"],sort=False):
        g2=g.sort_values("delta_mult"); row=g2.iloc[-1].to_dict(); row["scale_count"]=int(len(g2)); row["delta_mult_max"]=float(g2["delta_mult"].max()); row["reaction_amplitude"]=float(g2["reaction_amplitude"].max()); grouped.append(row)
    return pd.DataFrame(grouped).sort_values("known_time").reset_index(drop=True)


def memory_zones(bars: pd.DataFrame, sigma60: pd.Series, config: ResearchConfig) -> List[Zone]:
    turns=_dedupe_directional_turns(directional_change_turns(bars,sigma60,config))
    if turns.empty:return []
    widths=point_half_width(bars,sigma60,config); clusters=[]; spatial=[]; out=[]; min_sep=pd.Timedelta(minutes=config.memory_min_separation_minutes)
    for tr in turns.itertuples(index=False):
        kt=pd.Timestamp(tr.known_time)
        if kt not in widths.index or pd.isna(widths.loc[kt]):continue
        w=float(widths.loc[kt]); px=float(tr.price); left=bisect.bisect_left(spatial,(px-w,-1)); right=bisect.bisect_right(spatial,(px+w,10**18)); best=None; best_key=None
        for center,ci in spatial[left:right]:
            cl=clusters[ci]
            if kt-cl["last_known_time"]<min_sep:continue
            d=abs(px-cl["center"])
            if d<=w:
                key=(d,ci)
                if best_key is None or key<best_key:best_key,best=key,ci
        reaction_amp=float(tr.reaction_amplitude); tr_kind=str(tr.kind); tr_scale=float(getattr(tr,"delta_mult_max",tr.delta_mult))
        if best is None:
            ci=len(clusters); clusters.append({"center":px,"weight":max(reaction_amp,1e-9),"count":1,"origin_time":pd.Timestamp(tr.origin_time),"known_time":kt,"last_known_time":kt,"kind_high":int(tr_kind=="HIGH"),"kind_low":int(tr_kind=="LOW"),"max_scale":tr_scale}); bisect.insort(spatial,(px,ci)); continue
        cl=clusters[best]; old_pair=(cl["center"],best); k=bisect.bisect_left(spatial,old_pair)
        if k<len(spatial) and spatial[k]==old_pair:spatial.pop(k)
        else:spatial.remove(old_pair)
        wt=max(reaction_amp,1e-9); cl["center"]=(cl["center"]*cl["weight"]+px*wt)/(cl["weight"]+wt); cl["weight"]+=wt; cl["count"]+=1; cl["known_time"]=kt; cl["last_known_time"]=kt; cl["kind_high"]+=int(tr_kind=="HIGH"); cl["kind_low"]+=int(tr_kind=="LOW"); cl["max_scale"]=max(cl["max_scale"],tr_scale); bisect.insort(spatial,(cl["center"],best))
        if cl["count"]==2:
            side=ZoneSide.RESISTANCE if cl["kind_high"]>cl["kind_low"] else ZoneSide.SUPPORT if cl["kind_low"]>cl["kind_high"] else ZoneSide.NEUTRAL
            out.append(Zone(_make_zone_id("MEM",len(out)),ZoneFamily.MEMORY,"DIRECTIONAL_CHANGE_CLUSTER",side,cl["origin_time"],kt,cl["center"]-w,cl["center"]+w,cl["center"],"M1",json.dumps({"constituents_at_activation":2,"max_delta_scale":cl["max_scale"]})))
    return out


def fvg_zones(bars: pd.DataFrame, config: ResearchConfig) -> List[Zone]:
    out=[]; hi2=bars.high.shift(2); lo2=bars.low.shift(2); recent=recent_quote_activity_mask(bars,lookback_minutes=3); valid3=recent & recent.shift(1,fill_value=False) & recent.shift(2,fill_value=False)
    for i,ts in enumerate(bars.index):
        if i<2 or not bool(valid3.iloc[i]):continue
        low=float(bars.at[ts,"low"]); high=float(bars.at[ts,"high"])
        if low>float(hi2.loc[ts]):
            lo,up=float(hi2.loc[ts]),low; out.append(Zone(_make_zone_id("FVG_B",len(out)),ZoneFamily.FVG,"FVG_3BAR",ZoneSide.SUPPORT,bars.index[i-2],ts,lo,up,(lo+up)/2,"M1"))
        if high<float(lo2.loc[ts]):
            lo,up=high,float(lo2.loc[ts]); out.append(Zone(_make_zone_id("FVG_S",len(out)),ZoneFamily.FVG,"FVG_3BAR",ZoneSide.RESISTANCE,bars.index[i-2],ts,lo,up,(lo+up)/2,"M1"))
    return out


def _true_range(df: pd.DataFrame) -> pd.Series:
    prev=df.close.shift(1); return pd.concat([(df.high-df.low).abs(),(df.high-prev).abs(),(df.low-prev).abs()],axis=1).max(axis=1)


def displacement_origin_zones(bars: pd.DataFrame, config: ResearchConfig) -> List[Zone]:
    out=[]; active_bars=bars.loc[quote_activity_mask(bars)]
    for tf in config.do_z_timeframes:
        x=resample_ohlc(active_bars,tf)
        if len(x)<100:continue
        tr=_true_range(x); body=(x.close-x.open).abs(); disp_threshold=body.shift(1).rolling(20*max(1,int(pd.Timedelta("1D")/pd.Timedelta(tf))),min_periods=50).quantile(config.doz_displacement_quantile); recent_hi=x.high.shift(1).rolling(20,min_periods=10).max(); recent_lo=x.low.shift(1).rolling(20,min_periods=10).min(); efficiency=body/tr.replace(0,np.nan)
        for i in range(1,len(x)):
            ts=x.index[i]
            if pd.isna(disp_threshold.iloc[i]) or pd.isna(efficiency.iloc[i]):continue
            bull=x.close.iloc[i]>x.open.iloc[i] and body.iloc[i]>=disp_threshold.iloc[i] and efficiency.iloc[i]>=config.doz_efficiency_min and x.close.iloc[i]>recent_hi.iloc[i]
            bear=x.close.iloc[i]<x.open.iloc[i] and body.iloc[i]>=disp_threshold.iloc[i] and efficiency.iloc[i]>=config.doz_efficiency_min and x.close.iloc[i]<recent_lo.iloc[i]
            if not bull and not bear:continue
            direction=1 if bull else -1; opp_idx=None
            for j in range(i-1,max(-1,i-config.doz_base_max_bars-1),-1):
                if (direction==1 and x.close.iloc[j]<x.open.iloc[j]) or (direction==-1 and x.close.iloc[j]>x.open.iloc[j]):opp_idx=j;break
            if opp_idx is None:continue
            side=ZoneSide.SUPPORT if bull else ZoneSide.RESISTANCE; row=x.iloc[opp_idx]; variants=[("DOZ_LAST",float(row.low),float(row.high)),("DOZ_BODY",float(min(row.open,row.close)),float(max(row.open,row.close)))]; base=x.iloc[max(0,opp_idx-2):opp_idx+1]; variants.append(("DOZ_BASE",float(base.low.min()),float(base.high.max())))
            for variant,lo,up in variants:
                if up<=lo:continue
                out.append(Zone(_make_zone_id(variant,len(out)),ZoneFamily.DISPLACEMENT_ORIGIN,variant,side,x.index[opp_idx],ts,lo,up,(lo+up)/2,tf,json.dumps({"breakout_time":ts.isoformat(),"efficiency":float(efficiency.iloc[i])})))
    return out


def generate_baseline_zones(bars: pd.DataFrame, config: ResearchConfig) -> List[Zone]:
    sigma=robust_sigma60(bars); zones=[]
    zones.extend(previous_period_levels(bars,sigma,config)); zones.extend(completed_session_levels(bars,sigma,config)); zones.extend(round_number_levels(bars,sigma,config)); zones.extend(memory_zones(bars,sigma,config)); zones.extend(fvg_zones(bars,config)); zones.extend(displacement_origin_zones(bars,config)); return zones
