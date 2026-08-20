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
from rzr.zones import generate_baseline_zones
from rzr.contacts import find_first_contacts
from rzr.entries_v1 import _active_array, _next_active, _effective_side

import build_xau_core_causal_confluence_preoutcome_v1 as base


MAX_TRIGGER_MINUTES = 15


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iso(ts):
    return pd.Timestamp(ts).isoformat()


def causal_clean_rejection_trigger_minutes(
    bars: pd.DataFrame,
    rec: dict,
    max_minutes: int = MAX_TRIGGER_MINUTES,
) -> float:
    """Return first irreversible clean-rejection reclaim offset, else NaN.

    The trigger is causal: a reclaim is valid only if no distal breach has occurred
    from confluence through the reclaim bar inclusive. If breach and reclaim occur
    in the same M1 bar, adverse ambiguity applies and no clean-rejection trigger is
    emitted. Once a reclaim triggers, later bars are irrelevant.
    """
    i = int(rec["contact_idx"])
    if i < 0 or i >= len(bars):
        return np.nan

    side_eff = _effective_side(rec)
    lo_z = float(rec["lower"])
    up_z = float(rec["upper"])
    high = bars["high"].to_numpy(float)
    low = bars["low"].to_numpy(float)
    close = bars["close"].to_numpy(float)
    end = min(len(bars), i + int(max_minutes) + 1)

    for j in range(i, end):
        if side_eff == "SUPPORT":
            breach = bool(low[j] < lo_z)
            reclaim = bool(close[j] > up_z)
        else:
            breach = bool(high[j] > up_z)
            reclaim = bool(close[j] < lo_z)

        # A breach before or on the reclaim bar permanently disqualifies CLEAN_REJECTION.
        if breach:
            return np.nan
        if reclaim:
            return float(j - i)

    return np.nan


def side_relation(doz: dict, obj: dict) -> str:
    ds = str(doz.get("side", ""))
    os = str(obj.get("side", ""))
    if ds == "NEUTRAL" or os == "NEUTRAL":
        return "NEUTRAL_RESOLVED"
    return "SAME_SIDE" if ds == os else "OPPOSITE_SIDE"


def _anchor_record(e: dict) -> dict:
    r = dict(e["anchor"])
    r["event_id"] = e["event_id"]
    r["contact_time"] = pd.Timestamp(e["confluence_time"])
    r["contact_idx"] = int(e["confluence_idx"])
    r["causal_confluence"] = True
    return r


def event_manifest(
    events: list[dict],
    bars: pd.DataFrame,
    cfg: ResearchConfig,
    year: int,
) -> tuple[pd.DataFrame, dict]:
    active = _active_array(bars)
    out: list[dict] = []
    triggers = 0
    no_entry = 0
    timing_viol = 0
    prefix_viol = 0

    for e in events:
        rec = _anchor_record(e)
        m_full = causal_clean_rejection_trigger_minutes(
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

        # Hard prefix-invariance check: the trigger computed with only information
        # through the confirmation minute must be identical to the trigger found
        # when the full future path is present.
        prefix = bars.iloc[: confirm_i + 1]
        m_prefix = causal_clean_rejection_trigger_minutes(
            prefix, rec, max_minutes=int(cfg.failed_auction_primary_minutes)
        )
        prefix_ok = bool(np.isfinite(m_prefix) and int(m_prefix) == int(m_full))
        if not prefix_ok:
            prefix_viol += 1

        ei = _next_active(active, confirm_i + 1, 2)
        if ei < 0:
            no_entry += 1
            continue

        doz = e["doz"]
        obj = e["obj"]
        anchor = e["anchor"]
        partner = e["partner"]
        ct = pd.Timestamp(e["confluence_time"])
        confirm_t = pd.Timestamp(bars.index[confirm_i])
        entry_t = pd.Timestamp(bars.index[ei])
        td = pd.Timestamp(doz["contact_time"])
        to = pd.Timestamp(obj["contact_time"])

        timing_ok = (
            pd.Timestamp(e["doz_known_time"]) <= td <= ct <= confirm_t < entry_t
            and pd.Timestamp(e["objective_known_time"]) <= to <= ct
            and pd.Timestamp(anchor["contact_time"]) == ct
            and int(anchor["contact_idx"]) == ci
        )
        if not timing_ok:
            timing_viol += 1

        direction = "LONG" if _effective_side(rec) == "SUPPORT" else "SHORT"
        sr = side_relation(doz, obj)

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
            "timing_integrity_pass": bool(timing_ok),
            "prefix_invariance_pass": bool(prefix_ok),
        })

    df = pd.DataFrame(out)
    side_counts = (
        {str(k): int(v) for k, v in df["side_relation"].value_counts().to_dict().items()}
        if len(df)
        else {}
    )
    return df, {
        "causal_clean_rejection_triggers": int(triggers),
        "no_next_active_entry": int(no_entry),
        "entry_candidates": int(len(df)),
        "timing_integrity_violations": int(timing_viol),
        "prefix_invariance_violations": int(prefix_viol),
        "side_relation_counts": side_counts,
    }


