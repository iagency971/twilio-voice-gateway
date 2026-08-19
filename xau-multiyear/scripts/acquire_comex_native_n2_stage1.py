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
REQUIRED_AUTH_TEXT = "OK NATIVE N2 STAGE1, plafond 0,36 $"
QUOTE_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_QUOTE_V1"
QA_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_REQUEST_FILE_V1"
COMPLETE_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_ACQUISITION_COMPLETE_V1"
PER_REQUEST_TOLERANCE_USD = 1e-7


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


def quote_one(client: db.Historical, row: dict) -> dict:
    kw = request_kwargs(row)
    cost = float(retry_metadata(client.metadata.get_cost, **kw))
    records = int(retry_metadata(client.metadata.get_record_count, **kw))
    out = dict(row)
    out["gate_cost_usd"] = cost
    out["gate_records"] = records
    return out


def gate(args: argparse.Namespace) -> None:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")

    quote_path = Path(args.quote)
    market_path = Path(args.market_requests)
    level_path = Path(args.level_manifest)
    auth_path = Path(args.authorization)
    completion_path = Path(args.completion_marker)

    if completion_path.exists():
        raise SystemExit("HARD GATE: Stage1 completion marker already exists; refusing second acquisition")
    for p in [quote_path, market_path, level_path, auth_path]:
        if not p.exists():
            raise SystemExit(f"HARD GATE: missing required file {p}")

    quote = json.loads(quote_path.read_text())
    auth = json.loads(auth_path.read_text())
    if quote.get("version") != QUOTE_VERSION:
        raise SystemExit("HARD GATE: wrong quote version")
    if quote.get("authorization") != "METADATA_ONLY_N2_STAGE1_DOWNLOAD_NOT_AUTHORIZED":
        raise SystemExit("HARD GATE: frozen quote authorization field changed")
    if quote.get("market_data_download_performed") is not False or quote.get("n2_download_performed") is not False:
        raise SystemExit("HARD GATE: quote must be pre-download")
    if int(quote.get("levels_stage1", -1)) != 243 or int(quote.get("stage1_merged_market_requests", -1)) != 214:
        raise SystemExit("HARD GATE: frozen Stage1 population mismatch")
    if int(quote.get("one_minute_requests", -1)) != 206 or int(quote.get("two_minute_requests", -1)) != 8:
        raise SystemExit("HARD GATE: frozen request shape mismatch")
    frozen_cost = float(quote.get("exact_stage1_cost_usd", -1))
    if frozen_cost < 0 or frozen_cost > HARD_CAP_USD + 1e-12:
        raise SystemExit("HARD GATE: frozen quote exceeds approved cap")

    market_sha = sha256_file(market_path)
    level_sha = sha256_file(level_path)
    if market_sha != quote.get("market_request_manifest_sha256"):
        raise SystemExit("HARD GATE: market request manifest SHA mismatch")
    if level_sha != quote.get("level_manifest_sha256"):
        raise SystemExit("HARD GATE: level manifest SHA mismatch")

    if auth.get("authorization") != REQUIRED_AUTH_TEXT:
        raise SystemExit("HARD GATE: exact user authorization text absent")
    if abs(float(auth.get("hard_cap_usd", -1)) - HARD_CAP_USD) > 1e-12:
        raise SystemExit("HARD GATE: authorization cap mismatch")
    if auth.get("quote_version") != QUOTE_VERSION:
        raise SystemExit("HARD GATE: authorization quote version mismatch")
    if auth.get("market_request_manifest_sha256") != market_sha or auth.get("level_manifest_sha256") != level_sha:
        raise SystemExit("HARD GATE: authorization is not bound to current manifests")
    if abs(float(auth.get("frozen_quote_usd", -1)) - frozen_cost) > 1e-12:
        raise SystemExit("HARD GATE: authorization quote amount mismatch")
    if auth.get("stage1_only") is not True or auth.get("one_shot") is not True:
        raise SystemExit("HARD GATE: authorization must be stage1_only=true and one_shot=true")
    if auth.get("full_n2_union_authorized") is not False:
        raise SystemExit("HARD GATE: full N2 union must remain unauthorized")

    req = pd.read_csv(market_path, dtype={"symbols": str, "source_instrument_id": str})
    required = {"market_request_id", "request_type", "eligible_next_research_date", "source_instrument_id", "dataset", "schema", "symbols", "stype_in", "start", "end", "candidate_minute_count", "cost_usd"}
    missing = required - set(req.columns)
    if missing:
        raise SystemExit(f"HARD GATE: request manifest missing columns {sorted(missing)}")
    if len(req) != 214 or req.market_request_id.duplicated().any():
        raise SystemExit("HARD GATE: expected exactly 214 unique Stage1 market requests")
    if set(req.request_type.astype(str)) != {"NATIVE_N2_STAGE1_EXACT_TRADES"} or set(req.schema.astype(str)) != {"trades"}:
        raise SystemExit("HARD GATE: unexpected Stage1 request type/schema")
    if int((req.candidate_minute_count == 1).sum()) != 206 or int((req.candidate_minute_count == 2).sum()) != 8:
        raise SystemExit("HARD GATE: Stage1 request duration counts changed")

    levels = pd.read_csv(level_path, dtype={"source_instrument_id": str})
    if len(levels) != 243 or levels.level_id.nunique() != 243 or not levels.candidate_rank.eq(1).all():
        raise SystemExit("HARD GATE: Stage1 level manifest must contain 243 unique rank-1 levels")
    if set(levels.stage1_market_request_id.astype(str)) - set(req.market_request_id.astype(str)):
        raise SystemExit("HARD GATE: level manifest references unknown Stage1 market request")

    client = db.Historical(key)
    quoted = []
    errors = []
    rows = req.to_dict("records")
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(quote_one, client, row): row["market_request_id"] for row in rows}
        for fut in as_completed(futs):
            rid = futs[fut]
            try:
                quoted.append(fut.result())
            except Exception as exc:
                errors.append({"market_request_id": rid, "error": str(exc)})
    if errors:
        raise SystemExit(f"HARD GATE: metadata re-quote failure; no download. first={errors[:3]}")

    quoted = sorted(quoted, key=lambda x: str(x["market_request_id"]))
    total = float(sum(float(x["gate_cost_usd"]) for x in quoted))
    if total > HARD_CAP_USD + 1e-12:
        raise SystemExit(f"HARD GATE: current exact Stage1 quote ${total:.12f} exceeds cap ${HARD_CAP_USD:.2f}; no download")

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    gate_doc = {
        "version": "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_PRE_DOWNLOAD_GATE_V1",
        "authorization": REQUIRED_AUTH_TEXT,
        "approved_cap_usd": HARD_CAP_USD,
        "frozen_quote_usd": frozen_cost,
        "current_exact_quote_usd": total,
        "remaining_margin_usd": HARD_CAP_USD - total,
        "requests": len(quoted),
        "total_expected_records": int(sum(int(x["gate_records"]) for x in quoted)),
        "zero_record_requests": [x["market_request_id"] for x in quoted if int(x["gate_records"]) == 0],
        "market_request_manifest_sha256": market_sha,
        "level_manifest_sha256": level_sha,
        "market_data_download_performed": False,
        "n2_stage1_download_performed": False,
        "full_n2_union_download_authorized": False,
        "rows": quoted,
    }
    (out / "gate.json").write_text(json.dumps(gate_doc, indent=2))
    print(json.dumps({k:v for k,v in gate_doc.items() if k != "rows"}, indent=2))


