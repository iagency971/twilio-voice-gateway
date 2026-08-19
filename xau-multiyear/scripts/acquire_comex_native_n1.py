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

HARD_CAP_USD = 0.45
REQUIRED_AUTH_TEXT = "OK NATIVE N1, plafond 0,45 $"
QUOTE_VERSION = "COMEX_DEV_RANK1_NATIVE_N1_QUOTE_V1_1"
AUTH_VERSION = "COMEX_DEV_RANK1_NATIVE_N1_AUTHORIZATION_V1"
REQUEST_QA_VERSION = "COMEX_DEV_RANK1_NATIVE_N1_REQUEST_FILE_V1"


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
    out = dict(row)
    out["gate_cost_usd"] = float(retry_metadata(client.metadata.get_cost, **kw))
    out["gate_records"] = int(retry_metadata(client.metadata.get_record_count, **kw))
    return out


def validate_frozen_inputs(args: argparse.Namespace):
    quote_path = Path(args.quote)
    market_path = Path(args.market_requests)
    source_path = Path(args.source_requests)
    auth_path = Path(args.authorization)
    completion_path = Path(args.completion_marker)

    if completion_path.exists():
        raise SystemExit("HARD GATE: N1 completion marker already exists; refusing second acquisition")
    if not auth_path.exists():
        raise SystemExit("HARD GATE: N1 authorization file missing")

    quote = json.loads(quote_path.read_text())
    auth = json.loads(auth_path.read_text())

    if quote.get("version") != QUOTE_VERSION:
        raise SystemExit("HARD GATE: wrong N1 quote version")
    if quote.get("authorization") != "METADATA_ONLY":
        raise SystemExit("HARD GATE: quote authorization field changed")
    if quote.get("download_performed") is not False or quote.get("market_data_download_performed") is not False:
        raise SystemExit("HARD GATE: quote claims a prior download")
    if int(quote.get("source_levels", -1)) != 368 or int(quote.get("source_sessions", -1)) != 92:
        raise SystemExit("HARD GATE: wrong native source population")
    if int(quote.get("source_requests", -1)) != 92 or int(quote.get("unique_market_requests", -1)) != 92:
        raise SystemExit("HARD GATE: expected 92 source and market requests")
    if float(quote.get("exact_n1_cost_usd", 99)) > HARD_CAP_USD + 1e-12:
        raise SystemExit("HARD GATE: frozen N1 quote already exceeds approved cap")
    if quote.get("dev_rank2_opened") is not False or quote.get("retro_confirm_opened") is not False or quote.get("locked_comex_test_opened") is not False:
        raise SystemExit("HARD GATE: locked block state invalid")

    market_sha = sha256_file(market_path)
    source_sha = sha256_file(source_path)
    if market_sha != quote.get("market_request_manifest_sha256"):
        raise SystemExit("HARD GATE: market request manifest SHA mismatch")
    if source_sha != quote.get("source_request_manifest_sha256"):
        raise SystemExit("HARD GATE: source request manifest SHA mismatch")

    if auth.get("version") != AUTH_VERSION:
        raise SystemExit("HARD GATE: wrong authorization version")
    if auth.get("authorization") != REQUIRED_AUTH_TEXT:
        raise SystemExit("HARD GATE: exact user authorization text absent")
    if abs(float(auth.get("hard_cap_usd", -1)) - HARD_CAP_USD) > 1e-12:
        raise SystemExit("HARD GATE: authorization cap mismatch")
    if auth.get("one_shot") is not True:
        raise SystemExit("HARD GATE: authorization must be one_shot=true")
    if auth.get("n2_download_authorized") is not False:
        raise SystemExit("HARD GATE: N2 must remain unauthorized")
    if auth.get("market_request_manifest_sha256") != market_sha:
        raise SystemExit("HARD GATE: authorization not bound to market request manifest")
    if auth.get("source_request_manifest_sha256") != source_sha:
        raise SystemExit("HARD GATE: authorization not bound to source request manifest")
    if auth.get("quote_version") != QUOTE_VERSION:
        raise SystemExit("HARD GATE: authorization not bound to quote version")
    if abs(float(auth.get("approved_quote_usd", -1)) - float(quote["exact_n1_cost_usd"])) > 1e-12:
        raise SystemExit("HARD GATE: authorization quote amount mismatch")

    req = pd.read_csv(market_path, dtype={"symbols": str, "source_instrument_id": str})
    required = {"market_request_id", "dataset", "schema", "symbols", "stype_in", "start", "end"}
    missing = required - set(req.columns)
    if missing:
        raise SystemExit(f"HARD GATE: market manifest missing columns {sorted(missing)}")
    if len(req) != 92 or req.market_request_id.duplicated().any():
        raise SystemExit("HARD GATE: market manifest must contain 92 unique requests")
    if set(req.schema.astype(str)) != {"ohlcv-1m"} or set(req.stype_in.astype(str)) != {"instrument_id"}:
        raise SystemExit("HARD GATE: N1 schema/stype mismatch")
    return quote, auth, req, market_sha, source_sha


