#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

SCENARIOS = ["S10_C6", "S11_C6_PRIMARY", "S12_C6", "S18_C9_STRESS"]
TARGET_RS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
PRIMARY = "S11_C6_PRIMARY"
STRESS = "S18_C9_STRESS"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pf(values) -> float:
    x = pd.to_numeric(pd.Series(values), errors="coerce").dropna().to_numpy(float)
    pos = float(x[x > 0].sum()); neg = float(-x[x < 0].sum())
    if neg <= 0: return float("inf") if pos > 0 else float("nan")
    return pos / neg


def cell(ledger, scenario, rr):
    return ledger[(ledger.scenario == scenario) & np.isclose(ledger.target_r.astype(float), rr)].copy()


def aggregate_metrics(g: pd.DataFrame) -> dict:
    return {
        "trades": int(len(g)),
        "mean_net_R": float(g.net_R.mean()),
        "sum_net_R": float(g.net_R.sum()),
        "pf_net": float(pf(g.net_R)),
        "tp_pct": 100.0 * float((g.result == "TP").mean()),
        "sl_pct": 100.0 * float((g.result == "SL").mean()),
        "time_pct": 100.0 * float((g.result == "TIME").mean()),
    }


def bootstrap_date_clusters(ledger: pd.DataFrame, out: Path):
    ref = cell(ledger, PRIMARY, 1.5)
    dates = sorted(ref.entry_trading_date.astype(str).unique())
    D = len(dates)
    rng = np.random.default_rng(20260821)
    counts = rng.multinomial(D, np.full(D, 1.0 / D), size=20000)
    rows = []
    for scenario in SCENARIOS:
        for rr in TARGET_RS:
            g = cell(ledger, scenario, rr)
            d = g.groupby(g.entry_trading_date.astype(str)).agg(
                n=("net_R", "size"),
                sum_R=("net_R", "sum"),
                pos_R=("net_R", lambda x: float(x[x > 0].sum())),
                neg_R=("net_R", lambda x: float(-x[x < 0].sum())),
            ).reindex(dates, fill_value=0)
            n = d.n.to_numpy(float); sr = d.sum_R.to_numpy(float); ps = d.pos_R.to_numpy(float); ns = d.neg_R.to_numpy(float)
            draw_n = counts @ n; draw_sum = counts @ sr; draw_pos = counts @ ps; draw_neg = counts @ ns
            mean = np.divide(draw_sum, draw_n, out=np.full_like(draw_sum, np.nan), where=draw_n > 0)
            pfr = np.divide(draw_pos, draw_neg, out=np.full_like(draw_pos, np.nan), where=draw_neg > 0)
            rows.append({
                "scenario": scenario, "target_r": rr, "dates": D, "draws": 20000, "seed": 20260821,
                "observed_mean_net_R": float(g.net_R.mean()), "observed_pf_net": float(pf(g.net_R)),
                "mean_ci95_lower": float(np.nanpercentile(mean, 2.5)), "mean_ci95_upper": float(np.nanpercentile(mean, 97.5)),
                "pf_ci95_lower": float(np.nanpercentile(pfr, 2.5)), "pf_ci95_upper": float(np.nanpercentile(pfr, 97.5)),
                "bootstrap_prob_mean_gt_0": float(np.nanmean(mean > 0)),
            })
    df = pd.DataFrame(rows)
    df.to_csv(out / "date_cluster_bootstrap_summary.csv", index=False)
    return df


def moving_block_bootstrap(ledger: pd.DataFrame, out: Path):
    months = pd.period_range("2011-01", "2025-12", freq="M").astype(str).tolist()
    M = len(months); block = 3; draws = 20000
    rng = np.random.default_rng(20260822)
    blocks_needed = math.ceil(M / block)
    starts = rng.integers(0, M, size=(draws, blocks_needed))
    offsets = np.arange(block)
    idx = (starts[:, :, None] + offsets[None, None, :]) % M
    idx = idx.reshape(draws, -1)[:, :M]
    rows = []
    for scenario in (PRIMARY, STRESS):
        for rr in TARGET_RS:
            g = cell(ledger, scenario, rr).copy()
            g["month"] = pd.to_datetime(g.entry_time, utc=True).dt.tz_convert(None).dt.to_period("M").astype(str)
            m = g.groupby("month").net_R.sum().reindex(months, fill_value=0.0).to_numpy(float)
            draws_mean = m[idx].mean(axis=1)
            rows.append({
                "scenario": scenario, "target_r": rr, "months": M, "block_months": block, "draws": draws, "seed": 20260822,
                "observed_mean_monthly_R": float(m.mean()), "observed_annualized_R": float(12 * m.mean()),
                "mean_monthly_R_ci95_lower": float(np.percentile(draws_mean, 2.5)),
                "mean_monthly_R_ci95_upper": float(np.percentile(draws_mean, 97.5)),
                "annualized_R_ci95_lower": float(12 * np.percentile(draws_mean, 2.5)),
                "annualized_R_ci95_upper": float(12 * np.percentile(draws_mean, 97.5)),
            })
    df = pd.DataFrame(rows)
    df.to_csv(out / "moving_block_bootstrap_summary.csv", index=False)
    return df


