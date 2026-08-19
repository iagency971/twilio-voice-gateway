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

HARD_CAP_USD = 0.002
REQUIRED_AUTH_TEXT = "OK NATIVE N2 STAGE2, plafond 0,002 $"
QUOTE_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE1_RESOLUTION_STAGE2_QUOTE_V1"
AUTH_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE2_AUTH_V1"
REQ_MARKER_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE2_REQUEST_FILE_V1"
COMPLETE_VERSION = "COMEX_DEV_RANK1_NATIVE_N2_STAGE2_ACQUISITION_COMPLETE_V1"


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
    quote_path = Path(args.quote)
    req_path = Path(args.market_requests)
    lvl_path = Path(args.level_manifest)
    auth_path = Path(args.authorization)
    completion = Path(args.completion_marker)
    if completion.exists():
        raise SystemExit("HARD GATE: Stage2 completion marker already exists")
    if not auth_path.exists():
        raise SystemExit("HARD GATE: Stage2 authorization missing")

    q = json.loads(quote_path.read_text())
    a = json.loads(auth_path.read_text())
    if q.get("version") != QUOTE_VERSION:
        raise SystemExit("HARD GATE: wrong Stage2 quote version")
    if q.get("stage2_authorization") != "METADATA_ONLY_STAGE2_DOWNLOAD_NOT_AUTHORIZED":
        raise SystemExit("HARD GATE: frozen quote authorization state changed")
    if q.get("stage2_market_data_download_performed") is not False:
        raise SystemExit("HARD GATE: Stage2 already marked downloaded")
    if int(q.get("stage2_levels", -1)) != 7 or int(q.get("stage2_merged_market_requests", -1)) != 7:
        raise SystemExit("HARD GATE: expected exactly 7 Stage2 levels / requests")
    if abs(float(q.get("exact_stage2_cost_usd", -1)) - 0.001557111741) > 1e-15:
        raise SystemExit("HARD GATE: frozen Stage2 quote changed")

    req_sha = sha256_file(req_path)
    lvl_sha = sha256_file(lvl_path)
    if req_sha != q.get("stage2_market_request_manifest_sha256"):
        raise SystemExit("HARD GATE: Stage2 market manifest SHA mismatch")
    if lvl_sha != q.get("stage2_level_manifest_sha256"):
        raise SystemExit("HARD GATE: Stage2 level manifest SHA mismatch")

    if a.get("version") != AUTH_VERSION or a.get("authorization") != REQUIRED_AUTH_TEXT:
        raise SystemExit("HARD GATE: exact user authorization absent")
    if abs(float(a.get("hard_cap_usd", -1)) - HARD_CAP_USD) > 1e-15:
        raise SystemExit("HARD GATE: authorization cap mismatch")
    if a.get("stage2_market_request_manifest_sha256") != req_sha or a.get("stage2_level_manifest_sha256") != lvl_sha:
        raise SystemExit("HARD GATE: authorization not bound to current Stage2 manifests")
    if a.get("one_shot") is not True or a.get("later_stage_download_authorized") is not False:
        raise SystemExit("HARD GATE: authorization scope invalid")

    req = pd.read_csv(req_path, dtype={"source_instrument_id": str, "symbols": str})
    lvl = pd.read_csv(lvl_path, dtype={"source_instrument_id": str})
    if len(req) != 7 or req.market_request_id.nunique() != 7 or len(lvl) != 7 or lvl.level_id.nunique() != 7:
        raise SystemExit("HARD GATE: Stage2 manifest cardinality mismatch")
    if set(req.schema.astype(str)) != {"trades"} or set(req.dataset.astype(str)) != {"GLBX.MDP3"}:
        raise SystemExit("HARD GATE: unexpected Stage2 market schema/dataset")

    rows = req.to_dict("records")
    client = db.Historical(key)
    quoted = []
    errors = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        fs = {ex.submit(retry_metadata, client.metadata.get_cost, **request_kwargs(r)): r for r in rows}
        for f in as_completed(fs):
            r = fs[f]
            try:
                z = dict(r)
                z["gate_cost_usd"] = float(f.result())
                quoted.append(z)
            except Exception as exc:
                errors.append({"market_request_id": str(r["market_request_id"]), "error": str(exc)})
    if errors:
        raise SystemExit(f"HARD GATE: metadata quote errors: {errors[:3]}")
    quoted = sorted(quoted, key=lambda x: str(x["market_request_id"]))
    total = float(sum(float(x["gate_cost_usd"]) for x in quoted))
    if total > HARD_CAP_USD + 1e-15:
        raise SystemExit(f"HARD GATE: current Stage2 quote ${total:.12f} exceeds approved cap ${HARD_CAP_USD:.3f}")

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    g = {
        "version": "COMEX_DEV_RANK1_NATIVE_N2_STAGE2_PRE_DOWNLOAD_GATE_V1",
        "authorization": REQUIRED_AUTH_TEXT,
        "approved_cap_usd": HARD_CAP_USD,
        "frozen_quote_usd": float(q["exact_stage2_cost_usd"]),
        "current_exact_quote_usd": total,
        "remaining_margin_usd": HARD_CAP_USD - total,
        "requests": 7,
        "market_request_manifest_sha256": req_sha,
        "level_manifest_sha256": lvl_sha,
        "market_data_download_performed": False,
        "later_stage_download_authorized": False,
        "rows": quoted,
    }
    (out / "gate.json").write_text(json.dumps(g, indent=2))
    print(json.dumps(g, indent=2))


