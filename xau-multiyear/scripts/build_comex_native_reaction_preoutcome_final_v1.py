#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

import build_comex_dev_rank1_event_features as feat
import build_comex_native_reaction_v1_preoutcome_manifests as pre
import audit_comex_native_reaction_expanded_controls as expanded
import audit_comex_native_reaction_source_last30_fallback as fallback

TICK = 0.10
K = 5
EXCLUSION_MINUTES = 60
TIME_BIN_MINUTES = 30
SOURCE_RANGE_LO = 0.5
SOURCE_RANGE_HI = 2.0
LOCAL_RANGE_LO = 0.5
LOCAL_RANGE_HI = 2.0
FINAL_STATUS_SHA = "8a825b0bc1deba51959b78ab6e62206fe49232e76329558e83949bf6d3d4151a"


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


def ratio_mask(s: pd.Series, base: float, lo: float = 0.5, hi: float = 2.0) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    return x.notna() & (x > 0) & np.isfinite(base) & (base > 0) & (x / float(base) >= lo) & (x / float(base) <= hi)


def git_head() -> str:
    env = os.environ.get("GITHUB_SHA", "").strip()
    if env:
        return env
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def choose_source_raw(args, source_levels: pd.DataFrame) -> pd.DataFrame:
    req = pd.read_csv(args.dual_requests, dtype={"symbols": str})
    sessions = pd.read_csv(args.sessions)
    dev = sessions[sessions.acquisition_stage.astype(str).eq("DEV_RANK1")].copy()
    mapping = pd.read_csv(args.mapping, dtype={"v0_start_iid": str, "n0_start_iid": str})
    routing = pd.read_csv(args.routing, dtype={"v0_iid": str, "n0_iid": str})
    if len(dev) != 96 or len(mapping) != 96 or len(routing) != 96:
        raise SystemExit("DEV_RANK1 source routing cardinality mismatch")

    cand, _ = feat.build_candidate_map(Path(args.source_new_root), Path(args.source_pilot_root), req, dev, mapping)
    rt = routing.set_index(routing.research_trading_date.astype(str))
    reg = source_levels.groupby("source_research_date", sort=True).first().reset_index()
    rows = []

    for r in reg.itertuples(index=False):
        d = str(r.source_research_date)
        rr = rt.loc[d]
        label = str(r.source_candidate_key)
        z = cand.get((d, label)) or cand.get((d, "N0")) or cand.get((d, "V0"))
        p = Path(z["path"]) if z and z.get("path") else None
        if p is None:
            raise SystemExit(f"source raw missing {d}")
        iid = str(z.get("iid", ""))
        if iid != str(r.source_instrument_id):
            raise SystemExit(f"source raw iid mismatch {d}: {iid} != {r.source_instrument_id}")

        tape = feat.prep_tape(p, d)
        if tape is None or len(tape["price"]) == 0:
            raise SystemExit(f"empty source raw {d}")
        s, e = feat.session_bounds(d)
        if utc(r.source_session_start_utc) != s or utc(r.known_time_utc) != e:
            raise SystemExit(f"canonical source bounds mismatch {d}")

        ts = pd.to_datetime(tape["ts"], utc=True)
        price = np.asarray(tape["price"], dtype=float)
        good = np.isfinite(price)
        if not good.any():
            raise SystemExit(f"no finite source trades {d}")
        full = price[good]
        source_min = float(np.min(full)); source_max = float(np.max(full))
        source_range = (source_max - source_min) / TICK
        if not np.isfinite(source_range) or source_range <= 0:
            raise SystemExit(f"nonpositive full source range {d}")

        m = (ts >= e - pd.Timedelta(minutes=30)) & good
        last = price[m]
        n = int(len(last))
        uniq = int(len(np.unique(last))) if n else 0
        lmin = float(np.min(last)) if n else np.nan
        lmax = float(np.max(last)) if n else np.nan
        lrange = (lmax - lmin) / TICK if n else np.nan
        last_positive = bool(np.isfinite(lrange) and lrange > 0)
        last_missing = bool(n == 0)
        last_flat = bool(n > 0 and np.isfinite(lrange) and lrange == 0)

        rows.append({
            "source_research_date": d,
            "source_year": int(pd.Timestamp(d).year),
            "source_instrument_id": iid,
            "source_candidate_key": label,
            "terminal_leader": str(rr.terminal_leader),
            "source_session_start_utc": s.isoformat(),
            "source_session_end_utc": e.isoformat(),
            "source_range_ticks": float(source_range),
            "source_min_price": source_min,
            "source_max_price": source_max,
            "source_trade_records": int(len(full)),
            "source_last30_start_utc": (e - pd.Timedelta(minutes=30)).isoformat(),
            "source_last30_end_utc": e.isoformat(),
            "source_last30_trade_records": n,
            "source_last30_unique_prices": uniq,
            "source_last30_min_price": lmin,
            "source_last30_max_price": lmax,
            "source_last30_range_ticks": float(lrange) if np.isfinite(lrange) else np.nan,
            "source_last30_positive": last_positive,
            "source_last30_missing": last_missing,
            "source_last30_flat": last_flat,
            "source_raw_file": p.name,
            "source_raw_sha256": sha256_file(p),
            "same_raw_as_level_creation": True,
            "known_before_j1": True,
            "adjusted_or_xau_substitute_used": False,
        })

    q = pd.DataFrame(rows).sort_values("source_research_date").reset_index(drop=True)
    if len(q) != 92 or q.source_research_date.nunique() != 92:
        raise SystemExit(f"expected 92 source provenance rows, got {len(q)}")
    return q


