#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from rzr.config import ResearchConfig
from rzr.io import load_ohlc_csv
from rzr.features import quote_activity_mask, robust_sigma60, session_bucket
from rzr.contacts import find_first_contacts
from rzr.entries_v1 import _effective_side
from rzr.full_m1_zones_v1 import generate_baseline_zones_full_m1, opening_quote_mask

import build_xau_core_causal_confluence_preoutcome_v1 as base
import build_xau_core_causal_confluence_preoutcome_repair_v1 as repair
import build_xau_core_causal_confluence_preoutcome_timeframe_aligned_v1 as aligned


M1_TIMESTAMP_SEMANTICS = "BAR_START_UTC"
MAX_ENTRY_WAIT = 2
RELEVANT_FAMILIES = {"DISPLACEMENT_ORIGIN", "OBJECTIVE_LIQUIDITY", "MEMORY", "FVG"}
M1_FORMATION_FAMILIES = {"MEMORY", "FVG"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iso(ts) -> str:
    return pd.Timestamp(ts).isoformat()


def _parse_metadata(z) -> dict:
    try:
        return json.loads(str(z.metadata_json or "{}"))
    except Exception:
        return {}


def build_zone_information_provenance(
    zones,
    doz_prov: dict[str, dict],
) -> tuple[dict[str, dict], dict]:
    out: dict[str, dict] = {}
    all_viol = 0
    width_viol = 0
    generated_relevant = 0

    for z in zones:
        fam = str(z.family.value)
        if fam not in RELEVANT_FAMILIES:
            continue
        generated_relevant += 1
        known = pd.Timestamp(z.known_time)
        meta = _parse_metadata(z)

        if fam == "DISPLACEMENT_ORIGIN":
            d = doz_prov.get(str(z.zone_id), {})
            source_last = d.get("source_last_m1_timestamp")
            info = known
            base_pass = bool(d.get("provenance_pass", False))
            width_pass = True
        else:
            source_raw = meta.get("source_last_m1_timestamp_used")
            info_raw = meta.get("information_available_time")
            source_last = pd.Timestamp(source_raw) if source_raw else None
            info = pd.Timestamp(info_raw) if info_raw else None
            base_pass = bool(
                source_last is not None and info is not None
                and source_last < info <= known
            )
            requires_width = bool(
                fam == "MEMORY"
                or (fam == "OBJECTIVE_LIQUIDITY" and str(z.source_tf) in {"D1", "W1", "SESSION", "PRICE"})
            )
            if requires_width:
                width_source = str(meta.get("width_spread_source", ""))
                width_spread = meta.get("width_open_spread")
                width_pass = bool(
                    width_source == "OPEN_BID_ASK_AT_KNOWN_TIME"
                    and width_spread is not None
                    and np.isfinite(float(width_spread))
                    and float(width_spread) >= 0
                    and info is not None
                    and info == known
                )
            else:
                width_pass = True

        if not base_pass:
            all_viol += 1
        if not width_pass:
            width_viol += 1

        out[str(z.zone_id)] = {
            "zone_id": str(z.zone_id),
            "family": fam,
            "variant": str(z.variant),
            "source_tf": str(z.source_tf),
            "known_time": known,
            "source_last_m1_timestamp_used": source_last,
            "information_available_time": info,
            "zone_information_pass": bool(base_pass),
            "zone_width_information_pass": bool(width_pass),
        }

    return out, {
        "generated_relevant_zones": int(generated_relevant),
        "generated_zone_information_time_violations": int(all_viol),
        "generated_zone_width_information_violations": int(width_viol),
    }


def provenance_manifest_for_contacts(
    raw: pd.DataFrame,
    zone_info: dict[str, dict],
) -> tuple[pd.DataFrame, dict]:
    rows = []
    all_viol = 0
    formation_contact_viol = 0
    width_viol = 0

    for r in raw.to_dict("records"):
        fam = str(r.get("family", ""))
        if fam not in RELEVANT_FAMILIES:
            continue
        zid = str(r["zone_id"])
        p = zone_info.get(zid, {})
        contact = pd.Timestamp(r["contact_time"])
        known = pd.Timestamp(r["zone_known_time"])
        source_last = p.get("source_last_m1_timestamp_used")
        info = p.get("information_available_time")
        source_last = pd.Timestamp(source_last) if source_last is not None else None
        info = pd.Timestamp(info) if info is not None else None

        pass_order = bool(
            p.get("zone_information_pass", False)
            and source_last is not None and info is not None
            and source_last < info <= known <= contact
        )
        if not pass_order:
            all_viol += 1

        is_m1_formation = bool(
            fam in M1_FORMATION_FAMILIES
            or (fam == "OBJECTIVE_LIQUIDITY" and str(p.get("source_tf", "")) == "PRICE")
        )
        formation_ok = bool(not is_m1_formation or (source_last is not None and contact > source_last))
        if not formation_ok:
            formation_contact_viol += 1

        width_ok = bool(p.get("zone_width_information_pass", False))
        if not width_ok:
            width_viol += 1

        rows.append({
            "zone_id": zid,
            "family": fam,
            "variant": str(r.get("variant", "")),
            "source_tf": str(p.get("source_tf", "")),
            "source_last_m1_timestamp_used": "" if source_last is None else iso(source_last),
            "information_available_time": "" if info is None else iso(info),
            "known_time": iso(known),
            "first_contact_time": iso(contact),
            "provenance_pass": bool(pass_order),
            "m1_formation_contact_pass": bool(formation_ok),
            "zone_width_information_pass": bool(width_ok),
        })

    df = pd.DataFrame(rows)
    if len(df):
        df = df.sort_values(["first_contact_time", "family", "zone_id"], kind="mergesort").reset_index(drop=True)
    return df, {
        "contacted_relevant_zones": int(len(df)),
        "all_zone_information_time_violations": int(all_viol),
        "m1_formation_bar_contact_violations": int(formation_contact_viol),
        "zone_width_information_violations": int(width_viol),
    }


def _next_open_quote(mask: np.ndarray, start: int, max_wait: int = MAX_ENTRY_WAIT) -> int:
    n = len(mask)
    for j in range(start, min(n, start + int(max_wait) + 1)):
        if bool(mask[j]):
            return int(j)
    return -1


def _anchor_record(e: dict) -> dict:
    r = dict(e["anchor"])
    r["event_id"] = e["event_id"]
    r["contact_time"] = pd.Timestamp(e["confluence_time"])
    r["contact_idx"] = int(e["confluence_idx"])
    r["causal_confluence"] = True
    return r


def event_manifest_full_m1(
    events: list[dict],
    bars: pd.DataFrame,
    cfg: ResearchConfig,
    year: int,
) -> tuple[pd.DataFrame, dict]:
    opening = opening_quote_mask(bars).to_numpy(bool)
    out = []
    triggers = 0
    no_entry = 0
    timing_viol = 0
    prefix_viol = 0
    entry_quote_viol = 0

    for e in events:
        rec = _anchor_record(e)
        m_full = repair.causal_clean_rejection_trigger_minutes(
            bars, rec, max_minutes=int(cfg.failed_auction_primary_minutes)
        )
        if not np.isfinite(m_full):
            continue
        triggers += 1
        ci = int(rec["contact_idx"])
        confirm_i = ci + int(m_full)
        if confirm_i >= len(bars):
            timing_viol += 1
            continue

        prefix = bars.iloc[: confirm_i + 1]
        m_prefix = repair.causal_clean_rejection_trigger_minutes(
            prefix, rec, max_minutes=int(cfg.failed_auction_primary_minutes)
        )
        prefix_ok = bool(np.isfinite(m_prefix) and int(m_prefix) == int(m_full))
        if not prefix_ok:
            prefix_viol += 1

        start = confirm_i + 1
        ei = _next_open_quote(opening, start, MAX_ENTRY_WAIT)
        if ei < 0:
            no_entry += 1
            continue

        # Re-audit that only opening-quote availability selected this row.
        expected = _next_open_quote(opening, start, MAX_ENTRY_WAIT)
        entry_quote_ok = bool(expected == ei and opening[ei])
        if not entry_quote_ok:
            entry_quote_viol += 1

        doz = e["doz"]
        obj = e["obj"]
        anchor = e["anchor"]
        partner = e["partner"]
        ct = pd.Timestamp(e["confluence_time"])
        confirm_t = pd.Timestamp(bars.index[confirm_i])
        entry_t = pd.Timestamp(bars.index[ei])
        td = pd.Timestamp(doz["contact_time"])
        to = pd.Timestamp(obj["contact_time"])

        timing_ok = bool(
            pd.Timestamp(e["doz_known_time"]) <= td <= ct <= confirm_t < entry_t
            and pd.Timestamp(e["objective_known_time"]) <= to <= ct
            and pd.Timestamp(anchor["contact_time"]) == ct
            and int(anchor["contact_idx"]) == ci
        )
        if not timing_ok:
            timing_viol += 1

        direction = "LONG" if _effective_side(rec) == "SUPPORT" else "SHORT"
        sr = repair.side_relation(doz, obj)
        open_bid = float(pd.to_numeric(pd.Series([bars["open_bid"].iloc[ei]]), errors="coerce").iloc[0])
        open_ask = float(pd.to_numeric(pd.Series([bars["open_ask"].iloc[ei]]), errors="coerce").iloc[0])

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
            "causal_clean_rejection_trigger_minutes": int(m_full),
            "confirm_idx": int(confirm_i),
            "entry_idx": int(ei),
            "direction": direction,
            "anchor_side": str(rec["side"]),
            "doz_side": str(doz["side"]),
            "objective_side": str(obj["side"]),
            "side_relation": sr,
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
            "entry_open_bid": open_bid,
            "entry_open_ask": open_ask,
            "entry_open_quote_causality_pass": bool(entry_quote_ok),
            "timing_integrity_pass": bool(timing_ok),
            "prefix_invariance_pass": bool(prefix_ok),
        })

    df = pd.DataFrame(out)
    side_counts = (
        {str(k): int(v) for k, v in df["side_relation"].value_counts().to_dict().items()}
        if len(df) else {}
    )
    return df, {
        "causal_clean_rejection_triggers": int(triggers),
        "no_next_open_quote_entry": int(no_entry),
        "entry_candidates": int(len(df)),
        "timing_integrity_violations": int(timing_viol),
        "prefix_invariance_violations": int(prefix_viol),
        "entry_open_quote_causality_violations": int(entry_quote_viol),
        "side_relation_counts": side_counts,
    }


