#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rzr.config import ResearchConfig
from rzr.io import load_ohlc_csv
from rzr.features import quote_activity_mask, robust_sigma60, session_bucket, trading_day_key
from rzr.zones import generate_baseline_zones
from rzr.contacts import find_first_contacts
from rzr.stacking import collapse_contact_events
from rzr.labels import label_contacts
from rzr.behavior_v2 import classify_behavior_v2
from rzr.entries_v2 import build_entry
from rzr.entries_v1 import simulate_one
from rzr.vantage_overlay import apply_fixed_spread_overlay

SCENARIOS = {
    "S10_C6": {"spread_usd": 0.10, "commission_rt_usd": 6.0, "role": "sensitivity"},
    "S11_C6_PRIMARY": {"spread_usd": 0.11, "commission_rt_usd": 6.0, "role": "primary"},
    "S12_C6": {"spread_usd": 0.12, "commission_rt_usd": 6.0, "role": "sensitivity"},
    "S18_C9_STRESS": {"spread_usd": 0.18, "commission_rt_usd": 9.0, "role": "stress"},
}
TARGET_RS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
FAMILIES = ["DISPLACEMENT_ORIGIN", "OBJECTIVE_LIQUIDITY", "MEMORY", "FVG"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pf(values) -> float:
    x = pd.to_numeric(pd.Series(values), errors="coerce").dropna().to_numpy(float)
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg <= 0:
        return float("inf") if pos > 0 else float("nan")
    return pos / neg


def _relative_overlap(a_lo: float, a_up: float, b_lo: float, b_up: float) -> float:
    overlap = max(0.0, min(a_up, b_up) - max(a_lo, b_lo))
    denom = min(a_up - a_lo, b_up - b_lo)
    return overlap / denom if denom > 0 else 0.0


def collapse_with_membership(contacts: pd.DataFrame, overlap_threshold: float = 0.5,
                             time_tolerance_minutes: int = 2):
    """Exact first-match stacking semantics plus raw-member mapping for audit only."""
    if contacts.empty:
        return contacts.copy(), pd.DataFrame(columns=["stack_id", "member_zone_id"])

    x = contacts.sort_values(["contact_time", "lower", "upper", "zone_id"]).reset_index(drop=True).copy()
    n = len(x)
    lo = pd.to_numeric(x["lower"], errors="raise").to_numpy(float)
    up = pd.to_numeric(x["upper"], errors="raise").to_numpy(float)
    width = up - lo
    times_ns = pd.to_datetime(x["contact_time"], utc=True).astype("int64").to_numpy(np.int64)

    g_lo = np.empty(n, dtype=float)
    g_up = np.empty(n, dtype=float)
    g_last = np.empty(n, dtype=np.int64)
    g_start = np.empty(n, dtype=np.int64)
    g_rep = np.empty(n, dtype=np.int64)
    g_rep_width = np.empty(n, dtype=float)
    g_count = np.zeros(n, dtype=np.int64)
    g_families: list[set[str]] = []
    g_variants: list[set[str]] = []
    g_members: list[list[int]] = []

    active = np.empty(n, dtype=np.int64)
    active_count = 0
    group_count = 0
    tol_ns = int(pd.Timedelta(minutes=time_tolerance_minutes).value)
    last_now = None
    families = x["family"].astype(str).to_numpy(object)
    variants = x["variant"].astype(str).to_numpy(object)

    for idx in range(n):
        now = int(times_ns[idx])
        if now != last_now and active_count:
            cur = active[:active_count]
            keep = (now - g_last[cur]) <= tol_ns
            kept = cur[keep]
            active[:len(kept)] = kept
            active_count = len(kept)
        last_now = now

        row_lo = float(lo[idx]); row_up = float(up[idx]); row_w = float(width[idx])
        chosen = -1
        if active_count:
            cand_groups = active[:active_count]
            a_lo = g_lo[cand_groups]; a_up = g_up[cand_groups]
            if abs(overlap_threshold - 0.5) <= 1e-15 and row_w > 0:
                a_w = a_up - a_lo
                a_c = (a_lo + a_up) * 0.5
                row_c = (row_lo + row_up) * 0.5
                eps = np.finfo(float).eps * np.maximum(1.0, np.abs(row_c)) * 8.0
                possible = np.abs(a_c - row_c) <= (np.maximum(a_w, row_w) * 0.5 + eps)
            else:
                possible = (a_up >= row_lo) & (a_lo <= row_up)
            for gi in cand_groups[possible]:
                gii = int(gi)
                if _relative_overlap(row_lo, row_up, float(g_lo[gii]), float(g_up[gii])) >= overlap_threshold:
                    chosen = gii
                    break

        if chosen < 0:
            gi = group_count; group_count += 1
            g_lo[gi] = row_lo; g_up[gi] = row_up
            g_start[gi] = now; g_last[gi] = now
            g_rep[gi] = idx; g_rep_width[gi] = row_w; g_count[gi] = 1
            g_families.append({str(families[idx])})
            g_variants.append({str(variants[idx])})
            g_members.append([idx])
            active[active_count] = gi; active_count += 1
        else:
            gi = chosen
            g_last[gi] = now
            if row_lo < g_lo[gi]: g_lo[gi] = row_lo
            if row_up > g_up[gi]: g_up[gi] = row_up
            g_count[gi] += 1
            g_families[gi].add(str(families[idx]))
            g_variants[gi].add(str(variants[idx]))
            g_members[gi].append(idx)
            if row_w < g_rep_width[gi]:
                g_rep_width[gi] = row_w
                g_rep[gi] = idx

    rows = []
    membership = []
    for gi in range(group_count):
        stack_id = f"STACK_{gi:08d}"
        rep = x.iloc[int(g_rep[gi])].to_dict()
        rep["stack_id"] = stack_id
        rep["constituent_count"] = int(g_count[gi])
        rep["constituent_families"] = json.dumps(sorted(g_families[gi]))
        rep["constituent_variants"] = json.dumps(sorted(g_variants[gi]))
        rep["stack_contact_start"] = pd.Timestamp(int(g_start[gi]), tz="UTC")
        rep["stack_contact_end"] = pd.Timestamp(int(g_last[gi]), tz="UTC")
        rows.append(rep)
        for idx in g_members[gi]:
            r = x.iloc[int(idx)]
            membership.append({"stack_id": stack_id, "member_zone_id": str(r.zone_id)})
    return pd.DataFrame(rows), pd.DataFrame(membership)


def assert_stack_parity(canonical: pd.DataFrame, audit: pd.DataFrame) -> dict:
    cols = ["stack_id", "zone_id", "contact_time", "lower", "upper", "constituent_count",
            "constituent_families", "constituent_variants"]
    a = canonical[cols].copy().sort_values("stack_id").reset_index(drop=True)
    b = audit[cols].copy().sort_values("stack_id").reset_index(drop=True)
    ok = len(a) == len(b)
    mismatch = []
    if ok:
        for c in cols:
            if c in ("lower", "upper"):
                eq = np.isclose(pd.to_numeric(a[c]).to_numpy(float), pd.to_numeric(b[c]).to_numpy(float), rtol=0, atol=1e-12)
            elif c == "contact_time":
                eq = pd.to_datetime(a[c], utc=True).astype("int64").to_numpy() == pd.to_datetime(b[c], utc=True).astype("int64").to_numpy()
            else:
                eq = a[c].astype(str).to_numpy() == b[c].astype(str).to_numpy()
            if not bool(np.all(eq)):
                ok = False
                mismatch.append(c)
    return {"pass": bool(ok), "canonical_stacks": int(len(a)), "audit_stacks": int(len(b)), "mismatch_columns": mismatch}


def tf_minutes(tf: str) -> float:
    t = str(tf).lower().strip()
    mapping = {"1min": 1, "5min": 5, "15min": 15, "30min": 30, "1h": 60, "60min": 60}
    if t in mapping:
        return float(mapping[t])
    try:
        return float(pd.Timedelta(t).total_seconds() / 60.0)
    except Exception:
        return float("nan")


def age_bucket(hours: float) -> str:
    if not np.isfinite(hours): return "UNKNOWN"
    if hours < 1: return "<1h"
    if hours < 4: return "1-4h"
    if hours < 12: return "4-12h"
    if hours < 24: return "12-24h"
    if hours < 72: return "1-3d"
    if hours < 168: return "3-7d"
    if hours < 720: return "7-30d"
    return ">=30d"


def sess(ts, cfg: ResearchConfig) -> str:
    if ts is None or pd.isna(ts): return "UNKNOWN"
    return session_bucket(pd.Timestamp(ts), cfg.timezone)


def anchor_record(member_df: pd.DataFrame, family: str):
    g = member_df[member_df["family"].astype(str).eq(family)].copy()
    if g.empty:
        return None
    g["width"] = pd.to_numeric(g["upper"]) - pd.to_numeric(g["lower"])
    g["known_time"] = pd.to_datetime(g["known_time"], utc=True)
    g["origin_time"] = pd.to_datetime(g["origin_time"], utc=True)
    g = g.sort_values(["width", "known_time", "origin_time", "zone_id"], kind="mergesort")
    return g.iloc[0]


def canonical_json_list(values) -> str:
    vals = sorted({str(v) for v in values if pd.notna(v)})
    return json.dumps(vals, separators=(",", ":"))


def stable_event_id(year: int, rec: pd.Series) -> str:
    payload = "|".join([
        str(year), str(rec.get("stack_id")), str(rec.get("zone_id")),
        pd.Timestamp(rec.get("contact_time")).isoformat(),
        f"{float(rec.get('lower')):.10f}", f"{float(rec.get('upper')):.10f}",
    ])
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def compare_annual_summary(ledger: pd.DataFrame, expected_path: Path) -> dict:
    exp = pd.read_csv(expected_path)
    exp = exp[(exp["sample"] == "DOZ_OBJECTIVE_ONLY") &
              (exp["entry_model"] == "CLEAN_REJECTION") &
              (exp["risk_rule"] == "STRUCTURAL")].copy()
    checks = []
    all_pass = True
    for scenario in SCENARIOS:
        for rr in TARGET_RS:
            e = exp[(exp["scenario"] == scenario) & np.isclose(exp["target_r"].astype(float), rr)]
            g = ledger[(ledger["scenario"] == scenario) & np.isclose(ledger["target_r"].astype(float), rr)]
            row = {"scenario": scenario, "target_r": rr, "expected_rows": int(len(e)), "actual_trades": int(len(g))}
            if len(e) != 1:
                row["pass"] = False; row["reason"] = "EXPECTED_ROW_NOT_UNIQUE"; all_pass = False; checks.append(row); continue
            e = e.iloc[0]
            metrics = {
                "trades": (float(len(g)), float(e["trades"]), 0.0),
                "avg_gross_R": (float(g["gross_R"].mean()), float(e["avg_gross_R"]), 1e-10),
                "avg_net_R": (float(g["net_R"].mean()), float(e["avg_net_R"]), 1e-10),
                "pf_net": (float(pf(g["net_R"])), float(e["pf_net"]), 1e-9),
                "sum_net_R": (float(g["net_R"].sum()), float(e["sum_net_R"]), 1e-9),
                "median_risk_price": (float(g["risk_price"].median()), float(e["median_risk_price"]), 1e-10),
                "median_entry_delay_minutes": (float(g["entry_delay_minutes"].median()), float(e["median_entry_delay_minutes"]), 1e-10),
            }
            diffs = {}
            ok = True
            for name, (actual, expected, tol) in metrics.items():
                if np.isinf(actual) and np.isinf(expected):
                    pass
                elif not (np.isfinite(actual) and np.isfinite(expected)):
                    ok = False
                elif abs(actual - expected) > tol:
                    ok = False
                diffs[name] = {"actual": actual, "expected": expected, "abs_diff": abs(actual-expected) if np.isfinite(actual) and np.isfinite(expected) else None, "tol": tol}
            row["pass"] = bool(ok); row["metrics"] = diffs
            if not ok: all_pass = False
            checks.append(row)
    return {"pass": bool(all_pass), "cells": checks}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expected-annual-summary", required=True)
    args = ap.parse_args()

    year = int(args.year)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    input_path = Path(args.csv)
    cfg = ResearchConfig()
    input_sha = sha256_file(input_path)
    runtime_commit = os.getenv("GITHUB_SHA", "LOCAL")
    start = pd.Timestamp(f"{year}-01-01", tz="UTC")
    end = pd.Timestamp(f"{year+1}-01-01", tz="UTC")

    bars_mid = load_ohlc_csv(input_path).sort_index().copy()
    bars_mid["quote_active"] = quote_activity_mask(bars_mid)
    bars_mid["sigma60"] = robust_sigma60(bars_mid)

    zones = generate_baseline_zones(bars_mid, cfg)
    zdf = pd.DataFrame([{
        "zone_id": z.zone_id,
        "family": z.family.value,
        "variant": z.variant,
        "side": z.side.value,
        "origin_time": z.origin_time,
        "known_time": z.known_time,
        "lower": z.lower,
        "upper": z.upper,
        "center": z.center,
        "source_tf": z.source_tf,
        "metadata_json": z.metadata_json,
    } for z in zones])

    raw_contacts = find_first_contacts(bars_mid, zones, bars_mid["sigma60"], cfg)
    canonical_stacks = collapse_contact_events(raw_contacts, cfg.stack_overlap_threshold)
    audit_stacks, membership = collapse_with_membership(raw_contacts, cfg.stack_overlap_threshold)
    stack_parity = assert_stack_parity(canonical_stacks, audit_stacks)
    if not stack_parity["pass"]:
        (out / f"parity_{year}.json").write_text(json.dumps({"year": year, "stack_parity": stack_parity, "pass": False}, indent=2))
        raise SystemExit("audit stack implementation failed canonical parity")

    contacts = label_contacts(bars_mid, canonical_stacks, cfg)
    contacts = classify_behavior_v2(bars_mid, contacts, cfg)
    if not contacts.empty:
        ct = pd.to_datetime(contacts["contact_time"], utc=True)
        contacts = contacts[(ct >= start) & (ct < end)].copy()

    sf = contacts.get("constituent_families", pd.Series("", index=contacts.index)).fillna("")
    masks = {f: sf.str.contains(f'"{f}"', regex=False) for f in FAMILIES}
    core_mask = masks["DISPLACEMENT_ORIGIN"] & masks["OBJECTIVE_LIQUIDITY"] & ~masks["MEMORY"] & ~masks["FVG"]
    core_contacts = contacts[core_mask].copy()

    member_meta = membership.merge(zdf, left_on="member_zone_id", right_on="zone_id", how="left", validate="many_to_one")
    if member_meta["family"].isna().any():
        raise RuntimeError("untraceable stack member zone metadata")
    members_by_stack = {sid: g.copy() for sid, g in member_meta.groupby("stack_id", sort=False)}

    records = []
    scenario_event_ids = {}
    for scenario, sc in SCENARIOS.items():
        bars_exec = apply_fixed_spread_overlay(bars_mid, sc["spread_usd"])
        scenario_ids = []
        for _, rec in core_contacts.iterrows():
            recd = rec.to_dict()
            entry = build_entry(recd, bars_exec, "CLEAN_REJECTION", acceptance_minutes=cfg.acceptance_minutes)
            if entry is None:
                continue
            event_id = stable_event_id(year, rec)
            scenario_ids.append(event_id)
            sid = str(rec["stack_id"])
            members = members_by_stack.get(sid)
            if members is None or members.empty:
                raise RuntimeError(f"missing members for {sid}")
            doz = anchor_record(members, "DISPLACEMENT_ORIGIN")
            obj = anchor_record(members, "OBJECTIVE_LIQUIDITY")
            if doz is None or obj is None:
                raise RuntimeError(f"core event lacks required family member {sid}")

            contact_idx = int(rec["contact_idx"])
            confirm_idx = int(entry["confirm_idx"])
            entry_idx = int(entry["entry_idx"])
            contact_time = bars_mid.index[contact_idx]
            confirm_time = bars_mid.index[confirm_idx]
            entry_time = bars_mid.index[entry_idx]

            doz_origin = pd.Timestamp(doz["origin_time"])
            doz_known = pd.Timestamp(doz["known_time"])
            obj_origin = pd.Timestamp(obj["origin_time"])
            obj_known = pd.Timestamp(obj["known_time"])
            structural_age_h = (contact_time - doz_origin).total_seconds() / 3600.0
            tradable_age_h = (contact_time - doz_known).total_seconds() / 3600.0
            entry_age_h = (entry_time - doz_known).total_seconds() / 3600.0
            tfm = tf_minutes(str(doz["source_tf"]))
            age_bars = tradable_age_h * 60.0 / tfm if np.isfinite(tfm) and tfm > 0 else np.nan

            doz_members = members[members["family"] == "DISPLACEMENT_ORIGIN"]
            obj_members = members[members["family"] == "OBJECTIVE_LIQUIDITY"]
            base = {
                "event_id": event_id,
                "source_year": year,
                "stack_id": sid,
                "zone_id": str(rec["zone_id"]),
                "contact_trading_date": str(trading_day_key(contact_time, cfg.timezone)),
                "entry_trading_date": str(trading_day_key(entry_time, cfg.timezone)),
                "contact_idx": contact_idx,
                "confirm_idx": confirm_idx,
                "entry_idx": entry_idx,
                "contact_time": contact_time.isoformat(),
                "confirmation_time": confirm_time.isoformat(),
                "entry_time": entry_time.isoformat(),
                "direction": str(entry["direction"]),
                "representative_lower": float(rec["lower"]),
                "representative_upper": float(rec["upper"]),
                "representative_center": float(rec["center"]),
                "constituent_count": int(rec["constituent_count"]),
                "constituent_zone_ids": canonical_json_list(members["zone_id"]),
                "constituent_families": str(rec["constituent_families"]),
                "constituent_variants": str(rec["constituent_variants"]),
                "doz_zone_ids": canonical_json_list(doz_members["zone_id"]),
                "doz_source_timeframes": canonical_json_list(doz_members["source_tf"]),
                "doz_variants": canonical_json_list(doz_members["variant"]),
                "objective_zone_ids": canonical_json_list(obj_members["zone_id"]),
                "objective_variants": canonical_json_list(obj_members["variant"]),
                "doz_anchor_zone_id": str(doz["zone_id"]),
                "doz_anchor_variant": str(doz["variant"]),
                "doz_anchor_source_tf": str(doz["source_tf"]),
                "doz_anchor_origin_time": doz_origin.isoformat(),
                "doz_anchor_known_time": doz_known.isoformat(),
                "doz_origin_session": sess(doz_origin, cfg),
                "doz_activation_session": sess(doz_known, cfg),
                "doz_structural_age_hours": float(structural_age_h),
                "doz_tradable_age_hours": float(tradable_age_h),
                "doz_entry_age_hours": float(entry_age_h),
                "doz_tradable_age_source_bars": float(age_bars),
                "doz_tradable_age_bucket": age_bucket(tradable_age_h),
                "objective_anchor_zone_id": str(obj["zone_id"]),
                "objective_anchor_variant": str(obj["variant"]),
                "objective_anchor_source_tf": str(obj["source_tf"]),
                "objective_anchor_origin_time": obj_origin.isoformat(),
                "objective_anchor_known_time": obj_known.isoformat(),
                "objective_origin_session": sess(obj_origin, cfg),
                "objective_activation_session": sess(obj_known, cfg),
                "contact_session": sess(contact_time, cfg),
                "confirmation_session": sess(confirm_time, cfg),
                "entry_session": sess(entry_time, cfg),
                "entry_price": float(entry["entry_price"]),
                "stop_price": float(entry["stop_price"]),
                "risk_price": float(entry["risk_price"]),
                "entry_delay_minutes": int(entry["entry_delay_minutes"]),
                "scenario": scenario,
                "scenario_role": sc["role"],
                "spread_usd": float(sc["spread_usd"]),
                "commission_rt_usd": float(sc["commission_rt_usd"]),
                "annual_input_sha256": input_sha,
                "audit_runtime_commit": runtime_commit,
                "canonical_runner_source_commit": "6efa3789458a6584054fb3ee923dfccca2e15e9d",
            }
            for rr in TARGET_RS:
                sim = simulate_one(entry, bars_exec, rr, horizon_minutes=120,
                                   commission_rt_per_lot=float(sc["commission_rt_usd"]))
                exit_idx = int(sim["exit_idx"])
                exit_time = bars_mid.index[exit_idx]
                target_price = float(entry["entry_price"] + (rr * entry["risk_price"] if entry["direction"] == "LONG" else -rr * entry["risk_price"]))
                records.append({
                    **base,
                    "target_r": float(rr),
                    "target_price": target_price,
                    "exit_idx": exit_idx,
                    "exit_time": exit_time.isoformat(),
                    "exit_session": sess(exit_time, cfg),
                    "exit_price": float(sim["exit_price"]),
                    "gross_R": float(sim["gross_R"]),
                    "net_R": float(sim["net_R_legacy22"]),
                    "result": str(sim["result"]),
                    "ambiguous_same_bar": bool(sim["ambiguous_same_bar"]),
                })
        scenario_event_ids[scenario] = sorted(set(scenario_ids))

    ledger = pd.DataFrame(records)
    if ledger.empty:
        raise RuntimeError("empty core ledger")

    ledger["concurrent_open_positions_before_entry"] = 0
    for (scenario, rr), idxs in ledger.groupby(["scenario", "target_r"], sort=False).groups.items():
        g = ledger.loc[list(idxs)].copy()
        g["_entry"] = pd.to_datetime(g["entry_time"], utc=True)
        g["_exit"] = pd.to_datetime(g["exit_time"], utc=True)
        order = g.sort_values(["_entry", "contact_time", "event_id"], kind="mergesort")
        open_exits = []
        for ridx, row in order.iterrows():
            t = row["_entry"]
            open_exits = [x for x in open_exits if x > t]
            ledger.at[ridx, "concurrent_open_positions_before_entry"] = len(open_exits)
            open_exits.append(row["_exit"])

    ledger = ledger.sort_values(["source_year", "scenario", "target_r", "entry_time", "event_id"], kind="mergesort").reset_index(drop=True)
    ledger_path = out / f"ledger_{year}.csv.gz"
    ledger.to_csv(ledger_path, index=False, compression="gzip")

    annual_parity = compare_annual_summary(ledger, Path(args.expected_annual_summary))
    primary = ledger[ledger["scenario"] == "S11_C6_PRIMARY"]
    rr_sets = {str(rr): sorted(primary[np.isclose(primary["target_r"], rr)]["event_id"].unique()) for rr in TARGET_RS}
    rr_set_equal = all(rr_sets[str(rr)] == rr_sets[str(TARGET_RS[0])] for rr in TARGET_RS[1:])
    scenario_set_equal = all(scenario_event_ids[s] == scenario_event_ids["S11_C6_PRIMARY"] for s in SCENARIOS)
    duplicate_check = int(primary[np.isclose(primary["target_r"], 1.5)]["event_id"].duplicated().sum()) == 0

    parity = {
        "year": year,
        "pass": bool(stack_parity["pass"] and annual_parity["pass"] and rr_set_equal and scenario_set_equal and duplicate_check),
        "stack_parity": stack_parity,
        "annual_summary_parity": annual_parity,
        "rr_event_sets_identical": bool(rr_set_equal),
        "scenario_event_sets_identical": bool(scenario_set_equal),
        "duplicate_event_ids_rr15_primary": int(primary[np.isclose(primary["target_r"], 1.5)]["event_id"].duplicated().sum()),
        "core_entry_events": int(primary[np.isclose(primary["target_r"], 1.5)]["event_id"].nunique()),
        "input_sha256": input_sha,
        "ledger_gzip_sha256": sha256_file(ledger_path),
        "canonical_input_rehydration": True,
        "new_research_market_information": False,
        "new_market_data_spend": 0,
        "source_commit_runtime": runtime_commit,
    }
    (out / f"parity_{year}.json").write_text(json.dumps(parity, indent=2, allow_nan=False))
    print(json.dumps({k: parity[k] for k in ["year", "pass", "core_entry_events", "input_sha256", "ledger_gzip_sha256"]}, indent=2))
    if not parity["pass"]:
        raise SystemExit(f"annual parity failed for {year}")


if __name__ == "__main__":
    main()
