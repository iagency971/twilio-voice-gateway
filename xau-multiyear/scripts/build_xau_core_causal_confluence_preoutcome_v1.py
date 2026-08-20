#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd

from rzr.config import ResearchConfig
from rzr.io import load_ohlc_csv
from rzr.features import quote_activity_mask, robust_sigma60, session_bucket
from rzr.zones import generate_baseline_zones
from rzr.contacts import find_first_contacts
from rzr.behavior_v2 import classify_behavior_v2
from rzr.entries_v1 import _active_array, _next_active, _effective_side

PAIR_FAMILIES = {"DISPLACEMENT_ORIGIN", "OBJECTIVE_LIQUIDITY"}
EXCLUDING_FAMILIES = {"MEMORY", "FVG"}
TOL = pd.Timedelta(minutes=2)
OVERLAP_THRESHOLD = 0.50


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iso(ts):
    return pd.Timestamp(ts).isoformat()


def width(r) -> float:
    return float(r["upper"]) - float(r["lower"])


def rel_overlap_bounds(a_lo, a_up, b_lo, b_up) -> float:
    inter = max(0.0, min(float(a_up), float(b_up)) - max(float(a_lo), float(b_lo)))
    denom = min(float(a_up) - float(a_lo), float(b_up) - float(b_lo))
    return inter / denom if denom > 0 else 0.0


def rel_overlap(a, b) -> float:
    return rel_overlap_bounds(a["lower"], a["upper"], b["lower"], b["upper"])


def anchor_tie_key_full(r, zone_meta):
    z = zone_meta[str(r["zone_id"])]
    return (
        width(r),
        pd.Timestamp(r["zone_known_time"]).value,
        pd.Timestamp(z["origin_time"]).value,
        str(r["zone_id"]),
    )


