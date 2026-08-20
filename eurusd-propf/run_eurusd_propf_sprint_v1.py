#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures as cf
import gzip
import io
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import requests
from zoneinfo import ZoneInfo

BASE_URL = "https://candledata.fxcorporate.com/m1/EURUSD/{year}/{week}.csv.gz"
PIP = 0.0001
HALF_PIP = 0.5 * PIP
BASE_COST_PRICE = 0.00006  # $6/100k equivalent
STRESS_COST_PRICE = 0.00014  # $10/100k + 0.2 pip/side slippage
DEV_END = pd.Timestamp("2018-12-31")
OOS_START = pd.Timestamp("2019-01-01")
NY = ZoneInfo("America/New_York")
LONDON = ZoneInfo("Europe/London")


def iso_week_urls(start_year: int, end_year: int):
    for y in range(start_year, end_year + 1):
        for w in range(1, 54):
            yield y, w, BASE_URL.format(year=y, week=w)


def fetch_week(item, timeout=20):
    y, w, url = item
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "eurusd-propf-sprint-v1/1.0"})
        if r.status_code == 404:
            return y, w, None, "404"
        r.raise_for_status()
        raw = gzip.decompress(r.content)
        df = pd.read_csv(io.BytesIO(raw))
        if df.empty:
            return y, w, None, "empty"
        return y, w, df, "ok"
    except Exception as e:
        return y, w, None, f"error:{type(e).__name__}:{e}"


def normalize_week(df: pd.DataFrame) -> pd.DataFrame:
    cols = {str(c).strip(): c for c in df.columns}
    dt_col = None
    for c in df.columns:
        if str(c).strip().lower() in {"datetime", "date", "time", "timestamp"}:
            dt_col = c
            break
    if dt_col is None:
        dt_col = df.columns[0]
    rename = {}
    for wanted in ["BidOpen", "BidHigh", "BidLow", "BidClose", "AskOpen", "AskHigh", "AskLow", "AskClose"]:
        found = next((c for c in df.columns if str(c).strip().lower() == wanted.lower()), None)
        if found is None:
            raise ValueError(f"missing column {wanted}; columns={list(df.columns)}")
        rename[found] = wanted
    out = df[[dt_col] + list(rename.keys())].rename(columns={dt_col: "utc", **rename}).copy()
    out["utc"] = pd.to_datetime(out["utc"], utc=True, errors="coerce")
    out = out.dropna(subset=["utc"])
    for c in rename.values():
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna()
    return out


def load_fxcm(start_year: int, end_year: int, workers: int, outdir: Path):
    items = list(iso_week_urls(start_year, end_year))
    frames = []
    coverage = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(fetch_week, item) for item in items]
        for i, fut in enumerate(cf.as_completed(futs), 1):
            y, w, df, status = fut.result()
            coverage.append({"year": y, "week": w, "status": status})
            if df is not None:
                try:
                    n = normalize_week(df)
                    frames.append(n)
                except Exception as e:
                    coverage[-1]["status"] = f"parse_error:{e}"
            if i % 50 == 0:
                print(f"downloaded/probed {i}/{len(items)} weeks", flush=True)
    cov = pd.DataFrame(coverage).sort_values(["year", "week"])
    cov.to_csv(outdir / "fxcm_coverage.csv", index=False)
    if not frames:
        raise RuntimeError("No FXCM EURUSD M1 files were downloaded")
    d = pd.concat(frames, ignore_index=True)
    d = d.sort_values("utc").drop_duplicates("utc", keep="last").reset_index(drop=True)
    d["mid_open"] = (d.BidOpen + d.AskOpen) / 2
    d["mid_close"] = (d.BidClose + d.AskClose) / 2
    d["ny"] = d.utc.dt.tz_convert(NY)
    d["lon"] = d.utc.dt.tz_convert(LONDON)
    # retain only windows relevant to frozen engines to reduce memory
    ny_min = d.ny.dt.hour * 60 + d.ny.dt.minute
    lo_min = d.lon.dt.hour * 60 + d.lon.dt.minute
    mask = ((ny_min >= 120) & (ny_min <= 660)) | ((lo_min >= 780) & (lo_min <= 1110))
    return d.loc[mask].copy(), cov