def temporal_tables(ledger: pd.DataFrame, out: Path):
    loo = []; annual = []
    for scenario in SCENARIOS:
        for rr in TARGET_RS:
            g = cell(ledger, scenario, rr)
            year_sum = g.groupby("source_year").net_R.sum()
            denom = float(np.abs(year_sum).sum())
            for y in sorted(g.source_year.unique()):
                gy = g[g.source_year == y]
                annual.append({
                    "scenario": scenario, "target_r": rr, "year": int(y), "trades": int(len(gy)),
                    "mean_net_R": float(gy.net_R.mean()), "sum_net_R": float(gy.net_R.sum()), "pf_net": float(pf(gy.net_R)),
                    "abs_annual_contribution_share": float(abs(year_sum.loc[y]) / denom) if denom > 0 else np.nan,
                })
                h = g[g.source_year != y]
                loo.append({
                    "scenario": scenario, "target_r": rr, "left_out_year": int(y), "trades": int(len(h)),
                    "mean_net_R": float(h.net_R.mean()), "sum_net_R": float(h.net_R.sum()), "pf_net": float(pf(h.net_R)),
                })
    adf = pd.DataFrame(annual); ldf = pd.DataFrame(loo)
    adf.to_csv(out / "annual_contribution.csv", index=False)
    ldf.to_csv(out / "leave_one_year_out.csv", index=False)
    return adf, ldf


def concentration_and_drawdown(ledger: pd.DataFrame, out: Path):
    conc = []; dd = []
    for scenario in SCENARIOS:
        for rr in TARGET_RS:
            g = cell(ledger, scenario, rr).sort_values(["entry_time", "contact_time", "event_id"], kind="mergesort")
            vals = g.net_R.to_numpy(float); n = len(vals)
            order = np.argsort(vals)[::-1]
            row = {"scenario": scenario, "target_r": rr, "trades": n, "mean_net_R": float(np.mean(vals)), "pf_net": float(pf(vals))}
            for pct in (0.01, 0.05, 0.10):
                k = max(1, int(math.ceil(n * pct)))
                top = vals[order[:k]]
                row[f"best_{int(pct*100)}pct_trades"] = k
                row[f"best_{int(pct*100)}pct_sum_R"] = float(top.sum())
                row[f"best_{int(pct*100)}pct_share_total_positive_R"] = float(top.sum() / vals[vals > 0].sum()) if vals[vals > 0].sum() > 0 else np.nan
                if pct == 0.05:
                    keep = np.ones(n, dtype=bool); keep[order[:k]] = False
                    row["mean_net_R_after_removing_best_5pct"] = float(vals[keep].mean()) if keep.any() else np.nan
                    row["pf_after_removing_best_5pct"] = float(pf(vals[keep])) if keep.any() else np.nan
            conc.append(row)

            curve = np.cumsum(vals); peaks = np.maximum.accumulate(np.r_[0.0, curve]); curve0 = np.r_[0.0, curve]
            drawdowns = peaks - curve0
            maxdd = float(np.max(drawdowns))
            streak = 0; maxstreak = 0
            for v in vals:
                if v < 0: streak += 1; maxstreak = max(maxstreak, streak)
                else: streak = 0
            dd.append({
                "scenario": scenario, "target_r": rr, "trades": n, "sum_net_R": float(vals.sum()),
                "max_drawdown_R": maxdd, "longest_losing_streak": int(maxstreak),
                "ambiguous_same_bar_pct": 100.0 * float(g.ambiguous_same_bar.mean()),
                "min_risk_price": float(g.risk_price.min()), "median_risk_price": float(g.risk_price.median()),
            })
    cdf = pd.DataFrame(conc); ddf = pd.DataFrame(dd)
    cdf.to_csv(out / "concentration_stress.csv", index=False)
    ddf.to_csv(out / "drawdown_losing_streak.csv", index=False)
    return cdf, ddf


