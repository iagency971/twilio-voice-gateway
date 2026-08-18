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

NY = ZoneInfo("America/New_York")
SEED = "COMEX_V4_PILOT12_SEED_971"
SCHEMAS = ("trades", "tbbo", "bbo-1s", "mbp-1")
ERAS = (
    ("E1_2011_2013", 2011, 2013),
    ("E2_2014_2018", 2014, 2018),
    ("E3_2019_2022", 2019, 2022),
    ("E4_2023_2025", 2023, 2025),
)


def stable_hash(*parts: object) -> str:
    return hashlib.sha256("|".join(str(x) for x in parts).encode("utf-8")).hexdigest()


def session_bounds(date_str: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    d = pd.Timestamp(date_str)
    prev = (d - pd.Timedelta(days=1)).date()
    cur = d.date()
    # Deliberately wide envelope used by the prior canonical cost work.
    start = pd.Timestamp(f"{prev} 17:00:00", tz=NY).tz_convert("UTC")
    end = pd.Timestamp(f"{cur} 18:00:00", tz=NY).tz_convert("UTC")
    return start, end


def choose_sessions(candidates: pd.DataFrame) -> pd.DataFrame:
    required = {"research_trading_date", "year", "quarter", "vol_band"}
    missing = required - set(candidates.columns)
    if missing:
        raise ValueError(f"missing session candidate columns: {sorted(missing)}")

    x = candidates.copy()
    x["year"] = pd.to_numeric(x["year"], errors="raise").astype(int)
    x["quarter"] = pd.to_numeric(x["quarter"], errors="raise").astype(int)
    x["vol_band"] = pd.to_numeric(x["vol_band"], errors="raise").astype(int)

    rows: list[pd.Series] = []
    for era_name, y0, y1 in ERAS:
        era = x[(x.year >= y0) & (x.year <= y1)].copy()
        used_quarters: set[int] = set()
        bands = sorted(int(v) for v in era.vol_band.dropna().unique())
        if bands != [0, 1, 2]:
            raise ValueError(f"{era_name}: expected vol bands [0,1,2], got {bands}")

        # Process bands by a seed-derived order so quarter diversification itself is outcome-blind.
        band_order = sorted(bands, key=lambda b: stable_hash(SEED, era_name, "band_order", b))
        for band in band_order:
            q = era[era.vol_band == band].copy()
            if q.empty:
                raise ValueError(f"{era_name}: no candidate for vol_band={band}")
            q["pilot_hash"] = [
                stable_hash(SEED, era_name, band, r.quarter, r.research_trading_date)
                for r in q.itertuples()
            ]
            diversified = q[~q.quarter.isin(used_quarters)]
            pool = diversified if not diversified.empty else q
            pick = pool.sort_values(["pilot_hash", "research_trading_date"]).iloc[0].copy()
            pick["era"] = era_name
            pick["pilot_vol_band"] = band
            pick["quarter_diversified"] = bool(not diversified.empty)
            rows.append(pick)
            used_quarters.add(int(pick.quarter))

    out = pd.DataFrame(rows).copy()
    if len(out) != 12:
        raise AssertionError(f"expected 12 pilot sessions, got {len(out)}")
    if out.research_trading_date.duplicated().any():
        raise AssertionError("duplicate pilot dates selected")
    out = out.sort_values(["era", "pilot_vol_band"]).reset_index(drop=True)
    return out


def metadata_metric(client: db.Historical, method: str, schema: str, start: pd.Timestamp, end: pd.Timestamp):
    fn = getattr(client.metadata, method)
    last_err = None
    for attempt in range(7):
        try:
            return fn(
                dataset="GLBX.MDP3",
                symbols="GC.v.0",
                stype_in="continuous",
                schema=schema,
                start=start.isoformat(),
                end=end.isoformat(),
            )
        except Exception as exc:  # pragma: no cover - exercised in Actions
            last_err = exc
            time.sleep(min(20, 2**attempt))
    raise RuntimeError(f"metadata {method} failed for {schema} {start} {end}: {last_err}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("DATABENTO_API_KEY")
    if not api_key:
        raise SystemExit("DATABENTO_API_KEY missing")

    candidates = pd.read_csv(args.sessions)
    pilot = choose_sessions(candidates)
    client = db.Historical(api_key)

    quote_rows = []
    for r in pilot.itertuples():
        start, end = session_bounds(str(r.research_trading_date))
        for schema in SCHEMAS:
            cost = float(metadata_metric(client, "get_cost", schema, start, end))
            records = int(metadata_metric(client, "get_record_count", schema, start, end))
            billable = int(metadata_metric(client, "get_billable_size", schema, start, end))
            quote_rows.append(
                {
                    "era": r.era,
                    "research_trading_date": str(r.research_trading_date),
                    "year": int(r.year),
                    "quarter": int(r.quarter),
                    "vol_band": int(r.vol_band),
                    "schema": schema,
                    "start_utc": start.isoformat(),
                    "end_utc": end.isoformat(),
                    "cost_usd": cost,
                    "records": records,
                    "billable_bytes": billable,
                    "download_performed": False,
                }
            )

    qdf = pd.DataFrame(quote_rows)
    summary = []
    for schema, g in qdf.groupby("schema", sort=True):
        summary.append(
            {
                "schema": schema,
                "sessions": int(g.research_trading_date.nunique()),
                "cost_usd": float(g.cost_usd.sum()),
                "records": int(g.records.sum()),
                "billable_bytes": int(g.billable_bytes.sum()),
            }
        )

    pilot_cols = [
        "era", "research_trading_date", "year", "quarter", "vol_band",
        "pilot_vol_band", "quarter_diversified", "pilot_hash",
    ]
    pilot[pilot_cols].to_csv(outdir / "pilot12_sessions.csv", index=False)
    qdf.to_csv(outdir / "pilot12_schema_quotes.csv", index=False)

    result = {
        "version": "COMEX_V4_PILOT12_METADATA_V1",
        "selection_seed": SEED,
        "selection_rule": "4 eras x 3 XAU volatility bands; deterministic hash; unused quarter preferred within era when available",
        "eras": [{"name": n, "start_year": a, "end_year": b} for n, a, b in ERAS],
        "schemas": list(SCHEMAS),
        "sessions": pilot[pilot_cols].to_dict("records"),
        "summary": summary,
        "pilot_total_if_all_four_schemas_were_downloaded_usd": float(qdf.cost_usd.sum()),
        "authorization": "METADATA_ONLY",
        "download_performed": False,
        "warning": "No Databento market-data range/batch download is called by this script. Quotes only.",
    }
    (outdir / "pilot12_quote.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
