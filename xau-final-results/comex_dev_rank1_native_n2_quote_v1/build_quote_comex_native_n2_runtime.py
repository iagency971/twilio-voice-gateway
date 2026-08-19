#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import databento as db

DATASET = "GLBX.MDP3"
N2_SCHEMA = "trades"
N1_COMPLETE_VERSION = "COMEX_DEV_RANK1_NATIVE_N1_ACQUISITION_COMPLETE_V1"
N1_QA_VERSION = "COMEX_DEV_RANK1_NATIVE_N1_REQUEST_FILE_V1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_dbn(path: Path) -> pd.DataFrame:
    x = db.DBNStore.from_file(path).to_df().reset_index(drop=False)
    if "ts_event" not in x.columns:
        x = x.rename(columns={x.columns[0]: "ts_event"})
    x["ts_event"] = pd.to_datetime(x.ts_event, utc=True)
    return x.sort_values("ts_event").reset_index(drop=True)


def retry_cost(client: db.Historical, row: dict) -> float:
    err = None
    for k in range(7):
        try:
            return float(client.metadata.get_cost(
                dataset=str(row["dataset"]),
                symbols=str(row["symbols"]),
                stype_in=str(row["stype_in"]),
                schema=str(row["schema"]),
                start=str(row["start"]),
                end=str(row["end"]),
            ))
        except Exception as exc:
            err = exc
            time.sleep(min(20, 2**k))
    raise RuntimeError(f"metadata.get_cost failed after retries: {err}")


