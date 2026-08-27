#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

SEED = 20260827
B = 1000
NY = "America/New_York"
MODEL_FEATURES = [
    "close_pos", "body_frac", "lower_wick_frac", "upper_wick_frac",
    "log1p_lower_wick_to_body", "range_v",
]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_geometry_timefix(name: str, path: Path):
    src = path.read_text(encoding="utf-8")
    old = "tns=raw.time.astype('int64').to_numpy()"
    new = "tns=raw.time.dt.tz_convert('UTC').dt.tz_localize(None).to_numpy(dtype='datetime64[ns]').astype('int64')"
    if src.count(old) != 1:
        raise RuntimeError(f"geometry timestamp anchor count={src.count(old)}")
    src = src.replace(old, new, 1)
    mod = type(sys)(name)
    mod.__file__ = str(path)
    mod.__name__ = name
    sys.modules[name] = mod
    exec(compile(src, str(path), "exec"), mod.__dict__)
    return mod


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--files", nargs="+", required=True)
    p.add_argument("--aug-file", required=True)
    p.add_argument("--z4-pkl", required=True)
    p.add_argument("--model-json", required=True)
    p.add_argument("--source-freeze-json", required=True)
    p.add_argument("--output-json", required=True)
    p.add_argument("--contacts-csv", required=True)
    p.add_argument("--events-csv", required=True)
    return p.parse_args()


def us_ny(t) -> bool:
    q = pd.Timestamp(t).tz_convert(NY)
    return 8 <= q.hour < 17


def us_session_id(t) -> str:
    return pd.Timestamp(t).tz_convert(NY).date().isoformat()


def us_end(t):
    q = pd.Timestamp(t).tz_convert(NY)
    return pd.Timestamp(year=q.year, month=q.month, day=q.day, hour=17, tz=NY).tz_convert("UTC")


def us_subperiod(t):
    return "US_08_17"


def complete_august_sessions(aug: pd.DataFrame):
    """Mechanically require every M1 timestamp 08:00..16:59 NY."""
    t = pd.DatetimeIndex(pd.to_datetime(aug.time, utc=True))
    have = set(t.asi8.tolist())
    ny_days = sorted(set(t.tz_convert(NY).date))
    complete = []
    diagnostics = {}
    for d in ny_days:
        st = pd.Timestamp(year=d.year, month=d.month, day=d.day, hour=8, tz=NY).tz_convert("UTC")
        en = pd.Timestamp(year=d.year, month=d.month, day=d.day,hour=17, tz=NY).tz_convert("UTC")
        req = pd.date_range(st, en - pd.Timedelta(minutes=1), freq="1min")
        present = sum(int(x) in have for x in req.asi8)
        diagnostics[d.isoformat()] = {"required_minutes": int(len(req)), "present_minutes": int(present)}
        if present == len(req):
            complete.append(d.isoformat())
    return complete, diagnostics


def build_contacts_only(raw, z4, snaps, displays, asia, final):
    asia.asia_end = us_end
    asia.asia_session_id = us_session_id
    asia.asia_subperiod = us_subperiod
    asia.base = final.base
    targets = asia.target_map(z4, snaps)
    contacts = []
    prev_states = []
    prev_s = None
    next_id = 1

    for s, zs in zip(snaps, displays):
        t = pd.Timestamp(s["time"])
        states, next_id = asia.next_states(prev_states, prev_s, s, zs, next_id)
        sid = us_session_id(t)

        for st in states:
            z = st["zone"]
            if not st["armed"] and float(s["close"]) > float(z.zhi):
                st["armed"] = True
                st["arm_time"] = t
                st["arm_close"] = float(s["close"])

        tp = targets.get(t)
        end = min(t + pd.Timedelta(minutes=5), us_end(t))
        i0 = asia.raw_index(raw, t, "right") + 1
        i1 = asia.raw_index(raw, end - pd.Timedelta(nanoseconds=1), "right")

        if tp is not None and i1 >= i0:
            for st in states:
                if st.get("consumed_session_id") == sid:
                    continue
                z = st["zone"]
                contact_idx = None
                for j in range(max(0, i0), min(len(raw) - 1, i1) + 1):
                    rr = raw.loc[j]
                    if not st["armed"]:
                        if float(rr.close) > float(z.zhi):
                            st["armed"] = True
                            st["arm_time"] = pd.Timestamp(rr.time)
                            st["arm_close"] = float(rr.close)
                        continue
                    if float(rr.high) >= float(z.zlo) and float(rr.low) <= float(z.zhi):
                        contact_idx = j
                        break
                if contact_idx is None:
                    continue

                ct = pd.Timestamp(raw.at[contact_idx, "time"])
                contact_sid = us_session_id(ct)
                st["consumed_session_id"] = contact_sid
                v = float(s["v"])
                width = max(float(z.zhi) - float(z.zlo), 1e-12)
                contacts.append({
                    "episode_id": int(st["id"]),
                    "state_time": t,
                    "contact_time": ct,
                    "session_id": contact_sid,
                    "family": z.family,
                    "episode_origin_family": st["origin_family"],
                    "slot_rank": int(st["slot"]),
                    "episode_age_c5": int(st["age"]),
                    "zlo": float(z.zlo),
                    "center": float(z.center),
                    "zhi": float(z.zhi),
                    "zone_width_v": float(width / v),
                    "v_contact": v,
                    "arm_time": st["arm_time"],
                    "arm_close": st["arm_close"],
                    "tp1_zlo": float(tp["zlo"]),
                    "tp1_center": float(tp["center"]),
                    "tp1_zhi": float(tp["zhi"]),
                    "tp1_distance_from_touch_ref_v": float((float(tp["zlo"]) - float(z.zhi)) / v),
                    "minutes_to_us_end": float((us_end(ct) - ct).total_seconds() / 60.0),
                    "contact_bull": int(float(raw.at[contact_idx, "close"]) > float(raw.at[contact_idx, "open"])),
                })
        prev_states = states
        prev_s = s
    return contacts


