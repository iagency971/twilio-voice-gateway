#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import databento as db

SIDE_NONE = {"N", "None", "nan", "NaN", "", "0"}
EPS = 1e-9


def load_dbn(path: Path) -> pd.DataFrame:
    return db.DBNStore.from_file(path).to_df(map_symbols=True).reset_index(drop=False)


def side_stats(df: pd.DataFrame) -> tuple[int, int, float, dict[str, int]]:
    if "side" not in df.columns:
        return 0, len(df), 1.0, {}
    s = df["side"].astype(str)
    miss = s.isin(SIDE_NONE)
    return int(miss.sum()), int(len(s)), float(miss.mean()) if len(s) else 1.0, {str(k): int(v) for k, v in s.value_counts(dropna=False).to_dict().items()}


def multiset_equal(a: pd.DataFrame, b: pd.DataFrame, cols: list[str]) -> bool:
    if not cols or len(a) != len(b):
        return False
    ga = a.groupby(cols, dropna=False).size().rename("n_a").reset_index()
    gb = b.groupby(cols, dropna=False).size().rename("n_b").reset_index()
    m = ga.merge(gb, on=cols, how="outer")
    return bool(m["n_a"].fillna(0).eq(m["n_b"].fillna(0)).all())


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
        out["trades_duplicate_keys"] = int(tr.duplicated(key).sum())
        out["tbbo_duplicate_keys"] = int(tb.duplicated(key).sum())
        out["key_multiset_equal"] = multiset_equal(tr, tb, key)
        out["trade_payload_multiset_equal"] = multiset_equal(tr, tb, key + payload)
    else:
        out["key_multiset_equal"] = False
        out["trade_payload_multiset_equal"] = False

    miss, _, rate, counts = side_stats(tr)
    out["trades_side_missing"] = miss
    out["trades_side_missing_rate"] = rate
    out["trades_side_counts"] = counts
    miss2, _, rate2, counts2 = side_stats(tb)
    out["tbbo_side_missing"] = miss2
    out["tbbo_side_missing_rate"] = rate2
    out["tbbo_side_counts"] = counts2

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
        out["tbbo_valid_bbo_records"] = int(valid.sum())
        out["tbbo_valid_bbo_fraction"] = float(valid.mean()) if len(tb) else 0.0
        out["tbbo_locked_or_crossed_records"] = int((valid & (bid >= ask)).sum())
        out["tbbo_locked_or_crossed_fraction"] = float((valid & (bid >= ask)).mean()) if len(tb) else 0.0
        if valid.any():
            out["tbbo_spread_median"] = float(spread[valid].median())
            out["tbbo_spread_p95"] = float(spread[valid].quantile(0.95))

        # Databento Trade side convention: A=sell aggressor, B=buy aggressor, N=unspecified.
        # A trade is mechanically BBO-classifiable only if it is uniquely at/beyond one side.
        at_sell = valid & (px <= bid + EPS)
        at_buy = valid & (px >= ask - EPS)
        pred_sell = at_sell & ~at_buy
        pred_buy = at_buy & ~at_sell
        conflict = at_sell & at_buy
        neither = valid & ~at_sell & ~at_buy

        known = valid & side.isin(["A", "B"])
        known_classifiable = known & (pred_sell | pred_buy)
        known_correct = (side.eq("A") & pred_sell) | (side.eq("B") & pred_buy)
        out["known_side_records_with_valid_bbo"] = int(known.sum())
        out["known_side_bbo_classifiable_records"] = int(known_classifiable.sum())
        out["known_side_bbo_correct_records"] = int((known_correct & known_classifiable).sum())
        out["known_side_bbo_conflict_records"] = int((known & conflict).sum())
        out["known_side_bbo_ambiguous_records"] = int((known & neither).sum())
        out["known_side_bbo_classifiable_fraction"] = float(known_classifiable.sum() / known.sum()) if known.any() else None
        out["known_side_bbo_accuracy_if_classifiable"] = float((known_correct & known_classifiable).sum() / known_classifiable.sum()) if known_classifiable.any() else None

        none = valid & side.isin(SIDE_NONE)
        none_classifiable = none & (pred_sell | pred_buy)
        out["unspecified_side_records_with_valid_bbo"] = int(none.sum())
        out["unspecified_side_bbo_classifiable_records"] = int(none_classifiable.sum())
        out["unspecified_side_bbo_pred_sell_records"] = int((none & pred_sell).sum())
        out["unspecified_side_bbo_pred_buy_records"] = int((none & pred_buy).sum())
        out["unspecified_side_bbo_conflict_records"] = int((none & conflict).sum())
        out["unspecified_side_bbo_ambiguous_records"] = int((none & neither).sum())
        out["unspecified_side_bbo_classifiable_fraction"] = float(none_classifiable.sum() / none.sum()) if none.any() else None
    return out


