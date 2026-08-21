#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

SPY_URL = "https://raw.githubusercontent.com/BrianWeiss1/StockList/main/5min_data_SPY_2015_to_2024.csv"
ES_URL = "https://raw.githubusercontent.com/axb0306/cme-futures-ohlc/main/ES/ES_1min_20260120_20260415.csv"
TZ = "America/New_York"
ES_POINT_VALUE = 50.0
EVENTS = pd.to_datetime([
    "2020-06-10","2020-09-16","2020-12-16",
    "2021-03-17","2021-06-16","2021-09-22","2021-12-15",
    "2022-03-16","2022-06-15","2022-09-21","2022-12-14",
    "2023-03-22","2023-06-14","2023-09-20","2023-12-13",
    "2024-03-20","2024-06-12","2024-09-18","2024-12-18",
]).normalize()


def stat(x):
    a=np.asarray(x,dtype=float)
    if len(a)==0:
        return {"n":0,"mean":None,"median":None,"sum":0.0,"pf":None,"win_rate":None}
    pos=a[a>0].sum(); neg=-a[a<0].sum()
    pf=float(pos/neg) if neg>0 else (float("inf") if pos>0 else None)
    return {"n":int(len(a)),"mean":float(a.mean()),"median":float(np.median(a)),"sum":float(a.sum()),"pf":pf,"win_rate":float((a>0).mean())}


def normalize_spy(raw: bytes, out: Path) -> pd.DataFrame:
    d=pd.read_csv(io.BytesIO(raw))
    orig=[str(c) for c in d.columns]
    lk={str(c).strip().lower():c for c in d.columns}

    dt=None
    for key in ["datetime","date_time","timestamp","time_stamp","ds","date"]:
        if key in lk:
            dt=lk[key]; break
    if dt is None and "date" in lk and "time" in lk:
        d["__dt__"]=d[lk["date"]].astype(str)+" "+d[lk["time"]].astype(str); dt="__dt__"
    elif dt is not None and str(dt).strip().lower()=="date" and "time" in lk:
        d["__dt__"]=d[dt].astype(str)+" "+d[lk["time"]].astype(str); dt="__dt__"
    if dt is None and len(d.columns) > 0 and str(d.columns[0]).strip().lower().startswith("unnamed"):
        dt=d.columns[0]
    if dt is None:
        raise RuntimeError(f"SPY datetime column unresolved. columns={orig}")

    def col(name):
        aliases={"open":["open","o"],"high":["high","h"],"low":["low","l"],"close":["close","c","adj close","adj_close"]}
        for a in aliases[name]:
            if a in lk:return lk[a]
        raise RuntimeError(f"SPY missing {name}; columns={orig}")

    oo,hh,ll,cc=[col(k) for k in ["open","high","low","close"]]
    ts=pd.to_datetime(d[dt],errors="coerce")
    if isinstance(ts.dtype, pd.DatetimeTZDtype):
        ts=ts.dt.tz_convert(TZ).dt.tz_localize(None)
        tz_mode="aware_converted_to_ET"
    else:
        tz_mode="naive_assumed_ET_after_anchor_QA"
    z=pd.DataFrame({"dt":ts,"open":pd.to_numeric(d[oo],errors="coerce"),"high":pd.to_numeric(d[hh],errors="coerce"),"low":pd.to_numeric(d[ll],errors="coerce"),"close":pd.to_numeric(d[cc],errors="coerce")}).dropna().sort_values("dt").drop_duplicates("dt",keep="last")
    z["date"]=z.dt.dt.normalize(); z["minute"]=z.dt.dt.hour*60+z.dt.dt.minute
    counts=z[z.minute.isin([570,955])].groupby("date").minute.nunique()
    anchor_days=int((counts>=2).sum()); total_days=int(z.date.nunique())
    qa={"url":SPY_URL,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"columns":orig,"tz_mode":tz_mode,"rows":int(len(z)),"min":str(z.dt.min()),"max":str(z.dt.max()),"total_days":total_days,"days_with_0930_and_1555":anchor_days,"anchor_fraction":anchor_days/max(total_days,1)}
    (out/"spy_data_qa.json").write_text(json.dumps(qa,indent=2))
    if qa["anchor_fraction"] < 0.70:
        raise RuntimeError(f"SPY session anchor QA failed: {qa}")
    return z


def spy_events(z: pd.DataFrame, cost_bps: float):
    rows=[]
    for ev in EVENTS:
        g=z[z.date.eq(ev)]
        ent=g[g.minute.eq(13*60+55)]
        ex=g[g.minute.eq(14*60+55)]
        if len(ent)==1 and len(ex)==1:
            ep=float(ent.iloc[0].open); xp=float(ex.iloc[0].open)
            gross=xp/ep-1.0; net=gross-cost_bps/10000.0
            rows.append({"date":ev,"entry":ep,"exit":xp,"gross_return":gross,"net_return":net})
        else:
            rows.append({"date":ev,"entry":np.nan,"exit":np.nan,"gross_return":np.nan,"net_return":np.nan})
    return pd.DataFrame(rows)


