#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from rzr.config import ResearchConfig
from rzr.io import load_ohlc_csv
from rzr.features import quote_activity_mask, robust_sigma60
from rzr.zones import generate_baseline_zones
from rzr.contacts import find_first_contacts
from rzr.resample import resample_ohlc

import build_xau_core_causal_confluence_preoutcome_v1 as base
import build_xau_core_causal_confluence_preoutcome_repair_v1 as repair


M1_TIMESTAMP_SEMANTICS = "BAR_START_UTC"
RESAMPLE_CLOSED = "left"
RESAMPLE_LABEL = "right"
DOZ_KNOWN_TIME_SEMANTICS = "HTF_BAR_CLOSE_BOUNDARY"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iso(ts) -> str:
    return pd.Timestamp(ts).isoformat()


def build_doz_provenance(
    bars: pd.DataFrame,
    zones,
    cfg: ResearchConfig,
) -> tuple[dict[str, dict], dict]:
    """Verify every generated DOZ uses only M1 starts strictly before known_time."""
    active = bars.loc[quote_activity_mask(bars)]
    by_tf: dict[str, dict[pd.Timestamp, pd.Timestamp]] = {}
    for tf in cfg.do_z_timeframes:
        x = resample_ohlc(active, tf)
        mapping: dict[pd.Timestamp, pd.Timestamp] = {}
        for ts, row in x.iterrows():
            last = row.get("source_last_m1_timestamp")
            if pd.isna(last):
                continue
            mapping[pd.Timestamp(ts)] = pd.Timestamp(last)
        by_tf[str(tf)] = mapping

    out: dict[str, dict] = {}
    violations = 0
    missing = 0
    total = 0
    by_tf_counts: dict[str, int] = {}

    for z in zones:
        if str(z.family.value) != "DISPLACEMENT_ORIGIN":
            continue
        total += 1
        tf = str(z.source_tf)
        by_tf_counts[tf] = by_tf_counts.get(tf, 0) + 1
        known = pd.Timestamp(z.known_time)
        source_last = by_tf.get(tf, {}).get(known)
        if source_last is None:
            missing += 1
            violations += 1
            out[str(z.zone_id)] = {
                "source_last_m1_timestamp": None,
                "provenance_pass": False,
            }
            continue
        ok = bool(pd.Timestamp(source_last) < known)
        if not ok:
            violations += 1
        out[str(z.zone_id)] = {
            "source_last_m1_timestamp": pd.Timestamp(source_last),
            "provenance_pass": ok,
        }

    return out, {
        "doz_zones_total": int(total),
        "doz_zones_by_tf": by_tf_counts,
        "doz_provenance_missing": int(missing),
        "doz_provenance_violations": int(violations),
    }


def self_test() -> None:
    # Keep all previously validated direct-pair and irreversible-trigger tests.
    repair.self_test()

    idx = pd.date_range("2026-01-01T13:00:00Z", periods=16, freq="min")
    bars = pd.DataFrame(
        {
            "open": range(16),
            "high": range(1, 17),
            "low": range(16),
            "close": range(16),
        },
        index=idx,
    )
    x = resample_ohlc(bars, "15min")
    row = x.loc[pd.Timestamp("2026-01-01T13:15:00Z")]
    assert pd.Timestamp(row["source_last_m1_timestamp"]) == pd.Timestamp("2026-01-01T13:14:00Z")
    assert float(row["close"]) == 14.0
    print("TIMEFRAME_ALIGNED_SELF_TEST_PASS")


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
    doz_prov, prov_stats = build_doz_provenance(bars, zones, cfg)
    if int(prov_stats["doz_provenance_violations"]) != 0:
        raise RuntimeError(
            f"DOZ source provenance violations in {year}: {prov_stats['doz_provenance_violations']}"
        )

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
            "source_last_m1_timestamp": (
                doz_prov.get(str(z.zone_id), {}).get("source_last_m1_timestamp")
            ),
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

    manifest, entry_stats = repair.event_manifest(events, bars, cfg, year)

    event_by_id = {str(e["event_id"]): e for e in events}
    event_prov_viol = 0
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
                event_prov_viol += 1
        manifest["doz_breakout_source_last_m1_timestamp"] = source_last_values
        manifest["doz_source_provenance_pass"] = source_pass_values

    if len(manifest) and manifest["event_id"].duplicated().any():
        raise RuntimeError(f"duplicate event_id in timeframe-aligned annual manifest {year}")
    if int(entry_stats["timing_integrity_violations"]) != 0:
        raise RuntimeError(f"timing integrity violations in timeframe-aligned population {year}")
    if int(entry_stats["prefix_invariance_violations"]) != 0:
        raise RuntimeError(f"prefix invariance violations in timeframe-aligned population {year}")
    if int(event_prov_viol) != 0:
        raise RuntimeError(f"event DOZ provenance violations in timeframe-aligned population {year}")

    if len(manifest):
        manifest = manifest.sort_values(["entry_time", "event_id"], kind="mergesort").reset_index(drop=True)
    manifest_path = out / f"causal_core_preoutcome_timeframe_aligned_events_{year}.csv"
    manifest.to_csv(manifest_path, index=False)

    fam_counts = raw["family"].astype(str).value_counts().to_dict() if len(raw) else {}
    summary = {
        "version": "XAU_CORE_CAUSAL_CONFLUENCE_TIMEFRAME_ALIGNED_ANNUAL_V1",
        "year": year,
        "input_sha256": sha256_file(input_path),
        "m1_timestamp_semantics": M1_TIMESTAMP_SEMANTICS,
        "resample_closed": RESAMPLE_CLOSED,
        "resample_label": RESAMPLE_LABEL,
        "doz_known_time_semantics": DOZ_KNOWN_TIME_SEMANTICS,
        "raw_contacts": int(len(raw)),
        "raw_contacts_by_family": {str(k): int(v) for k, v in fam_counts.items()},
        **prov_stats,
        **{str(k): int(v) for k, v in pair_stats.items()},
        **entry_stats,
        "event_doz_provenance_violations": int(event_prov_viol),
        "shuffle_identity_pass": bool(shuffle_pass),
        "active_year": bool(len(manifest) > 0),
        "event_manifest_sha256": sha256_file(manifest_path),
        "pnl_inspected_or_used": False,
        "tp_sl_exit_simulated": False,
        "new_market_data_spend": 0,
    }
    with open(out / f"causal_core_preoutcome_timeframe_aligned_summary_{year}.json", "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
