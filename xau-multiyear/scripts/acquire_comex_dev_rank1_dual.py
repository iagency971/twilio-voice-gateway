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

HARD_CAP_USD = 20.84
REQUIRED_AUTH_TEXT = "OK DEV_RANK1 DUAL, plafond 20,84 $"
PER_REQUEST_TOLERANCE_USD = 0.00020


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

    requests_path = Path(args.requests)
    manifest_path = Path(args.manifest)
    auth_path = Path(args.authorization)
    completion_path = Path(args.completion_marker)

    if completion_path.exists():
        raise SystemExit("HARD GATE: acquisition completion marker already exists; refusing any second acquisition")
    if not auth_path.exists():
        raise SystemExit("HARD GATE: authorization file missing")

    manifest = json.loads(manifest_path.read_text())
    auth = json.loads(auth_path.read_text())

    if manifest.get("architecture") != "DUAL_V0_N0_CAUSAL_ACTIVE":
        raise SystemExit("HARD GATE: wrong architecture in manifest")
    if manifest.get("authorization") != "NOT_AUTHORIZED_FOR_DOWNLOAD":
        raise SystemExit("HARD GATE: frozen manifest authorization field unexpectedly changed")
    if int(manifest.get("total_new_requests", -1)) != 103:
        raise SystemExit("HARD GATE: expected exactly 103 requests")
    if abs(float(manifest.get("hard_cap_usd", -1)) - HARD_CAP_USD) > 1e-12:
        raise SystemExit("HARD GATE: manifest cap mismatch")

    actual_request_sha = sha256_file(requests_path)
    if actual_request_sha != manifest.get("request_csv_sha256"):
        raise SystemExit("HARD GATE: request CSV SHA256 differs from frozen manifest")

    if auth.get("authorization") != REQUIRED_AUTH_TEXT:
        raise SystemExit("HARD GATE: exact user authorization text absent")
    if auth.get("request_csv_sha256") != actual_request_sha:
        raise SystemExit("HARD GATE: authorization is not bound to current request CSV")
    if abs(float(auth.get("hard_cap_usd", -1)) - HARD_CAP_USD) > 1e-12:
        raise SystemExit("HARD GATE: authorization cap mismatch")
    if auth.get("one_shot") is not True:
        raise SystemExit("HARD GATE: authorization must be one_shot=true")

    req = pd.read_csv(requests_path, dtype={"symbols": str})
    required = {"request_id", "request_type", "candidate_role", "dataset", "schema", "symbols", "stype_in", "start", "end"}
    missing = required - set(req.columns)
    if missing:
        raise SystemExit(f"request CSV missing columns: {sorted(missing)}")
    if len(req) != 103 or req.request_id.duplicated().any():
        raise SystemExit("HARD GATE: request CSV must contain 103 unique requests")

    rows = req.to_dict("records")
    client = db.Historical(key)
    quoted: list[dict] = []
    errors: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(quote_one, client, row): row["request_id"] for row in rows}
        for fut in as_completed(futs):
            rid = futs[fut]
            try:
                quoted.append(fut.result())
            except Exception as exc:
                errors.append({"request_id": rid, "error": str(exc)})
    if errors:
        raise SystemExit(f"HARD GATE: metadata quote failure; no download. First errors: {errors[:3]}")

    quoted = sorted(quoted, key=lambda x: str(x["request_id"]))
    total = float(sum(float(x["gate_cost_usd"]) for x in quoted))
    if total > HARD_CAP_USD + 1e-12:
        raise SystemExit(f"HARD GATE: current exact quote ${total:.12f} exceeds approved cap ${HARD_CAP_USD:.2f}; no download")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    matrix = {"include": quoted}
    (out / "matrix.json").write_text(json.dumps(matrix, separators=(",", ":")), encoding="utf-8")
    gate_doc = {
        "version": "COMEX_DEV_RANK1_DUAL_PRE_DOWNLOAD_GATE_V1",
        "architecture": "DUAL_V0_N0_CAUSAL_ACTIVE",
        "authorization_bound_request_csv_sha256": actual_request_sha,
        "approved_cap_usd": HARD_CAP_USD,
        "current_exact_quote_usd": total,
        "remaining_margin_usd": HARD_CAP_USD - total,
        "requests": len(quoted),
        "zero_record_requests": [x["request_id"] for x in quoted if int(x["gate_records"]) == 0],
        "market_data_download_performed": False,
        "rows": quoted,
    }
    (out / "gate.json").write_text(json.dumps(gate_doc, indent=2), encoding="utf-8")
    print(json.dumps(gate_doc, indent=2))


