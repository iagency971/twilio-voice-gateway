#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import databento as db

HARD_CAP_USD = 0.025
REQUIRED_AUTH_TEXT = "OK NATIVE N2 STAGE3, plafond 0,025 $"
QUOTE_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE2_RESOLUTION_STAGE3_QUOTE_V1"
AUTH_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE3_AUTH_V1"
REQ_MARKER_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE3_REQUEST_FILE_V1"
COMPLETE_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE3_ACQUISITION_COMPLETE_V1"
EXPECTED_COST = 0.024528264999


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def retry_metadata(fn, **kwargs):
    err = None
    for k in range(7):
        try:
            return fn(**kwargs)
        except Exception as exc:
            err = exc
            time.sleep(min(20, 2**k))
    raise RuntimeError(f"metadata call failed after retries: {err}")


def request_kwargs(row: dict) -> dict:
    return {
        "dataset": str(row["dataset"]),
        "symbols": str(row["symbols"]),
        "stype_in": str(row["stype_in"]),
        "schema": str(row["schema"]),
        "start": str(row["start"]),
        "end": str(row["end"]),
    }


def gate(args: argparse.Namespace) -> None:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")
    qpath = Path(args.quote); rpath = Path(args.market_requests); lpath = Path(args.level_manifest)
    apath = Path(args.authorization); completion = Path(args.completion_marker)
    if completion.exists():
        raise SystemExit("HARD GATE: Stage3 completion marker already exists")
    q = json.loads(qpath.read_text()); a = json.loads(apath.read_text())
    if q.get("version") != QUOTE_VERSION:
        raise SystemExit("HARD GATE: wrong Stage3 quote version")
    if q.get("stage3_authorization") != "METADATA_ONLY_STAGE3_DOWNLOAD_NOT_AUTHORIZED":
        raise SystemExit("HARD GATE: frozen Stage3 authorization state changed")
    if q.get("stage3_market_data_download_performed") is not False:
        raise SystemExit("HARD GATE: Stage3 already marked downloaded")
    if int(q.get("stage3_levels", -1)) != 1 or int(q.get("stage3_merged_market_requests", -1)) != 1:
        raise SystemExit("HARD GATE: expected exactly one Stage3 level/request")
    if int(q.get("unresolved_after_stage2", -1)) != 1 or bool(q.get("all_368_classified")):
        raise SystemExit("HARD GATE: Stage2 terminal state mismatch")
    if abs(float(q.get("exact_stage3_cost_usd", -1)) - EXPECTED_COST) > 1e-15:
        raise SystemExit("HARD GATE: frozen Stage3 quote changed")

    rsha = sha256_file(rpath); lsha = sha256_file(lpath)
    if rsha != q.get("stage3_market_request_manifest_sha256") or lsha != q.get("stage3_level_manifest_sha256"):
        raise SystemExit("HARD GATE: Stage3 manifest SHA mismatch")
    if a.get("version") != AUTH_VERSION or a.get("authorization") != REQUIRED_AUTH_TEXT:
        raise SystemExit("HARD GATE: exact user authorization absent")
    if abs(float(a.get("hard_cap_usd", -1)) - HARD_CAP_USD) > 1e-15:
        raise SystemExit("HARD GATE: authorization cap mismatch")
    if a.get("stage3_market_request_manifest_sha256") != rsha or a.get("stage3_level_manifest_sha256") != lsha:
        raise SystemExit("HARD GATE: authorization not bound to current Stage3 manifests")
    if a.get("one_shot") is not True or a.get("later_stage_download_authorized") is not False:
        raise SystemExit("HARD GATE: authorization scope invalid")

    req = pd.read_csv(rpath, dtype={"source_instrument_id": str, "symbols": str})
    lvl = pd.read_csv(lpath, dtype={"source_instrument_id": str})
    if len(req) != 1 or len(lvl) != 1 or req.market_request_id.nunique() != 1 or lvl.level_id.nunique() != 1:
        raise SystemExit("HARD GATE: Stage3 cardinality mismatch")
    if str(lvl.iloc[0].level_id) != "1223ab410b28e74ebbed372e":
        raise SystemExit("HARD GATE: unexpected Stage3 level")
    if int(lvl.iloc[0].candidate_rank) != 3 or abs(float(lvl.iloc[0].contact_tick_price) - 1702.0) > 1e-9:
        raise SystemExit("HARD GATE: Stage3 level definition changed")
    if set(req.schema.astype(str)) != {"trades"} or set(req.dataset.astype(str)) != {"GLBX.MDP3"}:
        raise SystemExit("HARD GATE: unexpected Stage3 schema/dataset")

    row = req.iloc[0].to_dict(); client = db.Historical(key)
    current = float(retry_metadata(client.metadata.get_cost, **request_kwargs(row)))
    if current > HARD_CAP_USD + 1e-15:
        raise SystemExit(f"HARD GATE: current Stage3 quote ${current:.12f} exceeds approved cap ${HARD_CAP_USD:.3f}")
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    g = {
        "version": "COMEX_DEV_RANK1_NATIVE_N2_STAGE3_PRE_DOWNLOAD_GATE_V1",
        "authorization": REQUIRED_AUTH_TEXT,
        "approved_cap_usd": HARD_CAP_USD,
        "frozen_quote_usd": EXPECTED_COST,
        "current_exact_quote_usd": current,
        "remaining_margin_usd": HARD_CAP_USD-current,
        "requests": 1,
        "market_request_manifest_sha256": rsha,
        "level_manifest_sha256": lsha,
        "market_data_download_performed": False,
        "later_stage_download_authorized": False,
        "row": {**row, "gate_cost_usd": current},
    }
    (out / "gate.json").write_text(json.dumps(g, indent=2)); print(json.dumps(g, indent=2))