def self_test() -> None:
    aligned.self_test()
    repair.self_test()
    base.self_test()
    print("FULL_M1_PREOUTCOME_SELF_TEST_PASS")


def main() -> None:
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
    for c in ("open_bid", "high_bid", "low_bid", "close_bid", "open_ask", "high_ask", "low_ask", "close_ask"):
        if c in bars.columns:
            bars[c] = pd.to_numeric(bars[c], errors="coerce")
    bars["quote_active"] = quote_activity_mask(bars)
    bars["sigma60"] = robust_sigma60(bars)

    zones, generation_stats = generate_baseline_zones_full_m1(bars, cfg)
    doz_prov, doz_stats = aligned.build_doz_provenance(bars, zones, cfg)
    if int(doz_stats["doz_provenance_violations"]) != 0:
        raise RuntimeError(f"DOZ provenance violations in {year}: {doz_stats['doz_provenance_violations']}")

    zone_info, zone_info_stats = build_zone_information_provenance(zones, doz_prov)
    if int(zone_info_stats["generated_zone_information_time_violations"]) != 0:
        raise RuntimeError(f"generated zone information-time violations in {year}")
    if int(zone_info_stats["generated_zone_width_information_violations"]) != 0:
        raise RuntimeError(f"generated zone width-information violations in {year}")
    if int(generation_stats.get("memory_prefix_invariance_violations", 0)) != 0:
        raise RuntimeError(f"Memory prefix-invariance violations in {year}")

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
    prov_manifest, prov_contact_stats = provenance_manifest_for_contacts(raw, zone_info)
    for k in ("all_zone_information_time_violations", "m1_formation_bar_contact_violations", "zone_width_information_violations"):
        if int(prov_contact_stats[k]) != 0:
            raise RuntimeError(f"{k} in {year}: {prov_contact_stats[k]}")

    prov_path = out / f"causal_full_m1_zone_contact_provenance_{year}.csv.gz"
    prov_manifest.to_csv(prov_path, index=False, compression={"method": "gzip", "mtime": 0})

    events, pair_stats = base.build_direct_pair_events(raw, zone_meta)
    shuffled = raw.sample(frac=1, random_state=year).reset_index(drop=True) if len(raw) else raw
    events_shuffled, _ = base.build_direct_pair_events(shuffled, zone_meta)
    shuffle_pass = base._signature(events) == base._signature(events_shuffled)
    if not shuffle_pass:
        raise RuntimeError(f"row-order shuffle identity failed for {year}")

    start = pd.Timestamp(f"{year}-01-01T00:00:00Z")
    end = pd.Timestamp(f"{year+1}-01-01T00:00:00Z")
    events = [e for e in events if start <= pd.Timestamp(e["confluence_time"]) < end]

    manifest, entry_stats = event_manifest_full_m1(events, bars, cfg, year)
    event_by_id = {str(e["event_id"]): e for e in events}
    event_doz_prov_viol = 0
    if len(manifest):
        source_last_values = []
        source_pass_values = []
        for eid in manifest["event_id"].astype(str):
            e = event_by_id[eid]
            zid = str(e["doz"]["zone_id"])
            p = doz_prov.get(zid, {})
            source_last = p.get("source_last_m1_timestamp")
            ok = bool(p.get("provenance_pass", False))
            source_last_values.append(iso(source_last) if source_last is not None else "")
            source_pass_values.append(ok)
            if not ok:
                event_doz_prov_viol += 1
        manifest["doz_breakout_source_last_m1_timestamp"] = source_last_values
        manifest["doz_source_provenance_pass"] = source_pass_values

    if len(manifest) and manifest["event_id"].duplicated().any():
        raise RuntimeError(f"duplicate event_id in full-M1 annual manifest {year}")
    for k in ("timing_integrity_violations", "prefix_invariance_violations", "entry_open_quote_causality_violations"):
        if int(entry_stats[k]) != 0:
            raise RuntimeError(f"{k} in full-M1 population {year}: {entry_stats[k]}")
    if int(event_doz_prov_viol) != 0:
        raise RuntimeError(f"event DOZ provenance violations in full-M1 population {year}")

    if len(manifest):
        manifest = manifest.sort_values(["entry_time", "event_id"], kind="mergesort").reset_index(drop=True)
    manifest_path = out / f"causal_core_preoutcome_full_m1_events_{year}.csv"
    manifest.to_csv(manifest_path, index=False)

    fam_counts = raw["family"].astype(str).value_counts().to_dict() if len(raw) else {}
    summary = {
        "version": "XAU_CORE_CAUSAL_CONFLUENCE_FULL_M1_ANNUAL_V1",
        "year": year,
        "input_sha256": sha256_file(input_path),
        "m1_timestamp_semantics": M1_TIMESTAMP_SEMANTICS,
        "raw_contacts": int(len(raw)),
        "raw_contacts_by_family": {str(k): int(v) for k, v in fam_counts.items()},
        **generation_stats,
        **doz_stats,
        **zone_info_stats,
        **prov_contact_stats,
        **{str(k): int(v) for k, v in pair_stats.items()},
        **entry_stats,
        "event_doz_provenance_violations": int(event_doz_prov_viol),
        "shuffle_identity_pass": bool(shuffle_pass),
        "active_year": bool(len(manifest) > 0),
        "event_manifest_sha256": sha256_file(manifest_path),
        "zone_contact_provenance_manifest_rows": int(len(prov_manifest)),
        "zone_contact_provenance_manifest_sha256": sha256_file(prov_path),
        "pnl_inspected_or_used": False,
        "tp_sl_exit_simulated": False,
        "new_market_data_spend": 0,
    }
    with open(out / f"causal_core_preoutcome_full_m1_summary_{year}.json", "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