def concurrency_and_replay(ledger: pd.DataFrame, out: Path):
    concells = []; replay = []
    for scenario in SCENARIOS:
        for rr in TARGET_RS:
            g = cell(ledger, scenario, rr).copy()
            g["_entry"] = pd.to_datetime(g.entry_time, utc=True); g["_exit"] = pd.to_datetime(g.exit_time, utc=True); g["_contact"] = pd.to_datetime(g.contact_time, utc=True)
            g = g.sort_values(["_entry", "_contact", "event_id"], kind="mergesort")
            before = g.concurrent_open_positions_before_entry.astype(int)
            concells.append({
                "scenario": scenario, "target_r": rr, "trades": int(len(g)),
                "entries_while_other_position_open": int((before > 0).sum()),
                "pct_entries_while_other_position_open": 100.0 * float((before > 0).mean()),
                "max_concurrent_positions_at_entry": int(before.max() + 1 if len(before) else 0),
            })
            active_exit = None; selected = []; same_minute_skips = 0
            for _, r in g.iterrows():
                et = r["_entry"]
                if active_exit is not None and et <= active_exit:
                    if et == active_exit: same_minute_skips += 1
                    continue
                selected.append(r)
                active_exit = r["_exit"]
            h = pd.DataFrame(selected)
            replay.append({
                "scenario": scenario, "target_r": rr, "independent_trades": int(len(g)), "selected_trades": int(len(h)),
                "skipped_overlapping_entries": int(len(g) - len(h)), "same_minute_exit_entry_skips": int(same_minute_skips),
                "mean_net_R": float(h.net_R.mean()) if len(h) else np.nan, "sum_net_R": float(h.net_R.sum()) if len(h) else np.nan,
                "pf_net": float(pf(h.net_R)) if len(h) else np.nan, "sequencing_rule": "entry_time then contact_time then event_id; require next entry_time > active exit_time",
                "unresolved_sequencing_ambiguity": False,
            })
    cdf = pd.DataFrame(concells); rdf = pd.DataFrame(replay)
    (out / "concurrency_report.json").write_text(json.dumps({"cells": cdf.to_dict("records")}, indent=2, allow_nan=False))
    rdf.to_csv(out / "single_position_replay.csv", index=False)
    return cdf, rdf


def subgroup_metrics(g: pd.DataFrame):
    years = g.groupby("source_year").net_R.sum() if len(g) else pd.Series(dtype=float)
    return {
        "trades": int(len(g)), "mean_net_R": float(g.net_R.mean()) if len(g) else np.nan,
        "sum_net_R": float(g.net_R.sum()) if len(g) else np.nan, "pf_net": float(pf(g.net_R)) if len(g) else np.nan,
        "tp_pct": 100.0 * float((g.result == "TP").mean()) if len(g) else np.nan,
        "positive_years": int((years > 0).sum()), "active_years": int(len(years)),
    }


