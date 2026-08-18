#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import databento as db

DATASET = "GLBX.MDP3"
SYMBOL = "GC.v.0"
STYPE = "continuous"
PANEL_SEED = "COMEX_SESSION_PANEL_V1_SEED_971"
NY = ZoneInfo("America/New_York")
FAMILIES = ["DISPLACEMENT_ORIGIN", "OBJECTIVE_LIQUIDITY", "MEMORY", "FVG"]
MODELS = [
    "passive_touch",
    "touch_next_open",
    "clean_rejection",
    "failed_auction",
    "acceptance_retest",
    "reclaim_pullback",
]
CAP_USD = 20.16


def stable_hash(*parts: object) -> str:
    return hashlib.sha256("|".join(str(x) for x in parts).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def session_bounds(date_str: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    d = pd.Timestamp(date_str)
    prev = (d - pd.Timedelta(days=1)).date()
    cur = d.date()
    return (
        pd.Timestamp(f"{prev} 17:00:00", tz=NY).tz_convert("UTC"),
        pd.Timestamp(f"{cur} 18:00:00", tz=NY).tz_convert("UTC"),
    )


def retry(fn, **kwargs):
    err = None
    for k in range(7):
        try:
            return fn(**kwargs)
        except Exception as exc:
            err = exc
            time.sleep(min(20, 2**k))
    raise RuntimeError(f"Databento call failed after retries: {err}")


def get_cost(client: db.Historical, schema: str, start, end) -> float:
    return float(
        retry(
            client.metadata.get_cost,
            dataset=DATASET,
            symbols=SYMBOL,
            stype_in=STYPE,
            schema=schema,
            start=str(start),
            end=str(end),
        )
    )


def get_count(client: db.Historical, schema: str, start, end) -> int:
    return int(
        retry(
            client.metadata.get_record_count,
            dataset=DATASET,
            symbols=SYMBOL,
            stype_in=STYPE,
            schema=schema,
            start=str(start),
            end=str(end),
        )
    )


def prepare_candidates(raw: pd.DataFrame) -> pd.DataFrame:
    x = raw.copy()
    for c in ["year", "quarter", "vol_band"]:
        x[c] = pd.to_numeric(x[c], errors="raise").astype(int)
    x["research_trading_date"] = x.research_trading_date.astype(str)
    x["date_ts"] = pd.to_datetime(x.research_trading_date)
    x["weekday"] = x.date_ts.dt.weekday
    x = x[x.weekday < 5].copy()
    if "panel_hash" not in x.columns:
        x["panel_hash"] = [
            stable_hash(PANEL_SEED, r.year, r.quarter, r.vol_band, r.research_trading_date)
            for r in x.itertuples()
        ]
    x = x.sort_values(["year", "quarter", "vol_band", "panel_hash", "research_trading_date"]).copy()
    x["weekday_rank_v4"] = x.groupby(["year", "quarter", "vol_band"]).cumcount() + 1
    return x


def temporal_role(year: int) -> str:
    if year <= 2018:
        return "RETRO_DEV"
    if year <= 2022:
        return "RETRO_CONFIRM"
    return "LOCKED_COMEX_TEST"


def choose_primary_panel(cand: pd.DataFrame, pilot_dates: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for (year, quarter, vol_band), g in cand.groupby(["year", "quarter", "vol_band"], sort=True):
        g = g.sort_values(["panel_hash", "research_trading_date"]).copy()
        if int(year) <= 2018:
            pool = g
        else:
            # Confirm/test pilot dates have been exposed during QA and are excluded from primary evaluation.
            pool = g[~g.research_trading_date.isin(pilot_dates)].copy()
        take = min(2, len(pool))
        picks = pool.head(take).copy()
        picks["analysis_rank"] = range(1, len(picks) + 1)
        picks["temporal_role"] = temporal_role(int(year))
        rows.append(picks)
    panel = pd.concat(rows, ignore_index=True)
    panel["is_pilot"] = panel.research_trading_date.isin(pilot_dates)
    panel["already_paid"] = panel.is_pilot
    panel["primary_eligible"] = True
    panel["acquisition_stage"] = panel.apply(
        lambda r: f"DEV_RANK{int(r.analysis_rank)}" if int(r.year) <= 2018 else ("CONFIRM" if int(r.year) <= 2022 else "LOCKED_TEST"),
        axis=1,
    )

    qa = cand[cand.research_trading_date.isin(pilot_dates) & (cand.year >= 2019)].copy()
    qa["temporal_role"] = qa.year.map(temporal_role)
    qa["analysis_rank"] = pd.NA
    qa["is_pilot"] = True
    qa["already_paid"] = True
    qa["primary_eligible"] = False
    qa["acquisition_stage"] = "QA_ONLY_ALREADY_PAID"
    return panel, qa


def add_weights(cand: pd.DataFrame, panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pop = cand.groupby(["year", "quarter", "vol_band"]).size().rename("population_sessions").reset_index()
    sel = panel.groupby(["year", "quarter", "vol_band"]).size().rename("primary_selected_sessions").reset_index()
    w = pop.merge(sel, on=["year", "quarter", "vol_band"], how="left")
    w["primary_selected_sessions"] = w.primary_selected_sessions.fillna(0).astype(int)
    w["poststrat_weight"] = w.population_sessions / w.primary_selected_sessions.replace(0, pd.NA)
    w["selection_fraction"] = w.primary_selected_sessions / w.population_sessions
    p = panel.merge(w, on=["year", "quarter", "vol_band"], how="left")
    return p, w


def family_signature(series: pd.Series) -> pd.Series:
    vals = series.fillna("").astype(str)
    return vals.map(lambda x: "+".join(f for f in FAMILIES if f in x) or "OTHER")


def family_stack(sig: str) -> str:
    return {
        "DISPLACEMENT_ORIGIN": "DOZ_ONLY",
        "OBJECTIVE_LIQUIDITY": "OBJECTIVE_ONLY",
        "MEMORY": "MEMORY_ONLY",
        "FVG": "FVG_ONLY",
    }.get(sig, "CONFLUENCE" if "+" in sig else "OTHER")


def research_date(ts: pd.Series) -> pd.Series:
    return (pd.to_datetime(ts, utc=True).dt.tz_convert(NY) - pd.Timedelta(hours=17)).dt.date.astype(str)


def build_coverage(events_path: str, rank1_dates: set[str], out: Path) -> dict:
    use = [
        "event_uid", "year", "contact_time", "constituent_families", "behavior_v2", "side"
    ] + [f"{m}_eligible" for m in MODELS]
    e = pd.read_csv(events_path, compression="gzip", usecols=use, low_memory=False)
    e["research_trading_date"] = research_date(e.contact_time)
    e = e[e.research_trading_date.isin(rank1_dates)].copy()
    e["signature"] = family_signature(e.constituent_families)
    e["family_stack"] = e.signature.map(family_stack)
    for m in MODELS:
        e[f"{m}_eligible"] = e[f"{m}_eligible"].astype(str).str.lower().eq("true")

    fam = (
        e.groupby(["year", "family_stack", "behavior_v2", "side"], dropna=False)
        .agg(events=("event_uid", "size"), independent_sessions=("research_trading_date", "nunique"))
        .reset_index()
    )
    fam.to_csv(out / "dev_rank1_coverage_family_behavior_direction_year.csv", index=False)

    conf = e[e.signature.str.contains("+", regex=False)].copy()
    conf = (
        conf.groupby(["year", "signature", "behavior_v2", "side"], dropna=False)
        .agg(events=("event_uid", "size"), independent_sessions=("research_trading_date", "nunique"))
        .reset_index()
    )
    conf.to_csv(out / "dev_rank1_coverage_confluence_behavior_direction_year.csv", index=False)

    model_rows = []
    for m in MODELS:
        q = e[e[f"{m}_eligible"]].copy()
        if q.empty:
            continue
        g = (
            q.groupby(["year", "family_stack", "signature", "side"], dropna=False)
            .agg(eligible_events=("event_uid", "size"), independent_sessions=("research_trading_date", "nunique"))
            .reset_index()
        )
        g["entry_model"] = m.upper()
        model_rows.append(g)
    models = pd.concat(model_rows, ignore_index=True) if model_rows else pd.DataFrame()
    models.to_csv(out / "dev_rank1_coverage_entry_models.csv", index=False)

    broad = (
        e.groupby("family_stack")
        .agg(events=("event_uid", "size"), independent_sessions=("research_trading_date", "nunique"), years=("year", "nunique"))
        .reset_index()
    )
    broad.to_csv(out / "dev_rank1_coverage_broad_summary.csv", index=False)
    return {
        "events": int(len(e)),
        "independent_sessions": int(e.research_trading_date.nunique()),
        "years": sorted(int(x) for x in e.year.unique()),
        "broad_families": broad.to_dict("records"),
        "exact_confluence_signatures": int(e.loc[e.signature.str.contains("+", regex=False), "signature"].nunique()),
    }


def symbology_qa(client: db.Historical, out: Path) -> dict:
    # Symbology resolution is a free endpoint; no market-data records are downloaded.
    res = client.symbology.resolve(
        dataset=DATASET,
        symbols=[SYMBOL],
        stype_in="continuous",
        stype_out="instrument_id",
        start_date="2010-06-06",
        end_date="2019-01-01",
    )
    # SDK result can be dict-like or typed; normalize through json serialization fallback.
    try:
        payload = res.model_dump()  # pydantic-like
    except Exception:
        try:
            payload = dict(res)
        except Exception:
            payload = json.loads(json.dumps(res, default=lambda o: getattr(o, "__dict__", str(o))))
    (out / "dev_continuous_symbology.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    result = payload.get("result", {}) if isinstance(payload, dict) else {}
    mappings = result.get(SYMBOL, []) if isinstance(result, dict) else []
    ids = sorted({str(x.get("s")) for x in mappings if isinstance(x, dict) and x.get("s") is not None})
    return {
        "continuous_mapping_segments": int(len(mappings)),
        "unique_instrument_ids": int(len(ids)),
        "not_found": payload.get("not_found", []) if isinstance(payload, dict) else [],
        "partial": payload.get("partial", []) if isinstance(payload, dict) else [],
        "status": payload.get("status") if isinstance(payload, dict) else None,
        "message": payload.get("message") if isinstance(payload, dict) else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--events", required=True)
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY missing")
    client = db.Historical(key)

    cand = prepare_candidates(pd.read_csv(args.candidates))
    pilot = pd.read_csv(args.pilot)
    pilot_dates = set(pilot.research_trading_date.astype(str))
    panel, qa_only = choose_primary_panel(cand, pilot_dates)
    panel, weights = add_weights(cand, panel)

    # Hard structural checks from the Pro audit.
    dev_pilot = panel[(panel.year <= 2018) & panel.is_pilot]
    assert len(dev_pilot) == 6, len(dev_pilot)
    assert int((dev_pilot.acquisition_stage == "DEV_RANK1").sum()) == 4
    assert int((dev_pilot.acquisition_stage == "DEV_RANK2").sum()) == 2
    assert len(qa_only) == 6, len(qa_only)
    assert int((panel.acquisition_stage == "DEV_RANK1").sum()) == 96
    assert int((panel.acquisition_stage == "DEV_RANK2").sum()) == 96

    panel.to_csv(out / "corrected_primary_sessions.csv", index=False)
    qa_only.to_csv(out / "qa_only_exposed_sessions.csv", index=False)
    weights.to_csv(out / "corrected_strata_weights.csv", index=False)

    rank1 = panel[panel.acquisition_stage == "DEV_RANK1"].copy()
    new_rank1 = rank1[~rank1.already_paid].copy()
    coverage = build_coverage(args.events, set(rank1.research_trading_date.astype(str)), out)

    # Metadata-only session QA and exact re-quote for the 92 new trades sessions.
    quote_rows = []
    for r in new_rank1.itertuples():
        start, end = session_bounds(str(r.research_trading_date))
        quote_rows.append(
            {
                "research_trading_date": str(r.research_trading_date),
                "year": int(r.year),
                "quarter": int(r.quarter),
                "vol_band": int(r.vol_band),
                "analysis_rank": int(r.analysis_rank),
                "start_utc": start.isoformat(),
                "end_utc": end.isoformat(),
                "trades_cost_usd": get_cost(client, "trades", start.isoformat(), end.isoformat()),
                "trades_record_count": get_count(client, "trades", start.isoformat(), end.isoformat()),
            }
        )
    q = pd.DataFrame(quote_rows)
    q.to_csv(out / "dev_rank1_new_session_quotes.csv", index=False)

    ohlcv_cost = get_cost(client, "ohlcv-1m", "2010-06-06", "2019-01-01")
    ohlcv_records = get_count(client, "ohlcv-1m", "2010-06-06", "2019-01-01")
    trades_cost = float(q.trades_cost_usd.sum())
    total_quote = ohlcv_cost + trades_cost
    zero_sessions = q.loc[q.trades_record_count <= 0, "research_trading_date"].astype(str).tolist()
    low_threshold = float(q.trades_record_count.quantile(0.05)) if len(q) else 0.0
    low_sessions = q[q.trades_record_count <= low_threshold][["research_trading_date", "trades_record_count"]].to_dict("records")

    sym = symbology_qa(client, out)

    manifest = {
        "version": "COMEX_DEV_RANK1_ZERO_COST_GATE_V1",
        "metadata_only": True,
        "market_data_download_performed": False,
        "corrected_primary_panel_sessions": int(len(panel)),
        "dev_rank1_analytical_sessions": int(len(rank1)),
        "dev_rank1_already_paid_reused": int(rank1.already_paid.sum()),
        "dev_rank1_new_sessions_to_buy": int(len(new_rank1)),
        "dev_rank2_analytical_sessions": int((panel.acquisition_stage == "DEV_RANK2").sum()),
        "confirm_primary_sessions": int((panel.acquisition_stage == "CONFIRM").sum()),
        "locked_test_primary_sessions": int((panel.acquisition_stage == "LOCKED_TEST").sum()),
        "qa_only_exposed_confirm_test_sessions": int(len(qa_only)),
        "quote": {
            "ohlcv_1m_2010_06_06_to_2019_01_01_usd": ohlcv_cost,
            "ohlcv_1m_records": ohlcv_records,
            "new_dev_rank1_trades_usd": trades_cost,
            "total_usd": total_quote,
            "recommended_hard_cap_usd": CAP_USD,
            "within_cap": bool(total_quote <= CAP_USD),
        },
        "session_metadata_qa": {
            "new_sessions_quoted": int(len(q)),
            "zero_record_sessions": zero_sessions,
            "record_count_min": int(q.trades_record_count.min()) if len(q) else 0,
            "record_count_median": float(q.trades_record_count.median()) if len(q) else 0.0,
            "record_count_max": int(q.trades_record_count.max()) if len(q) else 0,
            "bottom_5pct_threshold": low_threshold,
            "bottom_5pct_sessions": low_sessions,
        },
        "symbology_qa": sym,
        "coverage": coverage,
        "hashes": {
            "corrected_primary_sessions_sha256": sha256_file(out / "corrected_primary_sessions.csv"),
            "corrected_strata_weights_sha256": sha256_file(out / "corrected_strata_weights.csv"),
            "coverage_family_sha256": sha256_file(out / "dev_rank1_coverage_family_behavior_direction_year.csv"),
            "coverage_entry_models_sha256": sha256_file(out / "dev_rank1_coverage_entry_models.csv"),
        },
        "blocking_gates": {
            "exactly_96_dev_rank1_sessions": bool(len(rank1) == 96),
            "exactly_92_new_dev_rank1_sessions": bool(len(new_rank1) == 92),
            "four_paid_rank1_reused": bool(int(rank1.already_paid.sum()) == 4),
            "no_zero_record_new_sessions": bool(len(zero_sessions) == 0),
            "symbology_complete": bool(not sym.get("not_found") and not sym.get("partial")),
            "quote_within_20_16": bool(total_quote <= CAP_USD),
        },
        "note": "No market-data range or batch request exists in this script. Only free symbology resolution and metadata cost/count queries are used.",
    }
    (out / "dev_rank1_zero_cost_gate.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
