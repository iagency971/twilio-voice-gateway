#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

EXT_REPO = "https://github.com/s-k-28/nq-es-trader-5k-payout.git"
EXT_SHA = "d472d6b442764c2adafbba4bbeb96881c100e3e0"
TICKER = "NQ=F"
TZ = "America/New_York"
FORWARD_START = pd.Timestamp("2026-08-21")
ROOT = Path("mnq-forward-shadow")
RESULTS = ROOT / "results"
LEDGER = RESULTS / "ledger.csv"


def pf(a: np.ndarray):
    pos = a[a > 0].sum(); neg = -a[a < 0].sum()
    if neg > 0: return float(pos / neg)
    return 1e99 if pos > 0 else None


def stats(vals):
    a = np.asarray(vals, dtype=float)
    if len(a) == 0:
        return {"n":0,"mean":None,"sum":0.0,"pf":None,"win_rate":None,"max_dd":None,"losing_streak":None}
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.0,eq])[:-1]; dd=np.maximum(peak-eq,0.0)
    cur=ls=0
    for v in a:
        if v < 0: cur += 1; ls=max(ls,cur)
        else: cur=0
    return {"n":int(len(a)),"mean":float(a.mean()),"sum":float(a.sum()),"pf":pf(a),
            "win_rate":float((a>0).mean()),"max_dd":float(dd.max(initial=0.0)),"losing_streak":int(ls)}


def normalize(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty: return pd.DataFrame()
    f=frame.copy()
    if isinstance(f.columns,pd.MultiIndex):
        price_names={"Open","High","Low","Close","Volume"}
        if set(map(str,f.columns.get_level_values(0))) & price_names: f.columns=f.columns.get_level_values(0)
        elif set(map(str,f.columns.get_level_values(-1))) & price_names: f.columns=f.columns.get_level_values(-1)
        else: raise RuntimeError("Unexpected Yahoo columns")
    idx=pd.DatetimeIndex(f.index)
    idx=idx.tz_localize(TZ) if idx.tz is None else idx.tz_convert(TZ)
    out=pd.DataFrame({"datetime":idx.tz_localize(None),"open":f["Open"].to_numpy(),"high":f["High"].to_numpy(),
                      "low":f["Low"].to_numpy(),"close":f["Close"].to_numpy(),"volume":f["Volume"].fillna(0).to_numpy()})
    for c in ["open","high","low","close","volume"]: out[c]=pd.to_numeric(out[c],errors="coerce")
    return out.dropna(subset=["datetime","open","high","low","close"]).sort_values("datetime").drop_duplicates("datetime")


def download_recent() -> pd.DataFrame:
    raw=yf.download(TICKER,period="30d",interval="1m",prepost=True,auto_adjust=False,progress=False,threads=False,timeout=30)
    d=normalize(raw)
    if d.empty: raise RuntimeError("Yahoo returned no recent NQ=F 1m data")
    return d


def latest_complete_rth_date(d: pd.DataFrame):
    tt=d.datetime.dt.time
    rth=d[(tt>=pd.Timestamp("09:30").time())&(tt<=pd.Timestamp("15:59").time())].copy()
    counts=rth.groupby(rth.datetime.dt.normalize()).size()
    complete=counts[counts>=380]
    if complete.empty: return None
    return complete.index.max()


def ensure_external(work: Path) -> Path:
    ext=work/"external"
    if not ext.exists(): subprocess.run(["git","clone","--quiet",EXT_REPO,str(ext)],check=True)
    subprocess.run(["git","checkout","--quiet",EXT_SHA],cwd=ext,check=True)
    got=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ext,text=True).strip()
    if got != EXT_SHA: raise RuntimeError(f"external commit mismatch {got}")
    return ext


def build_daily(ext: Path,d: pd.DataFrame) -> Path:
    hist=pd.read_csv(ext/"data"/"NQ_daily.csv")
    hist.columns=[str(c).strip().lower().replace(" ","_") for c in hist.columns]
    dc="datetime" if "datetime" in hist.columns else ("date" if "date" in hist.columns else hist.columns[0])
    hist["datetime"]=pd.to_datetime(hist[dc],errors="coerce").dt.normalize()
    for c in ["open","high","low","close","volume"]: hist[c]=pd.to_numeric(hist[c],errors="coerce")
    hist=hist.dropna(subset=["datetime","open","high","low","close"])[["datetime","open","high","low","close","volume"]]
    tt=d.datetime.dt.time
    rth=d[(tt>=pd.Timestamp("09:30").time())&(tt<pd.Timestamp("16:00").time())].copy(); rth["date"]=rth.datetime.dt.normalize()
    cur=rth.groupby("date",as_index=False).agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"),volume=("volume","sum")).rename(columns={"date":"datetime"})
    both=pd.concat([hist,cur],ignore_index=True).sort_values("datetime").drop_duplicates("datetime",keep="last")
    p=ext/"data"/"forward_daily.csv"; both.to_csv(p,index=False); return p


