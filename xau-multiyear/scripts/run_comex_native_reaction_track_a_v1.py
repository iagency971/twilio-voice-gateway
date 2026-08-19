#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import audit_comex_native_reaction_expanded_controls as expanded
import build_comex_dev_rank1_event_features as feat
import build_comex_native_reaction_preoutcome_final_v1 as prebuild

TICK = 0.10
HORIZONS = ("W5", "W15", "W60", "SC")
HMIN = {"W5": 5, "W15": 15, "W60": 60}
BOOT_REPS = 20_000
BOOT_SEED = 20260819
SIGNFLIP_REPS = 50_000
SIGNFLIP_SEED = 20260820
FAMILIES = ("POC", "VAH", "VAL", "VWAP")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def pb(v) -> bool:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() == "true"


def utc(v) -> pd.Timestamp:
    x = pd.Timestamp(v)
    return x.tz_localize("UTC") if x.tzinfo is None else x.tz_convert("UTC")


def load_and_verify_freeze(root: Path) -> tuple[dict, dict]:
    publication = json.loads((root / "FREEZE_PUBLICATION.json").read_text())
    freeze = json.loads((root / "preoutcome_freeze_manifest.json").read_text())
    listed = (root / "preoutcome_freeze_manifest.sha256").read_text().strip().split()[0]
    actual = sha256_file(root / "preoutcome_freeze_manifest.json")
    if actual != listed or actual != publication.get("preoutcome_freeze_manifest_sha256"):
        raise SystemExit(f"preoutcome freeze binding mismatch actual={actual} listed={listed} publication={publication.get('preoutcome_freeze_manifest_sha256')}")
    if publication.get("support_gate_status") != "SUPPORT_GATE_REPAIRED_AND_PASS":
        raise SystemExit("preoutcome publication support gate not PASS")
    for k in ["reaction_outcomes_computed", "w15_opened", "market_data_api_called", "market_data_download_performed"]:
        if pb(publication.get(k)):
            raise SystemExit(f"preoutcome publication guard unexpectedly true: {k}")
    if not freeze.get("support", {}).get("support_gate_pass"):
        raise SystemExit("freeze manifest support gate not PASS")
    if freeze.get("outcomes_opened") is not False:
        raise SystemExit("freeze manifest already says outcomes opened")
    for name, expected in freeze.get("generated_output_sha256", {}).items():
        p = root / name
        if not p.exists():
            raise SystemExit(f"frozen preoutcome artifact missing: {name}")
        got = sha256_file(p)
        if got != expected:
            raise SystemExit(f"frozen preoutcome artifact hash mismatch: {name} expected={expected} got={got}")
    return publication, freeze


def load_control_universe(root: Path, freeze: dict) -> pd.DataFrame:
    parts = []
    for name in freeze["control_universe_shards"]:
        parts.append(pd.read_csv(root / name, dtype={"source_instrument_id": str}))
    C = pd.concat(parts, ignore_index=True)
    if C.empty or C.control_candidate_id.duplicated().any():
        dup = int(C.control_candidate_id.duplicated().sum()) if len(C) else 0
        raise SystemExit(f"control universe invalid/duplicate candidate ids: rows={len(C)} dup={dup}")
    return C