def annual(t):
    z=t.dropna(subset=["net_return"]).copy();z["year"]=pd.to_datetime(z.date).dt.year
    return {str(int(y)):stat(g.net_return.to_numpy()) for y,g in z.groupby("year")}


def load_es(raw: bytes, out: Path):
    d=pd.read_csv(io.BytesIO(raw));d["datetime"]=pd.to_datetime(d["datetime"],utc=True,errors="coerce")
    for c in ["open","high","low","close","volume"]:d[c]=pd.to_numeric(d[c],errors="coerce")
    d=d.dropna(subset=["datetime","open","high","low","close"]).sort_values("datetime").drop_duplicates("datetime",keep="last")
    d.index=d["datetime"].dt.tz_convert(TZ);d=d[["open","high","low","close","volume"]]
    (out/"es_data_qa.json").write_text(json.dumps({"url":ES_URL,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"rows":int(len(d)),"min":str(d.index.min()),"max":str(d.index.max())},indent=2))
    return d


def es_event(d: pd.DataFrame,cost_usd:float):
    day=pd.Timestamp("2026-03-18",tz=TZ)
    g=d[d.index.normalize().eq(day)]
    ent=g[(g.index.hour==13)&(g.index.minute==55)]
    ex=g[(g.index.hour==14)&(g.index.minute==55)]
    if len(ent)!=1 or len(ex)!=1:return {"present":False}
    ep=float(ent.iloc[0].open);xp=float(ex.iloc[0].open);gross=xp-ep;net=gross-cost_usd/ES_POINT_VALUE
    return {"present":True,"entry":ep,"exit":xp,"gross_points":gross,"net_points":net,"net_usd":net*ES_POINT_VALUE}


def main():
    out=Path("fomc-sep/results/v1");out.mkdir(parents=True,exist_ok=True)
    try:
        sr=requests.get(SPY_URL,timeout=180);sr.raise_for_status();spy=normalize_spy(sr.content,out)
        er=requests.get(ES_URL,timeout=180);er.raise_for_status();es=load_es(er.content,out)
        spy_res={};led=[]
        for sc,cost in {"PRIMARY":2.0,"STRESS":5.0}.items():
            t=spy_events(spy,cost);t["scenario"]=sc;led.append(t)
            executed=t.dropna(subset=["net_return"]).copy();ann=annual(executed)
            vals=executed.net_return.to_numpy();best2=np.sort(vals)[-2:] if len(vals)>=2 else np.array([])
            rem=np.sort(vals)[:-2] if len(vals)>=3 else np.array([])
            spy_res[sc]={"metrics":stat(vals),"annual":ann,"missing_events":[str(x.date()) for x in EVENTS if x not in set(executed.date)],"remove_best_2_mean":float(rem.mean()) if len(rem) else None,"best_2":best2.tolist()}
        pd.concat(led,ignore_index=True).to_csv(out/"spy_events.csv",index=False)
        es_res={sc:es_event(es,cost) for sc,cost in {"PRIMARY":30.0,"STRESS":55.0}.items()}
        p=spy_res["PRIMARY"]["metrics"];s=spy_res["STRESS"]["metrics"];positive_years=sum(1 for v in spy_res["PRIMARY"]["annual"].values() if v["sum"]>0)
        gates={"events_present_ge18":p["n"]>=18,"primary_mean_gt10bps":p["mean"] is not None and p["mean"]>0.001,"primary_pf_ge1_30":p["pf"] is not None and p["pf"]>=1.30,"positive_years_ge4_of5":positive_years>=4,"median_positive":p["median"] is not None and p["median"]>0,"stress_mean_positive":s["mean"] is not None and s["mean"]>0,"stress_pf_ge1_10":s["pf"] is not None and s["pf"]>=1.10,"remove_best2_mean_nonnegative":spy_res["PRIMARY"]["remove_best_2_mean"] is not None and spy_res["PRIMARY"]["remove_best_2_mean"]>=0}
        status="FOMC_SEP_RELIEF_RALLY_V1_PASS_EVENT_ACCELERATOR_CANDIDATE" if all(gates.values()) else "FOMC_SEP_RELIEF_RALLY_V1_NO_GO_OR_INCONCLUSIVE"
        obj={"status":status,"spy":spy_res,"spy_positive_years":positive_years,"es_2026_03_18_spotcheck":es_res,"gates":gates,"notes":["Rules/dates frozen before calculation.","SPY 2020-2024 is the primary post-publication persistence test; the single ES 2026 event is descriptive only.","No rescue filter permitted on these opened events."]}
        (out/"RESULT.json").write_text(json.dumps(obj,indent=2,allow_nan=False));print(json.dumps(obj,indent=2,allow_nan=False))
    except Exception as e:
        obj={"status":"FOMC_SEP_RELIEF_RALLY_V1_INVALID_ABORT","error":repr(e)};(out/"RESULT.json").write_text(json.dumps(obj,indent=2));print(json.dumps(obj,indent=2));raise
if __name__=="__main__":main()