def diagnostics(ledger: pd.DataFrame, out: Path):
    dimensions = [
        "direction", "contact_session", "confirmation_session", "entry_session", "exit_session",
        "doz_anchor_source_tf", "doz_anchor_variant", "objective_anchor_variant", "doz_tradable_age_bucket",
    ]
    rows = []
    for scenario in SCENARIOS:
        for rr in TARGET_RS:
            base = cell(ledger, scenario, rr)
            for dim in dimensions:
                for key, g in base.groupby(dim, dropna=False, sort=True):
                    rows.append({"scenario": scenario, "target_r": rr, "dimension": dim, "group": str(key), **subgroup_metrics(g)})
    ddf = pd.DataFrame(rows)
    ddf.to_csv(out / "diagnostic_subgroups.csv", index=False)

    transitions = [
        ("doz_origin_to_contact", "doz_origin_session", "contact_session"),
        ("doz_activation_to_contact", "doz_activation_session", "contact_session"),
        ("doz_activation_to_entry", "doz_activation_session", "entry_session"),
        ("doz_origin_to_entry", "doz_origin_session", "entry_session"),
        ("objective_activation_to_contact", "objective_activation_session", "contact_session"),
        ("objective_activation_to_entry", "objective_activation_session", "entry_session"),
    ]
    trows = []
    for scenario in SCENARIOS:
        for rr in TARGET_RS:
            base = cell(ledger, scenario, rr)
            for name, a, b in transitions:
                for (fa, tb), g in base.groupby([a, b], dropna=False, sort=True):
                    trows.append({"scenario": scenario, "target_r": rr, "transition": name, "from_session": str(fa), "to_session": str(tb), **subgroup_metrics(g)})
    tdf = pd.DataFrame(trows); tdf.to_csv(out / "session_transition_diagnostics.csv", index=False)

    arows = []
    for scenario in SCENARIOS:
        for rr in TARGET_RS:
            g = cell(ledger, scenario, rr)
            age = pd.to_numeric(g.doz_tradable_age_hours, errors="coerce")
            rank_age = age.rank(method="average"); rank_r = g.net_R.rank(method="average")
            arows.append({
                "scenario": scenario, "target_r": rr, "trades": int(len(g)),
                "age_hours_min": float(age.min()), "age_hours_q25": float(age.quantile(.25)), "age_hours_median": float(age.median()),
                "age_hours_q75": float(age.quantile(.75)), "age_hours_max": float(age.max()),
                "spearman_age_vs_net_R": float(rank_age.corr(rank_r)),
            })
    adf = pd.DataFrame(arows); adf.to_csv(out / "zone_age_diagnostics.csv", index=False)
    return ddf, tdf, adf


def aggregate_parity(ledger: pd.DataFrame, survivors_path: Path, annual_parities):
    exp = pd.read_csv(survivors_path)
    exp = exp[(exp["sample"] == "DOZ_OBJECTIVE_ONLY") & (exp["entry_model"] == "CLEAN_REJECTION") & (exp["risk_rule"] == "STRUCTURAL")]
    primary_rr15 = cell(ledger, PRIMARY, 1.5)
    event_sets = {}
    for s in SCENARIOS:
        for rr in TARGET_RS:
            event_sets[f"{s}:{rr}"] = sorted(cell(ledger, s, rr).event_id.unique())
    refset = event_sets[f"{PRIMARY}:1.5"]
    same_sets = all(v == refset for v in event_sets.values())
    checks = []
    ok = all(p.get("pass", False) for p in annual_parities) and len(refset) == 304 and same_sets and not primary_rr15.event_id.duplicated().any()
    for rr in TARGET_RS:
        e = exp[np.isclose(exp.target_r.astype(float), rr)]
        if len(e) != 1:
            checks.append({"target_r": rr, "pass": False, "reason": "survivor row missing/not unique"}); ok = False; continue
        e = e.iloc[0]; gp = cell(ledger, PRIMARY, rr); gs = cell(ledger, STRESS, rr)
        py = gp.groupby("source_year").net_R.sum(); sy = gs.groupby("source_year").net_R.sum()
        vals = {
            "trades": (len(gp), int(e.total_trades_primary), 0),
            "primary_mean": (gp.net_R.mean(), float(e.weighted_avg_net_R_primary), 1e-10),
            "primary_positive_years": (int((py > 0).sum()), int(e.positive_years_primary), 0),
            "stress_mean": (gs.net_R.mean(), float(e.weighted_avg_net_R_stress), 1e-10),
            "stress_positive_years": (int((sy > 0).sum()), int(e.positive_years_stress), 0),
        }
        cpass = True; detail = {}
        for k, (a, b, tol) in vals.items():
            same = abs(float(a)-float(b)) <= tol
            cpass &= same; detail[k] = {"actual": float(a), "expected": float(b), "tol": tol, "pass": bool(same)}
        if not cpass: ok = False
        checks.append({"target_r": rr, "pass": bool(cpass), "metrics": detail})
    return {
        "pass": bool(ok), "annual_parity_all_pass": bool(all(p.get("pass", False) for p in annual_parities)),
        "unique_core_events": int(len(refset)), "expected_core_events": 304, "all_rr_and_scenario_event_sets_identical": bool(same_sets),
        "duplicate_event_ids_primary_rr15": int(primary_rr15.event_id.duplicated().sum()), "rr_checks": checks,
    }


