#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BASE = Path("us100-zero-data/results/native_12model_port_v5")
TRADES = BASE / "TRADES_RESCORED.csv"
RAW = BASE / "external_trades_raw.csv"
OUT = Path("us100-zero-data/results/native_12model_adapted_v6")
SOURCE_REPO = "CodyOutcast/Academic-Paper-Data-Source"
SOURCE_COMMIT = "50052606c16d71850755e6dbdda02d43b4399c2b"
YEARS = (2021, 2022, 2023, 2024, 2025)
EXPECTED_RAW_SHA = "c2c705318ff19aee4fb1137b7ec2102e98a848b297701b334e1b777a0d5b7d31"
SERVER_TO_NY_HOURS = 7
CACHE = Path("/tmp/us100_v6_dates")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(x, name="RESULT.json"):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(x, indent=2, allow_nan=False, default=str))


def pf(a):
    a = np.asarray(a, dtype=float)
    pos = a[a > 0].sum(); neg = -a[a < 0].sum()
    if neg > 0: return float(pos / neg)
    if pos > 0: return 1e99
    return None


def stats(vals):
    a = np.asarray(vals, dtype=float)
    if len(a) == 0:
        return {"n":0,"mean":None,"sum":0.0,"pf":None,"win_rate":None,"max_dd":None,"losing_streak":None}
    eq = np.cumsum(a)
    peaks = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(peaks - eq, 0.0)
    cur = longest = 0
    for v in a:
        if v < 0: cur += 1; longest = max(longest, cur)
        else: cur = 0
    return {"n":int(len(a)),"mean":float(a.mean()),"sum":float(a.sum()),"pf":pf(a),
            "win_rate":float((a>0).mean()),"max_dd":float(dd.max(initial=0.0)),"losing_streak":int(longest)}


def source_path(y):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"OHLC-USTEC-M1-{y}.csv"
    if not p.exists() or p.stat().st_size < 1000:
        u = f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/OHLC-USTEC-M1-{y}.csv"
        r = requests.get(u, timeout=180); r.raise_for_status(); p.write_bytes(r.content)
    return p


def complete_days_by_year():
    out = {}
    for y in YEARS:
        d = pd.read_csv(source_path(y), sep=";", usecols=["time"], low_memory=False)
        d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
        d = d.dropna().drop_duplicates("time")
        dt = d["time"] - pd.Timedelta(hours=SERVER_TO_NY_HOURS)
        x = pd.DataFrame({"datetime":dt})
        x["date"] = x.datetime.dt.date
        t = x.datetime.dt.time
        r = x[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())]
        counts = r.groupby("date").size()
        out[y] = set(counts[counts >= 380].index)
    return out


def ensemble_stats(z, sessions):
    return {
        "primary": stats(z.primary_r),
        "stress": stats(z.stress_r),
        "sessions": int(sessions),
        "trades_per_day": float(len(z)/sessions) if sessions else 0.0,
    }


def challenge_plan(expectancy, tpd, dd, worst_day):
    if not (expectancy and expectancy > 0 and tpd > 0 and dd > 0): return {"safe":None,"aggressive":None}
    levels={"safe":min(0.005,0.08/(2*dd)),"aggressive":min(0.005,0.08/(1.5*dd))}
    o={}
    for k,risk in levels.items():
        worst_pct=abs(min(0.0,worst_day))*risk; ok=worst_pct<0.04; daily=expectancy*tpd*risk
        o[k]={"risk_pct_per_trade":float(risk),"risk_dollars_10k":float(risk*10000),
              "observed_worst_day_loss_pct":float(worst_pct),"admissible":bool(ok),
              "expected_daily_return_pct":float(daily),
              "step1_days":float(.10/daily) if ok and daily>0 else None,
              "step2_days":float(.05/daily) if ok and daily>0 else None,
              "total_days":float(.15/daily) if ok and daily>0 else None}
    return o