def sigmoid(x):
    x = np.asarray(x, float)
    return np.where(x >= 0, 1.0 / (1.0 + np.exp(-x)), np.exp(x) / (1.0 + np.exp(x)))


def model_scores(d: pd.DataFrame, frozen: dict):
    m = frozen["model"]
    X = d[MODEL_FEATURES].to_numpy(float)
    mean = np.asarray(m["scaler_mean"], float)
    scale = np.asarray(m["scaler_scale"], float)
    coef = np.asarray(m["coefficients"], float)
    d["geometry_score"] = sigmoid(float(m["intercept"]) + ((X - mean) / scale) @ coef)

    c = frozen["closepos_only_reference"]
    x = d[["close_pos"]].to_numpy(float)
    d["closepos_score"] = sigmoid(
        float(c["intercept"])
        + ((x - np.asarray(c["scaler_mean"], float)) / np.asarray(c["scaler_scale"], float))
        @ np.asarray(c["coefficients"], float)
    )
    return d


def bootstrap_auc(d, pred_col, seed=SEED, nrep=B):
    sessions = sorted(d.session_id.unique())
    by = {s: d[d.session_id == s] for s in sessions}
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(nrep):
        picks = rng.integers(0, len(sessions), len(sessions))
        z = pd.concat([by[sessions[i]] for i in picks], ignore_index=True)
        if z.label.nunique() < 2:
            continue
        vals.append(roc_auc_score(z.label, z[pred_col]))
    return [float(np.quantile(vals, .025)), float(np.quantile(vals, .975))], int(len(vals))


def bootstrap_auc_diff(d, p1, p0, seed=SEED, nrep=B):
    sessions = sorted(d.session_id.unique())
    by = {s: d[d.session_id == s] for s in sessions}
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(nrep):
        picks = rng.integers(0, len(sessions), len(sessions))
        z = pd.concat([by[sessions[i]] for i in picks], ignore_index=True)
        if z.label.nunique() < 2:
            continue
        vals.append(roc_auc_score(z.label, z[p1]) - roc_auc_score(z.label, z[p0]))
    return [float(np.quantile(vals, .025)), float(np.quantile(vals, .975))], int(len(vals))


def bootstrap_band_diff(top, bottom, sessions, seed=SEED, nrep=B):
    sessions = sorted(sessions)
    gt = top.groupby("session_id").label.agg(["sum", "count"]).reindex(sessions, fill_value=0)
    gb = bottom.groupby("session_id").label.agg(["sum", "count"]).reindex(sessions, fill_value=0)
    pt, nt = gt["sum"].to_numpy(float), gt["count"].to_numpy(float)
    pb, nb = gb["sum"].to_numpy(float), gb["count"].to_numpy(float)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(nrep):
        ix = rng.integers(0, len(sessions), len(sessions))
        dt, db = nt[ix].sum(), nb[ix].sum()
        if dt > 0 and db > 0:
            vals.append(pt[ix].sum() / dt - pb[ix].sum() / db)
    return [float(np.quantile(vals, .025)), float(np.quantile(vals, .975))], int(len(vals))


