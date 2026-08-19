#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import databento as db
import numpy as np
import pandas as pd

PRICE_FIELDS = ["open", "high", "low", "close"]
MATCHING_FIELDS = ["instrument_id", *PRICE_FIELDS]
ALL_FIELDS = [*MATCHING_FIELDS, "volume"]


def to_utc(v) -> pd.Timestamp:
    x = pd.Timestamp(v)
    return x.tz_localize("UTC") if x.tzinfo is None else x.tz_convert("UTC")


def load_dbn(path: Path) -> pd.DataFrame:
    x = db.DBNStore.from_file(path).to_df().reset_index(drop=False)
    if "ts_event" not in x.columns:
        if len(x.columns) == 0:
            return pd.DataFrame(columns=["ts_event"])
        x = x.rename(columns={x.columns[0]: "ts_event"})
    x["ts_event"] = pd.to_datetime(x["ts_event"], utc=True)
    for c in PRICE_FIELDS + ["volume"]:
        if c in x.columns:
            x[c] = pd.to_numeric(x[c], errors="coerce")
    if "instrument_id" in x.columns:
        x["instrument_id"] = x["instrument_id"].astype(str)
    return x.sort_values("ts_event", kind="mergesort").reset_index(drop=True)


def find_context(root: Path) -> tuple[dict, Path]:
    found = []
    for p in root.rglob("*.json"):
        try:
            z = json.loads(p.read_text())
        except Exception:
            continue
        if z.get("request_type") != "CONTINUOUS_OHLCV_CONTEXT":
            continue
        raw = z.get("raw_file")
        qs = list(root.rglob(str(raw))) if raw else []
        if len(qs) == 1:
            found.append((z, qs[0]))
    if len(found) != 1:
        raise SystemExit(f"expected exactly one continuous context marker, got {len(found)}")
    return found[0]


def read_n1_markers(root: Path) -> dict[str, tuple[dict, Path]]:
    out: dict[str, tuple[dict, Path]] = {}
    for p in root.rglob("*.json"):
        try:
            z = json.loads(p.read_text())
        except Exception:
            continue
        rid, raw = z.get("market_request_id"), z.get("raw_file")
        if rid is None or not raw:
            continue
        qs = list(root.rglob(str(raw)))
        if len(qs) == 1:
            out[str(rid)] = (z, qs[0])
    return out