def _bars(rows: list[list[float]]) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01T00:00:00Z", periods=len(rows), freq="min")
    d = pd.DataFrame(rows, index=idx, columns=["open", "high", "low", "close"])
    d["quote_active"] = True
    return d


def _synthetic_rec(side: str = "SUPPORT") -> dict:
    return {
        "contact_idx": 0,
        "side": side,
        "lower": 99.0,
        "upper": 100.0,
        "approach_direction": -1 if side == "SUPPORT" else 1,
    }


def self_test() -> None:
    # 1) Reclaim first, later breach, later reclaim: first trigger must survive.
    a = _bars([
        [99.7, 100.3, 99.4, 100.2],
        [100.2, 100.4, 99.9, 100.1],
        [100.1, 100.2, 98.7, 98.9],
        [98.9, 100.5, 98.8, 100.3],
    ])
    assert causal_clean_rejection_trigger_minutes(a, _synthetic_rec()) == 0.0

    # 2) Breach before reclaim: never a clean-rejection trigger.
    b = _bars([
        [99.5, 99.8, 98.8, 99.4],
        [99.4, 100.4, 99.2, 100.2],
        [100.2, 100.3, 100.0, 100.1],
    ])
    assert np.isnan(causal_clean_rejection_trigger_minutes(b, _synthetic_rec()))

    # 3) Same M1 bar breach + reclaim: adverse ambiguity => no trigger.
    c = _bars([[99.5, 100.4, 98.8, 100.2]])
    assert np.isnan(causal_clean_rejection_trigger_minutes(c, _synthetic_rec()))

    # 4) Future extensions may not revoke or move an already-observable trigger.
    prefix = _bars([
        [99.5, 99.9, 99.2, 99.7],
        [99.7, 100.4, 99.5, 100.2],
    ])
    m0 = causal_clean_rejection_trigger_minutes(prefix, _synthetic_rec())
    assert m0 == 1.0
    futures = [
        [[100.2, 100.4, 98.0, 98.5], [98.5, 101.0, 98.4, 100.5]],
        [[100.2, 101.0, 100.0, 100.8], [100.8, 101.2, 100.7, 101.1]],
    ]
    for ext in futures:
        full = _bars([
            [99.5, 99.9, 99.2, 99.7],
            [99.7, 100.4, 99.5, 100.2],
            *ext,
        ])
        assert causal_clean_rejection_trigger_minutes(full, _synthetic_rec()) == m0

    # 5) No reclaim => no trigger.
    d = _bars([
        [99.5, 99.9, 99.2, 99.7],
        [99.7, 99.95, 99.4, 99.8],
        [99.8, 99.9, 99.5, 99.7],
    ])
    assert np.isnan(causal_clean_rejection_trigger_minutes(d, _synthetic_rec()))

    # 6) Inherited direct-pair shuffle identity.
    base.self_test()
    print("REPAIR_SELF_TEST_PASS")


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
    events, pair_stats = base.build_direct_pair_events(raw, zone_meta)

    shuffled = raw.sample(frac=1, random_state=year).reset_index(drop=True) if len(raw) else raw
    events_shuffled, _ = base.build_direct_pair_events(shuffled, zone_meta)
    shuffle_pass = base._signature(events) == base._signature(events_shuffled)
    if not shuffle_pass:
        raise RuntimeError(f"row-order shuffle identity failed for {year}")

    start = pd.Timestamp(f"{year}-01-01T00:00:00Z")
    end = pd.Timestamp(f"{year+1}-01-01T00:00:00Z")
    events = [e for e in events if start <= pd.Timestamp(e["confluence_time"]) < end]

    manifest, entry_stats = event_manifest(events, bars, cfg, year)

    if len(manifest) and manifest["event_id"].duplicated().any():
        raise RuntimeError(f"duplicate event_id in repaired annual manifest {year}")
    if int(entry_stats["timing_integrity_violations"]) != 0:
        raise RuntimeError(f"timing integrity violations in repaired population {year}")
    if int(entry_stats["prefix_invariance_violations"]) != 0:
        raise RuntimeError(f"prefix invariance violations in repaired population {year}")

    if len(manifest):
        manifest = manifest.sort_values(["entry_time", "event_id"], kind="mergesort").reset_index(drop=True)
    manifest_path = out / f"causal_core_preoutcome_repaired_events_{year}.csv"
    manifest.to_csv(manifest_path, index=False)

    fam_counts = raw["family"].astype(str).value_counts().to_dict() if len(raw) else {}
    summary = {
        "version": "XAU_CORE_CAUSAL_CONFLUENCE_PREOUTCOME_REPAIR_ANNUAL_V1",
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
    (out / f"causal_core_preoutcome_repaired_summary_{year}.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