def acquire(args: argparse.Namespace) -> None:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")
    gate_doc = json.loads(Path(args.gate).read_text())
    if gate_doc.get("version") != "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_PRE_DOWNLOAD_GATE_V1":
        raise SystemExit("invalid Stage1 gate")
    if float(gate_doc.get("approved_cap_usd", -1)) != HARD_CAP_USD:
        raise SystemExit("invalid Stage1 cap in gate")
    if gate_doc.get("market_data_download_performed") is not False:
        raise SystemExit("gate must be pre-download")

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    client = db.Historical(key)
    rows = sorted(gate_doc["rows"], key=lambda x: (str(x["start"]), str(x["market_request_id"])))
    success_upper = 0.0
    failed_reserve = 0.0
    completed = 0

    for row in rows:
        rid = str(row["market_request_id"])
        qa_path = out / f"{rid}.json"
        raw_path = out / f"{rid}.dbn.zst"
        if qa_path.exists() or raw_path.exists():
            raise SystemExit(f"refusing to overwrite Stage1 request {rid}")

        kw = request_kwargs(row)
        expected_cost = float(row["gate_cost_usd"])
        expected_records = int(row["gate_records"])
        current_cost = float(retry_metadata(client.metadata.get_cost, **kw))
        current_records = int(retry_metadata(client.metadata.get_record_count, **kw))
        if current_cost > expected_cost + PER_REQUEST_TOLERANCE_USD + 1e-12:
            raise SystemExit(f"REQUEST GATE {rid}: quote rose {expected_cost:.12f}->{current_cost:.12f}; no paid call")
        if current_records != expected_records:
            raise SystemExit(f"REQUEST GATE {rid}: record count changed {expected_records}->{current_records}; no paid call")
        if success_upper + failed_reserve + current_cost > HARD_CAP_USD + 1e-12:
            raise SystemExit(f"REQUEST GATE {rid}: conservative cumulative cost would exceed cap; no paid call")

        base = {
            "version": QA_VERSION,
            "market_request_id": rid,
            "request_type": str(row["request_type"]),
            "eligible_next_research_date": str(row["eligible_next_research_date"]),
            "source_instrument_id": str(row["source_instrument_id"]),
            "dataset": str(row["dataset"]),
            "schema": str(row["schema"]),
            "symbols": str(row["symbols"]),
            "stype_in": str(row["stype_in"]),
            "start": str(row["start"]),
            "end": str(row["end"]),
            "candidate_minute_count": int(row["candidate_minute_count"]),
            "gate_cost_usd": expected_cost,
            "immediate_pre_download_cost_usd": current_cost,
            "gate_records": expected_records,
        }

        if expected_records == 0:
            base.update({"records_downloaded": 0, "raw_file": None, "raw_file_bytes": 0, "sha256": None, "market_data_request_performed": False, "zero_record_metadata_only": True})
            qa_path.write_text(json.dumps(base, indent=2))
            success_upper += current_cost
            completed += 1
            continue

        try:
            # Sole paid call for this request. Intentionally no automatic retry.
            store = client.timeseries.get_range(path=str(raw_path), **kw)
            df = store.to_df()
        except Exception as exc:
            failed_reserve += current_cost
            failure = {
                "version": "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_FAILED_ATTEMPT_V1",
                "market_request_id": rid,
                "error": f"{type(exc).__name__}: {exc}",
                "conservative_failed_attempt_reserve_usd": current_cost,
                "confirmed_success_cost_upper_bound_before_failure_usd": success_upper,
                "conservative_total_after_failure_usd": success_upper + failed_reserve,
                "hard_cap_usd": HARD_CAP_USD,
                "paid_retry_performed": False,
            }
            (out / "FAILED_ATTEMPT.json").write_text(json.dumps(failure, indent=2))
            (out / "partial_state.json").write_text(json.dumps({"completed_requests": completed, "confirmed_success_cost_upper_bound_usd": success_upper, "failed_attempt_reserve_usd": failed_reserve, "hard_cap_usd": HARD_CAP_USD}, indent=2))
            raise

        downloaded = int(len(df))
        if downloaded != expected_records:
            # The paid call occurred; reserve its full quoted cost and stop. Do not retry.
            failed_reserve += current_cost
            failure = {
                "version": "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_POST_DOWNLOAD_QA_FAILURE_V1",
                "market_request_id": rid,
                "error": f"downloaded_records={downloaded} expected_records={expected_records}",
                "conservative_failed_attempt_reserve_usd": current_cost,
                "confirmed_success_cost_upper_bound_before_failure_usd": success_upper,
                "conservative_total_after_failure_usd": success_upper + failed_reserve,
                "hard_cap_usd": HARD_CAP_USD,
                "paid_retry_performed": False,
            }
            (out / "FAILED_ATTEMPT.json").write_text(json.dumps(failure, indent=2))
            raise RuntimeError(f"{rid}: record-count mismatch after paid call")

        base.update({
            "records_downloaded": downloaded,
            "raw_file": raw_path.name,
            "raw_file_bytes": int(raw_path.stat().st_size),
            "sha256": sha256_file(raw_path),
            "market_data_request_performed": True,
            "zero_record_metadata_only": False,
        })
        qa_path.write_text(json.dumps(base, indent=2))
        success_upper += current_cost
        completed += 1

    state = {
        "version": "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_ACQUIRE_STATE_V1",
        "completed_requests": completed,
        "confirmed_success_cost_upper_bound_usd": success_upper,
        "failed_attempt_reserve_usd": failed_reserve,
        "conservative_total_usd": success_upper + failed_reserve,
        "hard_cap_usd": HARD_CAP_USD,
    }
    (out / "acquire_state.json").write_text(json.dumps(state, indent=2))
    print(json.dumps(state, indent=2))