def gate_verdict(ledger, boot, annual, loo, conc, replay):
    bcell = []
    for rr in TARGET_RS:
        g = cell(ledger, PRIMARY, rr); br = boot[(boot.scenario == PRIMARY) & np.isclose(boot.target_r, rr)].iloc[0]
        bcell.append(bool(g.net_R.mean() >= .10 and pf(g.net_R) >= 1.25 and br.mean_ci95_lower > 0))
    stress_mean_all = all(cell(ledger, STRESS, rr).net_R.mean() > 0 for rr in TARGET_RS)
    stress_pf_pass = sum(pf(cell(ledger, STRESS, rr).net_R) >= 1.20 for rr in TARGET_RS)
    B = sum(bcell) >= 4 and stress_mean_all and stress_pf_pass >= 4

    temporal = {}
    for rr in TARGET_RS:
        lp = loo[(loo.scenario == PRIMARY) & np.isclose(loo.target_r, rr)]
        ap = annual[(annual.scenario == PRIMARY) & np.isclose(annual.target_r, rr)]
        ast = annual[(annual.scenario == STRESS) & np.isclose(annual.target_r, rr)]
        temporal[rr] = bool((lp.mean_net_R > 0).all() and (ap.mean_net_R > 0).sum() >= 10 and (ast.mean_net_R > 0).sum() >= 8 and ap.abs_annual_contribution_share.max() <= .35 and ast.abs_annual_contribution_share.max() <= .35)
    C = temporal[1.5] and sum(temporal.values()) >= 4

    D = True
    for s in (PRIMARY, STRESS):
        r = conc[(conc.scenario == s) & np.isclose(conc.target_r, 1.5)].iloc[0]
        D &= bool(r.mean_net_R_after_removing_best_5pct > 0 and r.best_5pct_share_total_positive_R <= .50)

    rp = replay[(replay.scenario == PRIMARY) & np.isclose(replay.target_r, 1.5)].iloc[0]
    rs = replay[(replay.scenario == STRESS) & np.isclose(replay.target_r, 1.5)].iloc[0]
    E = bool(rp.mean_net_R > 0 and rp.pf_net > 1.10 and rs.mean_net_R >= 0 and not bool(rp.unresolved_sequencing_ambiguity) and not bool(rs.unresolved_sequencing_ambiguity))
    return {"A_integrity": True, "B_broad_rr_statistical": bool(B), "C_temporal": bool(C), "D_concentration": bool(D), "E_portfolio": bool(E), "primary_cells_passing_B": int(sum(bcell)), "stress_cells_pf_ge_1_20": int(stress_pf_pass), "temporal_pass_by_rr": {str(k): bool(v) for k,v in temporal.items()}}