def gate(args: argparse.Namespace) -> None:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")

    quote, auth, req, market_sha, source_sha = validate_frozen_inputs(args)
    client = db.Historical(key)
    rows = req.to_dict("records")
    quoted, errors = [], []
    with ThreadPoolExecutor(max_workers=8) as ex:
        fs = {ex.submit(quote_one, client, r): str(r["market_request_id"]) for r in rows}
        for f in as_completed(fs):
            rid = fs[f]
            try:
                quoted.append(f.result())
            except Exception as exc:
                errors.append({"market_request_id": rid, "error": str(exc)})
    if errors:
        raise SystemExit(f"HARD GATE: metadata quote failure; no download. First errors={errors[:3]}")
    quoted = sorted(quoted, key=lambda x: str(x["market_request_id"]))
    total = float(sum(float(x["gate_cost_usd"]) for x in quoted))
    if total > HARD_CAP_USD + 1e-12:
        raise SystemExit(f"HARD GATE: current exact quote ${total:.12f} exceeds approved cap ${HARD_CAP_USD:.2f}; no download")

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    gate_doc = {
        "version": "COMEX_DEV_RANK1_NATIVE_N1_PRE_DOWNLOAD_GATE_V1",
        "authorization": auth["authorization"],
        "approved_cap_usd": HARD_CAP_USD,
        "frozen_quote_usd": float(quote["exact_n1_cost_usd"]),
        "current_exact_quote_usd": total,
        "remaining_margin_usd": HARD_CAP_USD - total,
        "requests": len(quoted),
        "zero_record_requests": [x["market_request_id"] for x in quoted if int(x["gate_records"]) == 0],
        "market_request_manifest_sha256": market_sha,
        "source_request_manifest_sha256": source_sha,
        "market_data_download_performed": False,
        "rows": quoted,
    }
    (out / "gate.json").write_text(json.dumps(gate_doc, indent=2))
    print(json.dumps(gate_doc, indent=2))