def band_summary(d, lo, hi):
    bottom = d[d.geometry_score <= lo]
    top = d[d.geometry_score >= hi]
    middle = d[(d.geometry_score > lo) & (d.geometry_score < hi)]

    def q(z):
        return {"n": int(len(z)), "tp1_positive_rate": float(z.label.mean()) if len(z) else None}
    return bottom, middle, top, {"bottom_q20": q(bottom), "middle": q(middle), "top_q80": q(top)}


def main():
    a = parse_args()
    root = Path(__file__).resolve().parents[1]
    entry = root / "entry-research"
    session = root / "session-research"

    v04 = load_module("fresh_v04", entry / "xau_ebuy_coverage_v0_4_sticky.py")
    v01 = v04.v01
    final = load_module("fresh_final", entry / "xau_ebuy_reaction_dev_v1_0_3_final_preoutcome.py")
    asia = load_module("fresh_contact_plumbing", session / "xau_ebuy_asia_reaction_v1_0.py")
    geom = load_geometry_timefix("fresh_geom", entry / "xau_ebuy_bull_candle_geometry_v1_0.py")

    frozen = json.load(open(a.model_json))
    source = json.load(open(a.source_freeze_json))

    raw = v01.load_raw(a.files)
    raw["time"] = pd.to_datetime(raw["time"], utc=True)
    active = v01.active_m1(raw)
    aug = v01.load_raw([a.aug_file])
    aug["time"] = pd.to_datetime(aug["time"], utc=True)
    complete, completeness = complete_august_sessions(aug)

    z4 = pd.read_pickle(a.z4_pkl).copy()
    z4["time"] = pd.to_datetime(z4.time, utc=True)
    bad = sorted(v01.FORBIDDEN & set(z4.columns))
    if bad:
        raise RuntimeError(f"future outcome columns present in Z4 geometry: {bad}")

    v04.v01.ny_us = us_ny
    snaps, pools = v04.build_fixed_pools(raw, active, z4)
    displays = v04.sticky_display(raw, snaps, pools)

    contacts = build_contacts_only(raw, z4, snaps, displays, asia, final)
    cdf = pd.DataFrame(contacts)
    if len(cdf):
        cdf["contact_time"] = pd.to_datetime(cdf.contact_time, utc=True)
        cdf = cdf[cdf.session_id.isin(set(complete))].copy()
        cdf = cdf[(cdf.contact_time >= pd.Timestamp("2026-08-01T00:00:00Z")) &
                  (cdf.contact_time < pd.Timestamp("2026-09-01T00:00:00Z"))].copy()
    cdf.to_csv(a.contacts_csv, index=False, compression="gzip")

    events, _, first_reasons, _ = geom.replay(cdf, raw, "FRESH_AUG2026_US")
    if len(events):
        events["session_id"] = pd.to_datetime(events.contact_time, utc=True).dt.tz_convert(NY).dt.strftime("%Y-%m-%d")
        events = events[events.session_id.isin(set(complete))].copy()
    resolved = events[events["label"].notna()].copy() if len(events) and "label" in events.columns else pd.DataFrame()
    out = {
        "status": None,
        "scope": "BUY US 08:00-17:00 America/New_York",
        "cadence": "C5",
        "architecture": "Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50",
        "source": source,
        "eligible_session_count": int(len(complete)),
        "eligible_session_ids": complete,
        "session_completeness": completeness,
        "contact_count": int(len(cdf)),
        "first_bull_event_count": int(len(events)),
        "resolved_first_bull_n": int(len(resolved)),
        "first_bull_nonfire_reasons": {str(k): int(v) for k, v in first_reasons.items()},
        "fresh_model_refit": False,
        "fresh_cutpoint_optimization": False,
        "pine_authorization": "NONE",
    }

    adequate = len(complete) >= 8 and len(resolved) >= 300
    out["sample_adequacy"] = {
        "adequate": bool(adequate),
        "sessions_ge_8": bool(len(complete) >= 8),
        "resolved_n_ge_300": bool(len(resolved) >= 300),
    }
    if not adequate:
        out["status"] = "INSUFFICIENT_FRESH_SAMPLE"
        out["production_decision"] = "ACCUMULATE_FUTURE_FRESH_SAMPLE_NO_REPLACEMENT"
        events.to_csv(a.events_csv, index=False, compression="gzip")
        Path(a.output_json).write_text(json.dumps(out, indent=2, default=str))
        print(json.dumps(out, indent=2, default=str))
        return

    resolved = model_scores(resolved, frozen)
    events["geometry_score"] = np.nan
    events["closepos_score"] = np.nan
    events.loc[resolved.index, "geometry_score"] = resolved["geometry_score"]
    events.loc[resolved.index, "closepos_score"] = resolved["closepos_score"]
    q20 = float(frozen["model"]["h1_score_quantiles"]["q20"])
    q80 = float(frozen["model"]["h1_score_quantiles"]["q80"])
    y = resolved.label.astype(int)

    auc6 = float(roc_auc_score(y, resolved.geometry_score))
    auc6_ci, auc6_nboot = bootstrap_auc(resolved, "geometry_score")
    ap6 = float(average_precision_score(y, resolved.geometry_score))
    brier6 = float(brier_score_loss(y, resolved.geometry_score))
    prevalence = float(y.mean())
    brier_const = float(brier_score_loss(y, np.full(len(y), prevalence)))

    auc0 = float(roc_auc_score(y, resolved.closepos_score))
    auc0_ci, auc0_nboot = bootstrap_auc(resolved, "closepos_score")
    aucdiff = auc6 - auc0
    aucdiff_ci, aucdiff_nboot = bootstrap_auc_diff(resolved, "geometry_score", "closepos_score")

    bottom, middle, top, bands = band_summary(resolved, q20, q80)
    band_diff = float(top.label.mean() - bottom.label.mean()) if len(top) and len(bottom) else None
    band_diff_ci, band_nboot = bootstrap_band_diff(top, bottom, complete)

    legacy = resolved[resolved.close_pos >= .70]
    range_auc = float(roc_auc_score(y, resolved.range_v))
    status_counts = events.status.value_counts().to_dict()

    gates = {
        "frozen_h1_model_auc_gt_050": bool(auc6 > .50),
        "frozen_h1_model_auc_ci_lower_gt_050": bool(auc6_ci[0] > .50),
        "frozen_score_top_rate_gt_bottom_rate": bool(len(top) and len(bottom) and top.label.mean() > bottom.label.mean()),
        "frozen_score_band_diff_ci_lower_gt_0": bool(band_diff_ci[0] > 0),
    }
    passed = bool(all(gates.values()))

    out.update({
        "status": "FRESH_GEOMETRY_SIGNAL_PASS" if passed else "FRESH_GEOMETRY_SIGNAL_FAIL",
        "resolved_status_counts": {str(k): int(v) for k, v in status_counts.items()},
        "positive_rate": prevalence,
        "primary": {
            "frozen_h1_6feature_auc": auc6,
            "session_bootstrap_auc_ci95": auc6_ci,
            "auc_bootstrap_valid_draws": auc6_nboot,
            "frozen_score_q20": q20,
            "frozen_score_q80": q80,
            "score_bands": bands,
            "top_minus_bottom_tp1_rate": band_diff,
            "session_bootstrap_top_minus_bottom_ci95": band_diff_ci,
            "band_bootstrap_valid_draws": band_nboot,
            "gates": gates,
            "pass": passed,
        },
        "secondary": {
            "average_precision": ap6,
            "brier": brier6,
            "constant_prevalence_brier": brier_const,
            "frozen_closepos_only_auc": auc0,
            "frozen_closepos_only_auc_ci95": auc0_ci,
            "closepos_auc_bootstrap_valid_draws": auc0_nboot,
            "six_feature_minus_closepos_auc": aucdiff,
            "six_feature_minus_closepos_auc_ci95": aucdiff_ci,
            "auc_diff_bootstrap_valid_draws": aucdiff_nboot,
            "legacy_first_bull_close_pos_ge_070": {
                "n": int(len(legacy)),
                "tp1_positive_rate": float(legacy.label.mean()) if len(legacy) else None,
            },
            "range_v_univariate_auc": range_auc,
        },
        "production_decision": (
            "AUTHORIZE_NEW_RESEARCH_CYCLE_FIRST_BULL_CONTINUOUS_GEOMETRY_NO_OLD_E_MODEL_NO_PINE"
            if passed else
            "RETAIN_BR70_LEGACY_E_SCORE_LINEAGE_NO_NATURAL_70PCT_CLAIM"
        ),
    })
    events.to_csv(a.events_csv, index=False, compression="gzip")
    Path(a.output_json).write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