def acquire(args: argparse.Namespace) -> None:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")
    g = json.loads(Path(args.gate).read_text()); row = dict(g["row"])
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    rid = str(row["market_request_id"]); raw = out / f"{rid}.dbn.zst"; marker = out / f"{rid}.json"
    if raw.exists() or marker.exists():
        raise SystemExit("refusing Stage3 overwrite")
    client = db.Historical(key); kw = request_kwargs(row)
    current = float(retry_metadata(client.metadata.get_cost, **kw))
    if current > HARD_CAP_USD + 1e-15:
        raise SystemExit(f"REQUEST GATE: Stage3 quote ${current:.12f} exceeds cap")
    # Sole paid market-data call. Deliberately no automatic paid retry.
    store = client.timeseries.get_range(path=str(raw), **kw)
    df = store.to_df()
    if not raw.exists():
        raise RuntimeError("Stage3 returned without raw DBN file")
    qa = {
        "version": REQ_MARKER_VERSION,
        "market_request_id": rid,
        "dataset": str(row["dataset"]), "schema": str(row["schema"]), "symbols": str(row["symbols"]),
        "stype_in": str(row["stype_in"]), "start": str(row["start"]), "end": str(row["end"]),
        "gate_cost_usd": float(row["gate_cost_usd"]), "immediate_pre_download_cost_usd": current,
        "decoded_trade_records": int(len(df)), "raw_file": raw.name, "raw_file_bytes": int(raw.stat().st_size),
        "sha256": sha256_file(raw), "market_data_request_performed": True, "record_count_equality_qa_used": False,
    }
    marker.write_text(json.dumps(qa, indent=2)); print(json.dumps(qa, indent=2))


def finalize(args: argparse.Namespace) -> None:
    req = pd.read_csv(args.market_requests); root = Path(args.root)
    rid = str(req.iloc[0].market_request_id); marker = root / f"{rid}.json"; raw = root / f"{rid}.dbn.zst"
    if not marker.exists() or not raw.exists():
        raise SystemExit("Stage3 incomplete")
    z = json.loads(marker.read_text())
    if z.get("version") != REQ_MARKER_VERSION or str(z.get("market_request_id")) != rid:
        raise SystemExit("Stage3 marker mismatch")
    if sha256_file(raw) != z.get("sha256"):
        raise SystemExit("Stage3 raw SHA mismatch")
    cost = float(z["immediate_pre_download_cost_usd"])
    if cost > HARD_CAP_USD + 1e-15:
        raise SystemExit("Stage3 cost exceeds cap")
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    summary = {
        "version": "COMEX_DEV_RANK1_NATIVE_N2_STAGE3_ACQUISITION_SUMMARY_V1", "complete": True,
        "expected_requests": 1, "completed_request_markers": 1, "decoded_trade_records_total": int(z["decoded_trade_records"]),
        "raw_bytes_total": int(z["raw_file_bytes"]), "confirmed_success_cost_upper_bound_usd": cost,
        "hard_cap_usd": HARD_CAP_USD, "hard_cap_respected": True, "stage3_market_data_download_performed": True,
        "later_stage_market_data_download_performed": False,
    }
    (out / "acquisition_summary.json").write_text(json.dumps(summary, indent=2))
    complete = {
        "version": COMPLETE_VERSION, "complete": True, "requests": 1,
        "confirmed_success_cost_upper_bound_usd": cost, "hard_cap_usd": HARD_CAP_USD,
        "later_stage_download_authorized": False, "dev_rank2_opened": False,
        "retro_confirm_opened": False, "locked_comex_test_opened": False,
        "summary_sha256": sha256_file(out / "acquisition_summary.json"),
    }
    (out / "ACQUISITION_COMPLETE.json").write_text(json.dumps(complete, indent=2)); print(json.dumps(summary, indent=2))


