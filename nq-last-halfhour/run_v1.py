#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

QQQ_URLS = [
    ("HIST", "https://raw.githubusercontent.com/lvrusu/QQQ_price_data/main/QQQ5m_regular_raw_01_01_2000_to_04_10_2024.csv", 0),
    ("EXT", "https://raw.githubusercontent.com/lvrusu/QQQ_price_data/main/QQQ5m_Ext_J_23_to_Mar_20a_2026.csv", 1),
]
NQ_URL = "https://raw.githubusercontent.com/getdata-finance/nq-1m-ohlcv-stocks-historical-data/main/NQ_1m.csv"
TZ = "America/New_York"
NQ_POINT_VALUE = 20.0


def pf_metric(r: np.ndarray):
    pos = r[r > 0].sum()
    neg = -r[r < 0].sum()
    if neg > 0:
        return float(pos / neg)
    return float("inf") if pos > 0 else None


def stats(r: np.ndarray):
    r = np.asarray(r, dtype=float)
    if len(r) == 0:
        return {"n": 0, "mean": None, "sum": 0.0, "pf": None, "win_rate": None, "max_dd": None, "losing_streak": None}
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(peak - eq, 0.0)
    cur = streak = 0
    for v in r:
        if v < 0:
            cur += 1; streak = max(streak, cur)
        else:
            cur = 0
    return {"n": int(len(r)), "mean": float(r.mean()), "sum": float(r.sum()), "pf": pf_metric(r),
            "win_rate": float((r > 0).mean()), "max_dd": float(dd.max(initial=0.0)), "losing_streak": int(streak)}


def normalize_qqq(raw: bytes, tag: str, priority: int):
    d = pd.read_csv(io.BytesIO(raw))
    lookup = {str(c).strip().lower(): c for c in d.columns}
    dtc = lookup.get("ds") or lookup.get("datetime") or lookup.get("timestamp")
    if dtc is None:
        raise RuntimeError(f"{tag}: datetime column missing")
    ren = {dtc: "dt"}
    for c in ["open", "high", "low", "close"]:
        if c not in lookup: raise RuntimeError(f"{tag}: {c} missing")
        ren[lookup[c]] = c
    d = d.rename(columns=ren)
    if "unique_id" in lookup and lookup["unique_id"] in d.columns:
        d = d[d[lookup["unique_id"]].astype(str).str.upper().eq("QQQ")]
    d["dt"] = pd.to_datetime(d["dt"], errors="coerce")
    for c in ["open", "high", "low", "close"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["dt", "open", "high", "low", "close"])
    d["priority"] = priority; d["source"] = tag
    return d[["dt", "open", "high", "low", "close", "priority", "source"]]


def load_qqq(out: Path):
    frames=[]; qa=[]
    for tag,url,p in QQQ_URLS:
        rr=requests.get(url,timeout=180); rr.raise_for_status()
        f=normalize_qqq(rr.content,tag,p); frames.append(f)
        qa.append({"tag":tag,"url":url,"sha256":hashlib.sha256(rr.content).hexdigest(),"bytes":len(rr.content),
                   "rows":int(len(f)),"min":str(f.dt.min()),"max":str(f.dt.max())})
    d=pd.concat(frames,ignore_index=True).sort_values(["dt","priority"]).drop_duplicates("dt",keep="last").sort_values("dt")
    d["date"]=d.dt.dt.normalize(); d["minute"]=d.dt.dt.hour*60+d.dt.dt.minute
    d=d[(d.minute>=570)&(d.minute<=955)].copy()
    (out/"qqq_data_qa.json").write_text(json.dumps({"sources":qa,"rows_rth":int(len(d)),"min":str(d.dt.min()),"max":str(d.dt.max()),"duplicates":int(d.dt.duplicated().sum())},indent=2))
    return d