def canonicalize_match_keys(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["treated_level_id", "control_rank", "control_candidate_id", "control_source_research_date",
            "control_next_research_date", "control_anchor_time_utc", "control_source_instrument_id"]
    q = df[cols].copy()
    for c in cols:
        if c != "control_rank": q[c] = q[c].astype(str)
    q["control_rank"] = q.control_rank.astype(int)
    return q.sort_values(["treated_level_id", "control_rank"]).reset_index(drop=True)


def regenerate_frozen_matching(E: pd.DataFrame, C: pd.DataFrame, frozen_m: pd.DataFrame):
    M, S, F, Y, D, R, summary = prebuild.match_final(E, C)
    if not summary.get("support_gate_pass"):
        raise SystemExit(f"regenerated frozen matcher support failed: {summary}")
    expected = {"defined_events": 235, "eligible_events": 231, "matched_events": 227, "matched_dates": 81}
    for k, v in expected.items():
        if int(summary.get(k, -1)) != v:
            raise SystemExit(f"regenerated matcher count mismatch {k}: {summary.get(k)} != {v}")
    a = canonicalize_match_keys(M); b = canonicalize_match_keys(frozen_m)
    if len(a) != len(b) or not a.equals(b):
        z = a.merge(b, how="outer", indicator=True)
        raise SystemExit(f"regenerated matches differ from frozen manifest: {z._merge.value_counts().to_dict()}")
    return M, S, summary


def load_n1(n1_root: Path, manifest_path: Path) -> dict[str, dict]:
    man = pd.read_csv(manifest_path, dtype={"source_instrument_id": str, "symbols": str})
    markers = expanded.read_n1_markers(n1_root); out = {}
    for r in man.itertuples(index=False):
        rid = str(r.market_request_id)
        if rid not in markers: raise SystemExit(f"N1 marker missing {rid}")
        mk, p = markers[rid]
        if mk.get("sha256") and sha256_file(p) != mk["sha256"]: raise SystemExit(f"N1 raw hash mismatch {rid}")
        iid = str(r.source_instrument_id)
        if str(r.symbols) != iid or str(mk.get("symbols")) != iid: raise SystemExit(f"N1 iid mismatch {rid}")
        m1 = expanded.pre.prepare_m1(p, r.start, r.end).copy()
        if "bar_end" not in m1.columns: m1["bar_end"] = m1.ts_event + pd.Timedelta(minutes=1)
        out[str(r.source_research_date)] = {"m1": m1.sort_values("ts_event").reset_index(drop=True),
            "start": expanded.pre.to_utc(r.start), "end": expanded.pre.to_utc(r.end),
            "next_date": str(r.eligible_next_research_date), "iid": iid, "raw_file": p.name, "raw_sha256": sha256_file(p)}
    if len(out) != 92: raise SystemExit(f"expected 92 N1 blocks, got {len(out)}")
    return out


def context_sessions(context_root: Path) -> tuple[dict[tuple[str, str], pd.DataFrame], str]:
    marker, path = expanded.find_context(context_root); x = expanded.load_context(path); out = {}
    for (d, iid), g in x.groupby([x.gc_trade_date.astype(str), x.instrument_id.astype(str)], sort=False):
        out[(str(d), str(iid))] = g.sort_values("ts_event").reset_index(drop=True)
    return out, sha256_file(path)


def metric_one(m1: pd.DataFrame, anchor: pd.Timestamp, anchor_price: float, sign: int, source_range_ticks: float,
               session_end: pd.Timestamp, horizon: str) -> dict:
    if sign not in (-1, 1) or not np.isfinite(anchor_price) or not np.isfinite(source_range_ticks) or source_range_ticks <= 0:
        return {"available": False, "missing_reason": "INVALID_ANCHOR_SIGN_OR_NORMALIZER"}
    if horizon == "SC": end = session_end
    else:
        end = anchor + pd.Timedelta(minutes=HMIN[horizon])
        if end > session_end: return {"available": False, "missing_reason": "CENSORED_AT_SESSION_CLOSE"}
    if end < anchor: return {"available": False, "missing_reason": "INVALID_WINDOW"}
    z = m1[(m1.ts_event >= anchor) & (m1.bar_end <= end)].copy()
    if len(z):
        hi = sign * (z.high.astype(float).to_numpy() - float(anchor_price)) / TICK
        lo = sign * (z.low.astype(float).to_numpy() - float(anchor_price)) / TICK
        signed_vals = np.concatenate([hi, lo]); max_signed = float(np.nanmax(signed_vals)); min_signed = float(np.nanmin(signed_vals))
    else: max_signed = min_signed = 0.0
    M = max(0.0, max_signed); Q = max(0.0, -min_signed); rb = M - Q; nrb = rb / float(source_range_ticks)
    endpoint_price = float(z.iloc[-1].close) if len(z) else float(anchor_price)
    end_signed = sign * (endpoint_price - float(anchor_price)) / TICK
    requested_minutes = int(round((end - anchor).total_seconds() / 60.0)); traded_minutes = int(z.ts_event.nunique()) if len(z) else 0
    return {"available": True, "missing_reason": "", "window_end_utc": end.isoformat(),
        "actual_elapsed_seconds": float((end - anchor).total_seconds()), "requested_minutes": requested_minutes,
        "traded_minutes": traded_minutes, "no_trade_minutes": max(0, requested_minutes - traded_minutes),
        "M_ticks": M, "Q_ticks": Q, "reaction_balance_ticks": rb, "NRB": nrb,
        "endpoint_price": endpoint_price, "end_signed_ticks": float(end_signed)}


def event_outcomes(E: pd.DataFrame, matched_levels: set[str], n1: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for e in E[E.level_id.astype(str).isin(matched_levels)].itertuples(index=False):
        d = str(e.source_research_date); ss = n1[d]
        if str(e.source_instrument_id) != ss["iid"]: raise SystemExit(f"treated N1 iid mismatch {e.level_id}")
        a = utc(e.a0_utc); bar = ss["m1"][ss["m1"].bar_end == a]
        if len(bar) != 1: raise SystemExit(f"treated anchor bar missing/nonunique {e.level_id}")
        A = float(bar.iloc[0].close)
        if not np.isclose(A, float(e.A0_close), rtol=0, atol=1e-9): raise SystemExit(f"treated A0 parity mismatch {e.level_id}: {A} != {e.A0_close}")
        base = {"level_id": str(e.level_id), "source_research_date": d, "source_year": int(e.source_year), "level_type": str(e.level_type),
            "source_instrument_id": str(e.source_instrument_id), "approach": str(e.approach), "away_sign": int(e.away_sign),
            "a0_utc": a.isoformat(), "anchor_price": A, "source_range_ticks": float(e.source_range_ticks)}
        for h in HORIZONS: rows.append({**base, "horizon": h, **metric_one(ss["m1"], a, A, int(e.away_sign), float(e.source_range_ticks), ss["end"], h)})
    return pd.DataFrame(rows)


def control_outcomes(M: pd.DataFrame, C: pd.DataFrame, n1: dict[str, dict], ctx: dict[tuple[str, str], pd.DataFrame]) -> pd.DataFrame:
    refs = M[["control_candidate_id", "control_origin", "control_source_research_date", "control_next_research_date",
              "control_anchor_time_utc", "control_source_instrument_id"]].drop_duplicates().copy()
    ccols = ["control_candidate_id", "source_range_ticks", "away_sign", "anchor_time_utc", "source_instrument_id", "control_source_research_date", "control_origin"]
    cm = C[ccols].copy().rename(columns={"anchor_time_utc": "candidate_anchor_time_utc", "source_instrument_id": "candidate_iid",
                                         "control_source_research_date": "candidate_source_date", "control_origin": "candidate_origin"})
    refs = refs.merge(cm, on="control_candidate_id", how="left", validate="one_to_one")
    if refs.source_range_ticks.isna().any(): raise SystemExit("selected control missing from frozen candidate universe")
    rows = []
    for r in refs.itertuples(index=False):
        d = str(r.control_source_research_date); nd = str(r.control_next_research_date); iid = str(r.control_source_instrument_id)
        if str(r.candidate_iid) != iid or str(r.candidate_source_date) != d or str(r.candidate_origin) != str(r.control_origin): raise SystemExit(f"selected control provenance join mismatch {r.control_candidate_id}")
        anchor = utc(r.control_anchor_time_utc)
        if utc(r.candidate_anchor_time_utc) != anchor: raise SystemExit(f"selected control anchor mismatch {r.control_candidate_id}")
        if str(r.control_origin) == "CANONICAL_N1":
            if d not in n1: raise SystemExit(f"canonical control source missing N1 {d}")
            ss = n1[d]
            if ss["next_date"] != nd or ss["iid"] != iid: raise SystemExit(f"canonical control adjacency/iid mismatch {r.control_candidate_id}")
            m1 = ss["m1"]; session_end = ss["end"]
        elif str(r.control_origin) == "OWNED_GC_N0_CONTEXT":
            key = (nd, iid)
            if key not in ctx: raise SystemExit(f"generic context next session missing {key}")
            s, session_end = feat.session_bounds(nd); m1 = ctx[key]; m1 = m1[(m1.ts_event >= s) & (m1.ts_event < session_end)].copy()
        else: raise SystemExit(f"unknown control origin {r.control_origin}")
        bar = m1[m1.bar_end == anchor]
        if len(bar) != 1: raise SystemExit(f"control anchor bar missing/nonunique {r.control_candidate_id} count={len(bar)}")
        A = float(bar.iloc[0].close); base = {"control_candidate_id": str(r.control_candidate_id), "control_origin": str(r.control_origin),
            "control_source_research_date": d, "control_next_research_date": nd, "control_source_instrument_id": iid,
            "control_anchor_time_utc": anchor.isoformat(), "anchor_price": A, "away_sign": int(r.away_sign), "source_range_ticks": float(r.source_range_ticks)}
        for h in HORIZONS: rows.append({**base, "horizon": h, **metric_one(m1, anchor, A, int(r.away_sign), float(r.source_range_ticks), session_end, h)})
    return pd.DataFrame(rows)


def build_event_control_effects(M: pd.DataFrame, E: pd.DataFrame, EO: pd.DataFrame, CO: pd.DataFrame) -> pd.DataFrame:
    ebase = E[["level_id", "source_research_date", "source_year", "level_type", "away_sign", "approach"]].copy(); rows = []
    for h in HORIZONS:
        em = EO[EO.horizon.eq(h)].set_index("level_id"); cm = CO[CO.horizon.eq(h)].set_index("control_candidate_id")
        for level, g in M.groupby("treated_level_id", sort=False):
            level = str(level); er = em.loc[level]; controls = [str(x) for x in g.sort_values("control_rank").control_candidate_id]; cr = cm.loc[controls]
            if isinstance(er, pd.DataFrame): raise SystemExit(f"duplicate treated outcome row {level} {h}")
            event_available = pb(er["available"]); controls_available = cr.available.map(pb).all(); complete = bool(event_available and controls_available and len(cr) == 5)
            meta = ebase[ebase.level_id.astype(str).eq(level)].iloc[0]
            row = {"level_id": level, "source_research_date": str(meta.source_research_date), "source_year": int(meta.source_year), "level_type": str(meta.level_type),
                "away_sign": int(meta.away_sign), "approach": str(meta.approach), "horizon": h, "k_controls": int(len(cr)),
                "complete_event_plus_k5": complete, "event_available": event_available, "all_controls_available": bool(controls_available)}
            if complete:
                row.update({"event_NRB": float(er.NRB), "control_mean_NRB": float(cr.NRB.astype(float).mean()), "delta_NRB": float(er.NRB) - float(cr.NRB.astype(float).mean()),
                    "event_reaction_balance_ticks": float(er.reaction_balance_ticks), "control_mean_reaction_balance_ticks": float(cr.reaction_balance_ticks.astype(float).mean()),
                    "delta_reaction_balance_ticks": float(er.reaction_balance_ticks) - float(cr.reaction_balance_ticks.astype(float).mean()),
                    "event_end_signed_ticks": float(er.end_signed_ticks), "control_mean_end_signed_ticks": float(cr.end_signed_ticks.astype(float).mean()),
                    "delta_end_signed_ticks": float(er.end_signed_ticks) - float(cr.end_signed_ticks.astype(float).mean())})
            rows.append(row)
    return pd.DataFrame(rows)


def date_effects(effect: pd.DataFrame, horizon: str, family: str | None = None, exclude_family: str | None = None) -> pd.DataFrame:
    q = effect[(effect.horizon == horizon) & effect.complete_event_plus_k5.map(pb)].copy()
    if family is not None: q = q[q.level_type.astype(str).eq(family)]
    if exclude_family is not None: q = q[~q.level_type.astype(str).eq(exclude_family)]
    if q.empty: return pd.DataFrame(columns=["source_research_date", "source_year", "delta_NRB", "delta_reaction_balance_ticks", "events"])
    return q.groupby(["source_research_date", "source_year"], as_index=False).agg(delta_NRB=("delta_NRB", "mean"),
        delta_reaction_balance_ticks=("delta_reaction_balance_ticks", "mean"), events=("level_id", "size")).sort_values("source_research_date").reset_index(drop=True)


def signflip_p(values: np.ndarray, seed: int = SIGNFLIP_SEED, reps: int = SIGNFLIP_REPS) -> float:
    x = np.asarray(values, dtype=float); x = x[np.isfinite(x)]
    if len(x) == 0: return float("nan")
    obs = abs(float(x.mean())); rng = np.random.default_rng(seed); ge = 0; done = 0; batch = 5000
    while done < reps:
        n = min(batch, reps - done); signs = rng.choice(np.array([-1.0, 1.0]), size=(n, len(x)), replace=True)
        ge += int(np.sum(np.abs((signs * x).mean(axis=1)) >= obs - 1e-15)); done += n
    return float((ge + 1) / (reps + 1))


def holm_adjust(pvals: dict[str, float]) -> dict[str, float]:
    finite = [(k, float(v)) for k, v in pvals.items() if np.isfinite(v)]; finite.sort(key=lambda kv: kv[1]); m = len(finite)
    out = {k: float("nan") for k in pvals}; prev = 0.0
    for i, (k, p) in enumerate(finite):
        adj = max(prev, min(1.0, (m - i) * p)); out[k] = adj; prev = adj
    return out


def bootstrap_primary(panel_dates: list[str], date_delta: dict[str, float], original_matched_dates: int = 81) -> tuple[np.ndarray, int]:
    if len(panel_dates) != 92 or len(set(panel_dates)) != 92: raise SystemExit(f"bootstrap panel must be 92 distinct dates, got {len(panel_dates)}/{len(set(panel_dates))}")
    min_retained = int(math.ceil(0.80 * original_matched_dates)); rng = np.random.default_rng(BOOT_SEED); arr = np.array(panel_dates, dtype=object)
    vals = []; attempts = 0
    while len(vals) < BOOT_REPS:
        attempts += 1; draw = rng.choice(arr, size=len(arr), replace=True); z = [date_delta[str(d)] for d in draw if str(d) in date_delta]
        if len(z) < min_retained: continue
        vals.append(float(np.mean(z)))
        if attempts > 2_000_000: raise SystemExit("bootstrap could not obtain 20,000 valid replicates")
    return np.asarray(vals, dtype=float), attempts


def year_stability(primary_dates: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows = []; N = len(primary_dates); contributions = {}
    for y in range(2011, 2019):
        g = primary_dates[primary_dates.source_year.astype(int).eq(y)]; theta = float(g.delta_NRB.mean()) if len(g) else float("nan"); contrib = float(g.delta_NRB.sum() / N) if N else float("nan")
        loyo = primary_dates[~primary_dates.source_year.astype(int).eq(y)]; loyo_theta = float(loyo.delta_NRB.mean()) if len(loyo) else float("nan"); contributions[y] = contrib
        rows.append({"source_year": y, "matched_dates": int(len(g)), "theta_NRB15": theta, "aggregate_contribution_to_primary": contrib, "leave_one_year_out_theta_NRB15": loyo_theta})
    denom = float(sum(abs(v) for v in contributions.values() if np.isfinite(v)))
    for r in rows: r["abs_contribution_share"] = abs(r["aggregate_contribution_to_primary"]) / denom if denom > 0 else float("nan")
    Y = pd.DataFrame(rows); criteria = {"positive_years": int((Y.theta_NRB15 > 0).sum()), "at_least_6_of_8_years_positive": bool((Y.theta_NRB15 > 0).sum() >= 6),
        "all_leave_one_year_out_positive": bool((Y.leave_one_year_out_theta_NRB15 > 0).all()), "max_abs_year_contribution_share": float(Y.abs_contribution_share.max()),
        "no_year_over_35pct_abs_contribution": bool((Y.abs_contribution_share <= 0.35 + 1e-15).all())}
    criteria["gate_pass"] = bool(criteria["at_least_6_of_8_years_positive"] and criteria["all_leave_one_year_out_positive"] and criteria["no_year_over_35pct_abs_contribution"])
    return Y, criteria


def family_robustness(primary_effects: pd.DataFrame, primary_dates: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    q = primary_effects[(primary_effects.horizon == "W15") & primary_effects.complete_event_plus_k5.map(pb)].copy(); Ndates = primary_dates.source_research_date.nunique()
    counts = q.groupby("source_research_date").level_id.transform("size").astype(float); q["primary_contribution"] = q.delta_NRB.astype(float) / counts / float(Ndates)
    fam_contrib = q.groupby("level_type").primary_contribution.sum().to_dict(); denom = float(sum(abs(float(fam_contrib.get(f, 0.0))) for f in FAMILIES)); rows = []
    for f in FAMILIES:
        fd = date_effects(primary_effects, "W15", family=f); lo = date_effects(primary_effects, "W15", exclude_family=f); contrib = float(fam_contrib.get(f, 0.0))
        rows.append({"level_type": f, "matched_events": int(len(q[q.level_type.eq(f)])), "matched_dates": int(len(fd)), "theta_NRB15": float(fd.delta_NRB.mean()) if len(fd) else float("nan"),
            "leave_one_family_out_theta_NRB15": float(lo.delta_NRB.mean()) if len(lo) else float("nan"), "aggregate_contribution_to_primary": contrib,
            "abs_contribution_share": abs(contrib) / denom if denom > 0 else float("nan")})
    F = pd.DataFrame(rows); criteria = {"positive_families": int((F.theta_NRB15 > 0).sum()), "at_least_3_of_4_families_positive": bool((F.theta_NRB15 > 0).sum() >= 3),
        "all_leave_one_family_out_positive": bool((F.leave_one_family_out_theta_NRB15 > 0).all()), "max_abs_family_contribution_share": float(F.abs_contribution_share.max()),
        "no_family_over_50pct_abs_contribution": bool((F.abs_contribution_share <= 0.50 + 1e-15).all())}
    criteria["gate_pass"] = bool(criteria["at_least_3_of_4_families_positive"] and criteria["all_leave_one_family_out_positive"] and criteria["no_family_over_50pct_abs_contribution"])
    return F, criteria


def secondary_tables(effect: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    fam_rows = []; fam_ps = {}
    for f in FAMILIES:
        d = date_effects(effect, "W15", family=f); theta = float(d.delta_NRB.mean()) if len(d) else float("nan"); p = signflip_p(d.delta_NRB.to_numpy(float)) if len(d) else float("nan")
        fam_ps[f] = p; fam_rows.append({"test": f, "horizon": "W15", "matched_dates": int(len(d)), "theta_NRB": theta, "signflip_p_raw": p})
    fam_adj = holm_adjust(fam_ps)
    for r in fam_rows: r["holm_p"] = fam_adj[r["test"]]
    h_rows = []; h_ps = {}
    for h in ("W5", "W60", "SC"):
        d = date_effects(effect, h); theta = float(d.delta_NRB.mean()) if len(d) else float("nan"); p = signflip_p(d.delta_NRB.to_numpy(float)) if len(d) else float("nan")
        h_ps[h] = p; h_rows.append({"test": h, "horizon": h, "matched_dates": int(len(d)), "theta_NRB": theta, "signflip_p_raw": p})
    h_adj = holm_adjust(h_ps)
    for r in h_rows: r["holm_p"] = h_adj[r["test"]]
    return pd.DataFrame(fam_rows), pd.DataFrame(h_rows)


def main():
    ap = argparse.ArgumentParser()
    for x in ["preoutcome-root", "n1-manifest", "n1-root", "context-root", "protocol", "script", "workflow", "out"]: ap.add_argument("--" + x, required=True)
    a = ap.parse_args(); pre_root = Path(a.preoutcome_root); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    publication, freeze = load_and_verify_freeze(pre_root)
    E = pd.read_csv(pre_root / "treated_event_causal_context_final.csv", dtype={"source_instrument_id": str})
    frozen_m = pd.read_csv(pre_root / "matched_control_manifest.csv", dtype={"control_source_instrument_id": str})
    C = load_control_universe(pre_root, freeze); M, S, match_summary = regenerate_frozen_matching(E, C, frozen_m)
    matched_levels = set(S[S.full_k5_match.map(pb)].level_id.astype(str))
    if len(matched_levels) != 227: raise SystemExit(f"expected 227 matched levels, got {len(matched_levels)}")
    n1 = load_n1(Path(a.n1_root), Path(a.n1_manifest)); ctx, context_sha = context_sessions(Path(a.context_root))
    if context_sha != freeze.get("context_artifact_raw_sha256"): raise SystemExit(f"context artifact hash drift {context_sha} != {freeze.get('context_artifact_raw_sha256')}")
    EO = event_outcomes(E, matched_levels, n1); CO = control_outcomes(M, C, n1, ctx); effects = build_event_control_effects(M, E, EO, CO)
    primary = date_effects(effects, "W15")
    if len(primary) != 81: raise SystemExit(f"primary matched-date count drift: {len(primary)} != 81")
    p15 = effects[(effects.horizon == "W15") & effects.complete_event_plus_k5.map(pb)]
    if p15.level_id.nunique() != 227: raise SystemExit(f"primary matched-event count drift: {p15.level_id.nunique()} != 227")
    theta = float(primary.delta_NRB.mean()); raw_theta = float(primary.delta_reaction_balance_ticks.mean())
    panel_dates = pd.read_csv(pre_root / "source_session_causal_provenance.csv").source_research_date.astype(str).tolist()
    date_delta = primary.set_index(primary.source_research_date.astype(str)).delta_NRB.astype(float).to_dict(); boots, boot_attempts = bootstrap_primary(panel_dates, date_delta, 81)
    ci_lo, ci_hi = [float(x) for x in np.percentile(boots, [2.5, 97.5])]; sign_p = signflip_p(primary.delta_NRB.to_numpy(float), SIGNFLIP_SEED, SIGNFLIP_REPS)
    Y, ycrit = year_stability(primary); FR, fcrit = family_robustness(effects, primary); SF, SH = secondary_tables(effects)
    support_crit = freeze["support"]["criteria"]; A = bool(freeze["support"]["support_gate_pass"] and all(bool(v) for v in support_crit.values()))
    B_detail = {"theta_NRB15": theta, "theta_ge_0_02": bool(theta >= 0.02), "bootstrap_ci95_lower": ci_lo, "bootstrap_ci95_upper": ci_hi,
        "ci_lower_gt_0": bool(ci_lo > 0), "date_weighted_raw_reaction_balance_ticks": raw_theta, "raw_ticks_ge_2": bool(raw_theta >= 2.0)}
    B = bool(B_detail["theta_ge_0_02"] and B_detail["ci_lower_gt_0"] and B_detail["raw_ticks_ge_2"]); Cgate = bool(ycrit["gate_pass"]); Dgate = bool(fcrit["gate_pass"])
    decision = "OPEN_DEV_RANK2_NATIVE_REACTION" if (A and B and Cgate and Dgate) else ("STOP_AND_REPAIR_DESIGN" if not A else "NO_GO_DEV_RANK2_NATIVE_REACTION")
    decision_obj = {"version": "COMEX_DEV_RANK1_NATIVE_REACTION_TRACK_A_DECISION_V1", "preoutcome_freeze_manifest_sha256": publication["preoutcome_freeze_manifest_sha256"],
        "preoutcome_artifact_freeze_commit_sha": publication["artifact_freeze_commit_sha"], "scientific_estimand": "EVENT_VS_MATCHED_REFERENCE_ANCHOR_POST_CONTACT_MINUTE",
        "primary_horizon": "W15", "primary_endpoint": "DELTA_NRB15", "matched_events": 227, "matched_treated_dates": 81,
        "A_support_gate": {"pass": A, "criteria": support_crit}, "B_primary_effect_gate": {"pass": B, **B_detail},
        "primary_signflip": {"draws": SIGNFLIP_REPS, "seed": SIGNFLIP_SEED, "two_sided_p": sign_p},
        "primary_bootstrap": {"valid_replicates": BOOT_REPS, "seed": BOOT_SEED, "panel_dates": 92, "minimum_matched_date_draws_per_valid_replicate": int(math.ceil(0.8 * 81)),
            "attempts_for_20000_valid": int(boot_attempts), "implementation": "DETERMINISTIC_EVENT_LOCAL_REMATCH_REGENERATED_AND_ASSERTED_IDENTICAL_THEN_MEMOIZED_PER_BOOTSTRAP_DRAW", "ci_method": "95_PERCENTILE_DATE_CLUSTER_BOOTSTRAP"},
        "C_year_stability_gate": {"pass": Cgate, **ycrit}, "D_family_robustness_gate": {"pass": Dgate, **fcrit}, "decision": decision,
        "secondary_results_can_rescue_primary": False, "dev_rank2_opened_by_this_run": False, "confirm_or_locked_opened_by_this_run": False,
        "market_data_api_called": False, "market_data_download_performed": False, "new_market_data_spend": 0, "mfe_mae_computed": False, "order_dependent_first_hit_metric_computed": False}
    EO.to_csv(out / "treated_anchor_outcomes.csv", index=False); CO.to_csv(out / "selected_control_anchor_outcomes.csv", index=False); effects.to_csv(out / "event_control_effects.csv", index=False)
    primary.to_csv(out / "primary_date_effects.csv", index=False); Y.to_csv(out / "year_stability.csv", index=False); FR.to_csv(out / "family_robustness.csv", index=False)
    SF.to_csv(out / "secondary_family_w15_holm.csv", index=False); SH.to_csv(out / "secondary_horizon_holm.csv", index=False)
    pd.DataFrame({"bootstrap_theta_NRB15": boots}).to_csv(out / "primary_bootstrap_20000.csv.gz", index=False, compression="gzip")
    (out / "track_a_decision.json").write_text(json.dumps(decision_obj, indent=2))
    guard = {"version": "COMEX_DEV_RANK1_NATIVE_REACTION_TRACK_A_EXECUTION_GUARD_V1", "freeze_sha_verified_before_outcomes": True,
        "all_frozen_generated_artifact_hashes_verified_before_outcomes": True, "frozen_matching_regenerated_before_outcomes": True, "frozen_matching_exact_identity_pass": True,
        "support_gate_pass_before_outcomes": True, "w15_opened": True, "reaction_outcomes_computed": True, "market_data_api_called": False,
        "market_data_download_performed": False, "new_market_data_spend": 0, "mfe_mae_computed": False, "order_dependent_metric_computed": False,
        "xauusd_economic_mapping_computed": False, "dev_rank2_executed": False, "confirm_executed": False, "locked_test_executed": False}
    (out / "outcome_execution_guard.json").write_text(json.dumps(guard, indent=2))
    verdict_plain = "Track A PASSES the preregistered DEV_RANK1 gate and may open DEV_RANK2; this is not yet a tradable-strategy validation." if decision == "OPEN_DEV_RANK2_NATIVE_REACTION" else ("Track A does NOT pass the preregistered DEV_RANK1 reaction gate; secondary slices are not allowed to rescue it." if decision == "NO_GO_DEV_RANK2_NATIVE_REACTION" else "The support/design gate failed; reaction results must not be interpreted.")
    md = f"""# COMEX DEV_RANK1 native reaction — Track A result\n\nDate: 2026-08-19\n\n## Frozen binding\n\n- pre-outcome manifest SHA-256: `{publication['preoutcome_freeze_manifest_sha256']}`\n- artifact freeze commit: `{publication['artifact_freeze_commit_sha']}`\n- frozen matching re-generated before outcomes and exact-identity checked: **PASS**\n- new market-data API/download/spend: **NONE**\n\n## Primary preregistered result\n\n- matched events: **227**\n- matched treated dates: **81**\n- W15 `theta_NRB15`: **{theta:.12g}**\n- 95% date-cluster bootstrap CI: **[{ci_lo:.12g}, {ci_hi:.12g}]**\n- date-weighted raw reaction-balance difference: **{raw_theta:.12g} GC ticks**\n- 50,000-draw two-sided sign-flip p: **{sign_p:.12g}**\n\n## Frozen gates\n\n- A support/control: **{'PASS' if A else 'FAIL'}**\n- B primary effect/uncertainty: **{'PASS' if B else 'FAIL'}**\n- C year stability: **{'PASS' if Cgate else 'FAIL'}**\n- D family robustness: **{'PASS' if Dgate else 'FAIL'}**\n\n## Decision\n\n`{decision}`\n\n{verdict_plain}\n\nThe generic-control limitation remains unchanged: generic anchors are matched reference anchors, not proven treatment-free counterfactuals. Track A is conditional on exact J+1 contact and does not measure the unconditional value of all generated levels.\n"""
    (out / "TRACK_A_RESULT.md").write_text(md)
    files = sorted([p for p in out.iterdir() if p.is_file()]); manifest = {"version": "COMEX_DEV_RANK1_NATIVE_REACTION_TRACK_A_RESULT_MANIFEST_V1",
        "preoutcome_freeze_manifest_sha256": publication["preoutcome_freeze_manifest_sha256"], "preoutcome_artifact_freeze_commit_sha": publication["artifact_freeze_commit_sha"],
        "protocol_sha256_at_execution": sha256_file(Path(a.protocol)), "execution_script_sha256": sha256_file(Path(a.script)), "workflow_sha256": sha256_file(Path(a.workflow)),
        "generated_files_sha256": {p.name: sha256_file(p) for p in files}, "decision": decision}
    (out / "track_a_result_manifest.json").write_text(json.dumps(manifest, indent=2)); (out / "track_a_result_manifest.sha256").write_text(sha256_file(out / "track_a_result_manifest.json") + "  track_a_result_manifest.json\n")
    print("TRACK_A_COMPLETE", json.dumps({"theta": theta, "ci": [ci_lo, ci_hi], "raw_ticks": raw_theta, "sign_p": sign_p, "decision": decision}))


if __name__ == "__main__": main()
