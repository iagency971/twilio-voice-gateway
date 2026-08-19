#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import databento as db

HARD_CAP_USD = 0.36
QA_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_REQUEST_FILE_V1"
GATE_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_PRE_DOWNLOAD_GATE_V1"
TOL = 1e-7


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def request_kwargs(row: dict) -> dict:
    return {k: str(row[k]) for k in ["dataset", "symbols", "stype_in", "schema", "start", "end"]}


def retry_metadata(fn, **kwargs):
    err = None
    for k in range(7):
        try: return fn(**kwargs)
        except Exception as exc:
            err = exc; time.sleep(min(20, 2**k))
    raise RuntimeError(f"metadata failed after retries: {err}")


def decode_validate(raw: Path, expected_iid: str) -> pd.DataFrame:
    store = db.DBNStore.from_file(raw)
    df = store.to_df().reset_index(drop=False)
    if "instrument_id" in df.columns and len(df):
        ids = set(pd.Series(df.instrument_id).dropna().astype(int).astype(str))
        if ids and ids != {str(expected_iid)}:
            raise SystemExit(f"raw file {raw.name} has unexpected instrument ids {ids}")
    return df


def quote_missing(client: db.Historical, rows: list[dict]) -> list[dict]:
    def one(row):
        kw = request_kwargs(row)
        z = dict(row)
        z["recovery_cost_usd"] = float(retry_metadata(client.metadata.get_cost, **kw))
        z["recovery_record_count_estimate"] = int(retry_metadata(client.metadata.get_record_count, **kw))
        return z
    out=[];errs=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        fs={ex.submit(one,row):row["market_request_id"] for row in rows}
        for f in as_completed(fs):
            try: out.append(f.result())
            except Exception as exc: errs.append({"market_request_id":fs[f],"error":str(exc)})
    if errs: raise SystemExit(f"recovery metadata gate failed; no further market call. first={errs[:3]}")
    return out


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--gate",required=True)
    ap.add_argument("--market-requests",required=True)
    ap.add_argument("--root",required=True)
    a=ap.parse_args()
    key=os.environ.get("DATABENTO_API_KEY")
    if not key: raise SystemExit("DATABENTO_API_KEY missing")

    gate=json.loads(Path(a.gate).read_text())
    if gate.get("version") != GATE_VERSION or abs(float(gate.get("approved_cap_usd",-1))-HARD_CAP_USD)>1e-12:
        raise SystemExit("invalid original Stage1 gate")
    req=pd.read_csv(a.market_requests,dtype={"symbols":str,"source_instrument_id":str})
    if len(req)!=214 or req.market_request_id.nunique()!=214:
        raise SystemExit("expected 214 frozen Stage1 requests")
    gate_rows={str(z["market_request_id"]):z for z in gate["rows"]}
    if set(gate_rows)!=set(req.market_request_id.astype(str)):
        raise SystemExit("gate/request manifest parity failure")

    root=Path(a.root); root.mkdir(parents=True,exist_ok=True)
    failure_path=root/"FAILED_ATTEMPT.json"
    failure=json.loads(failure_path.read_text()) if failure_path.exists() else None

    markers={}
    for p in root.glob("*.json"):
        try:z=json.loads(p.read_text())
        except Exception:continue
        if z.get("version")==QA_VERSION: markers[str(z["market_request_id"])]=z

    # Salvage the already-paid raw file from the invalid metadata-record-count equality QA.
    if failure and failure.get("version")=="COMEX_DEV_RANK1_NATIVE_N2_STAGE1_POST_DOWNLOAD_QA_FAILURE_V1":
        rid=str(failure["market_request_id"])
        if rid not in markers:
            row=gate_rows[rid]
            raw=root/f"{rid}.dbn.zst"
            if not raw.exists(): raise SystemExit("post-download QA failure has no raw file to salvage")
            df=decode_validate(raw,str(row["source_instrument_id"]))
            marker={
                "version":QA_VERSION,
                "market_request_id":rid,
                "request_type":str(row["request_type"]),
                "eligible_next_research_date":str(row["eligible_next_research_date"]),
                "source_instrument_id":str(row["source_instrument_id"]),
                "dataset":str(row["dataset"]),"schema":str(row["schema"]),"symbols":str(row["symbols"]),"stype_in":str(row["stype_in"]),
                "start":str(row["start"]),"end":str(row["end"]),"candidate_minute_count":int(row["candidate_minute_count"]),
                "gate_cost_usd":float(row["gate_cost_usd"]),
                "immediate_pre_download_cost_usd":float(failure["conservative_failed_attempt_reserve_usd"]),
                "metadata_record_count_estimate":int(row["gate_records"]),
                "records_downloaded":int(len(df)),
                "raw_file":raw.name,"raw_file_bytes":int(raw.stat().st_size),"sha256":sha256_file(raw),
                "market_data_request_performed":True,
                "recovered_without_replay":True,
                "recovery_reason":"Databento metadata.get_record_count may over-report for sub-10-minute ranges; raw DBN decoded successfully",
            }
            (root/f"{rid}.json").write_text(json.dumps(marker,indent=2));markers[rid]=marker
            (root/"RECOVERED_PREVIOUS_QA_FAILURE.json").write_text(json.dumps({
                "version":"COMEX_DEV_RANK1_NATIVE_N2_STAGE1_RECORD_COUNT_QA_RECOVERY_V1",
                "market_request_id":rid,"raw_records":int(len(df)),"metadata_record_count_estimate":int(row["gate_records"]),
                "paid_market_request_replayed":False,"raw_sha256":sha256_file(raw)
            },indent=2))

    # Validate any completed markers before resuming.
    success_upper=0.0
    for rid,z in markers.items():
        if rid not in gate_rows: raise SystemExit(f"unknown existing marker {rid}")
        raw_name=z.get("raw_file")
        if raw_name:
            raw=root/str(raw_name)
            if not raw.exists() or sha256_file(raw)!=z.get("sha256"): raise SystemExit(f"existing raw SHA failure {rid}")
            decode_validate(raw,str(gate_rows[rid]["source_instrument_id"]))
        success_upper += float(z.get("immediate_pre_download_cost_usd",z.get("gate_cost_usd",0.0)))

    missing=[gate_rows[rid] for rid in sorted(set(gate_rows)-set(markers))]
    client=db.Historical(key)
    quoted=quote_missing(client,missing)
    quoted_by={str(z["market_request_id"]):z for z in quoted}
    remaining_cost=float(sum(float(z["recovery_cost_usd"]) for z in quoted))
    if success_upper + remaining_cost > HARD_CAP_USD + 1e-12:
        raise SystemExit(f"RECOVERY HARD GATE: existing+remaining ${success_upper+remaining_cost:.12f} exceeds ${HARD_CAP_USD:.2f}; no further market call")
    for z in quoted:
        if float(z["recovery_cost_usd"]) > float(z["gate_cost_usd"]) + TOL + 1e-12:
            raise SystemExit(f"RECOVERY HARD GATE: request {z['market_request_id']} cost rose beyond tolerance; no further market call")

    plan={
        "version":"COMEX_DEV_RANK1_NATIVE_N2_STAGE1_RECOVERY_GATE_V1",
        "existing_completed_requests":len(markers),"missing_requests":len(missing),
        "existing_success_cost_upper_bound_usd":success_upper,"remaining_exact_quote_usd":remaining_cost,
        "conservative_completion_upper_bound_usd":success_upper+remaining_cost,"hard_cap_usd":HARD_CAP_USD,
        "record_count_semantics":"metadata record count is an estimate for these 1-2 minute ranges and is not used as post-download equality QA",
        "paid_replay_of_salvaged_request":False,
    }
    (root/"RECOVERY_GATE.json").write_text(json.dumps(plan,indent=2));print(json.dumps(plan,indent=2))

    # Resume only missing requests. Each market-data call is attempted at most once.
    for row0 in sorted(quoted,key=lambda z:(str(z["start"]),str(z["market_request_id"]))):
        rid=str(row0["market_request_id"])
        raw=root/f"{rid}.dbn.zst";qa=root/f"{rid}.json"
        if raw.exists() or qa.exists(): raise SystemExit(f"refusing overwrite on recovery {rid}")
        kw=request_kwargs(row0)
        current_cost=float(retry_metadata(client.metadata.get_cost,**kw))
        current_count=int(retry_metadata(client.metadata.get_record_count,**kw))
        if current_cost > float(row0["recovery_cost_usd"]) + TOL + 1e-12:
            raise SystemExit(f"REQUEST GATE {rid}: cost rose before paid call")
        if success_upper + current_cost + sum(float(quoted_by[x]["recovery_cost_usd"]) for x in quoted_by if x!=rid and x not in markers) > HARD_CAP_USD + 1e-12:
            raise SystemExit(f"REQUEST GATE {rid}: conservative completion would exceed cap")
        try:
            store=client.timeseries.get_range(path=str(raw),**kw)
            df=store.to_df()
        except Exception as exc:
            fail={
                "version":"COMEX_DEV_RANK1_NATIVE_N2_STAGE1_RECOVERY_FAILED_ATTEMPT_V1","market_request_id":rid,
                "error":f"{type(exc).__name__}: {exc}","conservative_failed_attempt_reserve_usd":current_cost,
                "confirmed_success_cost_upper_bound_before_failure_usd":success_upper,"hard_cap_usd":HARD_CAP_USD,
                "paid_retry_performed":False
            }
            (root/"RECOVERY_FAILED_ATTEMPT.json").write_text(json.dumps(fail,indent=2));raise
        marker={
            "version":QA_VERSION,"market_request_id":rid,"request_type":str(row0["request_type"]),
            "eligible_next_research_date":str(row0["eligible_next_research_date"]),"source_instrument_id":str(row0["source_instrument_id"]),
            "dataset":str(row0["dataset"]),"schema":str(row0["schema"]),"symbols":str(row0["symbols"]),"stype_in":str(row0["stype_in"]),
            "start":str(row0["start"]),"end":str(row0["end"]),"candidate_minute_count":int(row0["candidate_minute_count"]),
            "gate_cost_usd":float(row0["gate_cost_usd"]),"immediate_pre_download_cost_usd":current_cost,
            "metadata_record_count_estimate":current_count,"records_downloaded":int(len(df)),
            "raw_file":raw.name,"raw_file_bytes":int(raw.stat().st_size),"sha256":sha256_file(raw),
            "market_data_request_performed":True,"recovered_without_replay":False,
        }
        qa.write_text(json.dumps(marker,indent=2));markers[rid]=marker;success_upper+=current_cost

    if set(markers)!=set(gate_rows):
        raise SystemExit(f"recovery ended incomplete markers={len(markers)}/214")
    state={"version":"COMEX_DEV_RANK1_NATIVE_N2_STAGE1_RECOVERY_COMPLETE_V1","completed_requests":214,"confirmed_success_cost_upper_bound_usd":success_upper,"hard_cap_usd":HARD_CAP_USD,"paid_replay_of_salvaged_request":False}
    (root/"RECOVERY_COMPLETE.json").write_text(json.dumps(state,indent=2));print(json.dumps(state,indent=2))


if __name__=="__main__": main()