def qqq_trades(d: pd.DataFrame, cost_bps_rt: float):
    rows=[]; prev_close=None
    for date,g in d.groupby("date",sort=True):
        g=g.sort_values("minute").drop_duplicates("minute",keep="last")
        close_bar=g[g.minute.eq(955)]
        sig_bar=g[g.minute.eq(595)]  # 09:55 bar close = 10:00 price
        ent_bar=g[g.minute.eq(930)]  # 15:30 bar open
        if prev_close is not None and len(sig_bar)==1 and len(ent_bar)==1 and len(close_bar)==1:
            signal_px=float(sig_bar.iloc[0].close)
            direction=1 if signal_px>prev_close else (-1 if signal_px<prev_close else 0)
            if direction:
                entry=float(ent_bar.iloc[0].open); exit_px=float(close_bar.iloc[0].close)
                gross=direction*(exit_px/entry-1.0)
                net=gross-cost_bps_rt/10000.0
                rows.append({"date":date,"direction":"long" if direction>0 else "short","prior_close":prev_close,
                             "signal_px":signal_px,"entry":entry,"exit":exit_px,"gross_return":gross,"net_return":net})
        if len(close_bar)==1:
            prev_close=float(close_bar.iloc[0].close)
    return pd.DataFrame(rows)


def load_nq(out: Path):
    rr=requests.get(NQ_URL,timeout=180); rr.raise_for_status(); raw=rr.content
    d=pd.read_csv(io.BytesIO(raw))
    d["datetime"]=pd.to_datetime(d["datetime"],utc=True,errors="coerce")
    for c in ["open","high","low","close","volume"]: d[c]=pd.to_numeric(d[c],errors="coerce")
    d=d.dropna(subset=["datetime","open","high","low","close"]).sort_values("datetime").drop_duplicates("datetime",keep="last")
    idx=d["datetime"].dt.tz_convert(TZ); d.index=idx
    d=d[["open","high","low","close","volume"]].between_time("09:30","15:59"); d=d[d.index.weekday<5].copy()
    (out/"nq_data_qa.json").write_text(json.dumps({"url":NQ_URL,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"rows_rth":int(len(d)),
        "min":str(d.index.min()),"max":str(d.index.max()),"days":int(d.index.normalize().nunique()),"duplicates":int(d.index.duplicated().sum())},indent=2))
    return d


def nq_trades(d: pd.DataFrame, cost_usd_rt: float):
    rows=[]; prev_close=None
    for date,g in d.groupby(d.index.normalize(),sort=True):
        g=g.sort_index()
        bymin={ts.hour*60+ts.minute:ts for ts in g.index}
        cts=bymin.get(959); sts=bymin.get(599); ets=bymin.get(930) # 15:59, 09:59, 15:30
        if prev_close is not None and cts is not None and sts is not None and ets is not None:
            signal_px=float(g.loc[sts,"close"]); direction=1 if signal_px>prev_close else (-1 if signal_px<prev_close else 0)
            if direction:
                entry=float(g.loc[ets,"open"]); exit_px=float(g.loc[cts,"close"])
                gross_points=direction*(exit_px-entry); net_points=gross_points-cost_usd_rt/NQ_POINT_VALUE
                rows.append({"date":date,"direction":"long" if direction>0 else "short","prior_close":prev_close,"signal_px":signal_px,
                             "entry":entry,"exit":exit_px,"gross_points":gross_points,"net_points":net_points,"net_usd":net_points*NQ_POINT_VALUE})
        if cts is not None: prev_close=float(g.loc[cts,"close"])
    return pd.DataFrame(rows)


def annual_qqq(t):
    if t.empty:return {}
    z=t.copy();z["year"]=pd.to_datetime(z.date).dt.year
    return {str(int(y)):stats(g.net_return.to_numpy()) for y,g in z.groupby("year")}


def monthly_nq(t):
    if t.empty:return {}
    z=t.copy();z["month"]=pd.to_datetime(z.date).dt.strftime("%Y-%m")
    return {str(m):stats(g.net_points.to_numpy()) for m,g in z.groupby("month")}