def acquire(args: argparse.Namespace) -> None:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")
    gate_doc = json.loads(Path(args.gate).read_text())
    rows = list(gate_doc["rows"])
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    client = db.Historical(key)
    accumulated = 0.0
    for i, row in enumerate(rows):
        rid = str(row["market_request_id"])
        marker = out / f"{rid}.json"
        raw = out / f"{rid}.dbn.zst"
        if marker.exists() or raw.exists():
            raise SystemExit(f"refusing overwrite for {rid}")
        kw = request_kwargs(row)
        current = float(retry_metadata(client.metadata.get_cost, **kw))
        future_gate = float(sum(float(x["gate_cost_usd"]) for x in rows[i+1:]))
        projected = accumulated + current + future_gate
        if projected > HARD_CAP_USD + 1e-15:
            raise SystemExit(f"REQUEST GATE {rid}: projected Stage2 upper bound ${projected:.12f} exceeds cap ${HARD_CAP_USD:.3f}")

        # Sole market-data request for this interval. Deliberately no automatic paid retry.
        store = client.timeseries.get_range(path=str(raw), **kw)
        df = store.to_df()
        decoded = int(len(df))
        if not raw.exists():
            raise RuntimeError(f"{rid}: Databento returned without raw DBN file")
        qa = {
            "version": REQ_MARKER_VERSION,
            "market_request_id": rid,
            "dataset": str(row["dataset"]),
            "schema": str(row["schema"]),
            "symbols": str(row["symbols"]),
            "stype_in": str(row["stype_in"]),
            "start": str(row["start"]),
            "end": str(row["end"]),
            "gate_cost_usd": float(row["gate_cost_usd"]),
            "immediate_pre_download_cost_usd": current,
            "decoded_trade_records": decoded,
            "raw_file": raw.name,
            "raw_file_bytes": int(raw.stat().st_size),
            "sha256": sha256_file(raw),
            "market_data_request_performed": True,
            "record_count_equality_qa_used": False,
        }
        marker.write_text(json.dumps(qa, indent=2))
        accumulated += current
    print(json.dumps({"completed": len(rows), "cost_upper_bound_usd": accumulated}, indent=2))


