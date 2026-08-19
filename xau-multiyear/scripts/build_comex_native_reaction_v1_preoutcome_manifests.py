#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import databento as db

import build_comex_dev_rank1_event_features as feat

FINAL_STATUS_SHA = "8a825b0bc1deba51959b78ab6e62206fe49232e76329558e83949bf6d3d4151a"
TICK = 0.10
K_CONTROLS = 5
EXCLUSION_MINUTES = 60
TIME_BIN_MINUTES = 30
PRE_RANGE_MINUTES = 30
PRE_MOVE_MINUTES = 5
SOURCE_RANGE_RATIO_LO = 0.5
SOURCE_RANGE_RATIO_HI = 2.0
PRE30_RANGE_RATIO_LO = 0.5
PRE30_RANGE_RATIO_HI = 2.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_markers(root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in root.rglob("*.json"):
        try:
            z = json.loads(p.read_text())
        except Exception:
            continue
        rid = z.get("market_request_id")
        raw = z.get("raw_file")
        if rid is None or raw in (None, ""):
            continue
        candidates = list(root.rglob(str(raw)))
        if len(candidates) != 1:
            continue
        q = dict(z)
        q["_marker_path"] = str(p)
        q["_raw_path"] = str(candidates[0])
        out[str(rid)] = q
    return out


def load_dbn(path: Path) -> pd.DataFrame:
    x = db.DBNStore.from_file(path).to_df().reset_index(drop=False)
    if "ts_event" not in x.columns:
        if len(x.columns) == 0:
            return pd.DataFrame(columns=["ts_event"])
        x = x.rename(columns={x.columns[0]: "ts_event"})
    x["ts_event"] = pd.to_datetime(x.ts_event, utc=True)
    return x.sort_values("ts_event").reset_index(drop=True)


def parse_bool(v) -> bool:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() == "true"


def parse_stage(v) -> int:
    return int(float(v))


def to_utc(v) -> pd.Timestamp:
    x = pd.Timestamp(v)
    return x.tz_localize("UTC") if x.tzinfo is None else x.tz_convert("UTC")


def ratio_ok(a: float, b: float, lo: float, hi: float) -> bool:
    return bool(np.isfinite(a) and np.isfinite(b) and a > 0 and b > 0 and lo <= a / b <= hi)


def price_to_ticks(v: float) -> float:
    return float(v) / TICK


def prepare_m1(path: Path, start, end) -> pd.DataFrame:
    x = load_dbn(path)
    need = {"high", "low", "close"}
    if not need.issubset(x.columns):
        raise SystemExit(f"M1 raw {path} missing {sorted(need-set(x.columns))}")
    for c in ["high", "low", "close"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    s, e = to_utc(start), to_utc(end)
    x = x[(x.ts_event >= s) & (x.ts_event < e)].copy()
    x = x[x[["high", "low", "close"]].notna().all(axis=1)].copy()
    if x.ts_event.duplicated().any():
        raise SystemExit(f"duplicate M1 ts_event in {path}")
    x["bar_end"] = x.ts_event + pd.Timedelta(minutes=1)
    return x.sort_values("ts_event").reset_index(drop=True)


def last_close_at_or_before(m1: pd.DataFrame, boundary: pd.Timestamp):
    z = m1[m1.bar_end <= boundary]
    if z.empty:
        return np.nan
    return float(z.iloc[-1].close)


def pre_anchor_features(m1: pd.DataFrame, anchor: pd.Timestamp, sign: int, anchor_price: float):
    w0 = anchor - pd.Timedelta(minutes=PRE_RANGE_MINUTES)
    seg = m1[(m1.ts_event >= w0) & (m1.ts_event < anchor)].copy()
    if seg.empty:
        return {"pre30_range_ticks": np.nan, "pre5_signed_move_norm_unscaled": np.nan, "pre5_start_price": np.nan}
    r = price_to_ticks(float(seg.high.max()) - float(seg.low.min()))
    b5 = anchor - pd.Timedelta(minutes=PRE_MOVE_MINUTES)
    p5 = last_close_at_or_before(m1, b5)
    move_ticks = float(sign) * price_to_ticks(float(anchor_price) - p5) if np.isfinite(p5) else np.nan
    return {"pre30_range_ticks": r, "pre5_signed_move_ticks": move_ticks, "pre5_start_price": p5}


def pseudo_approach(m1: pd.DataFrame, anchor: pd.Timestamp, anchor_price: float):
    lo = anchor - pd.Timedelta(minutes=PRE_RANGE_MINUTES)
    # Completed closes strictly before the anchor. The selected anchor-minute close itself is at anchor and is excluded.
    z = m1[(m1.bar_end >= lo) & (m1.bar_end < anchor)].copy()
    if z.empty:
        return "APPROACH_UNDEFINED", 0, np.nan, "NONE"
    z = z[np.abs(z.close.astype(float) - float(anchor_price)) > 1e-9]
    if z.empty:
        return "APPROACH_UNDEFINED", 0, np.nan, "NONE"
    p = float(z.iloc[-1].close)
    if p < anchor_price:
        return "APPROACH_FROM_BELOW", -1, p, "M1_PRIOR_CLOSE"
    return "APPROACH_FROM_ABOVE", +1, p, "M1_PRIOR_CLOSE"


def exact_event_approach(raw: pd.DataFrame, t0: pd.Timestamp, level: float, fallback_m1: pd.DataFrame, contact_minute: pd.Timestamp):
    if "price" in raw.columns:
        y = raw[raw.ts_event < t0].copy()
        y["price"] = pd.to_numeric(y.price, errors="coerce")
        y = y[y.price.notna() & (np.abs(y.price.astype(float) - float(level)) > 1e-9)]
        if not y.empty:
            p = float(y.iloc[-1].price)
            if p < level:
                return "APPROACH_FROM_BELOW", -1, p, "RAW_LAST_OFF_LEVEL"
            return "APPROACH_FROM_ABOVE", +1, p, "RAW_LAST_OFF_LEVEL"
    # Fallback is a completed bar before the contact minute, hence fully known before t0.
    z = fallback_m1[fallback_m1.ts_event < contact_minute].copy()
    z = z[np.abs(z.close.astype(float) - float(level)) > 1e-9]
    if z.empty:
        return "APPROACH_UNDEFINED", 0, np.nan, "NONE"
    p = float(z.iloc[-1].close)
    if p < level:
        return "APPROACH_FROM_BELOW", -1, p, "M1_FALLBACK"
    return "APPROACH_FROM_ABOVE", +1, p, "M1_FALLBACK"


def build_source_ranges(args, source_levels: pd.DataFrame):
    req = pd.read_csv(args.dual_requests, dtype={"symbols": str})
    sessions = pd.read_csv(args.sessions)
    sessions = sessions[sessions.acquisition_stage.eq("DEV_RANK1")].copy()
    mapping = pd.read_csv(args.mapping, dtype={"v0_start_iid": str, "n0_start_iid": str})
    routing = pd.read_csv(args.routing, dtype={"v0_iid": str, "n0_iid": str})
    if len(sessions) != 96 or len(mapping) != 96 or len(routing) != 96:
        raise SystemExit("source provenance inputs must contain 96 DEV_RANK1 rows")
    cand, _ = feat.build_candidate_map(Path(args.source_new_root), Path(args.source_pilot_root), req, sessions, mapping)
    rt = routing.set_index(routing.research_trading_date.astype(str))
    reg = source_levels.groupby("source_research_date", sort=True).first().reset_index()
    rows = []
    for r in reg.itertuples(index=False):
        date = str(r.source_research_date)
        rr = rt.loc[date]
        leader = str(rr.terminal_leader)
        if leader == "MISSING":
            raise SystemExit(f"registry unexpectedly contains MISSING source date {date}")
        label = str(r.source_candidate_key)
        z = cand.get((date, label))
        if not z or z.get("path") is None:
            # Same deterministic fallback used by the canonical source-level builder.
            z = cand.get((date, "V0"))
        if not z or z.get("path") is None:
            raise SystemExit(f"source raw missing for {date}")
        raw_path = Path(z["path"])
        iid = str(z.get("iid", ""))
        if iid != str(r.source_instrument_id):
            raise SystemExit(f"source raw iid mismatch {date}: {iid} != {r.source_instrument_id}")
        s, e = feat.session_bounds(date)
        if to_utc(r.source_session_start_utc) != s or to_utc(r.known_time_utc) != e:
            raise SystemExit(f"source canonical bounds mismatch {date}")
        tape = feat.prep_tape(raw_path, date)
        if tape is None or len(tape["price"]) == 0:
            raise SystemExit(f"empty source raw session {date}")
        ticks = tape["ticks"]
        range_ticks = int(np.max(ticks) - np.min(ticks))
        if range_ticks <= 0:
            raise SystemExit(f"non-positive source range {date}")
        rows.append({
            "source_research_date": date,
            "source_instrument_id": iid,
            "source_candidate_key": label,
            "terminal_leader": leader,
            "source_session_start_utc": s.isoformat(),
            "source_session_end_utc": e.isoformat(),
            "source_range_ticks": range_ticks,
            "source_range_price": range_ticks * TICK,
            "source_raw_records": int(len(ticks)),
            "source_raw_sha256": sha256_file(raw_path),
            "source_raw_file": raw_path.name,
            "same_raw_instrument_verified": True,
            "canonical_source_session_verified": True,
            "known_before_j1": True,
            "positive_finite_range_verified": True,
            "continuous_adjusted_xau_used": False,
        })
    q = pd.DataFrame(rows).sort_values("source_research_date").reset_index(drop=True)
    if len(q) != 92 or q.source_research_date.nunique() != 92:
        raise SystemExit("expected exactly 92 source-range provenance rows")
    return q


def main():
    ap = argparse.ArgumentParser()
    for x in [
        "final-status", "source-levels", "dual-requests", "sessions", "mapping", "routing",
        "n1-market-manifest", "stage1-resolution", "stage2-resolution", "stage3-resolution",
        "source-new-root", "source-pilot-root", "n1-root", "stage1-root", "stage2-root", "stage3-root", "out"
    ]:
        ap.add_argument("--" + x, required=True)
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    final_path = Path(args.final_status)
    if sha256_file(final_path) != FINAL_STATUS_SHA:
        raise SystemExit("final 368 status SHA mismatch")
    final = pd.read_csv(final_path, dtype={"source_instrument_id": str})
    if len(final) != 368 or final.level_id.nunique() != 368:
        raise SystemExit("final status cardinality mismatch")
    contacts = final[final.exact_contact_final.map(parse_bool)].copy()
    if len(contacts) != 238:
        raise SystemExit("expected 238 exact contacts")
    contacts["t0"] = pd.to_datetime(contacts.first_exact_contact_time_utc, utc=True)
    contacts["contact_stage_int"] = contacts.contact_stage.map(parse_stage)

    source_levels = pd.read_csv(args.source_levels, dtype={"source_instrument_id": str})
    if len(source_levels) != 368 or source_levels.source_research_date.nunique() != 92:
        raise SystemExit("source registry cardinality mismatch")
    source_ranges = build_source_ranges(args, source_levels)
    source_range_map = source_ranges.set_index("source_research_date")["source_range_ticks"].astype(float).to_dict()

    n1_manifest = pd.read_csv(args.n1_market_manifest, dtype={"source_instrument_id": str, "symbols": str})
    if len(n1_manifest) != 92 or n1_manifest.source_research_date.nunique() != 92:
        raise SystemExit("N1 manifest cardinality mismatch")
    n1_markers = read_markers(Path(args.n1_root))
    sessions_m1: dict[str, dict] = {}
    for r in n1_manifest.itertuples(index=False):
        rid = str(r.market_request_id)
        mk = n1_markers.get(rid)
        if mk is None:
            raise SystemExit(f"N1 raw marker missing {rid}")
        raw = Path(mk["_raw_path"])
        if mk.get("sha256") and sha256_file(raw) != mk["sha256"]:
            raise SystemExit(f"N1 raw hash mismatch {rid}")
        if str(r.symbols) != str(r.source_instrument_id) or str(mk.get("symbols")) != str(r.symbols):
            raise SystemExit(f"N1 iid mismatch {rid}")
        m1 = prepare_m1(raw, r.start, r.end)
        if m1.empty:
            raise SystemExit(f"empty N1 M1 block {rid}")
        sessions_m1[str(r.source_research_date)] = {
            "m1": m1,
            "start": to_utc(r.start), "end": to_utc(r.end),
            "eligible_next_research_date": str(r.eligible_next_research_date),
            "source_instrument_id": str(r.source_instrument_id),
            "market_request_id": rid,
            "raw_sha256": sha256_file(raw),
        }

    s1 = pd.read_csv(args.stage1_resolution, dtype={"source_instrument_id": str})
    s2 = pd.read_csv(args.stage2_resolution, dtype={"source_instrument_id": str})
    s3 = pd.read_csv(args.stage3_resolution, dtype={"source_instrument_id": str})
    s1_map = s1.set_index("level_id")["stage1_market_request_id"].astype(str).to_dict()
    s2_map = s2.set_index("level_id")["stage2_market_request_id"].astype(str).to_dict()
    s3_map = s3.set_index("level_id")["stage3_market_request_id"].astype(str).to_dict()
    st_markers = {
        1: read_markers(Path(args.stage1_root)),
        2: read_markers(Path(args.stage2_root)),
        3: read_markers(Path(args.stage3_root)),
    }
    req_maps = {1: s1_map, 2: s2_map, 3: s3_map}

    # Exact contacts grouped by source/retest block for the control exclusion rule.
    contact_times_by_date: dict[str, list[pd.Timestamp]] = {}
    for r in contacts.itertuples(index=False):
        contact_times_by_date.setdefault(str(r.source_research_date), []).append(r.t0)

    event_rows = []
    for r in contacts.sort_values(["source_research_date", "level_id"]).itertuples(index=False):
        date = str(r.source_research_date)
        ss = sessions_m1[date]
        m1 = ss["m1"]
        t0 = r.t0
        m0 = t0.floor("min")
        a0 = m0 + pd.Timedelta(minutes=1)
        bar = m1[m1.ts_event == m0]
        if len(bar) != 1:
            raise SystemExit(f"contact minute M1 bar parity failure {r.level_id}: {len(bar)}")
        A0 = float(bar.iloc[0].close)
        stage = int(r.contact_stage_int)
        rid = req_maps[stage].get(str(r.level_id), "")
        mk = st_markers[stage].get(rid)
        if not rid or mk is None:
            raise SystemExit(f"N2 marker missing for {r.level_id}")
        raw = Path(mk["_raw_path"])
        if mk.get("sha256") and sha256_file(raw) != mk["sha256"]:
            raise SystemExit(f"N2 raw hash mismatch {r.level_id}")
        exact_raw = load_dbn(raw)
        approach, sign, prior_price, approach_source = exact_event_approach(exact_raw, t0, float(r.contact_tick_price), m1, m0)
        source_range = float(source_range_map[date])
        pre = pre_anchor_features(m1, a0, sign, A0) if sign else {"pre30_range_ticks": np.nan, "pre5_signed_move_ticks": np.nan, "pre5_start_price": np.nan}
        pre30_complete = bool(a0 - pd.Timedelta(minutes=PRE_RANGE_MINUTES) >= ss["start"])
        w15_complete = bool(a0 + pd.Timedelta(minutes=15) <= ss["end"])
        minute_offset = int((m0 - ss["start"]).total_seconds() // 60)
        if minute_offset < 0:
            raise SystemExit(f"negative event minute offset {r.level_id}")
        pre5_norm = float(pre.get("pre5_signed_move_ticks", np.nan)) / source_range if source_range > 0 and np.isfinite(pre.get("pre5_signed_move_ticks", np.nan)) else np.nan
        event_rows.append({
            "level_id": str(r.level_id),
            "source_research_date": date,
            "eligible_next_research_date": str(r.eligible_next_research_date),
            "year": int(pd.Timestamp(r.eligible_next_research_date).year),
            "source_instrument_id": str(r.source_instrument_id),
            "level_type": str(r.level_type),
            "contact_tick_price": float(r.contact_tick_price),
            "t0_utc": t0.isoformat(),
            "m0_utc": m0.isoformat(),
            "a0_utc": a0.isoformat(),
            "A0_close": A0,
            "approach": approach,
            "away_sign": int(sign),
            "approach_prior_price": prior_price,
            "approach_source": approach_source,
            "anchor_minute_of_session": minute_offset,
            "anchor_30m_bin": minute_offset // TIME_BIN_MINUTES,
            "source_range_ticks": source_range,
            "pre30_range_ticks": pre.get("pre30_range_ticks", np.nan),
            "pre5_signed_move_ticks": pre.get("pre5_signed_move_ticks", np.nan),
            "pre5_signed_move_norm": pre5_norm,
            "pre30_complete": pre30_complete,
            "w15_complete": w15_complete,
            "n1_market_request_id": ss["market_request_id"],
            "n2_market_request_id": rid,
            "contact_stage": stage,
            "post_anchor_reaction_values_read": False,
        })
    events = pd.DataFrame(event_rows)
    if len(events) != 238 or events.level_id.nunique() != 238:
        raise SystemExit("treated event context cardinality mismatch")

    # Build the full outcome-free M1 control-candidate universe.
    control_rows = []
    for date in sorted(sessions_m1):
        ss = sessions_m1[date]; m1 = ss["m1"]
        source_range = float(source_range_map[date])
        year = int(pd.Timestamp(ss["eligible_next_research_date"]).year)
        known_contacts = contact_times_by_date.get(date, [])
        for row in m1.itertuples(index=False):
            bar_start = row.ts_event
            anchor = row.bar_end
            if anchor - pd.Timedelta(minutes=PRE_RANGE_MINUTES) < ss["start"]:
                continue
            if anchor + pd.Timedelta(minutes=15) > ss["end"]:
                continue
            if any(abs((anchor - t).total_seconds()) <= EXCLUSION_MINUTES * 60 for t in known_contacts):
                continue
            anchor_price = float(row.close)
            approach, sign, prior_price, approach_source = pseudo_approach(m1, anchor, anchor_price)
            if sign == 0:
                continue
            pre = pre_anchor_features(m1, anchor, sign, anchor_price)
            pre30 = float(pre.get("pre30_range_ticks", np.nan))
            move = float(pre.get("pre5_signed_move_ticks", np.nan))
            if not (np.isfinite(pre30) and pre30 > 0 and np.isfinite(move)):
                continue
            minute_offset = int((bar_start - ss["start"]).total_seconds() // 60)
            if minute_offset < 0:
                continue
            move_norm = move / source_range
            cid = hashlib.sha256(f"CTRL|{date}|{bar_start.isoformat()}|{ss['source_instrument_id']}".encode()).hexdigest()[:24]
            control_rows.append({
                "control_candidate_id": cid,
                "control_source_research_date": date,
                "control_eligible_next_research_date": ss["eligible_next_research_date"],
                "year": year,
                "source_instrument_id": ss["source_instrument_id"],
                "anchor_bar_start_utc": bar_start.isoformat(),
                "anchor_time_utc": anchor.isoformat(),
                "anchor_price": anchor_price,
                "approach": approach,
                "away_sign": int(sign),
                "approach_prior_price": prior_price,
                "approach_source": approach_source,
                "anchor_minute_of_session": minute_offset,
                "anchor_30m_bin": minute_offset // TIME_BIN_MINUTES,
                "source_range_ticks": source_range,
                "pre30_range_ticks": pre30,
                "pre5_signed_move_ticks": move,
                "pre5_signed_move_norm": move_norm,
                "excluded_native_contact_pm60": False,
                "pre30_complete": True,
                "w15_complete": True,
                "post_anchor_reaction_values_read": False,
            })
    controls = pd.DataFrame(control_rows)
    if controls.empty or controls.control_candidate_id.duplicated().any():
        raise SystemExit("control candidate universe invalid")

    # Deterministic K=5 matching. No post-anchor outcome is read or used.
    match_rows = []
    support_rows = []
    for e in events.itertuples(index=False):
        defined = int(e.away_sign) in (-1, 1)
        causal_covariates_ok = bool(defined and e.pre30_complete and np.isfinite(e.pre30_range_ticks) and float(e.pre30_range_ticks) > 0 and np.isfinite(e.pre5_signed_move_norm) and float(e.source_range_ticks) > 0)
        primary_eligible = bool(causal_covariates_ok and e.w15_complete)
        candidates = controls.iloc[0:0].copy()
        if primary_eligible:
            c = controls[
                (controls.year == int(e.year)) &
                (controls.anchor_30m_bin == int(e.anchor_30m_bin)) &
                (controls.away_sign == int(e.away_sign)) &
                (controls.control_source_research_date.astype(str) != str(e.source_research_date))
            ].copy()
            if len(c):
                c = c[
                    c.source_range_ticks.map(lambda v: ratio_ok(float(v), float(e.source_range_ticks), SOURCE_RANGE_RATIO_LO, SOURCE_RANGE_RATIO_HI)) &
                    c.pre30_range_ticks.map(lambda v: ratio_ok(float(v), float(e.pre30_range_ticks), PRE30_RANGE_RATIO_LO, PRE30_RANGE_RATIO_HI))
                ].copy()
            if len(c):
                c["d_pre30_log"] = np.abs(np.log(c.pre30_range_ticks.astype(float) / float(e.pre30_range_ticks)))
                c["d_source_log"] = np.abs(np.log(c.source_range_ticks.astype(float) / float(e.source_range_ticks)))
                c["d_pre5_norm"] = np.abs(c.pre5_signed_move_norm.astype(float) - float(e.pre5_signed_move_norm))
                c["d_minute"] = np.abs(c.anchor_minute_of_session.astype(int) - int(e.anchor_minute_of_session))
                c["anchor_ts_sort"] = pd.to_datetime(c.anchor_time_utc, utc=True)
                sort_cols = ["d_pre30_log", "d_source_log", "d_pre5_norm", "d_minute", "anchor_ts_sort", "control_source_research_date", "source_instrument_id", "control_candidate_id"]
                # Best anchor per eligible control date first.
                c = c.sort_values(sort_cols, kind="mergesort")
                reps = c.groupby("control_source_research_date", sort=False, as_index=False).head(1).copy()
                reps = reps.sort_values(sort_cols, kind="mergesort").head(K_CONTROLS).copy()
                for rank, z in enumerate(reps.itertuples(index=False), start=1):
                    match_rows.append({
                        "treated_level_id": str(e.level_id),
                        "treated_source_research_date": str(e.source_research_date),
                        "treated_year": int(e.year),
                        "control_rank": rank,
                        "control_candidate_id": str(z.control_candidate_id),
                        "control_source_research_date": str(z.control_source_research_date),
                        "control_anchor_time_utc": str(z.anchor_time_utc),
                        "control_source_instrument_id": str(z.source_instrument_id),
                        "d_pre30_log": float(z.d_pre30_log),
                        "d_source_log": float(z.d_source_log),
                        "d_pre5_norm": float(z.d_pre5_norm),
                        "d_minute": int(z.d_minute),
                        "post_anchor_reaction_values_read": False,
                    })
        count = sum(1 for x in match_rows if x["treated_level_id"] == str(e.level_id))
        support_rows.append({
            "level_id": str(e.level_id),
            "source_research_date": str(e.source_research_date),
            "year": int(e.year),
            "approach_defined": bool(defined),
            "causal_covariates_ok": bool(causal_covariates_ok),
            "w15_complete": bool(e.w15_complete),
            "primary_eligible": bool(primary_eligible),
            "eligible_control_dates_found": int(count),
            "full_k5_match": bool(count == K_CONTROLS),
        })
    matches = pd.DataFrame(match_rows)
    support = pd.DataFrame(support_rows)

    defined = support[support.approach_defined]
    matched = support[support.full_k5_match]
    matched_events = int(len(matched))
    matched_dates = int(matched.source_research_date.nunique())
    defined_count = int(len(defined))
    full_match_rate = matched_events / defined_count if defined_count else 0.0
    by_year_rows = []
    for year in range(2011, 2019):
        d = support[(support.year == year) & support.approach_defined]
        m = d[d.full_k5_match]
        rate = len(m) / len(d) if len(d) else 0.0
        by_year_rows.append({
            "year": year,
            "defined_approach_events": int(len(d)),
            "full_k5_matched_events": int(len(m)),
            "full_k5_match_rate": float(rate),
            "matched_treated_dates": int(m.source_research_date.nunique()),
        })
    by_year = pd.DataFrame(by_year_rows)

    criteria = {
        "matched_events_ge_160": matched_events >= 160,
        "matched_dates_ge_60": matched_dates >= 60,
        "every_year_matched_dates_ge_5": bool((by_year.matched_treated_dates >= 5).all()),
        "defined_contact_full_match_rate_ge_0_85": full_match_rate >= 0.85,
        "every_year_full_match_rate_ge_0_75": bool((by_year.full_k5_match_rate >= 0.75).all()),
    }
    source_provenance_ok = bool(
        len(source_ranges) == 92 and
        source_ranges.same_raw_instrument_verified.all() and
        source_ranges.canonical_source_session_verified.all() and
        source_ranges.known_before_j1.all() and
        source_ranges.positive_finite_range_verified.all() and
        (~source_ranges.continuous_adjusted_xau_used).all()
    )
    support_pass = bool(all(criteria.values()))

    source_ranges.to_csv(out / "source_session_range_provenance.csv", index=False)
    events.to_csv(out / "treated_event_causal_context.csv", index=False)
    controls.to_csv(out / "control_candidate_universe.csv.gz", index=False, compression="gzip")
    matches.to_csv(out / "matched_control_manifest.csv", index=False)
    support.to_csv(out / "treated_event_support.csv", index=False)
    by_year.to_csv(out / "support_by_year.csv", index=False)

    files = [
        "source_session_range_provenance.csv", "treated_event_causal_context.csv", "control_candidate_universe.csv.gz",
        "matched_control_manifest.csv", "treated_event_support.csv", "support_by_year.csv"
    ]
    hashes = {name: sha256_file(out / name) for name in files}
    qa = {
        "version": "COMEX_DEV_RANK1_NATIVE_REACTION_V1_PREOUTCOME_MANIFEST_QA",
        "reaction_outcomes_computed": False,
        "mfe_mae_computed": False,
        "post_anchor_outcomes_read": False,
        "market_data_api_called": False,
        "market_data_download_performed": False,
        "native_levels": 368,
        "exact_contacts": 238,
        "source_sessions": 92,
        "source_range_provenance_pass": source_provenance_ok,
        "control_candidate_rows": int(len(controls)),
        "defined_approach_contacts": defined_count,
        "primary_eligible_events": int(support.primary_eligible.sum()),
        "full_k5_matched_events": matched_events,
        "full_k5_matched_treated_dates": matched_dates,
        "defined_contact_full_match_rate": float(full_match_rate),
        "support_criteria": criteria,
        "support_gate_pass": support_pass,
        "decision_if_frozen_now": "PREOUTCOME_MANIFEST_QA_PASS" if (source_provenance_ok and support_pass) else "STOP_AND_REPAIR_DESIGN",
        "hashes_sha256": hashes,
        "fixed_parameters": {
            "K_controls": K_CONTROLS,
            "contact_exclusion_minutes": EXCLUSION_MINUTES,
            "time_bin_minutes": TIME_BIN_MINUTES,
            "pre_anchor_range_minutes": PRE_RANGE_MINUTES,
            "pre_anchor_move_minutes": PRE_MOVE_MINUTES,
            "source_range_ratio_caliper": [SOURCE_RANGE_RATIO_LO, SOURCE_RANGE_RATIO_HI],
            "pre30_range_ratio_caliper": [PRE30_RANGE_RATIO_LO, PRE30_RANGE_RATIO_HI],
        },
        "notes": [
            "Only source-session and pre-anchor/control-selection data were decoded.",
            "No W5/W15/W60/session-close reaction endpoint was computed or inspected.",
            "Exact N2 raw was used only to determine causal approach before t0 where available.",
            "Control universe excludes anchors within plus/minus 60 wall-clock minutes of known native exact contacts."
        ],
    }
    (out / "preoutcome_manifest_qa.json").write_text(json.dumps(qa, indent=2))
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
