#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import databento as db

SIDE_NONE = {"N", "None", "nan", "NaN", "", "0"}


def load_dbn(path: Path) -> pd.DataFrame:
    return db.DBNStore.from_file(path).to_df(map_symbols=True).reset_index(drop=False)


def side_stats(df: pd.DataFrame) -> tuple[int, int, float, dict[str, int]]:
    if "side" not in df.columns:
        return 0, len(df), 1.0, {}
    s = df["side"].astype(str)
    miss = s.isin(SIDE_NONE)
    return int(miss.sum()), int(len(s)), float(miss.mean()) if len(s) else 1.0, {str(k): int(v) for k, v in s.value_counts(dropna=False).to_dict().items()}


def qa_pair(date: str, era: str, trades_path: Path, tbbo_path: Path) -> dict:
    tr = load_dbn(trades_path)
    tb = load_dbn(tbbo_path)
    out = {
        "era": era,
        "research_trading_date": date,
        "trades_records": int(len(tr)),
        "tbbo_records": int(len(tb)),
        "record_count_equal": bool(len(tr) == len(tb)),
    }

    key = [c for c in ["ts_event", "instrument_id", "sequence"] if c in tr.columns and c in tb.columns]
    payload = [c for c in ["price", "size", "side"] if c in tr.columns and c in tb.columns]
    if key:
        a = tr[key + payload].copy(); b = tb[key + payload].copy()
        out["trades_duplicate_keys"] = int(a.duplicated(key).sum())
        out["tbbo_duplicate_keys"] = int(b.duplicated(key).sum())
        m = a.merge(b, on=key, how="outer", suffixes=("_trades", "_tbbo"), indicator=True)
        out["key_match_fraction"] = float((m["_merge"] == "both").sum() / max(len(m), 1))
        for c in payload:
            left = f"{c}_trades"; right = f"{c}_tbbo"
            if left in m.columns and right in m.columns:
                if c == "side":
                    eq = m[left].astype(str).eq(m[right].astype(str))
                else:
                    eq = pd.to_numeric(m[left], errors="coerce").eq(pd.to_numeric(m[right], errors="coerce"))
                out[f"{c}_match_fraction"] = float(eq[m["_merge"] == "both"].mean()) if (m["_merge"] == "both").any() else 0.0
    else:
        out["key_match_fraction"] = 0.0

    miss, n, rate, counts = side_stats(tr)
    out["trades_side_missing"] = miss; out["trades_side_missing_rate"] = rate; out["trades_side_counts"] = counts
    miss2, n2, rate2, counts2 = side_stats(tb)
    out["tbbo_side_missing"] = miss2; out["tbbo_side_missing_rate"] = rate2; out["tbbo_side_counts"] = counts2

    out["trades_instrument_ids"] = sorted(int(x) for x in pd.Series(tr.get("instrument_id", pd.Series(dtype=float))).dropna().unique())
    out["tbbo_instrument_ids"] = sorted(int(x) for x in pd.Series(tb.get("instrument_id", pd.Series(dtype=float))).dropna().unique())
    out["trades_symbols"] = sorted(str(x) for x in pd.Series(tr.get("symbol", pd.Series(dtype=object))).dropna().unique())
    out["tbbo_symbols"] = sorted(str(x) for x in pd.Series(tb.get("symbol", pd.Series(dtype=object))).dropna().unique())

    if {"price", "side", "bid_px_00", "ask_px_00"}.issubset(tb.columns):
        px = pd.to_numeric(tb["price"], errors="coerce")
        bid = pd.to_numeric(tb["bid_px_00"], errors="coerce")
        ask = pd.to_numeric(tb["ask_px_00"], errors="coerce")
        valid = px.notna() & bid.notna() & ask.notna() & (bid > 0) & (ask > 0)
        side = tb["side"].astype(str)
        spread = ask - bid
        out["tbbo_valid_bbo_fraction"] = float(valid.mean()) if len(tb) else 0.0
        out["tbbo_locked_or_crossed_fraction"] = float((valid & (bid >= ask)).mean()) if len(tb) else 0.0
        if valid.any():
            out["tbbo_spread_median"] = float(spread[valid].median())
            out["tbbo_spread_p95"] = float(spread[valid].quantile(0.95))
        sell = valid & side.eq("A")
        buy = valid & side.eq("B")
        out["sell_aggressor_records"] = int(sell.sum())
        out["buy_aggressor_records"] = int(buy.sum())
        out["sell_price_at_or_below_bid_fraction"] = float((px[sell] <= bid[sell] + 1e-12).mean()) if sell.any() else None
        out["buy_price_at_or_above_ask_fraction"] = float((px[buy] >= ask[buy] - 1e-12).mean()) if buy.any() else None
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-root", required=True)
    ap.add_argument("--sessions", required=True)
    ap.add_argument("--gate", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.raw_root); outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    sessions = pd.read_csv(args.sessions)
    era_by_date = dict(zip(sessions.research_trading_date.astype(str), sessions.era.astype(str)))
    gate = json.loads(Path(args.gate).read_text())

    pair_rows = []
    for date, era in era_by_date.items():
        t = list(root.rglob(f"{date}__trades.dbn.zst"))
        b = list(root.rglob(f"{date}__tbbo.dbn.zst"))
        if len(t) != 1 or len(b) != 1:
            raise SystemExit(f"expected one trades and one tbbo file for {date}; got {len(t)}, {len(b)}")
        pair_rows.append(qa_pair(date, era, t[0], b[0]))

    q = pd.DataFrame(pair_rows)
    q.to_csv(outdir / "pilot12_qa_by_session.csv", index=False)

    total_tr = int(q.trades_records.sum()); total_tb = int(q.tbbo_records.sum())
    total_missing = int(q.trades_side_missing.sum())
    total_missing_rate = float(total_missing / total_tr) if total_tr else 1.0
    era_missing = []
    for era, g in q.groupby("era", sort=True):
        n = int(g.trades_records.sum()); m = int(g.trades_side_missing.sum())
        era_missing.append({"era": era, "records": n, "side_missing": m, "side_missing_rate": float(m / n) if n else 1.0})

    key_ok = bool((q.key_match_fraction >= 0.999999).all())
    payload_ok = all(bool((q[c] >= 0.999999).all()) for c in ["price_match_fraction", "size_match_fraction", "side_match_fraction"] if c in q.columns)
    side_total_ok = total_missing_rate <= 0.02
    side_era_ok = all(x["side_missing_rate"] <= 0.05 for x in era_missing)
    counts_ok = bool(q.record_count_equal.all())
    symbols_ok = bool(q.trades_symbols.astype(str).str.len().gt(2).all() and q.tbbo_symbols.astype(str).str.len().gt(2).all())

    raw_meta = []
    for p in sorted(root.rglob("*.json")):
        try:
            d = json.loads(p.read_text())
            if d.get("version") == "COMEX_V4_PILOT12_RAW_FILE_V1": raw_meta.append(d)
        except Exception:
            pass
    if len(raw_meta) != 24:
        raise SystemExit(f"expected 24 raw metadata JSON files, got {len(raw_meta)}")

    immediate_quote_total = float(sum(float(x["immediate_pre_download_quote_usd"]) for x in raw_meta))
    gate_quote_total = float(gate["current_pre_download_quote_usd"])
    cap = float(gate["approved_cap_usd"])

    summary = {
        "version": "COMEX_V4_PILOT12_QA_V1",
        "sessions": 12,
        "schemas_downloaded": ["trades", "tbbo"],
        "download_performed": True,
        "approved_cap_usd": cap,
        "gate_quote_total_usd": gate_quote_total,
        "immediate_pre_download_quote_total_usd": immediate_quote_total,
        "quote_within_cap": bool(gate_quote_total <= cap and immediate_quote_total <= cap),
        "trades_records": total_tr,
        "tbbo_records": total_tb,
        "record_counts_equal_all_sessions": counts_ok,
        "trade_key_match_all_sessions": key_ok,
        "trade_payload_match_all_sessions": payload_ok,
        "trades_side_missing_records": total_missing,
        "trades_side_missing_rate": total_missing_rate,
        "side_missing_by_era": era_missing,
        "qa_gate_side_total_le_2pct": side_total_ok,
        "qa_gate_side_each_era_le_5pct": side_era_ok,
        "qa_gate_symbols_present": symbols_ok,
        "qa_pass_for_trade_side_experiment": bool(counts_ok and key_ok and payload_ok and side_total_ok and side_era_ok and symbols_ok),
        "raw_files": [{k: x[k] for k in ["era", "research_trading_date", "schema", "raw_file", "raw_file_bytes", "sha256", "records_downloaded", "immediate_pre_download_quote_usd"]} for x in raw_meta],
        "note": "Portal/account billing remains the authority for actual credit consumption; these are immediate pre-download metadata quotes and downloaded-file QA.",
    }
    (outdir / "pilot12_qa_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