def exact_row(g: pd.DataFrame, local_col: str, hour: int, minute: int):
    t = g[local_col]
    x = g[(t.dt.hour == hour) & (t.dt.minute == minute)]
    if len(x) != 1:
        return None
    return x.iloc[0]


def window(g, local_col, start_hm, end_hm, inclusive_end=True):
    t = g[local_col]
    m = t.dt.hour * 60 + t.dt.minute
    s = start_hm[0] * 60 + start_hm[1]
    e = end_hm[0] * 60 + end_hm[1]
    if inclusive_end:
        return g[(m >= s) & (m <= e)]
    return g[(m >= s) & (m < e)]


def build_ny_days(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    x = d.copy()
    x["local_date"] = x.ny.dt.date
    for day, g in x.groupby("local_date", sort=True):
        if pd.Timestamp(day).weekday() >= 5:
            continue
        r0200 = exact_row(g, "ny", 2, 0)
        r0800 = exact_row(g, "ny", 8, 0)
        r0834 = exact_row(g, "ny", 8, 34)
        r0835 = exact_row(g, "ny", 8, 35)
        r1100 = exact_row(g, "ny", 11, 0)
        sw = window(g, "ny", (8, 25), (8, 34))
        tradebars = window(g, "ny", (8, 35), (10, 59))
        if any(v is None for v in [r0200, r0800, r0834, r0835, r1100]) or len(sw) < 8 or tradebars.empty:
            continue
        pre = float(r0834.mid_close - r0200.mid_open)
        imp = float(r0834.mid_close - r0800.mid_open)
        rows.append({
            "date": pd.Timestamp(day), "pre_move": pre, "impulse_30": imp,
            "entry_utc": r0835.utc, "entry_bid": float(r0835.BidOpen), "entry_ask": float(r0835.AskOpen),
            "long_stop_anchor": float(sw.BidLow.min()), "short_stop_anchor": float(sw.AskHigh.max()),
            "time_exit_bid": float(r1100.BidOpen), "time_exit_ask": float(r1100.AskOpen),
            "bars": tradebars[["utc","BidOpen","BidHigh","BidLow","BidClose","AskOpen","AskHigh","AskLow","AskClose"]].to_dict("records"),
        })
    out = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    if out.empty:
        return out
    out["med60"] = out.pre_move.abs().shift(1).rolling(60, min_periods=60).median()
    return out


def build_london_days(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    x = d.copy()
    x["local_date"] = x.lon.dt.date
    for day, g in x.groupby("local_date", sort=True):
        if pd.Timestamp(day).weekday() >= 5:
            continue
        r1300 = exact_row(g, "lon", 13, 0)
        r1559 = exact_row(g, "lon", 15, 59)
        r1605 = exact_row(g, "lon", 16, 5)
        r1830 = exact_row(g, "lon", 18, 30)
        sw = window(g, "lon", (15, 30), (16, 4))
        tradebars = window(g, "lon", (16, 5), (18, 29))
        if any(v is None for v in [r1300, r1559, r1605, r1830]) or len(sw) < 30 or tradebars.empty:
            continue
        pre = float(r1559.mid_close - r1300.mid_open)
        rows.append({
            "date": pd.Timestamp(day), "pre_move": pre,
            "entry_utc": r1605.utc, "entry_bid": float(r1605.BidOpen), "entry_ask": float(r1605.AskOpen),
            "stop_anchor": float(sw.BidLow.min()),
            "time_exit_bid": float(r1830.BidOpen),
            "bars": tradebars[["utc","BidOpen","BidHigh","BidLow","BidClose","AskOpen","AskHigh","AskLow","AskClose"]].to_dict("records"),
        })
    out = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    if out.empty:
        return out
    out["med60"] = out.pre_move.abs().shift(1).rolling(60, min_periods=60).median()
    return out


def simulate_trade(direction: int, entry_bid: float, entry_ask: float, stop_anchor: float, bars: list[dict], time_exit_bid: float, time_exit_ask: float, rr: float):
    if direction == 1:
        entry = entry_ask
        raw_stop = stop_anchor - HALF_PIP
        risk = entry - raw_stop
        if risk < 3*PIP:
            risk = 3*PIP
            stop = entry - risk
        else:
            stop = raw_stop
        if risk > 20*PIP or risk <= 0:
            return None
        target = entry + rr * risk
        exit_px = time_exit_bid
        reason = "TIME"
        for b in bars:
            op, hi, lo = float(b["BidOpen"]), float(b["BidHigh"]), float(b["BidLow"])
            if op <= stop:
                exit_px, reason = op, "SL_GAP"; break
            if op >= target:
                exit_px, reason = target, "TP_GAP"; break
            sl = lo <= stop
            tp = hi >= target
            if sl:
                exit_px, reason = stop, "SL"; break
            if tp:
                exit_px, reason = target, "TP"; break
        gross_r = (exit_px - entry) / risk
    else:
        entry = entry_bid
        raw_stop = stop_anchor + HALF_PIP
        risk = raw_stop - entry
        if risk < 3*PIP:
            risk = 3*PIP
            stop = entry + risk
        else:
            stop = raw_stop
        if risk > 20*PIP or risk <= 0:
            return None
        target = entry - rr * risk
        exit_px = time_exit_ask
        reason = "TIME"
        for b in bars:
            op, hi, lo = float(b["AskOpen"]), float(b["AskHigh"]), float(b["AskLow"])
            if op >= stop:
                exit_px, reason = op, "SL_GAP"; break
            if op <= target:
                exit_px, reason = target, "TP_GAP"; break
            sl = hi >= stop
            tp = lo <= target
            if sl:
                exit_px, reason = stop, "SL"; break
            if tp:
                exit_px, reason = target, "TP"; break
        gross_r = (entry - exit_px) / risk
    return {
        "entry": entry, "stop": stop, "target": target, "exit": exit_px,
        "risk_pips": risk/PIP, "gross_r": gross_r,
        "net_r_base": gross_r - BASE_COST_PRICE/risk,
        "net_r_stress": gross_r - STRESS_COST_PRICE/risk,
        "exit_reason": reason,
    }


def gen_engine_a(days: pd.DataFrame, q: float, rr: float, start=None, end=None):
    trades=[]
    for _, r in days.iterrows():
        if start is not None and r.date < start: continue
        if end is not None and r.date > end: continue
        if not np.isfinite(r.med60) or r.med60 <= 0: continue
        if abs(r.pre_move) < q*r.med60: continue
        if r.pre_move == 0 or r.impulse_30 == 0 or np.sign(r.pre_move) != np.sign(r.impulse_30): continue
        direction = 1 if r.pre_move > 0 else -1
        stop_anchor = r.long_stop_anchor if direction == 1 else r.short_stop_anchor
        sim = simulate_trade(direction, r.entry_bid, r.entry_ask, stop_anchor, r.bars, r.time_exit_bid, r.time_exit_ask, rr)
        if sim is None: continue
        trades.append({"engine":"A_NY_AMOM","q":q,"rr":rr,"date":r.date,"entry_utc":r.entry_utc,"direction":direction,**sim})
    return pd.DataFrame(trades)


def gen_engine_b(days: pd.DataFrame, q: float, rr: float, start=None, end=None):
    trades=[]
    for _, r in days.iterrows():
        if start is not None and r.date < start: continue
        if end is not None and r.date > end: continue
        if not np.isfinite(r.med60) or r.med60 <= 0: continue
        if r.pre_move >= 0: continue
        if abs(r.pre_move) < q*r.med60: continue
        sim = simulate_trade(1, r.entry_bid, r.entry_ask, r.stop_anchor, r.bars, r.time_exit_bid, np.nan, rr)
        if sim is None: continue
        trades.append({"engine":"B_LONDON_FIX","q":q,"rr":rr,"date":r.date,"entry_utc":r.entry_utc,"direction":1,**sim})
    return pd.DataFrame(trades)


def pf(series: pd.Series) -> float:
    pos = series[series>0].sum(); neg = -series[series<0].sum()
    return float(pos/neg) if neg>0 else (float("inf") if pos>0 else 0.0)


def max_dd(series: pd.Series) -> float:
    eq=series.cumsum(); peak=eq.cummax(); dd=peak-eq
    return float(dd.max()) if len(dd) else 0.0


def losing_streak(series: pd.Series) -> int:
    best=cur=0
    for x in series:
        if x<0: cur+=1; best=max(best,cur)
        else: cur=0
    return best


def metrics(trades: pd.DataFrame, col="net_r_base"):
    if trades is None or trades.empty:
        return {"n":0,"mean":None,"sum":0.0,"pf":0.0,"max_dd":0.0,"positive_years":0,"active_years":0,"losing_streak":0}
    t=trades.sort_values("entry_utc")
    s=t[col].astype(float)
    ys=t.assign(year=t.date.dt.year).groupby("year")[col].sum()
    return {"n":int(len(t)),"mean":float(s.mean()),"sum":float(s.sum()),"pf":pf(s),"max_dd":max_dd(s),"positive_years":int((ys>0).sum()),"active_years":int(len(ys)),"losing_streak":losing_streak(s),"annual":{str(int(k)):float(v) for k,v in ys.items()}}


def select_engine(days, engine):
    if engine=="A": qs=[1.0,1.5,2.0]; gen=gen_engine_a
    else: qs=[0.5,1.0,1.5]; gen=gen_engine_b
    rows=[]; candidates={}
    for q in qs:
        for rr in [1.0,1.5,2.0]:
            t=gen(days,q,rr,end=DEV_END)
            m=metrics(t)
            score=(m["mean"]*math.sqrt(m["n"])) if m["n"] and m["mean"] is not None else -1e99
            eligible=m["n"]>=50 and m["mean"]>0 and m["pf"]>1.05
            rows.append({"engine":engine,"q":q,"rr":rr,"eligible":eligible,"score":score,**{k:v for k,v in m.items() if k!="annual"}})
            candidates[(q,rr)]=(t,m,score,eligible)
    elig=[(q,rr,*vals) for (q,rr),vals in candidates.items() if vals[3]]
    if not elig:
        return None,pd.DataFrame(rows)
    elig.sort(key=lambda z:(-z[4], z[0], z[1]))
    q,rr,t,m,score,_=elig[0]
    return {"engine":engine,"q":q,"rr":rr,"trades":t,"metrics":m,"score":score},pd.DataFrame(rows)


def combine_selected(selA, selB, mode):
    parts=[]
    if mode in {"A","AB"}: parts.append(selA["trades"])
    if mode in {"B","AB"}: parts.append(selB["trades"])
    return pd.concat(parts,ignore_index=True).sort_values("entry_utc").reset_index(drop=True)


def choose_portfolio(selA, selB):
    modes=[]
    if selA: modes.append("A")
    if selB: modes.append("B")
    if selA and selB: modes.append("AB")
    rows=[]
    for mode in modes:
        t=combine_selected(selA,selB,mode)
        m=metrics(t)
        eligible=(m["n"]>=100 and m["mean"]>=0.08 and m["pf"]>=1.20 and m["positive_years"]>=5 and m["max_dd"]<=15)
        score=m["mean"]*math.sqrt(m["n"]) if m["n"] else -1e99
        rows.append({"mode":mode,"eligible":eligible,"score":score,**{k:v for k,v in m.items() if k!="annual"}})
    er=[r for r in rows if r["eligible"]]
    if not er: return None,pd.DataFrame(rows)
    tie={"AB":0,"A":1,"B":2}
    er.sort(key=lambda r:(-r["score"],tie[r["mode"]]))
    return er[0]["mode"],pd.DataFrame(rows)


def selected_oos(ny_days, lo_days, selA, selB, mode):
    parts=[]
    if mode in {"A","AB"}:
        parts.append(gen_engine_a(ny_days,selA["q"],selA["rr"],start=OOS_START))
    if mode in {"B","AB"}:
        parts.append(gen_engine_b(lo_days,selB["q"],selB["rr"],start=OOS_START))
    if not parts: return pd.DataFrame()
    return pd.concat(parts,ignore_index=True).sort_values("entry_utc").reset_index(drop=True)


def oos_verdict(t):
    mb=metrics(t,"net_r_base"); ms=metrics(t,"net_r_stress")
    if t.empty:
        return "EURUSD_PROPF_SPRINT_V1_INSUFFICIENT_OOS",mb,ms,{}
    years=mb["active_years"]
    support=mb["n"]>=80 and years>=3
    k=max(1,math.ceil(len(t)*0.05))
    trimmed=t.sort_values("net_r_base",ascending=False).iloc[k:]
    trim_mean=float(trimmed.net_r_base.mean()) if len(trimmed) else float("nan")
    gates={
        "support":support,
        "mean_base_ge_0_10":mb["mean"] is not None and mb["mean"]>=0.10,
        "pf_base_ge_1_25":mb["pf"]>=1.25,
        "positive_year_fraction_ge_0_60":years>0 and mb["positive_years"]/years>=0.60,
        "max_dd_le_12R":mb["max_dd"]<=12,
        "losing_streak_le_10":mb["losing_streak"]<=10,
        "trimmed_top5_mean_positive":trim_mean>0,
        "stress_mean_positive":ms["mean"] is not None and ms["mean"]>0,
        "stress_pf_ge_1_10":ms["pf"]>=1.10,
    }
    if not support: status="EURUSD_PROPF_SPRINT_V1_INSUFFICIENT_OOS"
    elif all(gates.values()): status="EURUSD_PROPF_SPRINT_V1_PASS_CANDIDATE"
    else: status="EURUSD_PROPF_SPRINT_V1_OOS_NO_GO"
    gates["trimmed_mean"] = trim_mean
    return status,mb,ms,gates


def prop_diag(t: pd.DataFrame, risk_frac: float):
    rs=t.sort_values("entry_utc").reset_index(drop=True)
    vals=rs.net_r_base.to_numpy(float)*risk_frac
    dates=pd.to_datetime(rs.date).to_numpy()
    starts=[]
    for i in range(len(vals)):
        eq=0.0; outcome="UNRESOLVED"; j=i
        for j in range(i,len(vals)):
            eq += vals[j]
            if eq>=0.10: outcome="PASS"; break
            if eq<=-0.10: outcome="FAIL"; break
        days=int((pd.Timestamp(dates[j])-pd.Timestamp(dates[i])).days) if j>=i else 0
        starts.append((outcome,days,j-i+1))
    resolved=[x for x in starts if x[0] != "UNRESOLVED"]
    pass_rate=(sum(x[0]=="PASS" for x in resolved)/len(resolved)) if resolved else None
    pass_days=[x[1] for x in resolved if x[0]=="PASS"]
    daily=pd.DataFrame({"date":rs.date,"ret":vals}).groupby("date").ret.sum()
    return {"risk_frac":risk_frac,"rolling_starts":len(starts),"resolved":len(resolved),"resolved_pass_rate":pass_rate,"median_days_to_pass":float(np.median(pass_days)) if pass_days else None,"p25_days_to_pass":float(np.percentile(pass_days,25)) if pass_days else None,"p75_days_to_pass":float(np.percentile(pass_days,75)) if pass_days else None,"worst_historical_day_return":float(daily.min()) if len(daily) else None,"breached_5pct_daily":bool((daily<=-0.05).any()) if len(daily) else False}


def bootstrap_pass_prob(t: pd.DataFrame, risk_frac: float, nrep=20000, seed=20260820):
    r=t.net_r_base.to_numpy(float)
    if len(r)==0: return None
    rng=np.random.default_rng(seed+int(risk_frac*10000))
    passes=0; fails=0; unresolved=0; steps_pass=[]
    for _ in range(nrep):
        eq=0.0
        for step in range(1,501):
            eq += risk_frac * float(rng.choice(r))
            if eq>=0.10:
                passes+=1; steps_pass.append(step); break
            if eq<=-0.10:
                fails+=1; break
        else: unresolved+=1
    return {"risk_frac":risk_frac,"nrep":nrep,"pass_probability_resolved":passes/(passes+fails) if passes+fails else None,"passes":passes,"fails":fails,"unresolved":unresolved,"median_trades_to_pass":float(np.median(steps_pass)) if steps_pass else None}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",default="eurusd-propf/results/v1"); ap.add_argument("--workers",type=int,default=10); ap.add_argument("--start-year",type=int,default=2012); ap.add_argument("--end-year",type=int,default=2026)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    print("Downloading FXCM EURUSD M1 bid/ask...",flush=True)
    d,cov=load_fxcm(a.start_year,a.end_year,a.workers,out)
    print(f"retained rows={len(d):,}, utc={d.utc.min()}..{d.utc.max()}",flush=True)
    ny=build_ny_days(d); lo=build_london_days(d)
    pd.DataFrame({"ny_dates":ny.date.astype(str)}).to_csv(out/"ny_valid_days.csv",index=False)
    pd.DataFrame({"london_dates":lo.date.astype(str)}).to_csv(out/"london_valid_days.csv",index=False)
    selA,gridA=select_engine(ny,"A"); selB,gridB=select_engine(lo,"B")
    gridA.to_csv(out/"dev_grid_engine_a.csv",index=False); gridB.to_csv(out/"dev_grid_engine_b.csv",index=False)
    mode,portgrid=choose_portfolio(selA,selB); portgrid.to_csv(out/"dev_portfolio_grid.csv",index=False)
    summary={"protocol":"EURUSD_PROPF_SPRINT_V1","data":{"rows_retained":int(len(d)),"utc_min":str(d.utc.min()),"utc_max":str(d.utc.max()),"ok_week_files":int((cov.status=="ok").sum()),"ny_valid_days":int(len(ny)),"london_valid_days":int(len(lo))},"dev":{"selected_A":None if selA is None else {"q":selA["q"],"rr":selA["rr"],"metrics":selA["metrics"]},"selected_B":None if selB is None else {"q":selB["q"],"rr":selB["rr"],"metrics":selB["metrics"]},"selected_portfolio":mode}}
    if mode is None:
        summary["status"]="EURUSD_PROPF_SPRINT_V1_DEV_NO_GO"
        (out/"RESULT.json").write_text(json.dumps(summary,indent=2,default=str))
        print(json.dumps(summary,indent=2,default=str)); return
    oos=selected_oos(ny,lo,selA,selB,mode)
    oos.to_csv(out/"oos_trades.csv",index=False)
    status,mb,ms,gates=oos_verdict(oos)
    summary["status"]=status; summary["oos"]={"base":mb,"stress":ms,"gates":gates}
    if not oos.empty:
        summary["prop_diagnostics"]=[]; summary["bootstrap"]=[]
        for rf in [0.005,0.0075,0.01]:
            summary["prop_diagnostics"].append(prop_diag(oos,rf)); summary["bootstrap"].append(bootstrap_pass_prob(oos,rf))
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2,default=str))
    print(json.dumps(summary,indent=2,default=str))

if __name__=="__main__": main()