def main():
    out=Path("nq-last-halfhour/results/v1");out.mkdir(parents=True,exist_ok=True)
    try:
        q=load_qqq(out); n=load_nq(out)
        qres={};nres={}; led=[]
        for scen,bps in {"PRIMARY":2.0,"STRESS":5.0}.items():
            t=qqq_trades(q,bps); t["scenario"]=scen;t["asset"]="QQQ";led.append(t)
            post=t[(t.date>=pd.Timestamp("2014-01-01"))&(t.date<pd.Timestamp("2026-01-01"))]
            recent=t[(t.date>=pd.Timestamp("2020-01-01"))&(t.date<pd.Timestamp("2026-01-01"))]
            partial=t[t.date>=pd.Timestamp("2026-01-01")]
            qres[scen]={"post_2014_2025":stats(post.net_return.to_numpy()),"recent_2020_2025":stats(recent.net_return.to_numpy()),
                        "partial_2026":stats(partial.net_return.to_numpy()),"annual":annual_qqq(post)}
        for scen,cost in {"PRIMARY":15.0,"STRESS":25.0}.items():
            t=nq_trades(n,cost);t["scenario"]=scen;t["asset"]="NQ";led.append(t)
            nres[scen]={"full_2026_sample":stats(t.net_points.to_numpy()),"monthly":monthly_nq(t)}
        pd.concat(led,ignore_index=True,sort=False).to_csv(out/"trades.csv",index=False)

        qp=qres["PRIMARY"]; np_=nres["PRIMARY"]["full_2026_sample"]; ns=nres["STRESS"]["full_2026_sample"]
        positive_years=sum(1 for v in qp["annual"].values() if v["sum"]>0)
        positive_months=sum(1 for v in nres["PRIMARY"]["monthly"].values() if v["sum"]>0)
        gates={
            "qqq_n_ge_2500":qp["post_2014_2025"]["n"]>=2500,
            "qqq_primary_mean_positive":qp["post_2014_2025"]["mean"] is not None and qp["post_2014_2025"]["mean"]>0,
            "qqq_primary_pf_ge_1_05":qp["post_2014_2025"]["pf"] is not None and qp["post_2014_2025"]["pf"]>=1.05,
            "qqq_positive_years_ge_8_of_12":positive_years>=8,
            "qqq_2020_2025_mean_nonnegative":qp["recent_2020_2025"]["mean"] is not None and qp["recent_2020_2025"]["mean"]>=0,
            "nq_n_ge_100":np_["n"]>=100,
            "nq_primary_mean_points_positive":np_["mean"] is not None and np_["mean"]>0,
            "nq_primary_pf_ge_1_10":np_["pf"] is not None and np_["pf"]>=1.10,
            "nq_positive_months_ge_4":positive_months>=4,
            "nq_max_dd_points_le_500":np_["max_dd"] is not None and np_["max_dd"]<=500,
            "nq_stress_mean_positive":ns["mean"] is not None and ns["mean"]>0,
            "nq_stress_pf_gt_1_02":ns["pf"] is not None and ns["pf"]>1.02,
        }
        passed=all(gates.values())
        status="NQ_LAST_HALFHOUR_MOMENTUM_V1_PASS_FOR_PROPFIRM_SIZING_RESEARCH" if passed else "NQ_LAST_HALFHOUR_MOMENTUM_V1_NO_GO_OR_INCONCLUSIVE"
        result={"status":status,"qqq":qres,"nq":nres,"qqq_positive_years_2014_2025":positive_years,"nq_positive_months":positive_months,"gates":gates,
                "notes":["Rule frozen from Gao et al. before calculation; no threshold/filter optimization.","QQQ post-publication persistence and NQ current usefulness are separate required gates.","NQ GetData is a price proxy, not official exchange tape; a PASS would still require CME/broker replication before live use."]}
        (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False));print(json.dumps(result,indent=2,allow_nan=False))
    except Exception as e:
        result={"status":"NQ_LAST_HALFHOUR_MOMENTUM_V1_INVALID_ABORT","error":repr(e)};(out/"RESULT.json").write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));raise

if __name__=="__main__":main()