def stable_event_id(doz, obj, confluence_time, anchor_id) -> str:
    payload = "|".join([
        str(doz["zone_id"]),
        str(obj["zone_id"]),
        iso(doz["contact_time"]),
        iso(obj["contact_time"]),
        iso(confluence_time),
        str(anchor_id),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _expire(dq, now):
    cutoff = now - TOL
    while dq and pd.Timestamp(dq[0]["contact_time"]) < cutoff:
        dq.popleft()


def _same_pair_key(doz, obj):
    return (str(doz["zone_id"]), str(obj["zone_id"]))


def build_direct_pair_events(raw: pd.DataFrame, zone_meta: dict[str, dict]) -> tuple[list[dict], dict]:
    if raw.empty:
        return [], {
            "direct_pairs_before_contamination": 0,
            "contaminated_pairs": 0,
            "qualifying_pairs": 0,
            "deduplicated_pairs": 0,
            "emitted_events": 0,
        }

    x = raw.sort_values(["contact_time", "lower", "upper", "zone_id"], kind="mergesort").copy()
    x["contact_time"] = pd.to_datetime(x["contact_time"], utc=True)
    x["zone_known_time"] = pd.to_datetime(x["zone_known_time"], utc=True)

    recents = {
        "DISPLACEMENT_ORIGIN": deque(),
        "OBJECTIVE_LIQUIDITY": deque(),
        "MEMORY": deque(),
        "FVG": deque(),
    }
    pair_rows: list[dict] = []
    pair_seen: set[tuple[str, str]] = set()
    contaminated = 0
    direct_before = 0

    for t, g in x.groupby("contact_time", sort=True):
        now = pd.Timestamp(t)
        for dq in recents.values():
            _expire(dq, now)

        current = g.to_dict("records")
        # Add the complete timestamp group first so same-minute contacts are observable together.
        for r in current:
            fam = str(r.get("family"))
            if fam in recents:
                recents[fam].append(r)

        current_doz = [r for r in current if str(r.get("family")) == "DISPLACEMENT_ORIGIN"]
        current_obj = [r for r in current if str(r.get("family")) == "OBJECTIVE_LIQUIDITY"]

        candidates = []
        for d in current_doz:
            for o in recents["OBJECTIVE_LIQUIDITY"]:
                candidates.append((d, o))
        for o in current_obj:
            for d in recents["DISPLACEMENT_ORIGIN"]:
                candidates.append((d, o))

        for doz, obj in candidates:
            key = _same_pair_key(doz, obj)
            if key in pair_seen:
                continue
            pair_seen.add(key)

            td = pd.Timestamp(doz["contact_time"])
            to = pd.Timestamp(obj["contact_time"])
            if abs(td - to) > TOL:
                continue
            if pd.Timestamp(doz["zone_known_time"]) > td or pd.Timestamp(obj["zone_known_time"]) > to:
                raise RuntimeError(f"zone known after raw first contact for pair {key}")
            ov = rel_overlap(doz, obj)
            if ov + 1e-15 < OVERLAP_THRESHOLD:
                continue
            direct_before += 1
            ct = max(td, to)

            # Causal ONLY: Memory/FVG can exclude only if already contacted inside the same
            # two-minute causal event window and directly overlapping one of the pair members.
            excluders = []
            for fam in EXCLUDING_FAMILIES:
                for ex in recents[fam]:
                    te = pd.Timestamp(ex["contact_time"])
                    if not (ct - TOL <= te <= ct):
                        continue
                    if pd.Timestamp(ex["zone_known_time"]) > te:
                        continue
                    if max(rel_overlap(ex, doz), rel_overlap(ex, obj)) + 1e-15 >= OVERLAP_THRESHOLD:
                        excluders.append(str(ex["zone_id"]))
            if excluders:
                contaminated += 1
                continue

            if td > to:
                anchor, partner = doz, obj
            elif to > td:
                anchor, partner = obj, doz
            else:
                if anchor_tie_key_full(doz, zone_meta) <= anchor_tie_key_full(obj, zone_meta):
                    anchor, partner = doz, obj
                else:
                    anchor, partner = obj, doz

            inter_lo = max(float(doz["lower"]), float(obj["lower"]))
            inter_up = min(float(doz["upper"]), float(obj["upper"]))
            zdoz = zone_meta[str(doz["zone_id"])]
            zobj = zone_meta[str(obj["zone_id"])]
            pair_rows.append({
                "doz": doz,
                "obj": obj,
                "anchor": anchor,
                "partner": partner,
                "confluence_time": ct,
                "confluence_idx": int(anchor["contact_idx"]),
                "pair_lower": inter_lo,
                "pair_upper": inter_up,
                "direct_overlap": float(ov),
                "doz_origin_time": pd.Timestamp(zdoz["origin_time"]),
                "doz_known_time": pd.Timestamp(zdoz["known_time"]),
                "doz_source_tf": str(zdoz.get("source_tf", "")),
                "doz_variant": str(zdoz.get("variant", "")),
                "objective_origin_time": pd.Timestamp(zobj["origin_time"]),
                "objective_known_time": pd.Timestamp(zobj["known_time"]),
                "objective_source_tf": str(zobj.get("source_tf", "")),
                "objective_variant": str(zobj.get("variant", "")),
            })

    pair_rows.sort(key=lambda p: (
        pd.Timestamp(p["confluence_time"]).value,
        width(p["anchor"]),
        width(p["partner"]),
        str(p["anchor"]["zone_id"]),
        str(p["partner"]["zone_id"]),
    ))

    emitted = []
    active = deque()
    dedup = 0
    for p in pair_rows:
        now = pd.Timestamp(p["confluence_time"])
        while active and now - pd.Timestamp(active[0]["confluence_time"]) > TOL:
            active.popleft()
        ids = {str(p["doz"]["zone_id"]), str(p["obj"]["zone_id"])}
        same = False
        for e in active:
            eids = {str(e["doz"]["zone_id"]), str(e["obj"]["zone_id"])}
            if ids & eids:
                same = True
                break
            if rel_overlap_bounds(
                p["pair_lower"], p["pair_upper"], e["pair_lower"], e["pair_upper"]
            ) + 1e-15 >= OVERLAP_THRESHOLD:
                same = True
                break
        if same:
            dedup += 1
            continue
        eid = stable_event_id(p["doz"], p["obj"], p["confluence_time"], p["anchor"]["zone_id"])
        p = dict(p)
        p["event_id"] = eid
        emitted.append(p)
        active.append(p)

    return emitted, {
        "direct_pairs_before_contamination": int(direct_before),
        "contaminated_pairs": int(contaminated),
        "qualifying_pairs": int(len(pair_rows)),
        "deduplicated_pairs": int(dedup),
        "emitted_events": int(len(emitted)),
    }


def event_records_for_behavior(events: list[dict]) -> pd.DataFrame:
    rows = []
    for e in events:
        r = dict(e["anchor"])
        r["event_id"] = e["event_id"]
        r["contact_time"] = pd.Timestamp(e["confluence_time"])
        r["contact_idx"] = int(e["confluence_idx"])
        r["causal_confluence"] = True
        rows.append(r)
    return pd.DataFrame(rows)


def event_manifest(
    events: list[dict], classified: pd.DataFrame, bars: pd.DataFrame,
    cfg: ResearchConfig, year: int,
) -> tuple[pd.DataFrame, dict]:
    by_id = {str(e["event_id"]): e for e in events}
    active = _active_array(bars)
    out = []
    clean = 0
    no_entry = 0
    timing_viol = 0

    for rec in classified.to_dict("records"):
        if str(rec.get("behavior_v2", "")) != "CLEAN_REJECTION":
            continue
        clean += 1
        m = rec.get("first_reclaim_minutes_v2", np.nan)
        if not np.isfinite(m):
            continue
        ci = int(rec["contact_idx"])
        confirm_i = ci + int(m)
        if confirm_i >= len(bars):
            continue
        ei = _next_active(active, confirm_i + 1, 2)
        if ei < 0:
            no_entry += 1
            continue

        e = by_id[str(rec["event_id"])]
        doz = e["doz"]
        obj = e["obj"]
        anchor = e["anchor"]
        partner = e["partner"]
        ct = pd.Timestamp(e["confluence_time"])
        confirm_t = pd.Timestamp(bars.index[confirm_i])
        entry_t = pd.Timestamp(bars.index[ei])
        td = pd.Timestamp(doz["contact_time"])
        to = pd.Timestamp(obj["contact_time"])

        ok = (
            pd.Timestamp(e["doz_known_time"]) <= td <= ct <= confirm_t < entry_t
            and pd.Timestamp(e["objective_known_time"]) <= to <= ct
            and pd.Timestamp(anchor["contact_time"]) == ct
        )
        if not ok:
            timing_viol += 1

        direction = "LONG" if _effective_side(rec) == "SUPPORT" else "SHORT"
        out.append({
            "event_id": e["event_id"],
            "source_year": int(year),
            "doz_zone_id": str(doz["zone_id"]),
            "objective_zone_id": str(obj["zone_id"]),
            "anchor_zone_id": str(anchor["zone_id"]),
            "anchor_family": str(anchor["family"]),
            "anchor_variant": str(anchor["variant"]),
            "partner_zone_id": str(partner["zone_id"]),
            "partner_family": str(partner["family"]),
            "partner_variant": str(partner["variant"]),
            "doz_contact_time": iso(td),
            "objective_contact_time": iso(to),
            "confluence_time": iso(ct),
            "confirm_time": iso(confirm_t),
            "entry_time": iso(entry_t),
            "confluence_idx": int(ci),
            "confirm_idx": int(confirm_i),
            "entry_idx": int(ei),
            "direction": direction,
            "anchor_side": str(rec["side"]),
            "anchor_lower": float(rec["lower"]),
            "anchor_upper": float(rec["upper"]),
            "pair_lower": float(e["pair_lower"]),
            "pair_upper": float(e["pair_upper"]),
            "direct_overlap": float(e["direct_overlap"]),
            "doz_origin_time": iso(e["doz_origin_time"]),
            "doz_known_time": iso(e["doz_known_time"]),
            "doz_source_tf": e["doz_source_tf"],
            "doz_variant": e["doz_variant"],
            "objective_origin_time": iso(e["objective_origin_time"]),
            "objective_known_time": iso(e["objective_known_time"]),
            "objective_source_tf": e["objective_source_tf"],
            "objective_variant": e["objective_variant"],
            "doz_activation_session": session_bucket(pd.Timestamp(e["doz_known_time"]), cfg.timezone),
            "objective_activation_session": session_bucket(pd.Timestamp(e["objective_known_time"]), cfg.timezone),
            "entry_session": session_bucket(entry_t, cfg.timezone),
            "timing_integrity_pass": bool(ok),
        })

    df = pd.DataFrame(out)
    return df, {
        "clean_rejection_events": int(clean),
        "no_next_active_entry": int(no_entry),
        "entry_candidates": int(len(df)),
        "timing_integrity_violations": int(timing_viol),
    }


def _signature(events: list[dict]) -> list[tuple]:
    return [
        (
            e["event_id"],
            iso(e["confluence_time"]),
            str(e["doz"]["zone_id"]),
            str(e["obj"]["zone_id"]),
            str(e["anchor"]["zone_id"]),
            round(float(e["pair_lower"]), 10),
            round(float(e["pair_upper"]), 10),
        )
        for e in events
    ]


def self_test():
    ts = pd.Timestamp("2020-01-01T12:00:00Z")
    rows = [
        {"zone_id":"D1","family":"DISPLACEMENT_ORIGIN","variant":"DOZ_BODY","side":"SUPPORT","zone_known_time":ts-pd.Timedelta("1h"),"contact_time":ts,"contact_idx":10,"lower":100.0,"upper":101.0,"center":100.5,"sigma60":1.0,"approach_direction":-1},
        {"zone_id":"O1","family":"OBJECTIVE_LIQUIDITY","variant":"PDL","side":"SUPPORT","zone_known_time":ts-pd.Timedelta("2h"),"contact_time":ts+pd.Timedelta("1min"),"contact_idx":11,"lower":100.4,"upper":100.8,"center":100.6,"sigma60":1.0,"approach_direction":-1},
        {"zone_id":"D2","family":"DISPLACEMENT_ORIGIN","variant":"DOZ_LAST","side":"SUPPORT","zone_known_time":ts-pd.Timedelta("1h"),"contact_time":ts+pd.Timedelta("1min"),"contact_idx":11,"lower":100.45,"upper":100.75,"center":100.6,"sigma60":1.0,"approach_direction":-1},
    ]
    meta = {
        "D1":{"origin_time":ts-pd.Timedelta("3h"),"known_time":ts-pd.Timedelta("1h"),"source_tf":"30min","variant":"DOZ_BODY"},
        "O1":{"origin_time":ts-pd.Timedelta("1d"),"known_time":ts-pd.Timedelta("2h"),"source_tf":"D1","variant":"PDL"},
        "D2":{"origin_time":ts-pd.Timedelta("4h"),"known_time":ts-pd.Timedelta("1h"),"source_tf":"15min","variant":"DOZ_LAST"},
    }
    a, _ = build_direct_pair_events(pd.DataFrame(rows), meta)
    b, _ = build_direct_pair_events(pd.DataFrame(rows).sample(frac=1, random_state=7), meta)
    if _signature(a) != _signature(b):
        raise AssertionError("shuffle determinism failed")
    if len(a) != 1:
        raise AssertionError(f"expected one deduplicated event, got {len(a)}")
    print("SELF_TEST_PASS")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--year", type=int)
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        if not args.csv:
            return
    if not args.csv or args.year is None or not args.out:
        raise SystemExit("csv, --year and --out required")

    year = int(args.year)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = ResearchConfig()

    input_path = Path(args.csv)
    bars = load_ohlc_csv(input_path).sort_index().copy()
    bars["quote_active"] = quote_activity_mask(bars)
    bars["sigma60"] = robust_sigma60(bars)

    zones = generate_baseline_zones(bars, cfg)
    zone_meta = {
        str(z.zone_id): {
            "zone_id": str(z.zone_id),
            "family": z.family.value,
            "variant": str(z.variant),
            "origin_time": pd.Timestamp(z.origin_time),
            "known_time": pd.Timestamp(z.known_time),
            "lower": float(z.lower),
            "upper": float(z.upper),
            "source_tf": str(z.source_tf),
        }
        for z in zones
    }
    raw = find_first_contacts(bars, zones, bars["sigma60"], cfg)
    events, pair_stats = build_direct_pair_events(raw, zone_meta)

    # Fixed row-order shuffle identity check before behavior/P&L.
    shuffled = raw.sample(frac=1, random_state=year).reset_index(drop=True) if len(raw) else raw
    events_shuffled, _ = build_direct_pair_events(shuffled, zone_meta)
    shuffle_pass = _signature(events) == _signature(events_shuffled)
    if not shuffle_pass:
        raise RuntimeError(f"row-order shuffle identity failed for {year}")

    start = pd.Timestamp(f"{year}-01-01T00:00:00Z")
    end = pd.Timestamp(f"{year+1}-01-01T00:00:00Z")
    events = [e for e in events if start <= pd.Timestamp(e["confluence_time"]) < end]

    recs = event_records_for_behavior(events)
    classified = classify_behavior_v2(bars, recs, cfg) if len(recs) else recs
    manifest, entry_stats = event_manifest(events, classified, bars, cfg, year)

    if len(manifest) and manifest["event_id"].duplicated().any():
        raise RuntimeError(f"duplicate event_id in annual manifest {year}")
    if int(entry_stats["timing_integrity_violations"]) != 0:
        raise RuntimeError(f"timing integrity violations in {year}")

    if len(manifest):
        manifest = manifest.sort_values(["entry_time", "event_id"], kind="mergesort").reset_index(drop=True)
    manifest_path = out / f"causal_core_preoutcome_events_{year}.csv"
    manifest.to_csv(manifest_path, index=False)

    fam_counts = raw["family"].astype(str).value_counts().to_dict() if len(raw) else {}
    summary = {
        "version": "XAU_CORE_CAUSAL_CONFLUENCE_PREOUTCOME_ANNUAL_V1",
        "year": year,
        "input_sha256": sha256_file(input_path),
        "raw_contacts": int(len(raw)),
        "raw_contacts_by_family": {str(k): int(v) for k, v in fam_counts.items()},
        **pair_stats,
        "target_year_emitted_confluences": int(len(events)),
        **entry_stats,
        "active_year": bool(len(manifest) > 0),
        "shuffle_identity_pass": bool(shuffle_pass),
        "duplicate_event_ids": 0,
        "event_manifest_sha256": sha256_file(manifest_path),
        "pnl_inspected_or_used": False,
        "tp_sl_exit_simulated": False,
        "new_market_data_spend": 0,
    }
    (out / f"causal_core_preoutcome_summary_{year}.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