def finalize(args: argparse.Namespace) -> None:
    req = pd.read_csv(args.market_requests, dtype={"symbols": str})
    root = Path(args.root)
    markers = []
    for p in root.glob("*.json"):
        try:
            z = json.loads(p.read_text())
        except Exception:
            continue
        if z.get("version") == REQ_MARKER_VERSION:
            markers.append(z)
    exp = set(req.market_request_id.astype(str))
    got = {str(z["market_request_id"]) for z in markers}
    if got != exp or len(got) != 7:
        raise SystemExit(f"Stage2 incomplete missing={sorted(exp-got)} extra={sorted(got-exp)}")
    cost = float(sum(float(z["immediate_pre_download_cost_usd"]) for z in markers))
    if cost > HARD_CAP_USD + 1e-15:
        raise SystemExit("Stage2 completed cost upper bound exceeds approved cap")
    result = {
        "version": "COMEX_DEV_RANK1_NATIVE_N2_STAGE2_ACQUISITION_SUMMARY_V1",
        "complete": True,
        "expected_requests": 7,
        "completed_request_markers": 7,
        "decoded_trade_records_total": int(sum(int(z["decoded_trade_records"]) for z in markers)),
        "raw_bytes_total": int(sum(int(z["raw_file_bytes"]) for z in markers)),
        "confirmed_success_cost_upper_bound_usd": cost,
        "hard_cap_usd": HARD_CAP_USD,
        "hard_cap_respected": True,
        "stage2_market_data_download_performed": True,
        "later_stage_market_data_download_performed": False,
    }
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "acquisition_summary.json").write_text(json.dumps(result, indent=2))
    marker = {
        "version": COMPLETE_VERSION,
        "complete": True,
        "requests": 7,
        "confirmed_success_cost_upper_bound_usd": cost,
        "hard_cap_usd": HARD_CAP_USD,
        "later_stage_download_authorized": False,
        "dev_rank2_opened": False,
        "retro_confirm_opened": False,
        "locked_comex_test_opened": False,
        "summary_sha256": sha256_file(out / "acquisition_summary.json"),
    }
    (out / "ACQUISITION_COMPLETE.json").write_text(json.dumps(marker, indent=2))
    print(json.dumps(result, indent=2))


def load_dbn(path: Path) -> pd.DataFrame:
    df = db.DBNStore.from_file(path).to_df().reset_index(drop=False)
    if "ts_event" not in df.columns:
        if len(df.columns) == 0:
            return pd.DataFrame(columns=["ts_event", "price"])
        df = df.rename(columns={df.columns[0]: "ts_event"})
    df["ts_event"] = pd.to_datetime(df.ts_event, utc=True)
    return df.sort_values("ts_event").reset_index(drop=True)


def quote_costs(rows: pd.DataFrame) -> pd.DataFrame:
    if len(rows) == 0:
        rows = rows.copy(); rows["cost_usd"] = pd.Series(dtype=float); return rows
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")
    client = db.Historical(key)
    costs = {}; errors = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        fs = {ex.submit(retry_metadata, client.metadata.get_cost, **request_kwargs(r)): str(r["market_request_id"]) for r in rows.to_dict("records")}
        for f in as_completed(fs):
            rid = fs[f]
            try: costs[rid] = float(f.result())
            except Exception as exc: errors.append({"market_request_id": rid, "error": str(exc)})
    if errors:
        raise SystemExit(f"next-stage metadata quote errors: {errors[:3]}")
    rows = rows.copy(); rows["cost_usd"] = rows.market_request_id.astype(str).map(costs).astype(float)
    return rows


