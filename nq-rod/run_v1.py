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
NQ_URL = "https://raw.githubusercontent.com/axb0306/cme-futures-ohlc/main/NQ/NQ_1min_20260120_20260415.csv"
TZ = "America/New_York"
POINT_VALUE = 20.0


def metric(r):
    a=np.asarray(r,dtype=float)
    if len(a)==0:return {"n":0,"mean":None,"sum":0.0,"pf":None,"win_rate":None,"max_dd":None,"losing_streak":None}
    pos=a[a>0].sum();neg=-a[a<0].sum();pf=float(pos/neg) if neg>0 else (float("inf") if pos>0 else None)
    eq=np.cumsum(a);peak=np.maximum.accumulate(np.r_[0.0,eq])[:-1];dd=np.maximum(peak-eq,0.0)
    cur=streak=0
    for v in a:
        if v<0:cur+=1;streak=max(streak,cur)
        else:cur=0
    return {"n":int(len(a)),"mean":float(a.mean()),"sum":float(a.sum()),"pf":pf,"win_rate":float((a>0).mean()),"max_dd":float(dd.max(initial=0.0)),"losing_streak":int(streak)}


def norm_qqq(raw,tag,p):
    d=pd.read_csv(io.BytesIO(raw));lk={str(c).strip().lower():c for c in d.columns};dtc=lk.get("ds") or lk.get("datetime") or lk.get("timestamp")
    if dtc is None:raise RuntimeError(f"{tag}: no datetime")
    ren={dtc:"dt"}
    for c in ["open","high","low","close"]:
        if c not in lk:raise RuntimeError(f"{tag}: missing {c}")
        ren[lk[c]]=c
    d=d.rename(columns=ren)
    if "unique_id" in lk and lk["unique_id"] in d.columns:d=d[d[lk["unique_id"]].astype(str).str.upper().eq("QQQ")]
    d["dt"]=pd.to_datetime(d["dt"],errors="coerce")
    for c in ["open","high","low","close"]:d[c]=pd.to_numeric(d[c],errors="coerce")
    d=d.dropna(subset=["dt","open","high","low","close"]);d["priority"]=p;d["source"]=tag
    return d[["dt","open","high","low","close","priority","source"]]


def load_qqq(out):
    fs=[];qa=[]
    for tag,url,p in QQQ_URLS:
        rr=requests.get(url,timeout=180);rr.raise_for_status();f=norm_qqq(rr.content,tag,p);fs.append(f)
        qa.append({"tag":tag,"url":url,"sha256":hashlib.sha256(rr.content).hexdigest(),"rows":int(len(f)),"min":str(f.dt.min()),"max":str(f.dt.max())})
    d=pd.concat(fs,ignore_index=True).sort_values(["dt","priority"]).drop_duplicates("dt",keep="last").sort_values("dt")
    d["date"]=d.dt.dt.normalize();d["minute"]=d.dt.dt.hour*60+d.dt.dt.minute;d=d[(d.minute>=570)&(d.minute<=955)].copy()
    (out/"qqq_qa.json").write_text(json.dumps({"sources":qa,"rows_rth":int(len(d)),"min":str(d.dt.min()),"max":str(d.dt.max())},indent=2))
    return d


def qqq_trades(d,cost_bps):
    rows=[];prev_close=None
    for date,g in d.groupby("date",sort=True):
        g=g.sort_values("minute").drop_duplicates("minute",keep="last")
        sig=g[g.minute.eq(925)]   # 15:25 bar close = price at 15:30
        ent=g[g.minute.eq(930)]   # 15:30 open
        clo=g[g.minute.eq(955)]   # 15:55 close = 16:00
        if prev_close is not None and len(sig)==len(ent)==len(clo)==1:
            sp=float(sig.iloc[0].close);direction=1 if sp>prev_close else (-1 if sp<prev_close else 0)
            if direction:
                ep=float(ent.iloc[0].open);xp=float(clo.iloc[0].close);gross=direction*(xp/ep-1.0);net=gross-cost_bps/10000.0
                rows.append({"date":date,"direction":"long" if direction>0 else "short","prior_close":prev_close,"signal_px":sp,"entry":ep,"exit":xp,"gross":gross,"net":net})
        if len(clo)==1:prev_close=float(clo.iloc[0].close)
    return pd.DataFrame(rows)


def load_nq(out):
    rr=requests.get(NQ_URL,timeout=180);rr.raise_for_status();raw=rr.content
    d=pd.read_csv(io.BytesIO(raw));d["datetime"]=pd.to_datetime(d["datetime"],utc=True,errors="coerce")
    for c in ["open","high","low","close","volume"]:d[c]=pd.to_numeric(d[c],errors="coerce")
    d=d.dropna(subset=["datetime","open","high","low","close"]).sort_values("datetime").drop_duplicates("datetime",keep="last")
    d.index=d["datetime"].dt.tz_convert(TZ);d=d[["open","high","low","close","volume"]].between_time("09:30","15:59");d=d[d.index.weekday<5]
    cnt=pd.Series(1,index=d.index).groupby(d.index.normalize()).sum()
    (out/"nq_qa.json").write_text(json.dumps({"url":NQ_URL,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"rows_rth":int(len(d)),"min":str(d.index.min()),"max":str(d.index.max()),"days":int(cnt.size),"median_rows_day":float(cnt.median()),"days_ge380":int((cnt>=380).sum())},indent=2))
    return d


