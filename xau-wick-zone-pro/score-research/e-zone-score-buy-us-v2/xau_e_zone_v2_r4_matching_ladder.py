#!/usr/bin/env python3
from __future__ import annotations

"""Outcome-blind R4 feasibility ladder for BUY-US E-zone V2 neutral controls.

R3 was outcome-blind and stopped at D4 with 74.8689% of donor episodes having
>=2 neutral controls, while max |SMD| remained 0.08812.  The R3 selection gate
was frozen at 80%, so it is not retrospectively relaxed.  R4 changes only the
pre-outcome matching density: weekday and upper-Z4 bucket remain soft distance
penalties, the >=10-session separation is retained, the same five numeric
matching variables and neutrality rule are retained, and hard log-volatility /
nearest-upper-Z4 calipers are relaxed in a predeclared ladder.

No future reaction/outcome column is read or generated here.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = "E_ZONE_SCORE_BUY_US_V2_R4_20260830"
MATCH = [
    "trend15_v",
    "trend60_v",
    "trend240_v",
    "nearest_upper_z4_dist_v",
    "log_v_snapshot",
]
# Frozen before opening any V2 reaction outcome.  First admissible design wins.
DESIGNS = [
    {"id": "R4_D5_MINIMAL_DENSE", "logv": 0.65, "z4": 1.25},
    {"id": "R4_D6_MODERATE_DENSE", "logv": 0.80, "z4": 1.50},
    {"id": "R4_D7_BROAD_DENSE", "logv": 1.00, "z4": 2.00},
    {"id": "R4_D8_DISTANCE_ONLY", "logv": None, "z4": None},
]
MIN_SESSION_GAP = 10
WEEKDAY_MISMATCH_PENALTY = 0.10
BUCKET_MISMATCH_PENALTY = 0.25
MAX_CONTROLS = 5
FRACTION_GE2_GATE = 0.80
MAX_ABS_SMD_GATE = 0.10
R3_D4_REFERENCE = {
    "design": "D4_BUCKET_AS_DISTANCE",
    "fraction_ge2": 0.7486888851294198,
    "max_abs_smd": 0.08812080255467425,
    "future_price_outcomes_used": False,
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--features", required=True)
    p.add_argument("--full-pool", required=True)
    p.add_argument("--context", required=True)
    p.add_argument("--output", required=True)
    return p.parse_args()


def read(path):
    d = pd.read_csv(path, compression="infer", float_precision="round_trip")
    for c in ["time", "snapshot_time_utc", "feature_available_time_utc"]:
        if c in d.columns:
            d[c] = pd.to_datetime(d[c], utc=True)
    return d


def smd(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    den = np.sqrt((np.var(a) + np.var(b)) / 2.0)
    delta = float(np.mean(a) - np.mean(b))
    if den <= 0:
        return 0.0 if abs(delta) < 1e-15 else float("inf")
    return float(delta / den)


def tie_hash(eid, recipient_session, design_id):
    return hashlib.sha256(
        f"{SEED}|{design_id}|{eid}|{recipient_session}".encode()
    ).hexdigest()


def exact_tie_order(distances, sessions, eid, design_id):
    """Distance first; SHA256 lexical tie-break only for exact float ties."""
    order = np.argsort(distances, kind="mergesort")
    if len(order) < 2:
        return order
    out = order.copy()
    i = 0
    while i < len(out):
        j = i + 1
        while j < len(out) and distances[out[j]] == distances[out[i]]:
            j += 1
        if j - i > 1:
            block = list(out[i:j])
            block.sort(key=lambda q: tie_hash(eid, str(sessions[q]), design_id))
            out[i:j] = block
        i = j
    return out


def main():
    a = parse_args()
    f = read(a.features)
    pool = read(a.full_pool)
    ctx = read(a.context)
    if not len(f) or not len(ctx):
        raise RuntimeError("R4_EMPTY_FEATURES_OR_CONTEXT")

    forbidden = {
        c for c in list(f.columns) + list(pool.columns) + list(ctx.columns)
        if any(x in c.lower() for x in ["w5", "w15", "w60", "nrb", "mfe", "mae", "outcome", "reaction_label", "win", "loss", "target_hit", "stop_hit"])
    }
    if forbidden:
        raise RuntimeError(f"R4_FORBIDDEN_OUTCOME_COLUMNS_PRESENT {sorted(forbidden)}")

    f["log_v_snapshot"] = np.log(f.v_snapshot.astype(float))
    ctx["log_v_snapshot"] = np.log(ctx.v_snapshot.astype(float))
    ctx = (
        ctx.sort_values(["session_date_ny", "minute_of_session", "time"])
        .drop_duplicates(["session_date_ny", "minute_of_session"], keep="last")
        .reset_index(drop=True)
    )

    sessions = sorted(ctx.session_date_ny.astype(str).unique())
    sess_idx = {s: i for i, s in enumerate(sessions)}
    ctx["_session"] = ctx.session_date_ny.astype(str)
    ctx["_sess_idx"] = ctx["_session"].map(sess_idx).astype(int)

    # Numeric normalization is entirely outcome-blind and frozen over context.
    stats = {}
    for c in MATCH:
        x = pd.to_numeric(ctx[c], errors="raise").to_numpy(float)
        mu = float(np.mean(x))
        sd = float(np.std(x, ddof=0))
        stats[c] = (mu, sd if np.isfinite(sd) and sd > 0 else 1.0)
        ctx[f"_z_{c}"] = (x - mu) / stats[c][1]

    by_min = {}
    for minute, g in ctx.groupby("minute_of_session", sort=False):
        gg = g.reset_index(drop=True)
        by_min[int(minute)] = {
            "session": gg["_session"].to_numpy(object),
            "sess_idx": gg["_sess_idx"].to_numpy(int),
            "weekday": gg.weekday_ny.astype(str).to_numpy(object),
            "bucket": gg.upper_z4_count_bucket.astype(str).to_numpy(object),
            "logv": gg.log_v_snapshot.to_numpy(float),
            "z4": gg.nearest_upper_z4_dist_v.to_numpy(float),
            "zmatch": np.column_stack([gg[f"_z_{c}"].to_numpy(float) for c in MATCH]),
        }

    # Fast random-access context and real-pool geometry for path neutrality.
    ctx_key = {
        (str(r.session_date_ny), int(r.minute_of_session)): r
        for _, r in ctx.iterrows()
    }
    pool_by = {}
    for t, g in pool.groupby("time", sort=False):
        pool_by[pd.Timestamp(t)] = (
            g.zlo.to_numpy(float),
            g.zhi.to_numpy(float),
            g.center.to_numpy(float),
        )

    starts = (
        f.sort_values(["display_episode_id", "snapshot_time_utc"])
        .groupby("display_episode_id", sort=False)
        .first()
        .reset_index()
    )
    paths = {}
    for eid, g in f.groupby("display_episode_id", sort=False):
        gg = g.sort_values("snapshot_time_utc")
        first_t = pd.Timestamp(gg.snapshot_time_utc.iloc[0])
        paths[str(eid)] = [
            (
                int(round((pd.Timestamp(r.snapshot_time_utc) - first_t).total_seconds() / 300.0)),
                float(r.distance_v),
                float(r.center),
                float(r.zlo),
                float(r.zhi),
                float(r.v_snapshot),
            )
            for _, r in gg.iterrows()
        ]

    reports = []
    chosen = None

    for des in DESIGNS:
        selected_counts = np.zeros(len(starts), dtype=int)
        path_lengths = []
        donor_vals = {c: [] for c in MATCH}
        recipient_vals = {c: [] for c in MATCH}

        for ix, d0 in starts.iterrows():
            eid = str(d0.display_episode_id)
            donor_session = str(d0.session_date_ny)
            donor_si = sess_idx[donor_session]
            minute = int(d0.minute_of_session)
            base = by_min.get(minute)
            if base is None:
                continue

            mask = np.abs(base["sess_idx"] - donor_si) >= MIN_SESSION_GAP
            mask &= base["session"] != donor_session
            if des["logv"] is not None:
                mask &= np.abs(base["logv"] - float(d0.log_v_snapshot)) <= float(des["logv"])
            if des["z4"] is not None:
                mask &= np.abs(base["z4"] - float(d0.nearest_upper_z4_dist_v)) <= float(des["z4"])
            cand_idx = np.flatnonzero(mask)
            if not len(cand_idx):
                continue

            dz = np.asarray([
                (float(d0[c]) - stats[c][0]) / stats[c][1] for c in MATCH
            ], dtype=float)
            dist = np.sum((base["zmatch"][cand_idx] - dz) ** 2, axis=1)
            dist += (base["bucket"][cand_idx] != str(d0.upper_z4_count_bucket)).astype(float) * BUCKET_MISMATCH_PENALTY
            dist += (base["weekday"][cand_idx] != str(d0.weekday_ny)).astype(float) * WEEKDAY_MISMATCH_PENALTY
            local_order = exact_tie_order(
                dist,
                base["session"][cand_idx],
                eid,
                des["id"],
            )

            selected = 0
            donor_path = paths[eid]
            for qq in local_order:
                if selected >= MAX_CONTROLS:
                    break
                ci = cand_idx[int(qq)]
                recipient_session = str(base["session"][ci])
                retained = 0
                first_rr = None

                for off, distance_v, center0, zlo0, zhi0, v0 in donor_path:
                    target_minute = minute + off * 5
                    rr = ctx_key.get((recipient_session, target_minute))
                    if rr is None:
                        break
                    rv = float(rr.v_snapshot)
                    center = float(rr.close) - distance_v * rv
                    zlo = center - ((center0 - zlo0) / v0) * rv
                    zhi = center + ((zhi0 - center0) / v0) * rv
                    pg = pool_by.get(pd.Timestamp(rr.time))
                    if pg is not None:
                        plo, phi, pc = pg
                        overlap = bool(np.any(np.minimum(zhi, phi) >= np.maximum(zlo, plo)))
                        near = bool(np.any(np.abs(pc - center) <= 0.20 * rv))
                        if overlap or near:
                            break
                    if first_rr is None:
                        first_rr = rr
                    retained += 1

                if retained <= 0 or first_rr is None:
                    continue

                selected += 1
                path_lengths.append(retained)
                for c in MATCH:
                    donor_vals[c].append(float(d0[c]))
                    recipient_vals[c].append(float(first_rr[c]))

            selected_counts[ix] = selected

        balance = {
            c: smd(donor_vals[c], recipient_vals[c])
            for c in MATCH if len(donor_vals[c])
        }
        frac2 = float(np.mean(selected_counts >= 2))
        frac5 = float(np.mean(selected_counts >= 5))
        max_abs_smd = max((abs(v) for v in balance.values()), default=float("inf"))
        feasible = bool(frac2 >= FRACTION_GE2_GATE and max_abs_smd <= MAX_ABS_SMD_GATE)
        report = {
            "design": {
                **des,
                "weekday_exact": False,
                "bucket_exact": False,
                "weekday_mismatch_penalty": WEEKDAY_MISMATCH_PENALTY,
                "bucket_mismatch_penalty": BUCKET_MISMATCH_PENALTY,
                "min_session_gap": MIN_SESSION_GAP,
                "max_controls": MAX_CONTROLS,
            },
            "donor_episodes": int(len(selected_counts)),
            "controls": int(selected_counts.sum()),
            "donors_ge2": int(np.sum(selected_counts >= 2)),
            "fraction_ge2": frac2,
            "donors_with_5": int(np.sum(selected_counts >= 5)),
            "fraction_with_5": frac5,
            "median_controls": float(np.median(selected_counts)),
            "median_retained_path_snapshots": float(np.median(path_lengths)) if path_lengths else None,
            "balance_smd": balance,
            "max_abs_smd": float(max_abs_smd),
            "preoutcome_feasibility_pass": feasible,
        }
        reports.append(report)
        print(json.dumps(report, sort_keys=True), flush=True)
        if feasible:
            chosen = report["design"]
            break

    out = {
        "status": "V2_R4_MATCHING_LADDER_OUTCOME_BLIND_COMPLETE",
        "future_price_outcomes_used": False,
        "forbidden_outcome_columns_present": False,
        "r3_d4_reference": R3_D4_REFERENCE,
        "r3_gate_not_retroactively_relaxed": True,
        "selection_rule": "first predeclared R4 design with fraction donors >=2 controls >=0.80 and max absolute numeric context SMD <=0.10",
        "matching_variables": MATCH,
        "neutrality_rule": "same R2/R3 causal full-pool overlap or center-within-0.20v exclusion; donor path truncates before first conflict",
        "chosen_design": chosen,
        "designs_evaluated": reports,
    }
    Path(a.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"chosen_design": chosen, "status": out["status"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