def aggregate_bbo_recovery(g: pd.DataFrame) -> dict:
    known = int(g.known_side_records_with_valid_bbo.sum())
    known_cls = int(g.known_side_bbo_classifiable_records.sum())
    known_ok = int(g.known_side_bbo_correct_records.sum())
    n_valid = int(g.unspecified_side_records_with_valid_bbo.sum())
    n_cls = int(g.unspecified_side_bbo_classifiable_records.sum())
    return {
        "known_side_records_with_valid_bbo": known,
        "known_side_bbo_classifiable_records": known_cls,
        "known_side_bbo_classifiable_fraction": float(known_cls / known) if known else None,
        "known_side_bbo_correct_records": known_ok,
        "known_side_bbo_accuracy_if_classifiable": float(known_ok / known_cls) if known_cls else None,
        "unspecified_side_records_with_valid_bbo": n_valid,
        "unspecified_side_bbo_classifiable_records": n_cls,
        "unspecified_side_bbo_classifiable_fraction": float(n_cls / n_valid) if n_valid else None,
        "unspecified_side_bbo_pred_sell_records": int(g.unspecified_side_bbo_pred_sell_records.sum()),
        "unspecified_side_bbo_pred_buy_records": int(g.unspecified_side_bbo_pred_buy_records.sum()),
        "unspecified_side_bbo_conflict_records": int(g.unspecified_side_bbo_conflict_records.sum()),
        "unspecified_side_bbo_ambiguous_records": int(g.unspecified_side_bbo_ambiguous_records.sum()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-root", required=True)
    ap.add_argument("--sessions", required=True)
    ap.add_argument("--gate", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.raw_root)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
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

    total_tr = int(q.trades_records.sum())
    total_tb = int(q.tbbo_records.sum())
    total_missing = int(q.trades_side_missing.sum())
    total_missing_rate = float(total_missing / total_tr) if total_tr else 1.0
    era_missing = []
    era_recovery = []
    for era, g in q.groupby("era", sort=True):
        n = int(g.trades_records.sum())
        m = int(g.trades_side_missing.sum())
        era_missing.append({"era": era, "records": n, "side_missing": m, "side_missing_rate": float(m / n) if n else 1.0})
        z = aggregate_bbo_recovery(g)
        z["era"] = era
        era_recovery.append(z)

    counts_ok = bool(q.record_count_equal.all())
    key_ok = bool(q.key_multiset_equal.all())
    payload_ok = bool(q.trade_payload_multiset_equal.all())
    side_total_ok = total_missing_rate <= 0.02
    side_era_ok = all(x["side_missing_rate"] <= 0.05 for x in era_missing)
    symbols_ok = bool(q.trades_symbols.astype(str).str.len().gt(2).all() and q.tbbo_symbols.astype(str).str.len().gt(2).all())
    recovery = aggregate_bbo_recovery(q)

    raw_meta = []
    for p in sorted(root.rglob("*.json")):
        try:
            d = json.loads(p.read_text())
            if d.get("version") == "COMEX_V4_PILOT12_RAW_FILE_V1":
                raw_meta.append(d)
        except Exception:
            pass
    if len(raw_meta) != 24:
        raise SystemExit(f"expected 24 raw metadata JSON files, got {len(raw_meta)}")

    immediate_quote_total = float(sum(float(x["immediate_pre_download_quote_usd"]) for x in raw_meta))
    gate_quote_total = float(gate["current_pre_download_quote_usd"])
    cap = float(gate["approved_cap_usd"])
    summary = {
        "version": "COMEX_V4_PILOT12_QA_V3_MULTISET_BBO_RECOVERY",
        "sessions": 12,
        "schemas_downloaded": ["trades", "tbbo"],
        "download_performed": True,
        "approved_cap_usd": cap,
        "gate_quote_total_usd": gate_quote_total,
        "immediate_pre_download_quote_total_usd": immediate_quote_total,
        "portal_observed_usage_usd": 4.01,
        "portal_observed_usage_source": "user-provided Databento Data usage screenshot, 2026-08-18",
        "quote_within_cap": bool(gate_quote_total <= cap and immediate_quote_total <= cap),
        "trades_records": total_tr,
        "tbbo_records": total_tb,
        "record_counts_equal_all_sessions": counts_ok,
        "trade_key_multiset_equal_all_sessions": key_ok,
        "trade_payload_multiset_equal_all_sessions": payload_ok,
        "trades_side_missing_records": total_missing,
        "trades_side_missing_rate": total_missing_rate,
        "side_missing_by_era": era_missing,
        "bbo_side_recovery_overall": recovery,
        "bbo_side_recovery_by_era": era_recovery,
        "qa_gate_side_total_le_2pct": side_total_ok,
        "qa_gate_side_each_era_le_5pct": side_era_ok,
        "qa_gate_symbols_present": symbols_ok,
        "qa_pass_for_native_side_only_experiment": bool(counts_ok and key_ok and payload_ok and side_total_ok and side_era_ok and symbols_ok),
        "note": "No market-data request is made by this QA script. Portal/account billing remains authoritative for actual credit consumption. V3 compares transaction multisets exactly and evaluates pre-trade BBO recovery of N-side records against native A/B records.",
    }
    (outdir / "pilot12_qa_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