def level_id(row) -> str:
    payload = "|".join([
        str(row.source_research_date),
        str(row.source_instrument_id),
        str(row.level_type),
        f"{float(row.contact_tick_price):.1f}",
        str(row.known_time_utc),
    ])
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-levels", required=True)
    ap.add_argument("--source-requests", required=True)
    ap.add_argument("--n1-root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")

    levels_path = Path(a.source_levels)
    source_req_path = Path(a.source_requests)
    n1_root = Path(a.n1_root)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    complete_path = n1_root / "ACQUISITION_COMPLETE.json"
    if not complete_path.exists():
        raise SystemExit("N1 completion marker missing")
    complete = json.loads(complete_path.read_text())
    if complete.get("version") != N1_COMPLETE_VERSION or complete.get("complete") is not True:
        raise SystemExit("invalid N1 completion marker")
    if complete.get("n2_download_authorized") is not False:
        raise SystemExit("N2 must remain unauthorized")

    levels = pd.read_csv(levels_path, dtype={"source_instrument_id": str})
    sreq = pd.read_csv(source_req_path, dtype={"source_instrument_id": str, "symbols": str})
    if len(levels) != 368 or levels.source_research_date.nunique() != 92:
        raise SystemExit("expected 368 source levels / 92 sessions")
    if len(sreq) != 92 or sreq.source_research_date.nunique() != 92 or sreq.market_request_id.nunique() != 92:
        raise SystemExit("expected 92 source requests")
    if set(levels.level_type.astype(str)) != {"VWAP", "POC", "VAH", "VAL"}:
        raise SystemExit("unexpected source level types")

    # Audit all N1 request markers before screening.
    markers = {}
    for p in n1_root.glob("*.json"):
        try:
            z = json.loads(p.read_text())
        except Exception:
            continue
        if z.get("version") == N1_QA_VERSION:
            markers[str(z["market_request_id"])] = z
    expected_market_ids = set(sreq.market_request_id.astype(str))
    if set(markers) != expected_market_ids:
        raise SystemExit(f"N1 request marker parity failure missing={sorted(expected_market_ids-set(markers))[:3]} extra={sorted(set(markers)-expected_market_ids)[:3]}")

    req_by_source = sreq.set_index(sreq.source_research_date.astype(str)).to_dict("index")
    dbn_cache: dict[str, pd.DataFrame] = {}
    level_screens = []
    candidate_rows = []

    for r in levels.itertuples(index=False):
        source_date = str(r.source_research_date)
        req = req_by_source[source_date]
        market_id = str(req["market_request_id"])
        marker = markers[market_id]
        lid = level_id(r)
        tick_price = float(r.contact_tick_price)
        tick_int = int(round(tick_price * 10.0))
        if abs(tick_price * 10.0 - tick_int) > 1e-8:
            raise SystemExit(f"off-tick source level {lid}: {tick_price}")

        if int(marker.get("records_downloaded", 0)) == 0:
            cands = pd.DataFrame()
        else:
            if market_id not in dbn_cache:
                raw_name = marker.get("raw_file")
                raw_path = n1_root / str(raw_name)
                if not raw_path.exists():
                    raise SystemExit(f"missing N1 raw file {market_id}")
                if sha256_file(raw_path) != marker.get("sha256"):
                    raise SystemExit(f"N1 raw SHA mismatch {market_id}")
                df = load_dbn(raw_path)
                for col in ["low", "high"]:
                    if col not in df.columns:
                        raise SystemExit(f"N1 file {market_id} missing {col}")
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                good = df.low.notna() & df.high.notna()
                if good.any():
                    low_scaled = df.loc[good, "low"].to_numpy(float) * 10.0
                    high_scaled = df.loc[good, "high"].to_numpy(float) * 10.0
                    off_tick = int((np.abs(low_scaled - np.rint(low_scaled)) > 1e-6).sum() + (np.abs(high_scaled - np.rint(high_scaled)) > 1e-6).sum())
                    if off_tick:
                        raise SystemExit(f"N1 raw bars are off GC 0.10 tick for {market_id}: {off_tick}")
                df["low_tick"] = pd.Series(np.rint(df.low.to_numpy(float) * 10.0), index=df.index).astype("Int64")
                df["high_tick"] = pd.Series(np.rint(df.high.to_numpy(float) * 10.0), index=df.index).astype("Int64")
                dbn_cache[market_id] = df
            df = dbn_cache[market_id]
            mask = df.low_tick.notna() & df.high_tick.notna() & (df.low_tick <= tick_int) & (df.high_tick >= tick_int)
            cands = df.loc[mask, ["ts_event", "low", "high", "low_tick", "high_tick"]].copy()

        cands = cands.sort_values("ts_event") if len(cands) else cands
        starts = list(pd.to_datetime(cands.ts_event, utc=True)) if len(cands) else []
        level_screens.append({
            "level_id": lid,
            "source_research_date": source_date,
            "eligible_next_research_date": str(req["eligible_next_research_date"]),
            "source_instrument_id": str(r.source_instrument_id),
            "level_type": str(r.level_type),
            "level_price": float(r.level_price),
            "contact_tick_price": tick_price,
            "market_request_id_n1": market_id,
            "n1_records_downloaded": int(marker.get("records_downloaded", 0)),
            "candidate_minute_count": len(starts),
            "first_candidate_minute_utc": starts[0].isoformat() if starts else "",
            "last_candidate_minute_utc": starts[-1].isoformat() if starts else "",
            "n1_screen_label": "N2_REQUIRED" if starts else "NO_EXACT_CONTACT_N1_SCREEN",
        })
        for ts in starts:
            candidate_rows.append({
                "level_id": lid,
                "source_research_date": source_date,
                "eligible_next_research_date": str(req["eligible_next_research_date"]),
                "source_instrument_id": str(r.source_instrument_id),
                "level_type": str(r.level_type),
                "contact_tick_price": tick_price,
                "minute_start_utc": ts.isoformat(),
                "minute_end_utc": (ts + pd.Timedelta(minutes=1)).isoformat(),
            })

    screen = pd.DataFrame(level_screens).sort_values(["source_research_date", "level_type"]).reset_index(drop=True)
    cand = pd.DataFrame(candidate_rows)
    if len(screen) != 368 or screen.level_id.nunique() != 368:
        raise SystemExit("level screening parity failure")

    # Union/deduplicate all candidate one-minute intervals, then merge only exactly contiguous
    # candidate minutes. This does not add any noncandidate minute to the N2 universe.
    runs = []
    minute_to_run = {}
    if len(cand):
        unique_min = cand[["eligible_next_research_date", "source_instrument_id", "minute_start_utc"]].drop_duplicates().copy()
        unique_min["minute_start"] = pd.to_datetime(unique_min.minute_start_utc, utc=True)
        for (date, iid), g in unique_min.groupby(["eligible_next_research_date", "source_instrument_id"], sort=True):
            times = sorted(g.minute_start.tolist())
            groups = []
            cur = [times[0]]
            for ts in times[1:]:
                if ts == cur[-1] + pd.Timedelta(minutes=1):
                    cur.append(ts)
                else:
                    groups.append(cur); cur = [ts]
            groups.append(cur)
            for seq in groups:
                start = seq[0]
                end = seq[-1] + pd.Timedelta(minutes=1)
                rid = hashlib.sha256(f"NATIVE_N2|{iid}|{start.isoformat()}|{end.isoformat()}|trades".encode()).hexdigest()[:24]
                row = {
                    "market_request_id": rid,
                    "request_type": "NATIVE_N2_EXACT_TRADES_CANDIDATE_UNION",
                    "eligible_next_research_date": str(date),
                    "source_instrument_id": str(iid),
                    "dataset": DATASET,
                    "schema": N2_SCHEMA,
                    "symbols": str(iid),
                    "stype_in": "instrument_id",
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "candidate_minute_count": len(seq),
                }
                runs.append(row)
                for ts in seq:
                    minute_to_run[(str(date), str(iid), ts.isoformat())] = rid

    n2 = pd.DataFrame(runs)
    if len(cand):
        cand["n2_market_request_id"] = [minute_to_run[(str(r.eligible_next_research_date), str(r.source_instrument_id), pd.Timestamp(r.minute_start_utc).isoformat())] for r in cand.itertuples()]
    else:
        cand = pd.DataFrame(columns=["level_id","source_research_date","eligible_next_research_date","source_instrument_id","level_type","contact_tick_price","minute_start_utc","minute_end_utc","n2_market_request_id"])

    costs = {}
    errors = []
    if len(n2):
        client = db.Historical(key)
        rows = n2.to_dict("records")
        with ThreadPoolExecutor(max_workers=12) as ex:
            fs = {ex.submit(retry_cost, client, row): row["market_request_id"] for row in rows}
            for f in as_completed(fs):
                rid = fs[f]
                try:
                    costs[rid] = f.result()
                except Exception as exc:
                    errors.append({"market_request_id": rid, "error": str(exc)})
        if errors:
            raise SystemExit(f"N2 quote failures={len(errors)} first={errors[:3]}")
        n2["cost_usd"] = n2.market_request_id.map(costs).astype(float)
    else:
        n2["cost_usd"] = pd.Series(dtype=float)

    total = float(n2.cost_usd.sum()) if len(n2) else 0.0
    screen.to_csv(out / "native_n1_level_screen.csv", index=False)
    cand.to_csv(out / "native_n2_candidate_level_minutes.csv", index=False)
    n2.to_csv(out / "native_n2_market_request_manifest.csv", index=False)

    manifest = {
        "version": "COMEX_DEV_RANK1_NATIVE_N2_QUOTE_V1",
        "authorization": "N2_DOWNLOAD_NOT_AUTHORIZED",
        "market_data_download_performed": False,
        "n2_download_performed": False,
        "n1_complete": True,
        "n1_completion_sha256": sha256_file(complete_path),
        "source_registry_sha256": sha256_file(levels_path),
        "source_request_manifest_sha256": sha256_file(source_req_path),
        "source_levels": 368,
        "source_sessions": 92,
        "levels_no_exact_contact_by_n1_screen": int((screen.n1_screen_label == "NO_EXACT_CONTACT_N1_SCREEN").sum()),
        "levels_requiring_n2": int((screen.n1_screen_label == "N2_REQUIRED").sum()),
        "candidate_level_minute_rows": int(len(cand)),
        "unique_candidate_minutes": int(cand[["eligible_next_research_date","source_instrument_id","minute_start_utc"]].drop_duplicates().shape[0]) if len(cand) else 0,
        "n2_merged_market_requests": int(len(n2)),
        "exact_n2_cost_usd": total,
        "level_screen_sha256": sha256_file(out / "native_n1_level_screen.csv"),
        "candidate_level_minutes_sha256": sha256_file(out / "native_n2_candidate_level_minutes.csv"),
        "n2_market_request_manifest_sha256": sha256_file(out / "native_n2_market_request_manifest.csv"),
        "ohlcv_timestamp_rule": "Databento ohlcv-1m ts_event is the inclusive start of the one-minute trade aggregation interval",
        "screening_rule": "low_tick <= contact_tick <= high_tick only creates an N2 candidate minute; M1 never confirms contact",
        "n2_union_rule": "deduplicate identical candidate minutes and merge only exactly contiguous candidate minutes on the same raw instrument/session; no noncandidate minute added",
        "exact_contact_rule_after_future_n2": "first chronological raw GC trade with price exactly equal to contact_tick_price on same source instrument",
        "dev_rank2_opened": False,
        "retro_confirm_opened": False,
        "locked_comex_test_opened": False,
        "notes": [
            "This script performs metadata.get_cost only for N2.",
            "No N2 timeseries.get_range call is present.",
            "Levels with no N1 bar spanning the contact tick are labeled NO_EXACT_CONTACT_N1_SCREEN under the frozen protocol.",
            "All levels with one or more candidate minutes remain in the future N2 acquisition universe."
        ],
    }
    (out / "native_n2_quote.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