def main():
    if not TRADES.exists() or not RAW.exists(): raise RuntimeError("V5.3 ledgers missing")
    rawsha=sha256_file(RAW)
    if rawsha != EXPECTED_RAW_SHA: raise RuntimeError(f"raw ledger SHA mismatch {rawsha}")
    tr=pd.read_csv(TRADES)
    for c in ["entry_time","exit_time"]: tr[c]=pd.to_datetime(tr[c],errors="coerce")
    for c in ["primary_r","stress_r"]: tr[c]=pd.to_numeric(tr[c],errors="coerce")
    tr=tr.dropna(subset=["entry_time","model","direction","primary_r","stress_r"]).copy()
    tr["year"]=tr.entry_time.dt.year; tr["month"]=tr.entry_time.dt.to_period("M").astype(str); tr["date"]=tr.entry_time.dt.date
    tr["combo"]=tr.model.astype(str)+"__"+tr.direction.astype(str).str.lower()
    dates=complete_days_by_year()

    dev=tr[tr.year.isin([2021,2022,2023])].copy()
    combo_diag={}; allowed=[]
    for combo,z in dev.groupby("combo",sort=True):
        p=stats(z.primary_r); s=stats(z.stress_r); yrs={}
        positives=0; worst_mean=1e9
        for y in [2021,2022,2023]:
            zy=z[z.year==y]; sy=stats(zy.primary_r); yrs[str(y)]=sy
            if sy["sum"]>0: positives+=1
            if sy["n"]>0 and sy["mean"] is not None: worst_mean=min(worst_mean,sy["mean"])
        if worst_mean==1e9: worst_mean=None
        gates={"n_ge_60":p["n"]>=60,"mean_ge_0_10":p["mean"]>=0.10,"pf_ge_1_25":p["pf"] is not None and p["pf"]>=1.25,
               "maxdd_le_12":p["max_dd"]<=12,"positive_years_ge_2":positives>=2,
               "worst_year_mean_ge_minus_0_05":worst_mean is not None and worst_mean>=-0.05,
               "stress_mean_ge_0_07":s["mean"]>=0.07,"stress_pf_ge_1_15":s["pf"] is not None and s["pf"]>=1.15}
        eligible=all(gates.values())
        if eligible: allowed.append(combo)
        combo_diag[combo]={"primary":p,"stress":s,"by_year_primary":yrs,"positive_years":positives,
                           "worst_year_mean":worst_mean,"gates":gates,"eligible":eligible}

    if not allowed:
        dump({"status":"V6_DEV_NO_GO_NO_COMBOS","raw_sha":rawsha,"allowed":[],"combo_diagnostics_2021_2023":combo_diag,
              "validation_status":"NOT_OPENED"}); return

    dev_sel=dev[dev.combo.isin(allowed)].copy(); dev_sessions=sum(len(dates[y]) for y in [2021,2022,2023]); ds=ensemble_stats(dev_sel,dev_sessions)
    dev_years={str(y):stats(dev_sel[dev_sel.year==y].primary_r) for y in [2021,2022,2023]}
    dg={"n_ge_1000":ds["primary"]["n"]>=1000,"tpd_ge_2":ds["trades_per_day"]>=2,
        "mean_ge_0_15":ds["primary"]["mean"]>=0.15,"pf_ge_1_35":ds["primary"]["pf"] is not None and ds["primary"]["pf"]>=1.35,
        "maxdd_le_12":ds["primary"]["max_dd"]<=12,"all_3_years_positive":all(v["sum"]>0 for v in dev_years.values()),
        "stress_mean_ge_0_12":ds["stress"]["mean"]>=0.12,"stress_pf_ge_1_25":ds["stress"]["pf"] is not None and ds["stress"]["pf"]>=1.25}
    if not all(dg.values()):
        dump({"status":"V6_DEV_NO_GO_ENSEMBLE_SANITY","raw_sha":rawsha,"allowed":allowed,
              "combo_diagnostics_2021_2023":combo_diag,"dev_ensemble":ds,"dev_by_year":dev_years,"dev_gates":dg,
              "validation_status":"NOT_OPENED"}); return

    val=tr[tr.year.isin([2024,2025]) & tr.combo.isin(allowed)].copy()
    val_sessions=sum(len(dates[y]) for y in [2024,2025]); vs=ensemble_stats(val,val_sessions)
    vyears={str(y):stats(val[val.year==y].primary_r) for y in [2024,2025]}
    monthly=val.groupby("month",sort=True).primary_r.sum(); active=int(len(monthly)); pos_rate=float((monthly>0).mean()) if active else 0
    worst_month=float(monthly.min()) if active else 0; total=float(monthly.sum()); max_pos=float(monthly[monthly>0].max()) if (monthly>0).any() else 0
    max_month_share=float(max_pos/total) if total>0 else None
    daily=val.groupby("date",sort=True).primary_r.sum(); worst_day=float(daily.min()) if len(daily) else 0
    plan=challenge_plan(vs["primary"]["mean"],vs["trades_per_day"],vs["primary"]["max_dd"],worst_day)
    speed=any(x is not None and x["admissible"] and x["step1_days"] is not None and x["step1_days"]<=45 and
              x["step2_days"] is not None and x["step2_days"]<=23 and x["total_days"] is not None and x["total_days"]<=68 for x in plan.values())
    vg={"n_ge_450":vs["primary"]["n"]>=450,"tpd_ge_2":vs["trades_per_day"]>=2,
        "mean_ge_0_15":vs["primary"]["mean"]>=0.15,"pf_ge_1_35":vs["primary"]["pf"] is not None and vs["primary"]["pf"]>=1.35,
        "maxdd_le_10_5":vs["primary"]["max_dd"]<=10.5,"year_2024_positive":vyears["2024"]["sum"]>0,
        "jan_apr_2025_positive":vyears["2025"]["sum"]>0,"positive_month_rate_ge_70pct":pos_rate>=0.70,
        "stress_mean_ge_0_12":vs["stress"]["mean"]>=0.12,"stress_pf_ge_1_25":vs["stress"]["pf"] is not None and vs["stress"]["pf"]>=1.25,
        "worst_month_ge_minus_8R":worst_month>=-8,"max_positive_month_share_le_35pct":max_month_share is not None and max_month_share<=0.35,
        "challenge_speed":bool(speed)}
    passed=all(vg.values())
    val.to_csv(OUT/"VALIDATION_TRADES.csv",index=False)
    dump({"status":"V6_NATIVE_ADAPTED_PROMISING_REQUIRES_FTMO_FORWARD" if passed else "V6_NATIVE_ADAPTED_NO_GO",
          "classification":"EXECUTION_FILTER_SELECTED_2021_2023_VALIDATED_2024_JANAPR2025","raw_sha":rawsha,
          "allowed":allowed,"allowed_count":len(allowed),"combo_diagnostics_2021_2023":combo_diag,
          "dev_ensemble":ds,"dev_by_year":dev_years,"dev_gates":dg,
          "validation_ensemble":vs,"validation_by_year":vyears,"validation_monthly_r":{str(k):float(v) for k,v in monthly.items()},
          "validation_positive_month_rate":pos_rate,"validation_worst_month_r":worst_month,"validation_max_positive_month_share":max_month_share,
          "validation_worst_daily_r":worst_day,"challenge_plan_10k":plan,"validation_gates":vg,"pass":passed,
          "notes":["No paid external data required live.","V6 filters finalized V5 signals only; rejected signals do not resurrect suppressed alternatives.",
                   "Aggregate 2024/2025 full-ensemble performance was previously known, so prospective FTMO forward remains required even if V6 passes."]})

if __name__=="__main__": main()