def download_one(args: argparse.Namespace) -> None:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rid = str(args.request_id)
    qa_path = out / f"{rid}.json"
    raw_path = out / f"{rid}.dbn.zst"
    if qa_path.exists() or raw_path.exists():
        raise SystemExit("refusing to overwrite request output")

    row = {
        "dataset": args.dataset,
        "symbols": args.symbols,
        "stype_in": args.stype_in,
        "schema": args.schema,
        "start": args.start,
        "end": args.end,
    }
    expected_cost = float(args.gate_cost_usd)
    expected_records = int(args.gate_records)
    client = db.Historical(key)
    kw = request_kwargs(row)

    # Immediate per-request metadata guard. Metadata retries are safe; paid range requests are never retried automatically.
    current_cost = float(retry_metadata(client.metadata.get_cost, **kw))
    current_records = int(retry_metadata(client.metadata.get_record_count, **kw))
    if current_cost > expected_cost + float(args.tolerance_usd) + 1e-12:
        raise SystemExit(f"REQUEST GATE {rid}: quote rose ${expected_cost:.12f} -> ${current_cost:.12f}; no download")
    if current_records != expected_records:
        raise SystemExit(f"REQUEST GATE {rid}: record count changed {expected_records} -> {current_records}; no download")

    base_qa = {
        "version": "COMEX_DEV_RANK1_DUAL_REQUEST_FILE_V1",
        "request_id": rid,
        "request_type": args.request_type,
        "candidate_role": args.candidate_role,
        "research_trading_date": args.research_trading_date,
        "dataset": args.dataset,
        "schema": args.schema,
        "symbols": args.symbols,
        "stype_in": args.stype_in,
        "start": args.start,
        "end": args.end,
        "gate_cost_usd": expected_cost,
        "immediate_pre_download_cost_usd": current_cost,
        "gate_records": expected_records,
    }

    if expected_records == 0:
        base_qa.update({
            "records_downloaded": 0,
            "raw_file": None,
            "raw_file_bytes": 0,
            "sha256": None,
            "market_data_request_performed": False,
            "zero_record_metadata_only": True,
        })
        qa_path.write_text(json.dumps(base_qa, indent=2), encoding="utf-8")
        print(json.dumps(base_qa, indent=2))
        return

    # Sole paid market-data call for this request. Intentionally NO automatic retry.
    store = client.timeseries.get_range(path=str(raw_path), **kw)
    df = store.to_df()
    downloaded = int(len(df))
    if downloaded != expected_records:
        raise RuntimeError(f"{rid}: downloaded {downloaded} records, expected {expected_records}")

    instrument_ids = []
    if "instrument_id" in df.columns:
        instrument_ids = sorted(int(x) for x in pd.Series(df["instrument_id"]).dropna().unique())

    base_qa.update({
        "records_downloaded": downloaded,
        "raw_file": raw_path.name,
        "raw_file_bytes": int(raw_path.stat().st_size),
        "sha256": sha256_file(raw_path),
        "instrument_ids": instrument_ids,
        "market_data_request_performed": True,
        "zero_record_metadata_only": False,
    })
    qa_path.write_text(json.dumps(base_qa, indent=2), encoding="utf-8")
    print(json.dumps(base_qa, indent=2))


def finalize(args: argparse.Namespace) -> None:
    requests_path = Path(args.requests)
    root = Path(args.root)
    expected = pd.read_csv(requests_path, dtype={"symbols": str})
    qa_files = sorted(root.rglob("*.json"))
    qa = []
    for p in qa_files:
        try:
            obj = json.loads(p.read_text())
        except Exception:
            continue
        if obj.get("version") == "COMEX_DEV_RANK1_DUAL_REQUEST_FILE_V1":
            qa.append(obj)
    got = {x["request_id"] for x in qa}
    exp = set(expected.request_id.astype(str))
    missing = sorted(exp - got)
    extra = sorted(got - exp)

    complete = len(missing) == 0 and len(extra) == 0 and len(got) == 103
    rows = sorted(qa, key=lambda x: x["request_id"])
    result = {
        "version": "COMEX_DEV_RANK1_DUAL_ACQUISITION_SUMMARY_V1",
        "expected_requests": 103,
        "completed_request_markers": len(got),
        "missing_request_ids": missing,
        "extra_request_ids": extra,
        "complete": complete,
        "paid_market_requests_performed": int(sum(bool(x.get("market_data_request_performed")) for x in rows)),
        "zero_record_metadata_only_requests": int(sum(bool(x.get("zero_record_metadata_only")) for x in rows)),
        "records_downloaded_total": int(sum(int(x.get("records_downloaded", 0)) for x in rows)),
        "raw_bytes_total": int(sum(int(x.get("raw_file_bytes", 0)) for x in rows)),
        "files": rows,
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "acquisition_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if complete:
        marker = {
            "version": "COMEX_DEV_RANK1_DUAL_ACQUISITION_COMPLETE_V1",
            "complete": True,
            "request_csv_sha256": sha256_file(requests_path),
            "requests": 103,
            "summary_sha256": sha256_file(out / "acquisition_summary.json"),
        }
        (out / "ACQUISITION_COMPLETE.json").write_text(json.dumps(marker, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gate")
    g.add_argument("--requests", required=True)
    g.add_argument("--manifest", required=True)
    g.add_argument("--authorization", required=True)
    g.add_argument("--completion-marker", required=True)
    g.add_argument("--out", required=True)

    d = sub.add_parser("download-one")
    for arg in ["request-id", "request-type", "candidate-role", "dataset", "schema", "symbols", "stype-in", "start", "end", "out"]:
        d.add_argument(f"--{arg}", required=True)
    d.add_argument("--research-trading-date", default="")
    d.add_argument("--gate-cost-usd", required=True, type=float)
    d.add_argument("--gate-records", required=True, type=int)
    d.add_argument("--tolerance-usd", type=float, default=PER_REQUEST_TOLERANCE_USD)

    f = sub.add_parser("finalize")
    f.add_argument("--requests", required=True)
    f.add_argument("--root", required=True)
    f.add_argument("--out", required=True)
    return ap.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.cmd == "gate":
        gate(args)
    elif args.cmd == "download-one":
        download_one(args)
    else:
        finalize(args)