def load_dbn(path: Path) -> pd.DataFrame:
    df = db.DBNStore.from_file(path).to_df().reset_index(drop=False)
    if "ts_event" not in df.columns:
        if len(df.columns) == 0:
            return pd.DataFrame(columns=["ts_event", "price"])
        df = df.rename(columns={df.columns[0]: "ts_event"})
    df["ts_event"] = pd.to_datetime(df.ts_event, utc=True)
    return df.sort_values("ts_event").reset_index(drop=True)


def analyze_final(args: argparse.Namespace) -> None:
    root = Path(args.root); complete = json.loads((root / "ACQUISITION_COMPLETE.json").read_text())
    if complete.get("version") != COMPLETE_VERSION or complete.get("complete") is not True:
        raise SystemExit("Stage3 completion invalid")
    lvl = pd.read_csv(args.stage3_level_manifest, dtype={"source_instrument_id": str})
    all368 = pd.read_csv(args.status_after_stage2, dtype={"source_instrument_id": str})
    if len(lvl) != 1 or len(all368) != 368 or all368.level_id.nunique() != 368:
        raise SystemExit("Stage3 analysis cardinality mismatch")
    r = lvl.iloc[0]; lid = str(r.level_id); rid = str(r.stage3_market_request_id)
    marker = json.loads((root / f"{rid}.json").read_text()); raw = root / marker["raw_file"]
    if sha256_file(raw) != marker["sha256"]:
        raise SystemExit("Stage3 raw integrity failure")
    df = load_dbn(raw)
    if "price" not in df.columns:
        if len(df): raise SystemExit("Stage3 raw lacks price")
        exact = df
    else:
        df["price"] = pd.to_numeric(df.price, errors="coerce")
        good = df.price.notna()
        if good.any():
            scaled = df.loc[good, "price"].to_numpy(float) * 10.0
            if int((np.abs(scaled - np.rint(scaled)) > 1e-6).sum()):
                raise SystemExit("off GC 0.10 tick trades in Stage3")
        tick = int(round(float(r.contact_tick_price) * 10.0))
        price_tick = np.rint(df.price.to_numpy(float) * 10.0)
        exact = df.loc[df.price.notna() & (price_tick == tick)].copy().sort_values("ts_event")
    contact = bool(len(exact)); first_time = exact.iloc[0].ts_event.isoformat() if contact else ""
    status = "RESOLVED_CONTACT_STAGE3" if contact else "RESOLVED_NO_CONTACT_EXHAUSTED_STAGE3"

    m = all368.level_id.astype(str) == lid
    if int(m.sum()) != 1 or str(all368.loc[m, "resolution_after_stage2"].iloc[0]) != "UNRESOLVED_ADVANCE_STAGE3":
        raise SystemExit("Stage3 target not uniquely unresolved in 368 status")
    all368.loc[m, "exact_contact_so_far"] = contact
    all368.loc[m, "first_exact_contact_time_utc"] = first_time
    all368.loc[m, "contact_stage"] = 3 if contact else ""
    all368.loc[m, "resolution_after_stage2"] = status
    all368 = all368.rename(columns={"exact_contact_so_far":"exact_contact_final","resolution_after_stage2":"final_resolution"})
    if all368.final_resolution.eq("UNRESOLVED_ADVANCE_STAGE3").any():
        raise SystemExit("final 368 still contains unresolved Stage3 status")

    bytype = all368.groupby("level_type", as_index=False).agg(levels=("level_id","size"), exact_contacts=("exact_contact_final","sum"))
    bytype["resolved_no_contact"] = bytype.level_type.map(all368[all368.final_resolution.str.startswith("RESOLVED_NO_CONTACT")].groupby("level_type").size()).fillna(0).astype(int)
    bytype["exact_contact_rate"] = bytype.exact_contacts / bytype.levels
    exact_total = int(all368.exact_contact_final.sum()); no_total = int(all368.final_resolution.str.startswith("RESOLVED_NO_CONTACT").sum())
    if exact_total + no_total != 368:
        raise SystemExit("final 368 accounting mismatch")

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    final_row = {
        "level_id": lid, "source_research_date": str(r.source_research_date),
        "eligible_next_research_date": str(r.eligible_next_research_date), "source_instrument_id": str(r.source_instrument_id),
        "level_type": str(r.level_type), "contact_tick_price": float(r.contact_tick_price),
        "stage3_candidate_minute_start_utc": str(r.minute_start_utc), "stage3_market_request_id": rid,
        "stage3_trade_records_in_candidate_minute": int(len(df)), "stage3_exact_tick_trade_count": int(len(exact)),
        "stage3_exact_contact": contact, "stage3_first_exact_contact_time_utc": first_time,
        "candidate_minutes_total": 3, "final_resolution": status,
    }
    pd.DataFrame([final_row]).to_csv(out / "native_n2_stage3_resolution.csv", index=False)
    all368.to_csv(out / "native_368_contact_status_final.csv", index=False)
    bytype.to_csv(out / "native_368_contact_status_by_type_final.csv", index=False)
    manifest = {
        "version": "COMEX_DEV_RANK1_NATIVE_N2_FINAL_CONTACT_CLASSIFICATION_V1",
        "native_levels_total": 368, "all_368_classified": True,
        "exact_contacts_final": exact_total, "resolved_no_contact_final": no_total,
        "exact_contact_rate_final": exact_total / 368.0,
        "stage3_exact_contact": contact, "stage3_exact_tick_trade_count": int(len(exact)),
        "stage3_first_exact_contact_time_utc": first_time,
        "stage3_final_resolution": status,
        "stage3_acquisition_cost_upper_bound_usd": float(json.loads((root / "acquisition_summary.json").read_text())["confirmed_success_cost_upper_bound_usd"]),
        "stage3_hard_cap_usd": HARD_CAP_USD,
        "later_stage_market_data_download_performed": False,
        "native_368_status_final_sha256": sha256_file(out / "native_368_contact_status_final.csv"),
        "native_368_by_type_final_sha256": sha256_file(out / "native_368_contact_status_by_type_final.csv"),
        "stage3_resolution_sha256": sha256_file(out / "native_n2_stage3_resolution.csv"),
        "dev_rank2_opened": False, "retro_confirm_opened": False, "locked_comex_test_opened": False,
        "notes": ["Stage3 was the final candidate minute for the sole unresolved level.", "No Stage4 exists under the frozen sequential protocol for this level.", "This closes exact-contact classification only; reaction-edge analysis is a separate step."],
    }
    (out / "native_n2_final_contact_classification.json").write_text(json.dumps(manifest, indent=2)); print(json.dumps(manifest, indent=2))


def main():
    p = argparse.ArgumentParser(); sp = p.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("gate")
    for x in ["quote","market-requests","level-manifest","authorization","completion-marker","out"]: g.add_argument("--"+x, required=True)
    a = sp.add_parser("acquire"); a.add_argument("--gate", required=True); a.add_argument("--out", required=True)
    f = sp.add_parser("finalize"); f.add_argument("--market-requests", required=True); f.add_argument("--root", required=True); f.add_argument("--out", required=True)
    z = sp.add_parser("analyze-final"); z.add_argument("--root", required=True); z.add_argument("--stage3-level-manifest", required=True); z.add_argument("--status-after-stage2", required=True); z.add_argument("--out", required=True)
    args = p.parse_args()
    if args.cmd == "gate": gate(args)
    elif args.cmd == "acquire": acquire(args)
    elif args.cmd == "finalize": finalize(args)
    else: analyze_final(args)


if __name__ == "__main__":
    main()
