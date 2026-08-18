#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

NY = ZoneInfo("America/New_York")
DATASET = "GLBX.MDP3"
HARD_CAP_USD = 20.84
PILOT_ACTUAL_USD = 4.01

REUSED_N0_SAME = {"2013-02-07", "2017-10-31", "2018-01-02"}
REUSED_V0_DIVERGENT = {"2013-05-29"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def session_bounds(date_str: str) -> tuple[str, str]:
    d = pd.Timestamp(date_str).date()
    prev = (pd.Timestamp(d) - pd.Timedelta(days=1)).date()
    start = pd.Timestamp(f"{prev} 18:00:00", tz=NY).tz_convert("UTC")
    if d < pd.Timestamp("2015-09-21").date():
        end = pd.Timestamp(f"{d} 17:15:00", tz=NY).tz_convert("UTC")
    else:
        end = pd.Timestamp(f"{d} 17:00:00", tz=NY).tz_convert("UTC")
    return start.isoformat(), end.isoformat()


def req_id(kind: str, date: str, iid: str) -> str:
    return hashlib.sha256(f"{kind}|{date}|{iid}".encode()).hexdigest()[:24]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mapping", required=True)
    ap.add_argument("--quote", required=True)
    ap.add_argument("--roll-policy", required=True)
    ap.add_argument("--sessions", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--analysis-prereg", required=True)
    ap.add_argument("--feature-v11", required=True)
    ap.add_argument("--feature-v12", required=True)
    ap.add_argument("--availability-policy", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    mapping_path = Path(args.mapping)
    quote_path = Path(args.quote)
    mapping = pd.read_csv(mapping_path)
    quote = json.loads(quote_path.read_text())

    if len(mapping) != 96:
        raise SystemExit(f"expected 96 DEV_RANK1 sessions, got {len(mapping)}")
    if mapping.research_trading_date.astype(str).duplicated().any():
        raise SystemExit("duplicate research_trading_date in frozen mapping")
    if int((~mapping.same_start_contract.astype(bool)).sum()) != 10:
        raise SystemExit("expected exactly 10 divergent V0/N0 sessions")

    qdual = quote["dual"]
    expected_quote = float(qdual["total_new_cost_usd"])
    if abs(expected_quote - 20.825925588608) > 1e-9:
        raise SystemExit(f"unexpected controlling quote: {expected_quote}")
    if float(qdual["recommended_hard_cap_usd"]) != HARD_CAP_USD:
        raise SystemExit("controlling hard cap mismatch")

    rows: list[dict] = []
    session_rows: list[dict] = []

    for r in mapping.sort_values("research_trading_date").itertuples():
        date = str(r.research_trading_date)
        v0 = str(r.v0_start_iid)
        n0 = str(r.n0_start_iid)
        same = bool(r.same_start_contract)
        start, end = session_bounds(date)

        n0_reused = date in REUSED_N0_SAME
        v0_reused = same and n0_reused or ((not same) and date in REUSED_V0_DIVERGENT)

        session_rows.append({
            "research_trading_date": date,
            "year": int(r.year),
            "quarter": int(r.quarter),
            "vol_band": int(r.vol_band),
            "session_start_utc": start,
            "session_end_utc": end,
            "v0_start_iid": v0,
            "n0_start_iid": n0,
            "same_start_contract": same,
            "n0_primary_reused_paid": n0_reused,
            "v0_candidate_reused_paid": v0_reused,
        })

        if not n0_reused:
            rows.append({
                "request_id": req_id("N0", date, n0),
                "request_type": "RAW_TRADES",
                "candidate_role": "N0_PRIMARY_CANDIDATE",
                "research_trading_date": date,
                "dataset": DATASET,
                "schema": "trades",
                "symbols": n0,
                "stype_in": "instrument_id",
                "start": start,
                "end": end,
                "reuse_paid": False,
            })

        if not same and date not in REUSED_V0_DIVERGENT:
            rows.append({
                "request_id": req_id("V0", date, v0),
                "request_type": "RAW_TRADES",
                "candidate_role": "V0_DUAL_ALTERNATE",
                "research_trading_date": date,
                "dataset": DATASET,
                "schema": "trades",
                "symbols": v0,
                "stype_in": "instrument_id",
                "start": start,
                "end": end,
                "reuse_paid": False,
            })

    raw = pd.DataFrame(rows)
    sessions = pd.DataFrame(session_rows)

    if len(raw) != 102:
        raise SystemExit(f"expected 102 new raw requests, got {len(raw)}")
    if int((raw.candidate_role == "N0_PRIMARY_CANDIDATE").sum()) != 93:
        raise SystemExit("expected 93 N0 raw requests")
    if int((raw.candidate_role == "V0_DUAL_ALTERNATE").sum()) != 9:
        raise SystemExit("expected 9 V0 alternate raw requests")
    if raw.request_id.duplicated().any():
        raise SystemExit("duplicate request_id")

    continuous = {
        "request_id": "n0_ohlcv_1m_context_20100606_20190101",
        "request_type": "CONTINUOUS_OHLCV_CONTEXT",
        "candidate_role": "N0_CONTEXT",
        "research_trading_date": "",
        "dataset": DATASET,
        "schema": "ohlcv-1m",
        "symbols": "GC.n.0",
        "stype_in": "continuous",
        "start": "2010-06-06T00:00:00+00:00",
        "end": "2019-01-01T00:00:00+00:00",
        "reuse_paid": False,
    }

    full = pd.concat([pd.DataFrame([continuous]), raw], ignore_index=True)
    if len(full) != 103:
        raise SystemExit("expected 103 total new requests")

    full.to_csv(out / "dev_rank1_dual_requests.csv", index=False)
    sessions.to_csv(out / "dev_rank1_dual_sessions.csv", index=False)

    controlling = {
        "frozen_session_mapping_all.csv": sha256_file(mapping_path),
        "dev_rank1_exact_raw_contract_quote.json": sha256_file(quote_path),
        "COMEX_DEV_RANK1_ROLL_POLICY_CANONICAL_v2.md": sha256_file(Path(args.roll_policy)),
        "corrected_primary_sessions.csv": sha256_file(Path(args.sessions)),
        "corrected_strata_weights.csv": sha256_file(Path(args.weights)),
        "COMEX_DEV_RANK1_ANALYSIS_PREREG_v1.md": sha256_file(Path(args.analysis_prereg)),
        "COMEX_DEV_RANK1_FEATURE_SPEC_CANONICAL_v1_1.md": sha256_file(Path(args.feature_v11)),
        "COMEX_DEV_RANK1_FEATURE_SPEC_CANONICAL_v1_2.md": sha256_file(Path(args.feature_v12)),
        "COMEX_DEV_RANK1_AVAILABILITY_POLICY_v1.md": sha256_file(Path(args.availability_policy)),
    }

    manifest = {
        "version": "COMEX_DEV_RANK1_DUAL_REQUEST_MANIFEST_V1",
        "created_without_market_download": True,
        "market_data_download_performed": False,
        "architecture": "DUAL_V0_N0_CAUSAL_ACTIVE",
        "dataset": DATASET,
        "selected_sessions": 96,
        "divergent_v0_n0_sessions": 10,
        "new_raw_requests": 102,
        "new_n0_raw_requests": 93,
        "new_v0_alternate_raw_requests": 9,
        "continuous_context_requests": 1,
        "total_new_requests": 103,
        "paid_raw_reuse": {
            "same_contract_n0_reuse_dates": sorted(REUSED_N0_SAME),
            "divergent_v0_reuse_dates": sorted(REUSED_V0_DIVERGENT),
        },
        "session_bounds": {
            "before_2015_09_21": "18:00 America/New_York D-1 to 17:15 D, end-exclusive",
            "on_after_2015_09_21": "18:00 America/New_York D-1 to 17:00 D, end-exclusive",
        },
        "controlling_metadata_quote_usd": expected_quote,
        "hard_cap_usd": HARD_CAP_USD,
        "pilot_actual_spend_usd": PILOT_ACTUAL_USD,
        "projected_cumulative_spend_usd": PILOT_ACTUAL_USD + expected_quote,
        "authorization": "NOT_AUTHORIZED_FOR_DOWNLOAD",
        "required_user_authorization_text": "OK DEV_RANK1 DUAL, plafond 20,84 $",
        "pre_download_gate": [
            "recompute metadata.get_cost for every request in dev_rank1_dual_requests.csv",
            "sum exact current cost",
            "abort if sum > 20.84 USD",
            "abort if request-manifest SHA256 differs from frozen authorization manifest",
            "abort if acquisition-complete marker already exists",
        ],
        "controlling_file_sha256": controlling,
    }

    (out / "dev_rank1_dual_request_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["request_csv_sha256"] = sha256_file(out / "dev_rank1_dual_requests.csv")
    manifest["session_csv_sha256"] = sha256_file(out / "dev_rank1_dual_sessions.csv")
    (out / "dev_rank1_dual_request_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