def acquire(args: argparse.Namespace) -> None:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")
    gate_doc = json.loads(Path(args.gate).read_text())
    if gate_doc.get("version") != "COMEX_DEV_RANK1_NATIVE_N1_PRE_DOWNLOAD_GATE_V1":
        raise SystemExit("wrong gate version")
    if float(gate_doc.get("current_exact_quote_usd", 99)) > HARD_CAP_USD + 1e-12:
        raise SystemExit("gate quote exceeds hard cap")
    rows = gate_doc.get("rows", [])
    if len(rows) != 92:
        raise SystemExit("expected 92 gated N1 requests")

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    if (out / "ACQUISITION_COMPLETE.json").exists():
        raise SystemExit("refusing to overwrite completed N1 acquisition")

    client = db.Historical(key)
    completed = []
    paid_quote_sum = 0.0
    try:
        for idx, row in enumerate(rows, start=1):
            rid = str(row["market_request_id"])
            qa_path = out / f"{rid}.json"
            raw_path = out / f"{rid}.dbn.zst"
            if qa_path.exists() or raw_path.exists():
                raise RuntimeError(f"{rid}: refusing overwrite")
            kw = request_kwargs(row)
            current_cost = float(retry_metadata(client.metadata.get_cost, **kw))
            current_records = int(retry_metadata(client.metadata.get_record_count, **kw))
            if current_records != int(row["gate_records"]):
                raise RuntimeError(f"{rid}: record count changed {row['gate_records']} -> {current_records}; stop before download")
            if paid_quote_sum + current_cost > HARD_CAP_USD + 1e-12:
                raise RuntimeError(f"{rid}: cumulative immediate quotes would exceed ${HARD_CAP_USD:.2f}; stop before download")

            qa = {
                "version": REQUEST_QA_VERSION,
                "ordinal": idx,
                "market_request_id": rid,
                "dataset": row["dataset"],
                "schema": row["schema"],
                "symbols": str(row["symbols"]),
                "stype_in": row["stype_in"],
                "start": row["start"],
                "end": row["end"],
                "gate_cost_usd": float(row["gate_cost_usd"]),
                "immediate_pre_download_cost_usd": current_cost,
                "gate_records": int(row["gate_records"]),
                "current_records": current_records,
            }

            if current_records == 0:
                qa.update({
                    "records_downloaded": 0,
                    "raw_file": None,
                    "raw_file_bytes": 0,
                    "sha256": None,
                    "market_data_request_performed": False,
                    "zero_record_metadata_only": True,
                })
                qa_path.write_text(json.dumps(qa, indent=2))
                completed.append(qa)
                continue

            # Sole paid call for this request. Intentionally no automatic retry.
            store = client.timeseries.get_range(path=str(raw_path), **kw)
            df = store.to_df()
            downloaded = int(len(df))
            if downloaded != current_records:
                raise RuntimeError(f"{rid}: downloaded {downloaded}, expected {current_records}")
            paid_quote_sum += current_cost
            qa.update({
                "records_downloaded": downloaded,
                "raw_file": raw_path.name,
                "raw_file_bytes": int(raw_path.stat().st_size),
                "sha256": sha256_file(raw_path),
                "market_data_request_performed": True,
                "zero_record_metadata_only": False,
            })
            qa_path.write_text(json.dumps(qa, indent=2))
            completed.append(qa)
    except Exception as exc:
        partial = {
            "version": "COMEX_DEV_RANK1_NATIVE_N1_ACQUISITION_PARTIAL_V1",
            "complete": False,
            "completed_markers": len(completed),
            "paid_market_requests_performed": int(sum(bool(x.get("market_data_request_performed")) for x in completed)),
            "paid_cost_upper_bound_usd": paid_quote_sum,
            "hard_cap_usd": HARD_CAP_USD,
            "error": str(exc),
        }
        (out / "ACQUISITION_PARTIAL.json").write_text(json.dumps(partial, indent=2))
        raise

    complete = len(completed) == 92
    summary = {
        "version": "COMEX_DEV_RANK1_NATIVE_N1_ACQUISITION_SUMMARY_V1",
        "complete": complete,
        "expected_requests": 92,
        "completed_request_markers": len(completed),
        "paid_market_requests_performed": int(sum(bool(x.get("market_data_request_performed")) for x in completed)),
        "zero_record_metadata_only_requests": int(sum(bool(x.get("zero_record_metadata_only")) for x in completed)),
        "records_downloaded_total": int(sum(int(x.get("records_downloaded", 0)) for x in completed)),
        "raw_bytes_total": int(sum(int(x.get("raw_file_bytes", 0)) for x in completed)),
        "paid_cost_upper_bound_usd": paid_quote_sum,
        "hard_cap_usd": HARD_CAP_USD,
        "hard_cap_respected": paid_quote_sum <= HARD_CAP_USD + 1e-12,
        "market_data_download_performed": any(bool(x.get("market_data_request_performed")) for x in completed),
        "n2_download_performed": False,
        "files": completed,
    }
    (out / "acquisition_summary.json").write_text(json.dumps(summary, indent=2))
    if not complete:
        raise SystemExit("N1 acquisition incomplete")
    marker = {
        "version": "COMEX_DEV_RANK1_NATIVE_N1_ACQUISITION_COMPLETE_V1",
        "complete": True,
        "requests": 92,
        "paid_cost_upper_bound_usd": paid_quote_sum,
        "hard_cap_usd": HARD_CAP_USD,
        "summary_sha256": sha256_file(out / "acquisition_summary.json"),
        "n2_download_authorized": False,
        "dev_rank2_opened": False,
        "retro_confirm_opened": False,
        "locked_comex_test_opened": False,
    }
    (out / "ACQUISITION_COMPLETE.json").write_text(json.dumps(marker, indent=2))
    print(json.dumps(summary, indent=2))


def parse_args():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gate")
    for x in ["quote", "market-requests", "source-requests", "authorization", "completion-marker", "out"]:
        g.add_argument(f"--{x}", required=True)
    a = sub.add_parser("acquire")
    a.add_argument("--gate", required=True)
    a.add_argument("--out", required=True)
    return ap.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.cmd == "gate":
        gate(args)
    else:
        acquire(args)
