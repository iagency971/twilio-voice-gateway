#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

SCENARIOS = ["S10_C6", "S11_C6_PRIMARY", "S12_C6", "S18_C9_STRESS"]
TARGET_RS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
PRIMARY = "S11_C6_PRIMARY"
STRESS = "S18_C9_STRESS"
EXPECTED_N = 498
EXPECTED_LEDGER_ROWS = EXPECTED_N * len(SCENARIOS) * len(TARGET_RS)
EXPECTED_PROTOCOL_SHA256 = "f72ec721c1fd754140dec9aba46173ee6f7b42873b8a7553470a14e382314eda"
EXPECTED_HUMAN_SHA256 = "0cae1aa3b2c086311d65a3520ddd35afcdf3edfe7b2c55f6cd8b5cdfea80dd13"
EXPECTED_AUTH_SHA256 = "0e6b6aad964d237786ff463c849f4ceeed27803d31c7aafcd6680834994e7f3c"
EXPECTED_FREEZE_SHA256 = "7a46a6847e8b574afa3576714349dbeaa8ec4d7ae2b1a39f4356a03e68fa4197"
EXPECTED_EVENT_SHA256 = "39ed2f7eac7465d46344bef85d64d3b897f0b56af66448e537fba1bfff315aeb"
ZERO_FIELDS = [
    "all_zone_information_time_violations",
    "m1_formation_bar_contact_violations",
    "memory_prefix_invariance_violations",
    "zone_width_information_violations",
    "entry_open_quote_causality_violations",
    "doz_provenance_violations",
    "event_doz_provenance_violations",
    "prefix_invariance_violations",
    "timing_integrity_violations",
    "duplicate_event_ids",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def pf(values) -> float:
    x = pd.to_numeric(pd.Series(values), errors="coerce").dropna().to_numpy(float)
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg <= 0:
        return float("inf") if pos > 0 else float("nan")
    return pos / neg


def cell(ledger: pd.DataFrame, scenario: str, rr: float) -> pd.DataFrame:
    return ledger[(ledger["scenario"].astype(str) == scenario) & np.isclose(pd.to_numeric(ledger["target_r"]), rr)].copy()


def date_cluster_bootstrap(g: pd.DataFrame, counts: np.ndarray, dates: list[str]) -> dict:
    d = g.groupby(g["entry_trading_date"].astype(str))["net_R"].agg(["size", "sum"]).reindex(dates, fill_value=0)
    n = d["size"].to_numpy(float)
    s = d["sum"].to_numpy(float)
    draw_n = counts @ n
    draw_s = counts @ s
    means = np.divide(draw_s, draw_n, out=np.full_like(draw_s, np.nan, dtype=float), where=draw_n > 0)
    return {
        "ci95_lower": float(np.nanpercentile(means, 2.5)),
        "ci95_upper": float(np.nanpercentile(means, 97.5)),
        "prob_mean_gt_0": float(np.nanmean(means > 0)),
    }


def surface_table(ledger: pd.DataFrame, scenario: str) -> pd.DataFrame:
    g = ledger[ledger["scenario"].astype(str) == scenario].copy()
    piv = g.pivot(index=["event_id", "entry_trading_date", "source_year"], columns="target_r", values="net_R")
    missing = [r for r in TARGET_RS if r not in piv.columns]
    if missing:
        raise RuntimeError(f"missing RR surface {scenario}: {missing}")
    piv = piv[list(TARGET_RS)]
    if piv.isna().any().any():
        raise RuntimeError(f"NA RR surface {scenario}")
    return piv.mean(axis=1).rename("surface_net_R").reset_index()


def moving_block_diagnostic(ledger: pd.DataFrame) -> pd.DataFrame:
    months = pd.period_range("2011-01", "2025-12", freq="M").astype(str).tolist()
    M = len(months)
    block = 3
    draws = 20000
    rng = np.random.default_rng(20260822)
    starts = rng.integers(0, M, size=(draws, math.ceil(M / block)))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % M
    idx = idx.reshape(draws, -1)[:, :M]
    rows = []
    for scenario in (PRIMARY, STRESS):
        for rr in TARGET_RS:
            g = cell(ledger, scenario, rr).copy()
            g["month"] = pd.to_datetime(g["entry_time"], utc=True).dt.tz_convert(None).dt.to_period("M").astype(str)
            m = g.groupby("month")["net_R"].sum().reindex(months, fill_value=0.0).to_numpy(float)
            dm = m[idx].mean(axis=1)
            rows.append({
                "scenario": scenario,
                "target_r": rr,
                "months": M,
                "block_months": block,
                "draws": draws,
                "seed": 20260822,
                "observed_mean_monthly_R": float(m.mean()),
                "ci95_lower_mean_monthly_R": float(np.percentile(dm, 2.5)),
                "ci95_upper_mean_monthly_R": float(np.percentile(dm, 97.5)),
            })
    return pd.DataFrame(rows)


def max_drawdown_and_streak(g: pd.DataFrame) -> dict:
    h = g.copy()
    h["_entry"] = pd.to_datetime(h["entry_time"], utc=True)
    h["_confluence"] = pd.to_datetime(h["confluence_time"], utc=True)
    h = h.sort_values(["_entry", "_confluence", "event_id"], kind="mergesort")
    vals = pd.to_numeric(h["net_R"]).to_numpy(float)
    curve = np.r_[0.0, np.cumsum(vals)]
    peaks = np.maximum.accumulate(curve)
    maxdd = float(np.max(peaks - curve))
    streak = 0
    best = 0
    for v in vals:
        if v < 0:
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return {"max_drawdown_R": maxdd, "longest_losing_streak": int(best)}


def concentration(g: pd.DataFrame) -> dict:
    h = g.copy()
    h["_entry"] = pd.to_datetime(h["entry_time"], utc=True)
    h = h.sort_values(["net_R", "_entry", "event_id"], ascending=[False, True, True], kind="mergesort").reset_index(drop=True)
    vals = pd.to_numeric(h["net_R"]).to_numpy(float)
    n = len(vals)
    pos = float(vals[vals > 0].sum())
    out = {}
    for frac in (0.01, 0.05, 0.10):
        k = max(1, int(math.ceil(n * frac)))
        top = float(vals[:k].sum())
        out[f"best_{int(frac * 100)}pct_trades"] = k
        out[f"best_{int(frac * 100)}pct_sum_R"] = top
        out[f"best_{int(frac * 100)}pct_share_total_positive_R"] = float(top / pos) if pos > 0 else float("nan")
        if frac == 0.05:
            remain = vals[k:]
            out["mean_net_R_after_removing_best_5pct"] = float(remain.mean()) if len(remain) else float("nan")
            out["pf_after_removing_best_5pct"] = float(pf(remain)) if len(remain) else float("nan")
    return out


def single_position(g: pd.DataFrame) -> dict:
    h = g.copy()
    h["_entry"] = pd.to_datetime(h["entry_time"], utc=True)
    h["_exit"] = pd.to_datetime(h["exit_time"], utc=True)
    h["_confluence"] = pd.to_datetime(h["confluence_time"], utc=True)
    h = h.sort_values(["_entry", "_confluence", "event_id"], kind="mergesort")
    selected = []
    active_exit = None
    same_minute = 0
    for _, r in h.iterrows():
        et = r["_entry"]
        if active_exit is not None and et <= active_exit:
            if et == active_exit:
                same_minute += 1
            continue
        selected.append(r)
        active_exit = r["_exit"]
    x = pd.DataFrame(selected)
    vals = pd.to_numeric(x["net_R"]).to_numpy(float) if len(x) else np.array([], dtype=float)
    return {
        "independent_trades": int(len(h)),
        "selected_trades": int(len(x)),
        "skipped_overlapping_entries": int(len(h) - len(x)),
        "same_minute_exit_entry_skips": int(same_minute),
        "mean_net_R": float(np.mean(vals)) if len(vals) else float("nan"),
        "sum_net_R": float(np.sum(vals)) if len(vals) else float("nan"),
        "pf_net": float(pf(vals)) if len(vals) else float("nan"),
        "unresolved_sequencing_ambiguity": False,
    }


def json_safe(v):
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, (np.integer, int)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        if not np.isfinite(float(v)):
            return None
        return float(v)
    return v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--freeze-manifest", required=True)
    ap.add_argument("--event-manifest", required=True)
    ap.add_argument("--support-result", required=True)
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--human-protocol", required=True)
    ap.add_argument("--authorization", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.root)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    freeze_p = Path(args.freeze_manifest)
    event_p = Path(args.event_manifest)
    support_p = Path(args.support_result)
    protocol_p = Path(args.protocol)
    human_p = Path(args.human_protocol)
    auth_p = Path(args.authorization)

    binding_checks = {
        "freeze_sha": sha256_file(freeze_p) == EXPECTED_FREEZE_SHA256,
        "event_sha": sha256_file(event_p) == EXPECTED_EVENT_SHA256,
        "protocol_sha": sha256_file(protocol_p) == EXPECTED_PROTOCOL_SHA256,
        "human_protocol_sha": sha256_file(human_p) == EXPECTED_HUMAN_SHA256,
        "authorization_sha": sha256_file(auth_p) == EXPECTED_AUTH_SHA256,
    }
    freeze = json.load(freeze_p.open())
    support = json.load(support_p.open())
    auth = json.load(auth_p.open())
    binding_checks.update({
        "freeze_status": freeze.get("status") == "CAUSAL_CORE_PREOUTCOME_FULL_M1_INFORMATION_SET_READY_FOR_PNL",
        "support_gate": bool(support.get("support_gate_pass")),
        "support_status": support.get("status") == "CAUSAL_CORE_PREOUTCOME_FULL_M1_INFORMATION_SET_READY_FOR_PNL",
        "authorization_status": auth.get("status") == "CAUSAL_CORE_OUTCOME_V1_1_AUTHORIZED",
        "event_rows": int(freeze["event_manifest"]["rows"]) == EXPECTED_N,
        "shuffle_identity": bool(support.get("shuffle_identity_all_pass")),
    })
    for f in ZERO_FIELDS:
        binding_checks[f"{f}_zero"] = int(support.get(f, -1)) == 0
    if not all(binding_checks.values()):
        bad = [k for k, v in binding_checks.items() if not v]
        raise RuntimeError(f"GATE_A_BINDING_FAIL {bad}")

    frozen_events = pd.read_csv(event_p)
    if len(frozen_events) != EXPECTED_N or frozen_events["event_id"].duplicated().any():
        raise RuntimeError("frozen event identity failure")
    frozen_ids = set(frozen_events["event_id"].astype(str))

    frames = []
    for y in range(2011, 2026):
        lp = root / f"causal_core_outcome_v1_1_ledger_{y}.csv.gz"
        sp = root / f"causal_core_outcome_v1_1_summary_{y}.json"
        if not lp.exists() or not sp.exists():
            raise RuntimeError(f"missing annual outcome artifact {y}")
        s = json.load(sp.open())
        fa = next(x for x in freeze["annual_artifacts"] if int(x["year"]) == y)
        if s["input_sha256"] != fa["input_sha256"] or s["annual_event_manifest_sha256"] != fa["event_manifest_sha256"]:
            raise RuntimeError(f"annual binding mismatch {y}")
        if s["protocol_sha256"] != EXPECTED_PROTOCOL_SHA256 or s["freeze_manifest_sha256"] != EXPECTED_FREEZE_SHA256:
            raise RuntimeError(f"annual protocol/freeze mismatch {y}")
        if sha256_file(lp) != s["ledger_sha256"]:
            raise RuntimeError(f"annual ledger hash mismatch {y}")
        frames.append(pd.read_csv(lp))

    ledger = pd.concat(frames, ignore_index=True)
    if len(ledger) != EXPECTED_LEDGER_ROWS:
        raise RuntimeError(f"ledger rows {len(ledger)} != {EXPECTED_LEDGER_ROWS}")

    identity_cells = []
    for scenario in SCENARIOS:
        for rr in TARGET_RS:
            g = cell(ledger, scenario, rr)
            ids = set(g["event_id"].astype(str))
            ok = len(g) == EXPECTED_N and ids == frozen_ids and not g["event_id"].duplicated().any()
            identity_cells.append({"scenario": scenario, "target_r": rr, "N": len(g), "identity_pass": bool(ok)})
            if not ok:
                raise RuntimeError(f"cell identity fail {scenario} {rr}")

    invariant_cols = ["event_id", "confluence_time", "entry_time", "direction", "anchor_lower", "anchor_upper", "sigma60_at_confluence"]
    base = cell(ledger, PRIMARY, 0.5)[invariant_cols].sort_values("event_id").reset_index(drop=True)
    for scenario in SCENARIOS:
        for rr in TARGET_RS:
            g = cell(ledger, scenario, rr)[invariant_cols].sort_values("event_id").reset_index(drop=True)
            if not base.equals(g):
                raise RuntimeError(f"cross-cell invariant mismatch {scenario} {rr}")

    ref = cell(ledger, PRIMARY, 1.5)
    dates = sorted(ref["entry_trading_date"].astype(str).unique())
    D = len(dates)
    rng = np.random.default_rng(20260821)
    counts = rng.multinomial(D, np.full(D, 1.0 / D), size=20000)

    metric_rows = []
    bootstrap_rows = []
    for scenario in SCENARIOS:
        for rr in TARGET_RS:
            g = cell(ledger, scenario, rr)
            b = date_cluster_bootstrap(g, counts, dates)
            metric_rows.append({
                "scenario": scenario,
                "target_r": rr,
                "N": int(len(g)),
                "mean_net_R": float(g["net_R"].mean()),
                "sum_net_R": float(g["net_R"].sum()),
                "pf_net": float(pf(g["net_R"])),
                "TP_pct": 100 * float((g["result"] == "TP").mean()),
                "SL_pct": 100 * float((g["result"] == "SL").mean()),
                "TIME_pct": 100 * float((g["result"] == "TIME").mean()),
                "same_bar_ambiguity_pct": 100 * float(pd.Series(g["ambiguous_same_bar"]).astype(bool).mean()),
                "date_cluster_ci95_lower": b["ci95_lower"],
                "date_cluster_ci95_upper": b["ci95_upper"],
            })
            bootstrap_rows.append({"scenario": scenario, "target_r": rr, "dates": D, "draws": 20000, "seed": 20260821, **b})
    metrics = pd.DataFrame(metric_rows)
    boot = pd.DataFrame(bootstrap_rows)

    surface_rows = []
    for scenario in (PRIMARY, STRESS):
        s = surface_table(ledger, scenario)
        b = date_cluster_bootstrap(s.rename(columns={"surface_net_R": "net_R"}), counts, dates)
        date_equal = float(s.groupby("entry_trading_date")["surface_net_R"].mean().mean())
        surface_rows.append({
            "scenario": scenario,
            "N": len(s),
            "surface_mean_net_R": float(s["surface_net_R"].mean()),
            "date_equal_weight_surface_mean_net_R_diagnostic": date_equal,
            "date_cluster_ci95_lower": b["ci95_lower"],
            "date_cluster_ci95_upper": b["ci95_upper"],
            "draws": 20000,
            "seed": 20260821,
        })
    surface_df = pd.DataFrame(surface_rows)

    annual_rows = []
    loo_rows = []
    temporal_rr = []
    for rr in TARGET_RS:
        row = {"target_r": rr}
        for scenario, prefix in ((PRIMARY, "primary"), (STRESS, "stress")):
            g = cell(ledger, scenario, rr)
            ys = g.groupby("source_year")["net_R"].sum().reindex(range(2011, 2026), fill_value=0.0)
            denom = float(np.abs(ys).sum())
            maxshare = float((np.abs(ys) / denom).max()) if denom > 0 else float("inf")
            positives = int((ys > 0).sum())
            loo_ok = True
            for y in range(2011, 2026):
                h = g[g["source_year"].astype(int) != y]
                m = float(h["net_R"].mean())
                loo_rows.append({
                    "scenario": scenario,
                    "target_r": rr,
                    "left_out_year": y,
                    "N": len(h),
                    "mean_net_R": m,
                    "sum_net_R": float(h["net_R"].sum()),
                    "pf_net": float(pf(h["net_R"])),
                })
                if scenario == PRIMARY and not (m > 0):
                    loo_ok = False
            for y in range(2011, 2026):
                gy = g[g["source_year"].astype(int) == y]
                annual_rows.append({
                    "scenario": scenario,
                    "target_r": rr,
                    "year": y,
                    "N": len(gy),
                    "mean_net_R": float(gy["net_R"].mean()) if len(gy) else np.nan,
                    "sum_net_R": float(gy["net_R"].sum()),
                    "pf_net": float(pf(gy["net_R"])) if len(gy) else np.nan,
                    "abs_annual_contribution_share": float(abs(ys.loc[y]) / denom) if denom > 0 else np.nan,
                })
            row[f"{prefix}_positive_years"] = positives
            row[f"{prefix}_max_abs_annual_share"] = maxshare
            if scenario == PRIMARY:
                row["primary_all_15_loo_positive"] = bool(loo_ok)
        rr_pass = bool(
            row["primary_all_15_loo_positive"]
            and row["primary_positive_years"] >= 10
            and row["stress_positive_years"] >= 8
            and row["primary_max_abs_annual_share"] <= 0.35
            and row["stress_max_abs_annual_share"] <= 0.35
        )
        row["temporal_rr_pass"] = rr_pass
        temporal_rr.append(row)
    temporal_df = pd.DataFrame(temporal_rr)
    annual_df = pd.DataFrame(annual_rows)
    loo_df = pd.DataFrame(loo_rows)

    concentration_rows = []
    dd_rows = []
    replay_rows = []
    for scenario in (PRIMARY, STRESS):
        g = cell(ledger, scenario, 1.5)
        concentration_rows.append({"scenario": scenario, "target_r": 1.5, **concentration(g)})
        dd_rows.append({"scenario": scenario, "target_r": 1.5, **max_drawdown_and_streak(g)})
        replay_rows.append({"scenario": scenario, "target_r": 1.5, **single_position(g)})
    conc_df = pd.DataFrame(concentration_rows)
    dd_df = pd.DataFrame(dd_rows)
    replay_df = pd.DataFrame(replay_rows)

    gateA = True
    pm = metrics[metrics["scenario"].eq(PRIMARY)].set_index("target_r")
    primary_surface = surface_df[surface_df["scenario"].eq(PRIMARY)].iloc[0]
    rr_b_pass = [bool(pm.loc[r, "mean_net_R"] >= 0.10 and pm.loc[r, "pf_net"] >= 1.25 and pm.loc[r, "date_cluster_ci95_lower"] > 0) for r in TARGET_RS]
    gateB = bool(primary_surface["surface_mean_net_R"] >= 0.10 and primary_surface["date_cluster_ci95_lower"] > 0 and sum(rr_b_pass) >= 4)

    sm = metrics[metrics["scenario"].eq(STRESS)].set_index("target_r")
    stress_surface = surface_df[surface_df["scenario"].eq(STRESS)].iloc[0]
    gateC = bool(
        all(sm.loc[r, "mean_net_R"] > 0 for r in TARGET_RS)
        and sum(sm.loc[r, "pf_net"] >= 1.20 for r in TARGET_RS) >= 4
        and stress_surface["surface_mean_net_R"] > 0
    )

    td = temporal_df.set_index("target_r")
    gateD = bool(td.loc[1.5, "temporal_rr_pass"] and int(td["temporal_rr_pass"].sum()) >= 4)

    cp = conc_df.set_index("scenario")
    gateE = bool(all(cp.loc[s, "mean_net_R_after_removing_best_5pct"] > 0 and cp.loc[s, "best_5pct_share_total_positive_R"] <= 0.50 for s in (PRIMARY, STRESS)))

    rp = replay_df.set_index("scenario")
    gateF = bool(
        rp.loc[PRIMARY, "mean_net_R"] > 0
        and rp.loc[PRIMARY, "pf_net"] > 1.10
        and rp.loc[STRESS, "mean_net_R"] >= 0
        and not bool(rp.loc[PRIMARY, "unresolved_sequencing_ambiguity"])
        and not bool(rp.loc[STRESS, "unresolved_sequencing_ambiguity"])
    )

    gates = {
        "A_integrity": gateA,
        "B_primary_broad_rr": gateB,
        "C_stress": gateC,
        "D_temporal": gateD,
        "E_concentration": gateE,
        "F_single_position_portfolio": gateF,
    }
    all_pass = all(gates.values())
    status = "CAUSAL_CORE_OUTCOME_V1_1_PASS_FOR_EXTERNAL_REPLICATION" if all_pass else "CAUSAL_CORE_OUTCOME_V1_1_NO_GO"

    moving = moving_block_diagnostic(ledger)

    ledger_out = out / "causal_core_outcome_v1_1_ledger_2011_2025.csv.gz"
    ledger.sort_values(["source_year", "entry_time", "event_id", "scenario", "target_r"], kind="mergesort").to_csv(
        ledger_out, index=False, compression={"method": "gzip", "mtime": 0}
    )
    metrics.to_csv(out / "cell_metrics.csv", index=False)
    boot.to_csv(out / "date_cluster_bootstrap_summary.csv", index=False)
    surface_df.to_csv(out / "surface_metrics.csv", index=False)
    moving.to_csv(out / "moving_block_bootstrap_summary.csv", index=False)
    annual_df.to_csv(out / "annual_contribution.csv", index=False)
    loo_df.to_csv(out / "leave_one_year_out.csv", index=False)
    temporal_df.to_csv(out / "temporal_gate_by_rr.csv", index=False)
    conc_df.to_csv(out / "concentration_rr15.csv", index=False)
    dd_df.to_csv(out / "drawdown_losing_streak_rr15.csv", index=False)
    replay_df.to_csv(out / "single_position_replay_rr15.csv", index=False)
    pd.DataFrame(identity_cells).to_csv(out / "cell_identity.csv", index=False)

    result = {
        "version": "XAU_CORE_CAUSAL_CONFLUENCE_OUTCOME_RESULT_V1_1",
        "status": status,
        "all_gates_pass": bool(all_pass),
        "gates": gates,
        "primary_endpoint": "CAUSAL_CORE_RR_SURFACE_MEAN_NET_R",
        "primary_surface": {k: json_safe(v) for k, v in primary_surface.to_dict().items()},
        "stress_surface": {k: json_safe(v) for k, v in stress_surface.to_dict().items()},
        "preoutcome_freeze_sha256": EXPECTED_FREEZE_SHA256,
        "event_manifest_sha256": EXPECTED_EVENT_SHA256,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "human_protocol_sha256": EXPECTED_HUMAN_SHA256,
        "authorization_sha256": EXPECTED_AUTH_SHA256,
        "events": EXPECTED_N,
        "ledger_rows": int(len(ledger)),
        "new_market_data_spend": 0,
        "post_outcome_rescue_forbidden": True,
    }
    (out / "outcome_result_v1_1.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")

    files = [p for p in out.iterdir() if p.is_file()]
    manifest = {"version": "XAU_CORE_OUTCOME_V1_1_ARTIFACT_MANIFEST", "status": status, "files": []}
    for p in sorted(files, key=lambda p: p.name):
        manifest["files"].append({"path": p.name, "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    (out / "outcome_artifact_manifest_v1_1.json").write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n")

    ck = f"""# CHECKPOINT — XAU CORE CAUSAL CONFLUENCE OUTCOME V1.1\n\nStatus: **{status}**\n\n- population: **498 events**\n- ledger rows: **{len(ledger)}**\n- primary endpoint: **CAUSAL_CORE_RR_SURFACE_MEAN_NET_R**\n- primary surface mean net R: **{float(primary_surface['surface_mean_net_R']):+.6f}R**\n- primary date-cluster 95% CI: **[{float(primary_surface['date_cluster_ci95_lower']):+.6f}, {float(primary_surface['date_cluster_ci95_upper']):+.6f}]**\n- stress surface mean net R: **{float(stress_surface['surface_mean_net_R']):+.6f}R**\n- gates: `{gates}`\n\nOutcome protocol V1.1 was frozen before any outcome read. No post-outcome subgroup rescue or parameter change is authorized. A PASS authorizes external broker/feed replication and prospective validation only; it is not live-ready. A NO_GO closes this core economically on 2011–2025.\n"""
    (out / "CHECKPOINT_XAU_CORE_CAUSAL_CONFLUENCE_OUTCOME_V1_1.md").write_text(ck)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
