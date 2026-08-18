#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, os, time
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import databento as db

NY = ZoneInfo("America/New_York")
PILOT_SEED = "COMEX_V4_PILOT12_SEED_971"
PANEL_SEED = "COMEX_SESSION_PANEL_V1_SEED_971"
SCHEMAS = ("trades", "tbbo", "bbo-1s", "mbp-1")
ERAS = (
    ("E1_2011_2013", 2011, 2013),
    ("E2_2014_2018", 2014, 2018),
    ("E3_2019_2022", 2019, 2022),
    ("E4_2023_2025", 2023, 2025),
)


def h(*parts):
    return hashlib.sha256("|".join(str(x) for x in parts).encode()).hexdigest()


def bounds(date_str):
    d = pd.Timestamp(date_str); prev=(d-pd.Timedelta(days=1)).date(); cur=d.date()
    return (pd.Timestamp(f"{prev} 17:00:00",tz=NY).tz_convert("UTC"),
            pd.Timestamp(f"{cur} 18:00:00",tz=NY).tz_convert("UTC"))


def prepare_panel(candidates):
    x=candidates.copy()
    for c in ["year","quarter","vol_band","panel_rank"]:
        x[c]=pd.to_numeric(x[c],errors="raise").astype(int)
    x["research_date_ts"]=pd.to_datetime(x.research_trading_date)
    x["weekday"]=x.research_date_ts.dt.weekday
    old_t2=x[x.panel_rank<=2].copy()
    old_weekend=old_t2[old_t2.weekday>=5].copy()

    valid=x[x.weekday<5].copy()
    if "panel_hash" not in valid.columns:
        valid["panel_hash"]=[h(PANEL_SEED,r.year,r.quarter,r.vol_band,r.research_trading_date) for r in valid.itertuples()]
    valid=valid.sort_values(["year","quarter","vol_band","panel_hash","research_trading_date"]).copy()
    valid["panel_rank_v4"]=valid.groupby(["year","quarter","vol_band"]).cumcount()+1
    t2=valid[valid.panel_rank_v4<=2].copy()
    if (t2.weekday>=5).any(): raise AssertionError("V4 tier2 still contains weekend dates")
    return t2, {
        "old_tier2_sessions": int(len(old_t2)),
        "old_tier2_weekend_sessions": int(len(old_weekend)),
        "old_tier2_weekend_dates": old_weekend.research_trading_date.astype(str).tolist(),
        "v4_tier2_sessions": int(len(t2)),
        "v4_tier2_weekend_sessions": 0,
        "rerank_rule": "exclude Saturday/Sunday research trading dates, then rerank by frozen panel_hash within year x quarter x vol_band",
    }


def choose_pilot(tier2):
    rows=[]
    for era_name,y0,y1 in ERAS:
        era=tier2[(tier2.year>=y0)&(tier2.year<=y1)].copy(); used=set()
        bands=sorted(int(v) for v in era.vol_band.unique())
        if bands != [0,1,2]: raise ValueError(f"{era_name}: bands={bands}")
        order=sorted(bands,key=lambda b:h(PILOT_SEED,era_name,"band_order",b))
        for band in order:
            q=era[era.vol_band==band].copy()
            q["pilot_hash"]=[h(PILOT_SEED,era_name,band,r.quarter,r.research_trading_date) for r in q.itertuples()]
            diversified=q[~q.quarter.isin(used)]; pool=diversified if len(diversified) else q
            pick=pool.sort_values(["pilot_hash","research_trading_date"]).iloc[0].copy()
            pick["era"]=era_name; pick["quarter_diversified"]=bool(len(diversified)); rows.append(pick); used.add(int(pick.quarter))
    out=pd.DataFrame(rows).sort_values(["era","vol_band"]).reset_index(drop=True)
    if len(out)!=12 or out.research_trading_date.duplicated().any(): raise AssertionError("invalid pilot selection")
    if (pd.to_datetime(out.research_trading_date).dt.weekday>=5).any(): raise AssertionError("pilot contains weekend")
    return out


def metric(client,method,schema,start,end):
    fn=getattr(client.metadata,method); err=None
    for k in range(7):
        try:
            return fn(dataset="GLBX.MDP3",symbols="GC.v.0",stype_in="continuous",schema=schema,start=start.isoformat(),end=end.isoformat())
        except Exception as e:
            err=e; time.sleep(min(20,2**k))
    raise RuntimeError(f"{method} failed {schema} {start} {end}: {err}")


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--sessions",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    key=os.environ.get("DATABENTO_API_KEY");
    if not key: raise SystemExit("DATABENTO_API_KEY missing")
    raw=pd.read_csv(a.sessions); tier2,panel_qa=prepare_panel(raw); pilot=choose_pilot(tier2); client=db.Historical(key)

    rows=[]
    for r in pilot.itertuples():
        start,end=bounds(str(r.research_trading_date))
        for schema in SCHEMAS:
            rows.append({"era":r.era,"research_trading_date":str(r.research_trading_date),"year":int(r.year),"quarter":int(r.quarter),"vol_band":int(r.vol_band),"panel_rank_v4":int(r.panel_rank_v4),"schema":schema,"start_utc":start.isoformat(),"end_utc":end.isoformat(),"cost_usd":float(metric(client,"get_cost",schema,start,end)),"records":int(metric(client,"get_record_count",schema,start,end)),"billable_bytes":int(metric(client,"get_billable_size",schema,start,end)),"download_performed":False})
    q=pd.DataFrame(rows)
    summary=[{"schema":s,"sessions":int(len(g)),"cost_usd":float(g.cost_usd.sum()),"records":int(g.records.sum()),"billable_bytes":int(g.billable_bytes.sum())} for s,g in q.groupby("schema",sort=True)]
    pcols=["era","research_trading_date","year","quarter","vol_band","panel_rank_v4","quarter_diversified","pilot_hash"]
    pilot[pcols].to_csv(out/"pilot12_sessions.csv",index=False); q.to_csv(out/"pilot12_schema_quotes.csv",index=False)
    result={"version":"COMEX_V4_PILOT12_METADATA_V2_CALENDAR_QA","selection_seed":PILOT_SEED,"panel_qa":panel_qa,"selection_rule":"V4 weekday-valid tier2 only; 4 eras x 3 vol bands; deterministic hash; unused quarter preferred","schemas":list(SCHEMAS),"sessions":pilot[pcols].to_dict("records"),"summary":summary,"pilot_cost_trades_plus_tbbo_usd":float(q[q.schema.isin(["trades","tbbo"])].cost_usd.sum()),"pilot_total_if_all_four_schemas_were_downloaded_usd":float(q.cost_usd.sum()),"authorization":"METADATA_ONLY","download_performed":False,"warning":"No Databento market-data download called."}
    (out/"pilot12_quote.json").write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))

if __name__=="__main__": main()