def run_external(ext: Path,d: pd.DataFrame,daily: Path,outcsv: Path):
    inp=ext/"data"/"forward_recent.csv"; d.to_csv(inp,index=False)
    outcsv.parent.mkdir(parents=True,exist_ok=True)
    cmd=[sys.executable,"run_multi.py","--nq",str(inp),"--nq-daily",str(daily),"--csv",str(outcsv.resolve())]
    p=subprocess.run(cmd,cwd=ext,text=True,capture_output=True,timeout=1200)
    (RESULTS/"last_external_stdout.txt").write_text(p.stdout); (RESULTS/"last_external_stderr.txt").write_text(p.stderr)
    if p.returncode != 0: raise RuntimeError(p.stderr[-3000:])


def rescore(df,points):
    risk=pd.to_numeric(df.risk_ticks,errors="coerce")*0.25
    return pd.to_numeric(df.total_r,errors="coerce") - points/risk


def summary(ledger: pd.DataFrame, latest_day: str):
    if ledger.empty:
        return {"status":"SHADOW_PROXY_ONLY_EMPTY","latest_complete_day":latest_day}
    ledger=ledger.sort_values("entry_time").copy()
    p=stats(ledger.primary_r.to_numpy()); s=stats(ledger.stress_r.to_numpy())
    z=ledger.copy(); z["week"]=pd.to_datetime(z.entry_time).dt.to_period("W-FRI").astype(str)
    weekly={w:stats(g.primary_r.to_numpy()) for w,g in z.groupby("week")}
    positive_weeks=sum(1 for v in weekly.values() if v["sum"]>0)
    k=max(1,int(np.ceil(len(z)*0.10))); rem=z.sort_values("primary_r",ascending=False).iloc[k:]
    robust_mean=float(rem.primary_r.mean()) if len(rem) else None
    if len(z)<40: stage="FORWARD_INSUFFICIENT_FOR_LIVE"
    elif len(z)<100: stage="FORWARD_EARLY_CHECKPOINT_DESCRIPTIVE_ONLY"
    else:
        gates={"exp_ge_0_10":p["mean"] is not None and p["mean"]>=0.10,"pf_ge_1_25":p["pf"] is not None and p["pf"]>=1.25,
               "dd_le_10R":p["max_dd"] is not None and p["max_dd"]<=10,"positive_weeks_ge_60pct":len(weekly)>0 and positive_weeks/len(weekly)>=0.60,
               "remove_best10_nonnegative":robust_mean is not None and robust_mean>=0,"stress_mean_positive":s["mean"] is not None and s["mean"]>0,
               "stress_pf_ge_1_10":s["pf"] is not None and s["pf"]>=1.10}
        stage="PROXY_FORWARD_PASS_REQUIRES_CME_REMEASUREMENT" if all(gates.values()) else "PROXY_FORWARD_NO_GO"
    return {"status":stage,"latest_complete_day":latest_day,"primary":p,"stress":s,"weekly":weekly,"positive_weeks":positive_weeks,
            "remove_best_10pct_mean":robust_mean,"notes":["Yahoo NQ=F shadow proxy only; not official CME validation.","Frozen external model commit; no post-forward retuning allowed."]}


def main():
    RESULTS.mkdir(parents=True,exist_ok=True)
    d=download_recent(); last=latest_complete_rth_date(d)
    if last is None: raise RuntimeError("No complete RTH day")
    if last < FORWARD_START:
        (RESULTS/"SUMMARY.json").write_text(json.dumps({"status":"WAITING_FOR_FORWARD_START","latest_complete_day":str(last.date())},indent=2)); return
    work=Path("/tmp/mnq_forward_shadow"); work.mkdir(parents=True,exist_ok=True); ext=ensure_external(work); daily=build_daily(ext,d)
    rawcsv=RESULTS/"latest_external_trades.csv"; run_external(ext,d,daily,rawcsv)
    t=pd.read_csv(rawcsv); t["entry_time"]=pd.to_datetime(t.entry_time,errors="coerce")
    t=t[(t.entry_time.dt.normalize()>=FORWARD_START)&(t.entry_time.dt.normalize()<=last)].copy()
    if len(t):
        t["primary_r"]=rescore(t,1.0); t["stress_r"]=rescore(t,2.0)
        t["key"]=t.entry_time.astype(str)+"|"+t.model.astype(str)+"|"+t.direction.astype(str)
        cols=["key","entry_time","exit_time","direction","model","tag","entry","exit","stop","target","reason","risk_ticks","total_r","primary_r","stress_r"]
        t=t[cols]
    if LEDGER.exists(): old=pd.read_csv(LEDGER)
    else: old=pd.DataFrame(columns=t.columns if len(t) else ["key","entry_time","exit_time","direction","model","tag","entry","exit","stop","target","reason","risk_ticks","total_r","primary_r","stress_r"])
    combined=pd.concat([old,t],ignore_index=True).drop_duplicates("key",keep="first").sort_values("entry_time") if len(t) or len(old) else old
    combined.to_csv(LEDGER,index=False)
    obj=summary(combined,str(last.date())); obj["ledger_sha256"]=hashlib.sha256(LEDGER.read_bytes()).hexdigest(); (RESULTS/"SUMMARY.json").write_text(json.dumps(obj,indent=2,allow_nan=False)); print(json.dumps(obj,indent=2,allow_nan=False))

if __name__=="__main__": main()