def finalize(args: argparse.Namespace) -> None:
    market_path = Path(args.market_requests)
    root = Path(args.root)
    req = pd.read_csv(market_path, dtype={"symbols": str, "source_instrument_id": str})
    expected = set(req.market_request_id.astype(str))
    markers = {}
    for p in root.glob("*.json"):
        try:
            z = json.loads(p.read_text())
        except Exception:
            continue
        if z.get("version") == QA_VERSION:
            markers[str(z["market_request_id"])] = z
    got = set(markers)
    missing = sorted(expected - got)
    extra = sorted(got - expected)
    complete = len(missing) == 0 and len(extra) == 0 and len(got) == 214
    rows = [markers[k] for k in sorted(markers)]
    success_upper = float(sum(float(z.get("immediate_pre_download_cost_usd", 0.0)) for z in rows))
    records_total = int(sum(int(z.get("records_downloaded", 0)) for z in rows))
    raw_bytes = int(sum(int(z.get("raw_file_bytes", 0)) for z in rows))
    if success_upper > HARD_CAP_USD + 1e-12:
        raise SystemExit("FINALIZE: successful request upper-bound cost exceeds cap")

    result = {
        "version": "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_ACQUISITION_SUMMARY_V1",
        "complete": complete,
        "expected_requests": 214,
        "completed_request_markers": len(got),
        "missing_request_ids": missing,
        "extra_request_ids": extra,
        "records_downloaded_total": records_total,
        "raw_bytes_total": raw_bytes,
        "confirmed_success_cost_upper_bound_usd": success_upper,
        "hard_cap_usd": HARD_CAP_USD,
        "hard_cap_respected": success_upper <= HARD_CAP_USD + 1e-12,
        "n2_stage1_market_data_download_performed": complete,
        "n2_later_stage_download_performed": False,
        "full_n2_union_download_performed": False,
    }
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "acquisition_summary.json").write_text(json.dumps(result, indent=2))
    if not complete:
        raise SystemExit(f"FINALIZE incomplete: missing={missing[:5]} extra={extra[:5]}")

    marker = {
        "version": COMPLETE_VERSION,
        "complete": True,
        "requests": 214,
        "market_request_manifest_sha256": sha256_file(market_path),
        "records_downloaded_total": records_total,
        "confirmed_success_cost_upper_bound_usd": success_upper,
        "hard_cap_usd": HARD_CAP_USD,
        "summary_sha256": sha256_file(out / "acquisition_summary.json"),
        "n2_stage2_download_authorized": False,
        "full_n2_union_download_authorized": False,
        "dev_rank2_opened": False,
        "retro_confirm_opened": False,
        "locked_comex_test_opened": False,
    }
    (out / "ACQUISITION_COMPLETE.json").write_text(json.dumps(marker, indent=2))
    print(json.dumps(result, indent=2))


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gate")
    g.add_argument("--quote", required=True)
    g.add_argument("--market-requests", required=True)
    g.add_argument("--level-manifest", required=True)
    g.add_argument("--authorization", required=True)
    g.add_argument("--completion-marker", required=True)
    g.add_argument("--out", required=True)
    a = sub.add_parser("acquire")
    a.add_argument("--gate", required=True)
    a.add_argument("--out", required=True)
    f = sub.add_parser("finalize")
    f.add_argument("--market-requests", required=True)
    f.add_argument("--root", required=True)
    f.add_argument("--out", required=True)
    return ap.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.cmd == "gate": gate(args)
    elif args.cmd == "acquire": acquire(args)
    else: finalize(args)