def eq_numeric(a: pd.Series, b: pd.Series) -> pd.Series:
    aa = pd.to_numeric(a, errors="coerce")
    bb = pd.to_numeric(b, errors="coerce")
    same_nan = aa.isna() & bb.isna()
    finite = aa.notna() & bb.notna()
    out = pd.Series(False, index=a.index, dtype=bool)
    out.loc[same_nan] = True
    if finite.any():
        out.loc[finite] = np.isclose(aa.loc[finite].astype(float), bb.loc[finite].astype(float), rtol=0.0, atol=1e-9)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--context-root", required=True)
    ap.add_argument("--n1-root", required=True)
    ap.add_argument("--n1-market-manifest", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    _, context_path = find_context(Path(a.context_root))
    context = load_dbn(context_path)
    required_ctx = {"ts_event", *ALL_FIELDS}
    miss_ctx = sorted(required_ctx - set(context.columns))
    if miss_ctx:
        raise SystemExit(f"context missing fields {miss_ctx}")

    manifest = pd.read_csv(a.n1_market_manifest, dtype={"source_instrument_id": str, "symbols": str})
    markers = read_n1_markers(Path(a.n1_root))

    block_rows = []
    field_totals = {f: 0 for f in ALL_FIELDS}
    joined_total = 0
    n1_only_total = 0
    ctx_only_total = 0
    duplicate_n1_total = 0
    duplicate_ctx_total = 0
    matching_field_mismatch_total = 0
    volume_only_mismatch_total = 0

    for r in manifest.itertuples(index=False):
        rid = str(r.market_request_id)
        if rid not in markers:
            raise SystemExit(f"N1 marker missing {rid}")
        _, raw_path = markers[rid]
        n1 = load_dbn(raw_path)
        s, e = to_utc(r.start), to_utc(r.end)
        n1 = n1[(n1.ts_event >= s) & (n1.ts_event < e)].copy()
        ctx = context[(context.ts_event >= s) & (context.ts_event < e)].copy()

        n1_dups = int(n1.ts_event.duplicated(keep=False).sum())
        ctx_dups = int(ctx.ts_event.duplicated(keep=False).sum())
        duplicate_n1_total += n1_dups
        duplicate_ctx_total += ctx_dups

        # Keep this diagnostic explicit: duplicate timestamps prevent unambiguous row parity.
        if n1_dups or ctx_dups:
            raise SystemExit(f"duplicate timestamp in parity block {rid}: n1={n1_dups} ctx={ctx_dups}")

        needed_n1 = {"ts_event", *PRICE_FIELDS, "volume"}
        miss_n1 = sorted(needed_n1 - set(n1.columns))
        if miss_n1:
            raise SystemExit(f"N1 block {rid} missing fields {miss_n1}")

        # If DBN decoded N1 has no instrument_id column, the frozen request iid is the row iid.
        if "instrument_id" not in n1.columns:
            n1["instrument_id"] = str(r.source_instrument_id)
        else:
            n1["instrument_id"] = n1.instrument_id.astype(str)

        left = n1[["ts_event", *ALL_FIELDS]].copy()
        right = ctx[["ts_event", *ALL_FIELDS]].copy()
        z = left.merge(right, on="ts_event", how="outer", suffixes=("_n1", "_ctx"), indicator=True, validate="one_to_one")
        both = z["_merge"].eq("both")
        n1_only = int(z["_merge"].eq("left_only").sum())
        ctx_only = int(z["_merge"].eq("right_only").sum())
        n1_only_total += n1_only
        ctx_only_total += ctx_only
        joined = int(both.sum())
        joined_total += joined

        field_mismatch = {}
        masks: dict[str, pd.Series] = {}
        for f in ALL_FIELDS:
            if f == "instrument_id":
                eq = z[f"{f}_n1"].astype(str).eq(z[f"{f}_ctx"].astype(str)) & both
            else:
                eq = eq_numeric(z[f"{f}_n1"], z[f"{f}_ctx"]) & both
            mismatch = both & ~eq
            masks[f] = mismatch
            n = int(mismatch.sum())
            field_mismatch[f] = n
            field_totals[f] += n

        matching_any = pd.Series(False, index=z.index, dtype=bool)
        for f in MATCHING_FIELDS:
            matching_any |= masks[f]
        volume_mismatch = masks["volume"]
        volume_only = both & volume_mismatch & ~matching_any
        matching_count = int(matching_any.sum())
        volume_only_count = int(volume_only.sum())
        matching_field_mismatch_total += matching_count
        volume_only_mismatch_total += volume_only_count

        expected_iid = str(r.source_instrument_id)
        ctx_iids = sorted(ctx.instrument_id.astype(str).unique().tolist())
        n1_iids = sorted(n1.instrument_id.astype(str).unique().tolist())

        block_rows.append({
            "market_request_id": rid,
            "source_research_date": str(r.source_research_date),
            "eligible_next_research_date": str(r.eligible_next_research_date),
            "source_year": int(pd.Timestamp(r.source_research_date).year),
            "source_instrument_id": expected_iid,
            "start": str(r.start),
            "end": str(r.end),
            "n1_rows": int(len(n1)),
            "context_rows": int(len(ctx)),
            "joined_rows": joined,
            "n1_only_timestamps": n1_only,
            "context_only_timestamps": ctx_only,
            "n1_duplicate_timestamp_rows": n1_dups,
            "context_duplicate_timestamp_rows": ctx_dups,
            "n1_iids": "+".join(n1_iids),
            "context_iids": "+".join(ctx_iids),
            **{f"mismatch_{f}_rows": field_mismatch[f] for f in ALL_FIELDS},
            "matching_field_mismatch_rows": matching_count,
            "volume_only_mismatch_rows": volume_only_count,
            "timestamp_set_exact": n1_only == 0 and ctx_only == 0,
            "matching_fields_exact": n1_only == 0 and ctx_only == 0 and matching_count == 0,
            "full_ohlcv_exact": n1_only == 0 and ctx_only == 0 and matching_count == 0 and field_mismatch["volume"] == 0,
        })

    blocks = pd.DataFrame(block_rows).sort_values(["source_research_date", "market_request_id"]).reset_index(drop=True)
    blocks.to_csv(out / "context_field_parity_by_block.csv", index=False)

    by_year = blocks.groupby("source_year", as_index=False).agg(
        blocks=("market_request_id", "count"),
        matching_exact_blocks=("matching_fields_exact", "sum"),
        full_ohlcv_exact_blocks=("full_ohlcv_exact", "sum"),
        joined_rows=("joined_rows", "sum"),
        matching_field_mismatch_rows=("matching_field_mismatch_rows", "sum"),
        volume_only_mismatch_rows=("volume_only_mismatch_rows", "sum"),
        n1_only_timestamps=("n1_only_timestamps", "sum"),
        context_only_timestamps=("context_only_timestamps", "sum"),
    )
    by_year.to_csv(out / "context_field_parity_by_year.csv", index=False)

    summary = {
        "version": "COMEX_NATIVE_REACTION_CONTEXT_FIELD_PARITY_V1",
        "authorization": "ZERO_OUTCOME_ZERO_MARKET_API_DIAGNOSTIC",
        "post_anchor_outcomes_read": False,
        "reaction_outcomes_computed": False,
        "databento_api_calls": 0,
        "market_data_api_called": False,
        "market_data_download_performed": False,
        "matching_fields": MATCHING_FIELDS,
        "volume_used_by_matching": False,
        "n1_blocks": int(len(blocks)),
        "joined_rows": int(joined_total),
        "n1_only_timestamps": int(n1_only_total),
        "context_only_timestamps": int(ctx_only_total),
        "n1_duplicate_timestamp_rows": int(duplicate_n1_total),
        "context_duplicate_timestamp_rows": int(duplicate_ctx_total),
        "field_mismatch_rows": {k: int(v) for k, v in field_totals.items()},
        "matching_field_mismatch_rows": int(matching_field_mismatch_total),
        "volume_only_mismatch_rows": int(volume_only_mismatch_total),
        "timestamp_sets_all_exact": bool(blocks.timestamp_set_exact.all()),
        "matching_field_parity_all_pass": bool(blocks.matching_fields_exact.all()),
        "full_ohlcv_parity_all_pass": bool(blocks.full_ohlcv_exact.all()),
        "matching_exact_blocks": int(blocks.matching_fields_exact.sum()),
        "full_ohlcv_exact_blocks": int(blocks.full_ohlcv_exact.sum()),
        "notes": [
            "Timestamp is the one-to-one join key and is audited via left/right-only counts and duplicate checks.",
            "Matching-field parity is instrument_id + OHLC. Volume is reported separately because the frozen matching design does not use volume.",
            "No post-anchor reaction field is read or computed by this diagnostic.",
        ],
    }
    (out / "context_field_parity.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