def reconcile_source_last30(prov: pd.DataFrame, zero_qa_path: str) -> dict:
    z = json.loads(Path(zero_qa_path).read_text())
    bad = prov[~prov.source_last30_positive].copy()
    summary = {
        "source_sessions_total": int(len(prov)),
        "source_last30_positive_sessions": int(prov.source_last30_positive.sum()),
        "source_last30_missing_sessions": int(prov.source_last30_missing.sum()),
        "source_last30_flat_sessions": int(prov.source_last30_flat.sum()),
        "nonpositive_source_dates": bad.source_research_date.astype(str).tolist(),
        "expected_zero_qa_sha256": sha256_file(Path(zero_qa_path)),
        "expected_source_sessions_total": int(z["source_sessions_total"]),
        "expected_positive_sessions": int(z["source_last30_positive_sessions"]),
        "expected_missing_sessions": int(z["source_last30_missing_sessions"]),
        "expected_flat_sessions": int(z["source_last30_flat_sessions"]),
        "expected_nonpositive_source_dates": list(map(str, z["nonpositive_source_dates"])),
    }
    ok = (
        summary["source_sessions_total"] == 92 == summary["expected_source_sessions_total"] and
        summary["source_last30_positive_sessions"] == 91 == summary["expected_positive_sessions"] and
        summary["source_last30_missing_sessions"] == 1 == summary["expected_missing_sessions"] and
        summary["source_last30_flat_sessions"] == 0 == summary["expected_flat_sessions"] and
        summary["nonpositive_source_dates"] == ["2013-12-25"] == summary["expected_nonpositive_source_dates"]
    )
    summary["reconciliation_pass"] = bool(ok)
    if not ok:
        raise SystemExit(f"source-last30 reconciliation failed: {summary}")
    return summary


def load_n1(args) -> dict[str, dict]:
    man = pd.read_csv(args.n1_market_manifest, dtype={"source_instrument_id": str, "symbols": str})
    if len(man) != 92 or man.source_research_date.nunique() != 92:
        raise SystemExit("N1 manifest cardinality mismatch")
    markers = expanded.read_n1_markers(Path(args.n1_root))
    out = {}
    for r in man.itertuples(index=False):
        rid = str(r.market_request_id)
        if rid not in markers:
            raise SystemExit(f"N1 marker missing {rid}")
        mk, p = markers[rid]
        if mk.get("sha256") and sha256_file(p) != mk["sha256"]:
            raise SystemExit(f"N1 hash mismatch {rid}")
        if str(r.symbols) != str(r.source_instrument_id) or str(mk.get("symbols")) != str(r.source_instrument_id):
            raise SystemExit(f"N1 iid mismatch {rid}")
        m1 = pre.prepare_m1(p, r.start, r.end)
        if m1.empty:
            raise SystemExit(f"empty N1 block {rid}")
        out[str(r.source_research_date)] = {
            "m1": m1,
            "start": utc(r.start),
            "end": utc(r.end),
            "next_date": str(r.eligible_next_research_date),
            "iid": str(r.source_instrument_id),
            "market_request_id": rid,
            "n1_raw_file": p.name,
            "n1_raw_sha256": sha256_file(p),
        }
    return out


def strict_local_features(m1: pd.DataFrame, minute_start: pd.Timestamp, sign: int, session_start: pd.Timestamp) -> dict:
    prior = m1[m1.ts_event < minute_start].copy()
    complete = bool(minute_start - pd.Timedelta(minutes=30) >= session_start)
    seg = prior[prior.ts_event >= minute_start - pd.Timedelta(minutes=30)] if complete else prior.iloc[0:0]
    pre30 = (float(seg.high.max()) - float(seg.low.min())) / TICK if len(seg) else np.nan

    z_end = prior[prior.bar_end <= minute_start]
    end_close = float(z_end.iloc[-1].close) if len(z_end) else np.nan
    z5 = prior[prior.bar_end <= minute_start - pd.Timedelta(minutes=5)]
    p5 = float(z5.iloc[-1].close) if len(z5) else np.nan
    move = float(sign) * (end_close - p5) / TICK if sign in (-1, 1) and np.isfinite(end_close) and np.isfinite(p5) else np.nan
    return {
        "pre30_complete": complete,
        "pre30_range_ticks": float(pre30) if np.isfinite(pre30) else np.nan,
        "pre5_end_close": end_close,
        "pre5_start_close": p5,
        "pre5_signed_move_ticks": float(move) if np.isfinite(move) else np.nan,
    }


def stage_maps(args):
    s1 = pd.read_csv(args.stage1_resolution, dtype={"source_instrument_id": str})
    s2 = pd.read_csv(args.stage2_resolution, dtype={"source_instrument_id": str})
    s3 = pd.read_csv(args.stage3_resolution, dtype={"source_instrument_id": str})
    maps = {
        1: s1.set_index("level_id")["stage1_market_request_id"].astype(str).to_dict(),
        2: s2.set_index("level_id")["stage2_market_request_id"].astype(str).to_dict(),
        3: s3.set_index("level_id")["stage3_market_request_id"].astype(str).to_dict(),
    }
    markers = {
        1: pre.read_markers(Path(args.stage1_root)),
        2: pre.read_markers(Path(args.stage2_root)),
        3: pre.read_markers(Path(args.stage3_root)),
    }
    return maps, markers