def checkpoint_text(verdict, parity, gates, ledger):
    refp = aggregate_metrics(cell(ledger, PRIMARY, 1.5)); refs = aggregate_metrics(cell(ledger, STRESS, 1.5))
    lines = [
        "# CHECKPOINT — XAU CORE EVIDENCE AUDIT V1", "", "Date: 2026-08-19", "",
        f"Terminal verdict: **{verdict}**", "", "## Integrity", "",
        f"- aggregate parity: `{parity['pass']}`", f"- unique core events: `{parity['unique_core_events']}`", "- new market-data spend: `0`", "- canonical input rehydration: `true` (same previously used public source/period only)", "",
        "## RR1.5 descriptive reference", "",
        f"- primary: N={refp['trades']}, mean={refp['mean_net_R']:.6f}R, PF={refp['pf_net']:.4f}, sum={refp['sum_net_R']:.3f}R",
        f"- stress: N={refs['trades']}, mean={refs['mean_net_R']:.6f}R, PF={refs['pf_net']:.4f}, sum={refs['sum_net_R']:.3f}R", "",
        "## Frozen Pro gates", "",
    ]
    for k,v in gates.items():
        if k.startswith(("A_","B_","C_","D_","E_")): lines.append(f"- {k}: `{v}`")
    lines += ["", "## Diagnostic dimensions", "", "Direction, contact/entry sessions, DOZ age, DOZ timeframe/variant, objective subtype and session A→B transitions were computed as hypothesis-generation diagnostics only. They do not alter the terminal verdict and may not be used as post-hoc filters in this audit.", "", "See `diagnostic_subgroups.csv`, `zone_age_diagnostics.csv` and `session_transition_diagnostics.csv` for complete tables.", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--annual-dir", required=True); ap.add_argument("--out", required=True); ap.add_argument("--survivors", required=True); args = ap.parse_args()
    annual_dir = Path(args.annual_dir); out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    parity_files = sorted(annual_dir.glob("parity_*.json")); ledger_files = sorted(annual_dir.glob("ledger_*.csv.gz"))
    annual_parities = [json.load(open(p)) for p in parity_files]
    if len(parity_files) != 15 or len(ledger_files) != 15:
        raise RuntimeError(f"expected 15 annual parity/ledger files, got {len(parity_files)}/{len(ledger_files)}")
    ledger = pd.concat([pd.read_csv(p) for p in ledger_files], ignore_index=True)
    ledger = ledger.sort_values(["scenario","target_r","entry_time","contact_time","event_id"], kind="mergesort").reset_index(drop=True)

    parity = aggregate_parity(ledger, Path(args.survivors), annual_parities)
    (out / "aggregate_parity_report.json").write_text(json.dumps(parity, indent=2, allow_nan=False))
    if not parity["pass"]:
        verdict = {"terminal_verdict":"CORE_RESULT_INVALID_REPAIR_REQUIRED","aggregate_parity":parity,"inference_computed":False}
        (out / "audit_verdict.json").write_text(json.dumps(verdict, indent=2, allow_nan=False))
        (out / "CHECKPOINT_XAU_CORE_EVIDENCE_AUDIT_V1.md").write_text("# CHECKPOINT — XAU CORE EVIDENCE AUDIT V1\n\nTerminal verdict: **CORE_RESULT_INVALID_REPAIR_REQUIRED**\n\nAggregate parity failed. No inferential or subgroup interpretation was computed.\n")
        return

    ledger_path = out / "core_trade_ledger.csv"
    ledger.to_csv(ledger_path, index=False)
    ledger_sha = sha256_file(ledger_path)
    manifest = {
        "version":"XAU_CORE_EVIDENCE_AUDIT_V1", "protocol":"xau-multiyear/docs/XAU_CORE_EVIDENCE_AUDIT_PROTOCOL_v1_1.md",
        "core_events":304, "ledger_rows":int(len(ledger)), "ledger_sha256":ledger_sha,
        "annual_input_sha256":{str(p["year"]):p["input_sha256"] for p in annual_parities},
        "canonical_input_rehydration":True, "new_research_market_information":False, "new_market_data_spend":0,
        "runtime_commit":os.getenv("GITHUB_SHA","LOCAL"), "date_cluster_bootstrap_draws":20000, "date_cluster_bootstrap_seed":20260821,
        "moving_block_bootstrap_draws":20000, "moving_block_bootstrap_seed":20260822,
    }
    (out / "ledger_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False))

    surface = []
    for s in SCENARIOS:
        for rr in TARGET_RS:
            surface.append({"scenario":s,"target_r":rr,**aggregate_metrics(cell(ledger,s,rr))})
    pd.DataFrame(surface).to_csv(out / "rr_surface_inference.csv", index=False)

    boot = bootstrap_date_clusters(ledger, out)
    moving_block_bootstrap(ledger, out)
    annual, loo = temporal_tables(ledger, out)
    conc, dd = concentration_and_drawdown(ledger, out)
    concurrency, replay = concurrency_and_replay(ledger, out)
    diagnostics(ledger, out)
    gates = gate_verdict(ledger, boot, annual, loo, conc, replay)
    gates["A_integrity"] = bool(parity["pass"])
    if all(gates[k] for k in ["A_integrity","B_broad_rr_statistical","C_temporal","D_concentration","E_portfolio"]):
        terminal = "CORE_INTERNAL_AUDIT_PASS_FOR_EXTERNAL_REPLICATION"
    else:
        terminal = "CORE_HISTORICAL_CANDIDATE_NO_GO_FOR_EXTERNAL_REPLICATION"
    verdict = {
        "version":"XAU_CORE_EVIDENCE_AUDIT_V1_VERDICT", "terminal_verdict":terminal, "gates":gates,
        "aggregate_parity_pass":True, "core_events":304, "live_ready":False, "external_replication_authorized": terminal == "CORE_INTERNAL_AUDIT_PASS_FOR_EXTERNAL_REPLICATION",
        "m5_authorized":False, "comex_continuation_authorized":False, "new_market_data_spend":0,
        "diagnostic_subgroups_can_rescue_verdict":False,
    }
    (out / "audit_verdict.json").write_text(json.dumps(verdict, indent=2, allow_nan=False))
    (out / "CHECKPOINT_XAU_CORE_EVIDENCE_AUDIT_V1.md").write_text(checkpoint_text(terminal, parity, gates, ledger))

    sums = []
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name != "SHA256SUMS": sums.append(f"{sha256_file(p)}  {p.name}")
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__": main()