def nq_trades(d,cost_usd):
    rows=[];prev_close=None
    for date,g in d.groupby(d.index.normalize(),sort=True):
        g=g.sort_index();mp={ts.hour*60+ts.minute:ts for ts in g.index};sig=mp.get(929);ent=mp.get(930);clo=mp.get(959)
        if prev_close is not None and sig is not None and ent is not None and clo is not None:
            sp=float(g.loc[sig,"close"]);direction=1 if sp>prev_close else (-1 if sp<prev_close else 0)
            if direction:
                ep=float(g.loc[ent,"open"]);xp=float(g.loc[clo,"close"]);gross=direction*(xp-ep);net=gross-cost_usd/POINT_VALUE
                rows.append({"date":date,"direction":"long" if direction>0 else "short","prior_close":prev_close,"signal_px":sp,"entry":ep,"exit":xp,"gross_points":gross,"net_points":net,"net_usd":net*POINT_VALUE})
        if clo is not None:prev_close=float(g.loc[clo,"close"])
    return pd.DataFrame(rows)


def annual(t,col):
    if t.empty:return {}
    z=t.copy();z["year"]=pd.to_datetime(z.date).dt.year
    return {str(int(y)):metric(g[col].to_numpy()) for y,g in z.groupby("year")}


def monthly(t,col):
    if t.empty:return {}
    z=t.copy();z["month"]=pd.to_datetime(z.date).dt.strftime("%Y-%m")
    return {str(m):metric(g[col].to_numpy()) for m,g in z.groupby("month")}


def main():
    out=Path("nq-rod/results/v1");out.mkdir(parents=True,exist_ok=True)
    try:
        q=load_qqq(out);n=load_nq(out);qres={};nres={};led=[]
        for sc,bps in {"PRIMARY":2.0,"STRESS":5.0}.items():
            t=qqq_trades(q,bps);t["scenario"]=sc;t["asset"]="QQQ";led.append(t)
            post=t[(t.date>=pd.Timestamp("2022-01-01"))&(t.date<pd.Timestamp("2026-01-01"))];part=t[t.date>=pd.Timestamp("2026-01-01")]
            qres[sc]={"post_2022_2025":metric(post.net.to_numpy()),"partial_2026":metric(part.net.to_numpy()),"annual":annual(post,"net")}
        for sc,cost in {"PRIMARY":15.0,"STRESS":25.0}.items():
            t=nq_trades(n,cost);t["scenario"]=sc;t["asset"]="NQ";led.append(t)
            nres[sc]={"full":metric(t.net_points.to_numpy()),"monthly":monthly(t,"net_points")}
        pd.concat(led,ignore_index=True,sort=False).to_csv(out/"trades.csv",index=False)
        qp=qres["PRIMARY"]["post_2022_2025"];np_=nres["PRIMARY"]["full"];ns=nres["STRESS"]["full"]
        py=sum(1 for v in qres["PRIMARY"]["annual"].values() if v["sum"]>0)
        pm=sum(1 for m,v in nres["PRIMARY"]["monthly"].items() if m in {"2026-02","2026-03","2026-04"} and v["sum"]>0)
        gates={"qqq_n_ge900":qp["n"]>=900,"qqq_mean_positive":qp["mean"] is not None and qp["mean"]>0,"qqq_pf_ge1_05":qp["pf"] is not None and qp["pf"]>=1.05,"qqq_positive_years_ge3":py>=3,
               "nq_n_ge45":np_["n"]>=45,"nq_mean_points_positive":np_["mean"] is not None and np_["mean"]>0,"nq_pf_ge1_15":np_["pf"] is not None and np_["pf"]>=1.15,"nq_positive_feb_mar_apr_ge2":pm>=2,
               "nq_dd_le400pts":np_["max_dd"] is not None and np_["max_dd"]<=400,"nq_stress_mean_positive":ns["mean"] is not None and ns["mean"]>0,"nq_stress_pf_ge1_05":ns["pf"] is not None and ns["pf"]>=1.05}
        nq_keys=[k for k in gates if k.startswith("nq_")];qqq_keys=[k for k in gates if k.startswith("qqq_")];nq_pass=all(gates[k] for k in nq_keys);qqq_pass=all(gates[k] for k in qqq_keys)
        if nq_pass and qqq_pass:status="NQ_ROD_INTRADAY_MOMENTUM_V1_PASS_FOR_PROPFIRM_RISK_RESEARCH"
        elif nq_pass:status="NQ_ROD_INTRADAY_MOMENTUM_V1_NQ_PASS_QQQ_NONCONFIRMING_REQUIRES_SECOND_FUTURES_REPLICATION"
        else:status="NQ_ROD_INTRADAY_MOMENTUM_V1_NO_GO_OR_INCONCLUSIVE"
        res={"status":status,"qqq":qres,"nq":nres,"qqq_positive_years":py,"nq_positive_feb_mar_apr":pm,"gates":gates,
             "notes":["rROD sign rule frozen from Baltussen et al. 2021 before outcome calculation.","Direct NQ source is mandatory core evidence; GetData proxy is not used.","No transaction-cost assumption from the paper is relied upon; explicit primary/stress costs are applied here."]}
        (out/"RESULT.json").write_text(json.dumps(res,indent=2,allow_nan=False));print(json.dumps(res,indent=2,allow_nan=False))
    except Exception as e:
        res={"status":"NQ_ROD_INTRADAY_MOMENTUM_V1_INVALID_ABORT","error":repr(e)};(out/"RESULT.json").write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2));raise

if __name__=="__main__":main()