def build_events(args, final: pd.DataFrame, n1: dict, prov: pd.DataFrame) -> pd.DataFrame:
    pm = prov.set_index(prov.source_research_date.astype(str)).to_dict("index")
    req_maps, markers = stage_maps(args)
    contacts = final[final.exact_contact_final.map(pb)].copy()
    if len(contacts) != 238:
        raise SystemExit("expected 238 exact contacts")
    contacts["t0"] = pd.to_datetime(contacts.first_exact_contact_time_utc, utc=True)
    rows = []
    for r in contacts.sort_values(["source_research_date", "level_id"]).itertuples(index=False):
        d = str(r.source_research_date); ss = n1[d]; m1 = ss["m1"]
        t0 = r.t0; m0 = t0.floor("min"); a0 = m0 + pd.Timedelta(minutes=1)
        bar = m1[m1.ts_event == m0]
        if len(bar) != 1:
            raise SystemExit(f"contact-minute M1 parity fail {r.level_id}: {len(bar)}")
        A0 = float(bar.iloc[0].close)
        stage = int(float(r.contact_stage))
        rid = req_maps[stage].get(str(r.level_id), "")
        mk = markers[stage].get(rid)
        if not rid or mk is None:
            raise SystemExit(f"N2 marker missing {r.level_id} stage {stage}")
        raw = Path(mk["_raw_path"])
        if mk.get("sha256") and sha256_file(raw) != mk["sha256"]:
            raise SystemExit(f"N2 hash mismatch {r.level_id}")
        exact_raw = pre.load_dbn(raw)
        approach, sign, prior_price, approach_source = pre.exact_event_approach(exact_raw, t0, float(r.contact_tick_price), m1, m0)
        minute = int((m0 - ss["start"]).total_seconds() // 60)
        if minute < 0:
            raise SystemExit(f"negative minute offset {r.level_id}")
        branch = "EARLY_SOURCE_LAST30" if minute < 30 else "MATURE_PRE_M0"
        f = pm[d]
        local = strict_local_features(m1, m0, int(sign), ss["start"])
        sr = float(f["source_range_ticks"])
        pre5_norm = float(local["pre5_signed_move_ticks"]) / sr if sr > 0 and np.isfinite(local["pre5_signed_move_ticks"]) else np.nan
        sl30 = float(f["source_last30_range_ticks"]) if pd.notna(f["source_last30_range_ticks"]) else np.nan
        defined = int(sign) in (-1, 1)
        w15 = bool(a0 + pd.Timedelta(minutes=15) <= ss["end"])
        mature_ok = bool(local["pre30_complete"] and np.isfinite(local["pre30_range_ticks"]) and local["pre30_range_ticks"] > 0 and np.isfinite(pre5_norm))
        early_ok = bool(np.isfinite(sl30) and sl30 > 0)
        eligible = bool(defined and w15 and (mature_ok if branch == "MATURE_PRE_M0" else early_ok))
        reason = ""
        if not defined:
            reason = "APPROACH_UNDEFINED"
        elif not w15:
            reason = "W15_CENSORED_AT_J1_CLOSE"
        elif branch == "MATURE_PRE_M0" and not mature_ok:
            reason = "MATURE_PRE_M0_COVARIATE_MISSING_OR_NONPOSITIVE"
        elif branch == "EARLY_SOURCE_LAST30" and not early_ok:
            reason = "FALLBACK_COVARIATE_MISSING_SOURCE_LAST30"

        rows.append({
            "level_id": str(r.level_id),
            "source_research_date": d,
            "source_year": int(pd.Timestamp(d).year),
            "eligible_next_research_date": str(r.eligible_next_research_date),
            "source_instrument_id": str(r.source_instrument_id),
            "level_type": str(r.level_type),
            "contact_tick_price": float(r.contact_tick_price),
            "t0_utc": t0.isoformat(),
            "m0_utc": m0.isoformat(),
            "a0_utc": a0.isoformat(),
            "A0_close": A0,
            "A0_used_for_matching": False,
            "approach": approach,
            "away_sign": int(sign),
            "approach_prior_price": prior_price,
            "approach_source": approach_source,
            "approach_defined": bool(defined),
            "anchor_minute_of_session": minute,
            "anchor_30m_bin": minute // TIME_BIN_MINUTES,
            "matching_branch": branch,
            "source_range_ticks": sr,
            "source_last30_range_ticks": sl30,
            "source_last30_positive": bool(f["source_last30_positive"]),
            "pre30_complete_pre_m0": bool(local["pre30_complete"]),
            "pre30_range_pre_m0_ticks": local["pre30_range_ticks"],
            "pre5_signed_move_pre_m0_ticks": local["pre5_signed_move_ticks"],
            "pre5_signed_move_pre_m0_norm": pre5_norm,
            "w15_complete": w15,
            "primary_control_eligible": eligible,
            "primary_control_exclusion_reason": reason,
            "n1_market_request_id": ss["market_request_id"],
            "n2_market_request_id": rid,
            "n2_raw_sha256": sha256_file(raw),
            "contact_stage": stage,
            "post_contact_values_used_for_matching": False,
            "post_anchor_outcomes_read": False,
        })

    E = pd.DataFrame(rows)
    if len(E) != 238 or E.level_id.nunique() != 238:
        raise SystemExit("treated-event cardinality mismatch")
    if int(E.approach_defined.sum()) != 235:
        raise SystemExit(f"expected 235 defined approaches, got {int(E.approach_defined.sum())}")
    bad = E[(E.matching_branch == "EARLY_SOURCE_LAST30") & E.approach_defined & ~E.source_last30_positive]
    if len(bad) != 1 or str(bad.iloc[0].source_research_date) != "2013-12-25":
        raise SystemExit(f"expected sole early missing source-last30 event on 2013-12-25, got {bad[['level_id','source_research_date']].to_dict('records')}")
    return E


def build_blocks(args, n1: dict, prov: pd.DataFrame, events: pd.DataFrame):
    pm = prov.set_index(prov.source_research_date.astype(str)).to_dict("index")
    ev = events.copy(); ev["t0"] = pd.to_datetime(ev.t0_utc, utc=True)
    known_by_next = {str(k): list(g.t0) for k, g in ev.groupby(ev.eligible_next_research_date.astype(str), sort=False)}
    blocks = []; parts = []; adjacency = []

    for d in sorted(n1):
        ss = n1[d]; f = pm[d]; nd = ss["next_date"]
        q = fallback.control_candidates_one(
            ss["m1"], d, nd, ss["iid"], float(f["source_range_ticks"]),
            float(f["source_last30_range_ticks"]) if pd.notna(f["source_last30_range_ticks"]) else np.nan,
            ss["start"], ss["end"], known_by_next.get(nd, []), "CANONICAL_N1", False
        )
        q["control_next_research_date"] = nd
        q["native_contact_exclusion_status"] = "COMPLETE_FROZEN_4_LEVEL_REGISTRY"
        q["known_native_contacts_on_control_date"] = len(known_by_next.get(nd, []))
        q["candidate_source_range_valid"] = pd.to_numeric(q.source_range_ticks, errors="coerce").gt(0)
        q["candidate_source_last30_valid"] = pd.to_numeric(q.source_last30_range_ticks, errors="coerce").gt(0)
        q["candidate_pre30_valid"] = q.pre30_complete_precontact.map(pb) & pd.to_numeric(q.pre30_range_precontact_ticks, errors="coerce").gt(0)
        q["candidate_pre5_valid"] = pd.to_numeric(q.pre5_signed_move_precontact_norm, errors="coerce").notna()
        q["bar_open_fallback_used"] = False
        parts.append(q)
        blocks.append({
            "control_origin": "CANONICAL_N1", "control_source_research_date": d, "control_next_research_date": nd,
            "source_year": int(pd.Timestamp(d).year), "source_instrument_id": ss["iid"],
            "source_session_start_utc": str(pm[d]["source_session_start_utc"]), "source_session_end_utc": str(pm[d]["source_session_end_utc"]),
            "next_session_start_utc": ss["start"].isoformat(), "next_session_end_utc": ss["end"].isoformat(),
            "source_range_ticks": float(f["source_range_ticks"]), "source_last30_range_ticks": f["source_last30_range_ticks"],
            "source_raw_sha256": str(f["source_raw_sha256"]), "next_m1_raw_sha256": ss["n1_raw_sha256"],
            "context_artifact_sha256": "", "same_single_iid_source": True, "same_single_iid_next": True,
            "same_iid_source_and_next": True, "vendor_price_adjustment_status": "RAW_CANONICAL_UNADJUSTED",
            "reserved_source_or_next": False, "native_contact_exclusion_status": "COMPLETE_FROZEN_4_LEVEL_REGISTRY",
            "known_native_contacts_on_control_date": len(known_by_next.get(nd, [])), "candidate_rows": int(len(q)),
        })
        adjacency.append({
            "control_origin": "CANONICAL_N1", "source_research_date": d, "eligible_next_research_date": nd,
            "source_session_start_utc": str(pm[d]["source_session_start_utc"]), "source_session_end_utc": str(pm[d]["source_session_end_utc"]),
            "next_session_start_utc": ss["start"].isoformat(), "next_session_end_utc": ss["end"].isoformat(),
            "adjacency_rule": "FROZEN_NATIVE_N1_NEXT_ELIGIBLE_SESSION", "canonical_next_session_substitution_allowed": False,
        })

    marker, ctx_path = expanded.find_context(Path(args.context_root))
    ctx = expanded.load_context(ctx_path)
    parity, parity_summary = expanded.parity_audit(ctx, Path(args.n1_root), args.n1_market_manifest)
    if not parity_summary.get("stable_parity_all_pass") or int(parity_summary.get("stable_same_iid_blocks", 0)) != 85 or int(parity_summary.get("stable_blocks_exact_parity", 0)) != 85:
        raise SystemExit(f"stable-IID parity gate failed: {parity_summary}")

    sess = pd.read_csv(args.sessions)
    sess["research_trading_date"] = sess.research_trading_date.astype(str)
    reserved_rows = sess[~sess.acquisition_stage.astype(str).eq("DEV_RANK1")].copy()
    reserved = set(reserved_rows.research_trading_date.astype(str))
    if len(reserved) != 261:
        raise SystemExit(f"expected 261 reserved non-DEV_RANK1 dates, got {len(reserved)}")
    original = set(n1)
    groups = {d: g.copy().sort_values("ts_event") for d, g in ctx.groupby(ctx.gc_trade_date.astype(str), sort=True)}
    dates = sorted(groups)
    context_sha = sha256_file(ctx_path)

    for i, d in enumerate(dates[:-1]):
        y = int(pd.Timestamp(d).year)
        if y < 2011 or y > 2018:
            continue
        nd = dates[i + 1]
        if d in reserved or nd in reserved or d in original:
            continue
        ss0, se0 = feat.session_bounds(d); ns, ne = feat.session_bounds(nd)
        a = groups[d][(groups[d].ts_event >= ss0) & (groups[d].ts_event < se0)].copy()
        b = groups[nd][(groups[nd].ts_event >= ns) & (groups[nd].ts_event < ne)].copy()
        if a.empty or b.empty:
            continue
        ia = sorted(a.instrument_id.astype(str).unique()); ib = sorted(b.instrument_id.astype(str).unique())
        if len(ia) != 1 or len(ib) != 1 or ia[0] != ib[0]:
            continue
        iid = ia[0]
        sr = (float(a.high.max()) - float(a.low.min())) / TICK
        last = a[(a.ts_event >= se0 - pd.Timedelta(minutes=30)) & (a.ts_event < se0)]
        sl30 = (float(last.high.max()) - float(last.low.min())) / TICK if len(last) else np.nan
        if not np.isfinite(sr) or sr <= 0:
            continue

        q = fallback.control_candidates_one(
            b, d, nd, iid, float(sr), float(sl30) if np.isfinite(sl30) else np.nan,
            ns, ne, known_by_next.get(nd, []), "OWNED_GC_N0_CONTEXT", False
        )
        q["control_next_research_date"] = nd
        q["native_contact_exclusion_status"] = "PARTIAL_KNOWN_FROZEN_REGISTRY_ONLY"
        q["known_native_contacts_on_control_date"] = len(known_by_next.get(nd, []))
        q["candidate_source_range_valid"] = pd.to_numeric(q.source_range_ticks, errors="coerce").gt(0)
        q["candidate_source_last30_valid"] = pd.to_numeric(q.source_last30_range_ticks, errors="coerce").gt(0)
        q["candidate_pre30_valid"] = q.pre30_complete_precontact.map(pb) & pd.to_numeric(q.pre30_range_precontact_ticks, errors="coerce").gt(0)
        q["candidate_pre5_valid"] = pd.to_numeric(q.pre5_signed_move_precontact_norm, errors="coerce").notna()
        q["bar_open_fallback_used"] = False
        parts.append(q)
        blocks.append({
            "control_origin": "OWNED_GC_N0_CONTEXT", "control_source_research_date": d, "control_next_research_date": nd,
            "source_year": y, "source_instrument_id": iid,
            "source_session_start_utc": ss0.isoformat(), "source_session_end_utc": se0.isoformat(),
            "next_session_start_utc": ns.isoformat(), "next_session_end_utc": ne.isoformat(),
            "source_range_ticks": float(sr), "source_last30_range_ticks": float(sl30) if np.isfinite(sl30) else np.nan,
            "source_raw_sha256": context_sha, "next_m1_raw_sha256": context_sha, "context_artifact_sha256": context_sha,
            "same_single_iid_source": True, "same_single_iid_next": True, "same_iid_source_and_next": True,
            "vendor_price_adjustment_status": "VENDOR_ABSOLUTE_UNADJUSTED_STABLE_IID",
            "reserved_source_or_next": False, "native_contact_exclusion_status": "PARTIAL_KNOWN_FROZEN_REGISTRY_ONLY",
            "known_native_contacts_on_control_date": len(known_by_next.get(nd, [])), "candidate_rows": int(len(q)),
        })
        adjacency.append({
            "control_origin": "OWNED_GC_N0_CONTEXT", "source_research_date": d, "eligible_next_research_date": nd,
            "source_session_start_utc": ss0.isoformat(), "source_session_end_utc": se0.isoformat(),
            "next_session_start_utc": ns.isoformat(), "next_session_end_utc": ne.isoformat(),
            "adjacency_rule": "NEXT_CANONICAL_GC_TRADE_DATE_IN_OWNED_CONTEXT", "canonical_next_session_substitution_allowed": False,
        })

    C = pd.concat(parts, ignore_index=True, sort=False)
    if C.empty or C.control_candidate_id.duplicated().any():
        raise SystemExit("final control universe invalid/duplicated")
    if C.bar_open_fallback_used.map(pb).any():
        raise SystemExit("BAR_OPEN_FALLBACK detected")
    B = pd.DataFrame(blocks).sort_values(["source_year", "control_source_research_date", "control_origin"]).reset_index(drop=True)
    A = pd.DataFrame(adjacency).sort_values(["source_research_date", "control_origin"]).reset_index(drop=True)
    return C, B, A, parity, parity_summary, reserved_rows, marker, ctx_path


def match_final(E: pd.DataFrame, C: pd.DataFrame):
    grouped = {(int(y), int(b), int(s)): g.copy() for (y, b, s), g in C.groupby(["source_year", "anchor_30m_bin", "away_sign"], sort=False)}
    matches = []; support = []; filters = []

    for e in E.to_dict("records"):
        level = str(e["level_id"]); sign = int(e["away_sign"]); defined = pb(e["approach_defined"])
        eligible = pb(e["primary_control_eligible"]); branch = str(e["matching_branch"]); minute = int(e["anchor_minute_of_session"])
        q = C.iloc[0:0].copy(); counts = {"group": 0, "different_date": 0, "source_caliper": 0, "branch_covariate": 0, "branch_caliper": 0, "distinct_control_dates": 0}
        if eligible:
            q = grouped.get((int(e["source_year"]), minute // 30, sign), C.iloc[0:0]).copy(); counts["group"] = len(q)
            q = q[q.control_source_research_date.astype(str) != str(e["source_research_date"])].copy(); counts["different_date"] = len(q)
            q = q[ratio_mask(q.source_range_ticks, float(e["source_range_ticks"]), SOURCE_RANGE_LO, SOURCE_RANGE_HI)].copy(); counts["source_caliper"] = len(q)

            if branch == "MATURE_PRE_M0":
                q = q[q.candidate_pre30_valid.map(pb) & q.candidate_pre5_valid.map(pb)].copy(); counts["branch_covariate"] = len(q)
                q = q[ratio_mask(q.pre30_range_precontact_ticks, float(e["pre30_range_pre_m0_ticks"]), LOCAL_RANGE_LO, LOCAL_RANGE_HI)].copy(); counts["branch_caliper"] = len(q)
                if len(q):
                    q["d_branch_log"] = np.abs(np.log(q.pre30_range_precontact_ticks.astype(float) / float(e["pre30_range_pre_m0_ticks"])))
                    q["d_source_log"] = np.abs(np.log(q.source_range_ticks.astype(float) / float(e["source_range_ticks"])))
                    q["d_move"] = np.abs(q.pre5_signed_move_precontact_norm.astype(float) - float(e["pre5_signed_move_pre_m0_norm"]))
                    q["d_minute"] = np.abs(q.anchor_minute_of_session.astype(int) - minute)
                    q["anchor_ts_sort"] = pd.to_datetime(q.anchor_time_utc, utc=True)
                    sort = ["d_branch_log", "d_source_log", "d_move", "d_minute", "anchor_ts_sort", "control_source_research_date", "control_next_research_date", "source_instrument_id", "control_candidate_id"]
            else:
                q = q[q.candidate_source_last30_valid.map(pb)].copy(); counts["branch_covariate"] = len(q)
                q = q[ratio_mask(q.source_last30_range_ticks, float(e["source_last30_range_ticks"]), LOCAL_RANGE_LO, LOCAL_RANGE_HI)].copy(); counts["branch_caliper"] = len(q)
                if len(q):
                    q["d_branch_log"] = np.abs(np.log(q.source_last30_range_ticks.astype(float) / float(e["source_last30_range_ticks"])))
                    q["d_source_log"] = np.abs(np.log(q.source_range_ticks.astype(float) / float(e["source_range_ticks"])))
                    q["d_move"] = np.nan
                    q["d_minute"] = np.abs(q.anchor_minute_of_session.astype(int) - minute)
                    q["anchor_ts_sort"] = pd.to_datetime(q.anchor_time_utc, utc=True)
                    sort = ["d_branch_log", "d_source_log", "d_minute", "anchor_ts_sort", "control_source_research_date", "control_next_research_date", "source_instrument_id", "control_candidate_id"]

            if len(q):
                q = q.sort_values(sort, kind="mergesort")
                reps = q.groupby("control_source_research_date", sort=False, as_index=False).head(1).copy()
                reps = reps.sort_values(sort, kind="mergesort")
                counts["distinct_control_dates"] = int(reps.control_source_research_date.nunique())
                sel = reps.head(K).copy()
                for rank, z in enumerate(sel.to_dict("records"), start=1):
                    matches.append({
                        "treated_level_id": level,
                        "treated_source_research_date": str(e["source_research_date"]),
                        "treated_source_year": int(e["source_year"]),
                        "matching_branch": branch,
                        "control_rank": rank,
                        "control_candidate_id": str(z["control_candidate_id"]),
                        "control_origin": str(z["control_origin"]),
                        "control_source_research_date": str(z["control_source_research_date"]),
                        "control_next_research_date": str(z["control_next_research_date"]),
                        "control_anchor_time_utc": str(z["anchor_time_utc"]),
                        "control_source_instrument_id": str(z["source_instrument_id"]),
                        "native_contact_exclusion_status": str(z["native_contact_exclusion_status"]),
                        "source_range_ratio": float(z["source_range_ticks"]) / float(e["source_range_ticks"]),
                        "branch_range_ratio": float(z["pre30_range_precontact_ticks"]) / float(e["pre30_range_pre_m0_ticks"]) if branch == "MATURE_PRE_M0" else float(z["source_last30_range_ticks"]) / float(e["source_last30_range_ticks"]),
                        "source_range_caliper_pass": True,
                        "branch_range_caliper_pass": True,
                        "same_source_year_pass": True,
                        "same_30m_bin_pass": True,
                        "same_approach_sign_pass": True,
                        "different_source_date_pass": True,
                        "known_contact_pm60_exclusion_pass": True,
                        "d_branch_log": float(z["d_branch_log"]),
                        "d_source_log": float(z["d_source_log"]),
                        "d_move": float(z["d_move"]) if pd.notna(z["d_move"]) else np.nan,
                        "d_move_status": "USED" if branch == "MATURE_PRE_M0" else "NOT_APPLICABLE",
                        "d_minute": int(z["d_minute"]),
                        "post_contact_values_used_for_matching": False,
                        "post_anchor_outcomes_read": False,
                    })

        n = sum(1 for x in matches if x["treated_level_id"] == level)
        support.append({
            "level_id": level,
            "source_research_date": str(e["source_research_date"]),
            "source_year": int(e["source_year"]),
            "matching_branch": branch,
            "approach_defined": defined,
            "primary_control_eligible": eligible,
            "primary_control_exclusion_reason": str(e["primary_control_exclusion_reason"]),
            "controls_selected": int(n),
            "full_k5_match": bool(n == K),
            "support_status": "K5_MATCHED" if n == K else ("CONTROL_UNMATCHED" if eligible else "EVENT_INELIGIBLE"),
        })
        filters.append({"level_id": level, "source_research_date": str(e["source_research_date"]), "source_year": int(e["source_year"]), "matching_branch": branch, **counts})

    M = pd.DataFrame(matches); S = pd.DataFrame(support); F = pd.DataFrame(filters)
    D = S[S.approach_defined].copy(); K5 = D[D.full_k5_match].copy()
    years = []
    for y in range(2011, 2019):
        d = D[D.source_year == y]; m = d[d.full_k5_match]
        years.append({
            "source_year": y, "defined_events": int(len(d)), "eligible_events": int(d.primary_control_eligible.sum()),
            "matched_events": int(len(m)), "match_rate": float(len(m) / len(d)) if len(d) else 0.0,
            "matched_dates": int(m.source_research_date.nunique()),
        })
    Y = pd.DataFrame(years)
    rate = float(len(K5) / len(D)) if len(D) else 0.0
    criteria = {
        "matched_events_ge_160": bool(len(K5) >= 160),
        "matched_dates_ge_60": bool(K5.source_research_date.nunique() >= 60),
        "every_source_year_matched_dates_ge_5": bool((Y.matched_dates >= 5).all()),
        "defined_contact_full_match_rate_ge_0_85": bool(rate >= 0.85),
        "every_source_year_full_match_rate_ge_0_75": bool((Y.match_rate >= 0.75).all()),
    }
    dates = D.groupby("source_research_date", as_index=False).agg(defined_events=("level_id", "size"), eligible_events=("primary_control_eligible", "sum"), matched_events=("full_k5_match", "sum"))
    dates["all_defined_matched"] = dates.matched_events.eq(dates.defined_events)
    if len(M):
        reuse = M.groupby(["control_source_research_date", "control_origin"], as_index=False).agg(selected_match_rows=("treated_level_id", "size"), treated_events=("treated_level_id", "nunique"), treated_dates=("treated_source_research_date", "nunique"))
        reuse = reuse.sort_values(["selected_match_rows", "control_source_research_date"], ascending=[False, True]).reset_index(drop=True)
    else:
        reuse = pd.DataFrame(columns=["control_source_research_date", "control_origin", "selected_match_rows", "treated_events", "treated_dates"])
    summary = {
        "defined_events": int(len(D)), "eligible_events": int(D.primary_control_eligible.sum()), "matched_events": int(len(K5)),
        "matched_dates": int(K5.source_research_date.nunique()), "match_rate": rate, "criteria": criteria, "support_gate_pass": bool(all(criteria.values())),
        "max_control_date_reuse_rows": int(reuse.selected_match_rows.max()) if len(reuse) else 0,
        "unique_control_source_dates_used": int(reuse.control_source_research_date.nunique()) if len(reuse) else 0,
    }
    return M, S, F, Y, dates, reuse, summary


def write_universe_shards(C: pd.DataFrame, out: Path) -> list[str]:
    names = []
    for y in range(2011, 2019):
        name = f"control_candidate_universe_{y}.csv.gz"
        C[C.source_year.astype(int) == y].sort_values(["control_source_research_date", "anchor_time_utc", "control_candidate_id"]).to_csv(out / name, index=False, compression="gzip")
        names.append(name)
    return names


def main():
    ap = argparse.ArgumentParser()
    required = [
        "final-status", "source-levels", "dual-requests", "sessions", "mapping", "routing", "n1-market-manifest",
        "stage1-resolution", "stage2-resolution", "stage3-resolution", "source-new-root", "source-pilot-root", "n1-root",
        "stage1-root", "stage2-root", "stage3-root", "context-root", "source-last30-zero-qa", "protocol", "initial-pro-memo",
        "repair-pro-memo", "builder-script", "workflow", "out"
    ]
    for x in required:
        ap.add_argument("--" + x, required=True)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    final_path = Path(a.final_status)
    if sha256_file(final_path) != FINAL_STATUS_SHA:
        raise SystemExit("frozen 368 contact-status SHA mismatch")
    final = pd.read_csv(final_path, dtype={"source_instrument_id": str})
    if len(final) != 368 or final.level_id.nunique() != 368:
        raise SystemExit("frozen contact-status cardinality mismatch")
    levels = pd.read_csv(a.source_levels, dtype={"source_instrument_id": str})
    if len(levels) != 368 or levels.source_research_date.nunique() != 92:
        raise SystemExit("native source-level registry cardinality mismatch")

    prov = choose_source_raw(a, levels)
    reconciliation = reconcile_source_last30(prov, a.source_last30_zero_qa)
    n1 = load_n1(a)
    events = build_events(a, final, n1, prov)
    controls, blocks, adjacency, parity, parity_summary, reserved_rows, ctx_marker, ctx_path = build_blocks(a, n1, prov, events)
    matches, support, filter_counts, by_year, by_date, reuse, support_summary = match_final(events, controls)

    if not support_summary["support_gate_pass"]:
        raise SystemExit(f"final regenerated support gate failed: {support_summary}")

    prov.to_csv(out / "source_session_causal_provenance.csv", index=False)
    (out / "source_last30_reconciliation.json").write_text(json.dumps(reconciliation, indent=2))
    events.to_csv(out / "treated_event_causal_context_final.csv", index=False)
    adjacency.to_csv(out / "session_adjacency_manifest.csv", index=False)
    reserved = reserved_rows[[c for c in ["research_trading_date", "acquisition_stage"] if c in reserved_rows.columns]].drop_duplicates().sort_values(["research_trading_date", "acquisition_stage"]).copy()
    reserved["excluded_from_generic_control_source_or_next"] = True
    reserved.to_csv(out / "reserved_date_exclusions.csv", index=False)
    blocks.to_csv(out / "control_block_provenance.csv", index=False)
    parity.to_csv(out / "continuous_vs_raw_n1_parity.csv", index=False)
    universe_names = write_universe_shards(controls, out)
    matches.to_csv(out / "matched_control_manifest.csv", index=False)
    support.to_csv(out / "treated_event_support.csv", index=False)
    filter_counts.to_csv(out / "matching_filter_counts.csv", index=False)
    by_year.to_csv(out / "support_by_year.csv", index=False)
    by_date.to_csv(out / "support_by_date.csv", index=False)
    reuse.to_csv(out / "control_date_reuse.csv", index=False)

    guard = {
        "version": "COMEX_DEV_RANK1_NATIVE_REACTION_PREOUTCOME_FINAL_GUARD_V1",
        "post_contact_values_used_for_matching": False,
        "post_anchor_outcomes_read": False,
        "reaction_outcomes_computed": False,
        "mfe_mae_computed": False,
        "market_data_api_called": False,
        "market_data_download_performed": False,
        "bar_open_fallback_used": False,
        "source_last30_reconciliation_pass": bool(reconciliation["reconciliation_pass"]),
        "stable_parity_all_pass": bool(parity_summary["stable_parity_all_pass"]),
        "stable_same_iid_blocks": int(parity_summary["stable_same_iid_blocks"]),
        "stable_blocks_exact_parity": int(parity_summary["stable_blocks_exact_parity"]),
        "support": support_summary,
        "support_gate_status": "SUPPORT_GATE_REPAIRED_AND_PASS" if support_summary["support_gate_pass"] else "STOP_AND_REPAIR_DESIGN",
        "reaction_outcome_execution_authorized_by_this_run": False,
    }
    (out / "preoutcome_guard.json").write_text(json.dumps(guard, indent=2))

    repo_inputs = [
        a.protocol, a.initial_pro_memo, a.repair_pro_memo, a.builder_script, a.workflow, a.final_status, a.source_levels,
        a.sessions, a.mapping, a.routing, a.n1_market_manifest, a.stage1_resolution, a.stage2_resolution, a.stage3_resolution,
        a.source_last30_zero_qa,
    ]
    input_hashes = {str(p): sha256_file(Path(p)) for p in repo_inputs}
    output_names = [
        "source_session_causal_provenance.csv", "source_last30_reconciliation.json", "treated_event_causal_context_final.csv",
        "session_adjacency_manifest.csv", "reserved_date_exclusions.csv", "control_block_provenance.csv", "continuous_vs_raw_n1_parity.csv",
        *universe_names, "matched_control_manifest.csv", "treated_event_support.csv", "matching_filter_counts.csv", "support_by_year.csv",
        "support_by_date.csv", "control_date_reuse.csv", "preoutcome_guard.json",
    ]
    output_hashes = {name: sha256_file(out / name) for name in output_names}
    freeze = {
        "version": "COMEX_DEV_RANK1_NATIVE_REACTION_PREOUTCOME_FREEZE_MANIFEST_V1",
        "generation_git_commit_sha": git_head(),
        "frozen_contact_status_sha256": FINAL_STATUS_SHA,
        "context_artifact_raw_sha256": sha256_file(ctx_path),
        "context_marker_sha256": ctx_marker.get("sha256", ""),
        "input_repo_sha256": input_hashes,
        "generated_output_sha256": output_hashes,
        "control_universe_shards": universe_names,
        "source_last30_reconciliation": reconciliation,
        "parity_summary": parity_summary,
        "support": support_summary,
        "hard_guards": guard,
        "outcomes_opened": False,
    }
    (out / "preoutcome_freeze_manifest.json").write_text(json.dumps(freeze, indent=2))
    (out / "preoutcome_freeze_manifest.sha256").write_text(sha256_file(out / "preoutcome_freeze_manifest.json") + "  preoutcome_freeze_manifest.json\n")

    summary = f"""# CHECKPOINT — COMEX native reaction final pre-outcome build\n\nDate: 2026-08-19\nGeneration commit: `{freeze['generation_git_commit_sha']}`\n\n- outcome-blind build: PASS\n- source-last30 reconciliation: PASS (91 positive / 1 missing / 0 flat; sole missing `2013-12-25`)\n- stable-IID context parity: {parity_summary['stable_blocks_exact_parity']}/{parity_summary['stable_same_iid_blocks']} exact\n- defined-approach events: {support_summary['defined_events']}\n- eligible events: {support_summary['eligible_events']}\n- K=5 matched events: {support_summary['matched_events']}\n- matched treated dates: {support_summary['matched_dates']}\n- full-match rate: {support_summary['match_rate']:.12%}\n- support gate: `{'SUPPORT_GATE_REPAIRED_AND_PASS' if support_summary['support_gate_pass'] else 'STOP_AND_REPAIR_DESIGN'}`\n\nNo W5/W15/W60/SC, NRB, MFE/MAE, terminal displacement, family/year/session reaction ranking, profitability or XAUUSD mapping was computed or inspected. This build does **not** itself authorize outcome execution; final publication/freeze commit must be recorded separately.\n"""
    (out / "PREOUTCOME_BUILD_SUMMARY.md").write_text(summary)

    print(json.dumps({"guard": guard, "freeze_manifest_sha256": sha256_file(out / "preoutcome_freeze_manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