def analyze_quote_next(args: argparse.Namespace) -> None:
    root = Path(args.root)
    complete = json.loads((root / "ACQUISITION_COMPLETE.json").read_text())
    if complete.get("version") != COMPLETE_VERSION or complete.get("complete") is not True:
        raise SystemExit("Stage2 completion marker invalid")
    if complete.get("later_stage_download_authorized") is not False:
        raise SystemExit("later-stage download must remain unauthorized")

    lvl2 = pd.read_csv(args.stage2_level_manifest, dtype={"source_instrument_id": str})
    stage1 = pd.read_csv(args.stage1_resolution, dtype={"source_instrument_id": str})
    cand = pd.read_csv(args.candidate_minutes, dtype={"source_instrument_id": str})
    screen = pd.read_csv(args.n1_level_screen, dtype={"source_instrument_id": str})
    if len(lvl2) != 7 or len(stage1) != 243 or len(screen) != 368:
        raise SystemExit("analysis input cardinality mismatch")

    # Candidate ranks are derived mechanically from N1 candidate minutes only.
    cand["minute_start"] = pd.to_datetime(cand.minute_start_utc, utc=True)
    cand = cand.sort_values(["level_id", "minute_start"]).copy()
    cand["candidate_rank_derived"] = cand.groupby("level_id").cumcount() + 1

    req_markers = {}
    for p in root.glob("*.json"):
        try: z = json.loads(p.read_text())
        except Exception: continue
        if z.get("version") == REQ_MARKER_VERSION:
            req_markers[str(z["market_request_id"])] = z

    resolution_rows = []
    for r in lvl2.itertuples(index=False):
        rid = str(r.stage2_market_request_id)
        z = req_markers[rid]
        raw = root / str(z["raw_file"])
        if not raw.exists() or sha256_file(raw) != z["sha256"]:
            raise SystemExit(f"Stage2 raw file integrity failure {rid}")
        df = load_dbn(raw)
        if "price" not in df.columns:
            if len(df) == 0:
                exact = df
            else:
                raise SystemExit(f"Stage2 raw file {rid} lacks price")
        else:
            df["price"] = pd.to_numeric(df.price, errors="coerce")
            good = df.price.notna()
            if good.any():
                scaled = df.loc[good, "price"].to_numpy(float) * 10.0
                if int((np.abs(scaled - np.rint(scaled)) > 1e-6).sum()):
                    raise SystemExit(f"off GC 0.10 tick trades in {rid}")
            tick = int(round(float(r.contact_tick_price) * 10.0))
            price_tick = np.rint(df.price.to_numpy(float) * 10.0)
            exact = df.loc[df.price.notna() & (price_tick == tick)].copy()
        exact = exact.sort_values("ts_event") if len(exact) else exact
        contact = bool(len(exact))
        first_time = exact.iloc[0].ts_event.isoformat() if contact else ""
        allc = cand[cand.level_id.astype(str) == str(r.level_id)]
        max_rank = int(allc.candidate_rank_derived.max()) if len(allc) else 0
        next_rank = 3 if (not contact and max_rank >= 3) else None
        if contact:
            status = "RESOLVED_CONTACT_STAGE2"
        elif max_rank >= 3:
            status = "UNRESOLVED_ADVANCE_STAGE3"
        else:
            status = "RESOLVED_NO_CONTACT_EXHAUSTED_STAGE2"
        resolution_rows.append({
            "level_id": str(r.level_id),
            "source_research_date": str(r.source_research_date),
            "eligible_next_research_date": str(r.eligible_next_research_date),
            "source_instrument_id": str(r.source_instrument_id),
            "level_type": str(r.level_type),
            "contact_tick_price": float(r.contact_tick_price),
            "stage2_candidate_minute_start_utc": str(r.minute_start_utc),
            "stage2_market_request_id": rid,
            "stage2_trade_records_in_candidate_minute": int(len(df)),
            "stage2_exact_tick_trade_count": int(len(exact)),
            "stage2_exact_contact": contact,
            "stage2_first_exact_contact_time_utc": first_time,
            "candidate_minutes_total": max_rank,
            "resolution_after_stage2": status,
            "next_candidate_rank": next_rank if next_rank is not None else "",
        })
    res2 = pd.DataFrame(resolution_rows).sort_values("level_id").reset_index(drop=True)

    # Update the 243 N2-required levels cumulatively.
    res2_map = res2.set_index("level_id").to_dict("index")
    cumulative_rows = []
    for r in stage1.itertuples(index=False):
        lid = str(r.level_id)
        s1_contact = str(r.stage1_exact_contact).lower() == "true" if not isinstance(r.stage1_exact_contact, (bool, np.bool_)) else bool(r.stage1_exact_contact)
        if s1_contact:
            final_status = "RESOLVED_CONTACT_STAGE1"
            contact = True
            ctime = str(r.stage1_first_exact_contact_time_utc)
            stage = 1
        elif lid in res2_map:
            z = res2_map[lid]
            contact = bool(z["stage2_exact_contact"])
            final_status = str(z["resolution_after_stage2"])
            ctime = str(z["stage2_first_exact_contact_time_utc"])
            stage = 2 if contact else ""
        else:
            # These are the five Stage1-exhausted levels from the frozen sequential rule.
            contact = False
            final_status = "RESOLVED_NO_CONTACT_EXHAUSTED_STAGE1"
            ctime = ""
            stage = ""
        cumulative_rows.append({
            "level_id": lid,
            "source_research_date": str(r.source_research_date),
            "eligible_next_research_date": str(r.eligible_next_research_date),
            "source_instrument_id": str(r.source_instrument_id),
            "level_type": str(r.level_type),
            "contact_tick_price": float(r.contact_tick_price),
            "exact_contact_so_far": contact,
            "first_exact_contact_time_utc": ctime,
            "contact_stage": stage,
            "resolution_after_stage2": final_status,
        })
    cum = pd.DataFrame(cumulative_rows)

    # Build the mechanically required Stage3 population from unresolved Stage2 levels only.
    unresolved = set(res2.loc[res2.resolution_after_stage2 == "UNRESOLVED_ADVANCE_STAGE3", "level_id"].astype(str))
    stage3_levels = []
    for lid in sorted(unresolved):
        g = cand[(cand.level_id.astype(str) == lid) & (cand.candidate_rank_derived == 3)]
        if len(g) != 1:
            raise SystemExit(f"Stage3 candidate rank 3 parity failure for {lid}: {len(g)}")
        z = g.iloc[0]
        stage3_levels.append({
            "level_id": lid,
            "source_research_date": str(z.source_research_date),
            "eligible_next_research_date": str(z.eligible_next_research_date),
            "source_instrument_id": str(z.source_instrument_id),
            "level_type": str(z.level_type),
            "contact_tick_price": float(z.contact_tick_price),
            "minute_start_utc": str(z.minute_start_utc),
            "minute_end_utc": str(z.minute_end_utc),
            "candidate_rank": 3,
        })
    lvl3 = pd.DataFrame(stage3_levels)

    runs = []
    minute_to_run = {}
    if len(lvl3):
        u = lvl3[["eligible_next_research_date", "source_instrument_id", "minute_start_utc"]].drop_duplicates().copy()
        u["minute_start"] = pd.to_datetime(u.minute_start_utc, utc=True)
        for (date, iid), g in u.groupby(["eligible_next_research_date", "source_instrument_id"], sort=True):
            times = sorted(g.minute_start.tolist()); groups = []; cur = [times[0]]
            for ts in times[1:]:
                if ts == cur[-1] + pd.Timedelta(minutes=1): cur.append(ts)
                else: groups.append(cur); cur = [ts]
            groups.append(cur)
            for seq in groups:
                start = seq[0]; end = seq[-1] + pd.Timedelta(minutes=1)
                rid = hashlib.sha256(f"NATIVE_N2_STAGE3|{iid}|{start.isoformat()}|{end.isoformat()}|trades".encode()).hexdigest()[:24]
                runs.append({
                    "market_request_id": rid,
                    "request_type": "NATIVE_N2_STAGE3_EXACT_TRADES",
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
                for ts in seq: minute_to_run[(str(date), str(iid), ts.isoformat())] = rid
        lvl3["stage3_market_request_id"] = [minute_to_run[(str(r.eligible_next_research_date), str(r.source_instrument_id), pd.Timestamp(r.minute_start_utc).isoformat())] for r in lvl3.itertuples()]
    req3 = pd.DataFrame(runs, columns=["market_request_id","request_type","eligible_next_research_date","source_instrument_id","dataset","schema","symbols","stype_in","start","end","candidate_minute_count"])
    req3 = quote_costs(req3)

    # Build 368-level status by adding the N1-impossible contacts.
    cum_map = cum.set_index("level_id").to_dict("index")
    all_rows = []
    for r in screen.itertuples(index=False):
        lid = str(r.level_id)
        if str(r.n1_screen_label) == "NO_EXACT_CONTACT_N1_SCREEN":
            status = "RESOLVED_NO_CONTACT_N1_SCREEN"; contact = False; ctime = ""; cstage = ""
        else:
            z = cum_map[lid]; status = str(z["resolution_after_stage2"]); contact = bool(z["exact_contact_so_far"]); ctime = str(z["first_exact_contact_time_utc"]); cstage = z["contact_stage"]
        all_rows.append({
            "level_id": lid,
            "source_research_date": str(r.source_research_date),
            "eligible_next_research_date": str(r.eligible_next_research_date),
            "source_instrument_id": str(r.source_instrument_id),
            "level_type": str(r.level_type),
            "contact_tick_price": float(r.contact_tick_price),
            "exact_contact_so_far": contact,
            "first_exact_contact_time_utc": ctime,
            "contact_stage": cstage,
            "resolution_after_stage2": status,
        })
    all368 = pd.DataFrame(all_rows)
    bytype = all368.groupby("level_type", as_index=False).agg(
        levels=("level_id","size"),
        exact_contacts_so_far=("exact_contact_so_far","sum"),
    )
    bytype["exact_contact_rate_so_far"] = bytype.exact_contacts_so_far / bytype.levels
    bytype["unresolved_after_stage2"] = bytype.level_type.map(all368[all368.resolution_after_stage2 == "UNRESOLVED_ADVANCE_STAGE3"].groupby("level_type").size()).fillna(0).astype(int)

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    res2.to_csv(out / "native_n2_stage2_resolution.csv", index=False)
    cum.to_csv(out / "native_n2_cumulative_243_after_stage2.csv", index=False)
    all368.to_csv(out / "native_368_contact_status_after_stage2.csv", index=False)
    bytype.to_csv(out / "native_368_contact_status_by_type_after_stage2.csv", index=False)
    lvl3.to_csv(out / "native_n2_stage3_level_manifest.csv", index=False)
    req3.to_csv(out / "native_n2_stage3_market_request_manifest.csv", index=False)

    total3 = float(req3.cost_usd.sum()) if len(req3) else 0.0
    manifest = {
        "version": "COMEX_DEV_RANK1_NATIVE_N2_STAGE2_RESOLUTION_STAGE3_QUOTE_V1",
        "stage2_acquisition_complete": True,
        "stage2_levels": 7,
        "stage2_resolved_exact_contact": int(res2.stage2_exact_contact.sum()),
        "stage2_unresolved_advance_stage3": int((res2.resolution_after_stage2 == "UNRESOLVED_ADVANCE_STAGE3").sum()),
        "stage2_resolved_no_contact_exhausted": int((res2.resolution_after_stage2 == "RESOLVED_NO_CONTACT_EXHAUSTED_STAGE2").sum()),
        "native_levels_total": 368,
        "exact_contacts_so_far": int(all368.exact_contact_so_far.sum()),
        "resolved_no_contact_so_far": int(all368.resolution_after_stage2.str.startswith("RESOLVED_NO_CONTACT").sum()),
        "unresolved_after_stage2": int((all368.resolution_after_stage2 == "UNRESOLVED_ADVANCE_STAGE3").sum()),
        "all_368_classified": bool((all368.resolution_after_stage2 != "UNRESOLVED_ADVANCE_STAGE3").all()),
        "stage3_levels": int(len(lvl3)),
        "stage3_unique_candidate_minutes": int(lvl3[["eligible_next_research_date","source_instrument_id","minute_start_utc"]].drop_duplicates().shape[0]) if len(lvl3) else 0,
        "stage3_merged_market_requests": int(len(req3)),
        "exact_stage3_cost_usd": total3,
        "stage3_authorization": "METADATA_ONLY_STAGE3_DOWNLOAD_NOT_AUTHORIZED",
        "stage3_market_data_download_performed": False,
        "full_n2_union_download_performed": False,
        "stage2_resolution_sha256": sha256_file(out / "native_n2_stage2_resolution.csv"),
        "native_368_status_sha256": sha256_file(out / "native_368_contact_status_after_stage2.csv"),
        "stage3_level_manifest_sha256": sha256_file(out / "native_n2_stage3_level_manifest.csv"),
        "stage3_market_request_manifest_sha256": sha256_file(out / "native_n2_stage3_market_request_manifest.csv"),
        "sequential_freeze": "COMEX_DEV_RANK1_NATIVE_N2_SEQUENTIAL_ACQUISITION_FREEZE_v1.md",
        "dev_rank2_opened": False,
        "retro_confirm_opened": False,
        "locked_comex_test_opened": False,
        "notes": [
            "Stage2 raw trades are used only to confirm exact contact at the frozen GC tick.",
            "Any Stage3 population is mechanical: candidate rank 3 only for levels unresolved after Stage2.",
            "Stage3 uses metadata.get_cost only; no Stage3 timeseries.get_range call is made.",
            "A new explicit financial authorization is required before any Stage3 download."
        ],
    }
    (out / "native_n2_stage2_resolution_stage3_quote.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


def parse_args():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gate")
    for x in ["quote","market-requests","level-manifest","authorization","completion-marker","out"]: g.add_argument(f"--{x}", required=True)
    a = sub.add_parser("acquire"); a.add_argument("--gate", required=True); a.add_argument("--out", required=True)
    f = sub.add_parser("finalize"); f.add_argument("--market-requests", required=True); f.add_argument("--root", required=True); f.add_argument("--out", required=True)
    q = sub.add_parser("analyze-quote-next")
    for x in ["root","stage2-level-manifest","stage1-resolution","candidate-minutes","n1-level-screen","out"]: q.add_argument(f"--{x}", required=True)
    return ap.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.cmd == "gate": gate(args)
    elif args.cmd == "acquire": acquire(args)
    elif args.cmd == "finalize": finalize(args)
    else: analyze_quote_next(args)
