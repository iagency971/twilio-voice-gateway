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

QA_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_REQUEST_FILE_V1"
COMPLETE_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_ACQUISITION_COMPLETE_V1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_dbn(path: Path) -> pd.DataFrame:
    df = db.DBNStore.from_file(path).to_df().reset_index(drop=False)
    if "ts_event" not in df.columns:
        df = df.rename(columns={df.columns[0]: "ts_event"})
    df["ts_event"] = pd.to_datetime(df.ts_event, utc=True)
    return df.sort_values("ts_event").reset_index(drop=True)


def metadata_cost(client: db.Historical, row: dict) -> float:
    err = None
    for k in range(7):
        try:
            return float(client.metadata.get_cost(
                dataset=str(row["dataset"]), symbols=str(row["symbols"]), stype_in=str(row["stype_in"]),
                schema=str(row["schema"]), start=str(row["start"]), end=str(row["end"])))
        except Exception as exc:
            err = exc
            time.sleep(min(20, 2**k))
    raise RuntimeError(f"metadata.get_cost failed after retries: {err}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage1-level-manifest", required=True)
    ap.add_argument("--all-candidate-minutes", required=True)
    ap.add_argument("--stage1-market-manifest", required=True)
    ap.add_argument("--stage1-root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")

    lpath = Path(a.stage1_level_manifest)
    cpath = Path(a.all_candidate_minutes)
    mpath = Path(a.stage1_market_manifest)
    root = Path(a.stage1_root)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    complete_path = root / "ACQUISITION_COMPLETE.json"
    if not complete_path.exists():
        raise SystemExit("Stage1 acquisition completion marker missing")
    complete = json.loads(complete_path.read_text())
    if complete.get("version") != COMPLETE_VERSION or complete.get("complete") is not True:
        raise SystemExit("invalid Stage1 completion marker")
    if complete.get("n2_stage2_download_authorized") is not False or complete.get("full_n2_union_download_authorized") is not False:
        raise SystemExit("later N2 downloads must remain unauthorized")
    if int(complete.get("requests", -1)) != 214:
        raise SystemExit("Stage1 completion request count mismatch")
    if complete.get("market_request_manifest_sha256") != sha256_file(mpath):
        raise SystemExit("Stage1 completion marker not bound to current market manifest")

    levels = pd.read_csv(lpath, dtype={"source_instrument_id": str})
    market = pd.read_csv(mpath, dtype={"source_instrument_id": str, "symbols": str})
    cand = pd.read_csv(cpath, dtype={"source_instrument_id": str})
    if len(levels) != 243 or levels.level_id.nunique() != 243 or not levels.candidate_rank.eq(1).all():
        raise SystemExit("expected 243 unique Stage1 rank-1 levels")
    if len(market) != 214 or market.market_request_id.nunique() != 214:
        raise SystemExit("expected 214 Stage1 market requests")
    if cand.level_id.nunique() != 243 or len(cand) != 9093:
        raise SystemExit("full candidate-minute manifest mismatch")

    markers = {}
    for p in root.glob("*.json"):
        try:
            z = json.loads(p.read_text())
        except Exception:
            continue
        if z.get("version") == QA_VERSION:
            markers[str(z["market_request_id"])] = z
    expected_ids = set(market.market_request_id.astype(str))
    if set(markers) != expected_ids:
        raise SystemExit(f"Stage1 request-marker parity failure missing={len(expected_ids-set(markers))} extra={len(set(markers)-expected_ids)}")

    cache = {}
    resolution = []
    for r in levels.itertuples(index=False):
        rid = str(r.stage1_market_request_id)
        marker = markers[rid]
        start = pd.Timestamp(r.minute_start_utc)
        end = pd.Timestamp(r.minute_end_utc)
        if start.tzinfo is None: start = start.tz_localize("UTC")
        else: start = start.tz_convert("UTC")
        if end.tzinfo is None: end = end.tz_localize("UTC")
        else: end = end.tz_convert("UTC")
        target_tick = int(round(float(r.contact_tick_price) * 10.0))

        if int(marker.get("records_downloaded", 0)) == 0:
            sub = pd.DataFrame(columns=["ts_event", "price"])
        else:
            if rid not in cache:
                raw = root / str(marker.get("raw_file"))
                if not raw.exists() or sha256_file(raw) != marker.get("sha256"):
                    raise SystemExit(f"raw Stage1 file missing/SHA mismatch {rid}")
                df = load_dbn(raw)
                if "price" not in df.columns:
                    raise SystemExit(f"Stage1 trades file {rid} missing price")
                df["price"] = pd.to_numeric(df.price, errors="coerce")
                if "instrument_id" in df.columns:
                    ids = set(pd.Series(df.instrument_id).dropna().astype(int).astype(str))
                    if ids and ids != {str(marker["source_instrument_id"])}:
                        raise SystemExit(f"unexpected instrument ids in {rid}: {ids}")
                cache[rid] = df
            df = cache[rid]
            sub = df[(df.ts_event >= start) & (df.ts_event < end) & df.price.notna()].copy()

        if len(sub):
            scaled = sub.price.to_numpy(float) * 10.0
            tick_int = np.rint(scaled).astype(np.int64)
            on_tick = np.abs(scaled - tick_int) <= 1e-6
            matches = sub.loc[on_tick & (tick_int == target_tick)].sort_values("ts_event")
        else:
            matches = sub
        exact = len(matches) > 0
        first_time = pd.Timestamp(matches.iloc[0].ts_event).isoformat() if exact else ""
        resolution.append({
            "level_id": str(r.level_id),
            "source_research_date": str(r.source_research_date),
            "eligible_next_research_date": str(r.eligible_next_research_date),
            "source_instrument_id": str(r.source_instrument_id),
            "level_type": str(r.level_type),
            "contact_tick_price": float(r.contact_tick_price),
            "stage1_candidate_minute_start_utc": start.isoformat(),
            "stage1_candidate_minute_end_utc": end.isoformat(),
            "stage1_market_request_id": rid,
            "stage1_trade_records_in_candidate_minute": int(len(sub)),
            "stage1_exact_tick_trade_count": int(len(matches)),
            "stage1_exact_contact": bool(exact),
            "stage1_first_exact_contact_time_utc": first_time,
        })

    res = pd.DataFrame(resolution).sort_values(["source_research_date", "level_type", "level_id"]).reset_index(drop=True)
    if len(res) != 243 or res.level_id.nunique() != 243:
        raise SystemExit("Stage1 resolution parity failure")

    # Reconstruct deterministic candidate ranks from the N1-only candidate universe.
    c = cand.copy()
    c["minute_start"] = pd.to_datetime(c.minute_start_utc, utc=True)
    c = c.sort_values(["level_id", "minute_start"]).reset_index(drop=True)
    c["candidate_rank"] = c.groupby("level_id").cumcount() + 1
    rank1 = c[c.candidate_rank.eq(1)][["level_id", "minute_start_utc"]].copy()
    chk = levels[["level_id", "minute_start_utc"]].merge(rank1, on="level_id", suffixes=("_stage1", "_reconstructed"), validate="one_to_one")
    if not (chk.minute_start_utc_stage1.astype(str) == chk.minute_start_utc_reconstructed.astype(str)).all():
        raise SystemExit("candidate rank-1 reconstruction differs from frozen Stage1 manifest")

    contact_ids = set(res.loc[res.stage1_exact_contact, "level_id"].astype(str))
    unresolved_ids = set(res.loc[~res.stage1_exact_contact, "level_id"].astype(str))
    rank2 = c[(c.level_id.astype(str).isin(unresolved_ids)) & c.candidate_rank.eq(2)].copy()
    ids_with_rank2 = set(rank2.level_id.astype(str))
    exhausted_ids = unresolved_ids - ids_with_rank2

    res["stage1_resolution"] = np.where(res.stage1_exact_contact, "RESOLVED_CONTACT", np.where(res.level_id.astype(str).isin(exhausted_ids), "RESOLVED_NO_CONTACT_EXHAUSTED", "UNRESOLVED_ADVANCE_STAGE2"))
    res.to_csv(out / "native_n2_stage1_resolution.csv", index=False)

    by_type = res.groupby("level_type", as_index=False).agg(
        levels=("level_id", "count"),
        resolved_contact=("stage1_exact_contact", "sum"),
    )
    by_type["contact_rate_stage1"] = by_type.resolved_contact / by_type.levels
    by_type["unresolved_after_stage1"] = by_type.levels - by_type.resolved_contact
    by_type.to_csv(out / "native_n2_stage1_resolution_by_type.csv", index=False)

    # Build Stage2 only for mechanically unresolved levels that have candidate rank 2.
    stage2_level = rank2.copy()
    if len(stage2_level):
        unique = stage2_level[["eligible_next_research_date", "source_instrument_id", "minute_start"]].drop_duplicates().copy()
        runs = []
        minute_to_run = {}
        for (date, iid), g in unique.groupby(["eligible_next_research_date", "source_instrument_id"], sort=True):
            times = sorted(g.minute_start.tolist())
            groups = []
            cur = [times[0]]
            for ts in times[1:]:
                if ts == cur[-1] + pd.Timedelta(minutes=1): cur.append(ts)
                else: groups.append(cur); cur = [ts]
            groups.append(cur)
            for seq in groups:
                start = seq[0]; end = seq[-1] + pd.Timedelta(minutes=1)
                rid = hashlib.sha256(f"NATIVE_N2_STAGE2|{iid}|{start.isoformat()}|{end.isoformat()}|trades".encode()).hexdigest()[:24]
                runs.append({
                    "market_request_id": rid,
                    "request_type": "NATIVE_N2_STAGE2_EXACT_TRADES",
                    "eligible_next_research_date": str(date),
                    "source_instrument_id": str(iid),
                    "dataset": "GLBX.MDP3",
                    "schema": "trades",
                    "symbols": str(iid),
                    "stype_in": "instrument_id",
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "candidate_minute_count": len(seq),
                })
                for ts in seq:
                    minute_to_run[(str(date), str(iid), ts.isoformat())] = rid
        req2 = pd.DataFrame(runs)
        stage2_level["stage2_market_request_id"] = [minute_to_run[(str(z.eligible_next_research_date), str(z.source_instrument_id), z.minute_start.isoformat())] for z in stage2_level.itertuples()]
        client = db.Historical(key)
        costs = {}; errs = []
        with ThreadPoolExecutor(max_workers=12) as ex:
            futs = {ex.submit(metadata_cost, client, row): row["market_request_id"] for row in req2.to_dict("records")}
            for fut in as_completed(futs):
                rid = futs[fut]
                try: costs[rid] = fut.result()
                except Exception as exc: errs.append({"market_request_id": rid, "error": str(exc)})
        if errs:
            raise SystemExit(f"Stage2 metadata quote failures={len(errs)} first={errs[:3]}")
        req2["cost_usd"] = req2.market_request_id.map(costs).astype(float)
    else:
        req2 = pd.DataFrame(columns=["market_request_id","request_type","eligible_next_research_date","source_instrument_id","dataset","schema","symbols","stype_in","start","end","candidate_minute_count","cost_usd"])
        stage2_level["stage2_market_request_id"] = pd.Series(dtype=str)

    stage2_level.drop(columns=["minute_start"], errors="ignore").to_csv(out / "native_n2_stage2_level_manifest.csv", index=False)
    req2.to_csv(out / "native_n2_stage2_market_request_manifest.csv", index=False)
    total2 = float(req2.cost_usd.sum()) if len(req2) else 0.0

    summary = {
        "version": "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_RESOLUTION_STAGE2_QUOTE_V1",
        "stage1_acquisition_complete": True,
        "stage1_levels": 243,
        "stage1_resolved_exact_contact": int(res.stage1_exact_contact.sum()),
        "stage1_exact_contact_rate": float(res.stage1_exact_contact.mean()),
        "stage1_unresolved_total": int((~res.stage1_exact_contact).sum()),
        "stage1_resolved_no_contact_exhausted": int(len(exhausted_ids)),
        "stage2_levels": int(len(stage2_level)),
        "stage2_unique_candidate_minutes": int(stage2_level[["eligible_next_research_date","source_instrument_id","minute_start_utc"]].drop_duplicates().shape[0]) if len(stage2_level) else 0,
        "stage2_merged_market_requests": int(len(req2)),
        "exact_stage2_cost_usd": total2,
        "stage2_authorization": "METADATA_ONLY_STAGE2_DOWNLOAD_NOT_AUTHORIZED",
        "stage2_market_data_download_performed": False,
        "full_n2_union_download_performed": False,
        "stage1_resolution_sha256": sha256_file(out / "native_n2_stage1_resolution.csv"),
        "stage1_resolution_by_type_sha256": sha256_file(out / "native_n2_stage1_resolution_by_type.csv"),
        "stage2_level_manifest_sha256": sha256_file(out / "native_n2_stage2_level_manifest.csv"),
        "stage2_market_request_manifest_sha256": sha256_file(out / "native_n2_stage2_market_request_manifest.csv"),
        "sequential_freeze": "COMEX_DEV_RANK1_NATIVE_N2_SEQUENTIAL_ACQUISITION_FREEZE_v1.md",
        "contact_rule": "first chronological raw GC trade in tested candidate minute whose price equals frozen contact_tick_price on 0.10 GC tick",
        "dev_rank2_opened": False,
        "retro_confirm_opened": False,
        "locked_comex_test_opened": False,
        "notes": [
            "Stage1 exact trades are outcome data for contact confirmation only.",
            "Stage2 population is mechanical: candidate rank 2 only for levels not resolved in Stage1.",
            "Stage2 uses metadata.get_cost only; no Stage2 timeseries.get_range call is present.",
            "A new explicit financial authorization is required before any Stage2 market-data download."
        ],
    }
    (out / "native_n2_stage1_resolution_stage2_quote.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
