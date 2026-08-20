#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from rzr.features import robust_sigma60, trading_day_key
from rzr.io import load_ohlc_csv

SCENARIOS = {
    "S10_C6": {"spread": 0.10, "commission": 6.0, "role": "sensitivity"},
    "S11_C6_PRIMARY": {"spread": 0.11, "commission": 6.0, "role": "primary"},
    "S12_C6": {"spread": 0.12, "commission": 6.0, "role": "sensitivity"},
    "S18_C9_STRESS": {"spread": 0.18, "commission": 9.0, "role": "stress"},
}
TARGET_RS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
EXPECTED_PROTOCOL_SHA256 = "f72ec721c1fd754140dec9aba46173ee6f7b42873b8a7553470a14e382314eda"
EXPECTED_FREEZE_SHA256 = "7a46a6847e8b574afa3576714349dbeaa8ec4d7ae2b1a39f4356a03e68fa4197"
EXPECTED_EVENT_SHA256 = "39ed2f7eac7465d46344bef85d64d3b897f0b56af66448e537fba1bfff315aeb"
EXPECTED_EVENT_COUNT = 498


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def valid_opening_quote(bid: float, ask: float) -> bool:
    return bool(np.isfinite(bid) and np.isfinite(ask) and bid > 0 and ask > 0 and ask >= bid)


def scenario_bar(row: pd.Series, spread: float, direction: str) -> tuple[float, float, float]:
    half = 0.5 * float(spread)
    if direction == "LONG":
        return float(row["open"] - half), float(row["high"] - half), float(row["low"] - half)
    return float(row["open"] + half), float(row["high"] + half), float(row["low"] + half)


def simulate_trade(
    bars: pd.DataFrame,
    entry_idx: int,
    entry_time: pd.Timestamp,
    direction: str,
    entry_price: float,
    stop_price: float,
    target_price: float,
    risk_price: float,
    spread: float,
    commission: float,
    horizon_minutes: int = 120,
) -> dict:
    if direction not in {"LONG", "SHORT"}:
        raise RuntimeError(f"invalid direction {direction}")
    deadline = pd.Timestamp(entry_time) + pd.Timedelta(minutes=int(horizon_minutes))
    if pd.Timestamp(bars.index[entry_idx]) != pd.Timestamp(entry_time):
        raise RuntimeError("entry index/time mismatch")

    result = None
    exit_idx = None
    exit_time = None
    exit_price = None
    ambiguous = False

    n = len(bars)
    j = int(entry_idx)
    while j < n and pd.Timestamp(bars.index[j]) < deadline:
        row = bars.iloc[j]
        op, hi, lo = scenario_bar(row, spread, direction)
        if not all(np.isfinite(x) for x in (op, hi, lo)):
            raise RuntimeError(f"non-finite scenario OHLC at {bars.index[j]}")

        if direction == "LONG":
            if op <= stop_price:
                result, exit_price = "SL", float(op)
            elif op >= target_price:
                result, exit_price = "TP", float(target_price)
            else:
                sl = lo <= stop_price
                tp = hi >= target_price
                if sl and tp:
                    result, exit_price, ambiguous = "SL", float(stop_price), True
                elif sl:
                    result, exit_price = "SL", float(stop_price)
                elif tp:
                    result, exit_price = "TP", float(target_price)
        else:
            if op >= stop_price:
                result, exit_price = "SL", float(op)
            elif op <= target_price:
                result, exit_price = "TP", float(target_price)
            else:
                sl = hi >= stop_price
                tp = lo <= target_price
                if sl and tp:
                    result, exit_price, ambiguous = "SL", float(stop_price), True
                elif sl:
                    result, exit_price = "SL", float(stop_price)
                elif tp:
                    result, exit_price = "TP", float(target_price)

        if result is not None:
            exit_idx = j
            exit_time = pd.Timestamp(bars.index[j])
            break
        j += 1

    if result is None:
        start = int(bars.index.searchsorted(deadline, side="left"))
        k = start
        while k < n:
            b = float(pd.to_numeric(pd.Series([bars["open_bid"].iloc[k]]), errors="coerce").iloc[0])
            a = float(pd.to_numeric(pd.Series([bars["open_ask"].iloc[k]]), errors="coerce").iloc[0])
            if valid_opening_quote(b, a):
                break
            k += 1
        if k >= n:
            raise RuntimeError(f"no valid opening quote at/after deadline {deadline}")
        op, _, _ = scenario_bar(bars.iloc[k], spread, direction)
        if direction == "LONG":
            if op <= stop_price:
                result, exit_price = "SL", float(op)
            elif op >= target_price:
                result, exit_price = "TP", float(target_price)
            else:
                result, exit_price = "TIME", float(op)
        else:
            if op >= stop_price:
                result, exit_price = "SL", float(op)
            elif op <= target_price:
                result, exit_price = "TP", float(target_price)
            else:
                result, exit_price = "TIME", float(op)
        exit_idx = k
        exit_time = pd.Timestamp(bars.index[k])

    if direction == "LONG":
        gross_r = (float(exit_price) - float(entry_price)) / float(risk_price)
    else:
        gross_r = (float(entry_price) - float(exit_price)) / float(risk_price)
    commission_r = float(commission) / (100.0 * float(risk_price))
    net_r = float(gross_r - commission_r)
    return {
        "result": str(result),
        "exit_idx": int(exit_idx),
        "exit_time": pd.Timestamp(exit_time).isoformat(),
        "exit_price": float(exit_price),
        "gross_R": float(gross_r),
        "commission_R": float(commission_r),
        "net_R": float(net_r),
        "ambiguous_same_bar": bool(ambiguous),
    }


def self_test() -> None:
    idx = pd.date_range("2026-01-01T10:00:00Z", periods=125, freq="min")
    bars = pd.DataFrame(index=idx)
    bars["open"] = 100.0
    bars["high"] = 100.2
    bars["low"] = 99.8
    bars["close"] = 100.0
    bars["open_bid"] = 99.95
    bars["open_ask"] = 100.05
    bars.loc[idx[0], ["high", "low"]] = [101.2, 98.8]
    s = simulate_trade(bars, 0, idx[0], "LONG", 100.05, 99.0, 101.0, 1.05, 0.10, 6.0)
    assert s["result"] == "SL" and s["ambiguous_same_bar"] is True

    bars2 = bars.copy()
    bars2.loc[:, ["high", "low"]] = [100.2, 99.8]
    bars2.loc[idx[120], ["high", "low"]] = [105.0, 95.0]
    s2 = simulate_trade(bars2, 0, idx[0], "LONG", 100.05, 98.0, 102.0, 2.05, 0.10, 6.0)
    assert s2["result"] == "TIME" and pd.Timestamp(s2["exit_time"]) == idx[120]

    bars3 = bars2.copy()
    bars3.loc[idx[1], "open"] = 97.0
    s3 = simulate_trade(bars3, 0, idx[0], "LONG", 100.05, 98.0, 102.0, 2.05, 0.10, 6.0)
    assert s3["result"] == "SL" and s3["exit_price"] < 98.0

    bars4 = bars2.copy()
    bars4.loc[idx[1], "open"] = 104.0
    s4 = simulate_trade(bars4, 0, idx[0], "LONG", 100.05, 98.0, 102.0, 2.05, 0.10, 6.0)
    assert s4["result"] == "TP" and abs(s4["exit_price"] - 102.0) < 1e-12
    print("OUTCOME_V1_1_SELF_TEST_PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--year", type=int)
    ap.add_argument("--events")
    ap.add_argument("--freeze-manifest")
    ap.add_argument("--protocol")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        if not args.csv:
            return
    if not all([args.csv, args.year, args.events, args.freeze_manifest, args.protocol, args.out]):
        raise SystemExit("csv --year --events --freeze-manifest --protocol --out required")

    year = int(args.year)
    input_path = Path(args.csv)
    events_path = Path(args.events)
    freeze_path = Path(args.freeze_manifest)
    protocol_path = Path(args.protocol)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if sha256_file(protocol_path) != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError("protocol hash mismatch")
    if sha256_file(freeze_path) != EXPECTED_FREEZE_SHA256:
        raise RuntimeError("freeze manifest hash mismatch")
    freeze = json.load(freeze_path.open())
    if freeze.get("status") != "CAUSAL_CORE_PREOUTCOME_FULL_M1_INFORMATION_SET_READY_FOR_PNL":
        raise RuntimeError("preoutcome freeze not ready")
    if freeze["event_manifest"]["sha256"] != EXPECTED_EVENT_SHA256 or int(freeze["event_manifest"]["rows"]) != EXPECTED_EVENT_COUNT:
        raise RuntimeError("aggregate event binding mismatch")
    annual = next((x for x in freeze["annual_artifacts"] if int(x["year"]) == year), None)
    if annual is None:
        raise RuntimeError(f"missing annual freeze row {year}")
    if sha256_file(input_path) != annual["input_sha256"]:
        raise RuntimeError(f"input hash mismatch {year}")
    if sha256_file(events_path) != annual["event_manifest_sha256"]:
        raise RuntimeError(f"annual event hash mismatch {year}")

    protocol = json.load(protocol_path.open())
    if protocol.get("authorization_status") != "CAUSAL_CORE_OUTCOME_V1_1_AUTHORIZED":
        raise RuntimeError("protocol not authorized")
    if protocol["preoutcome_binding"]["event_manifest_sha256"] != EXPECTED_EVENT_SHA256:
        raise RuntimeError("protocol event binding mismatch")

    events = pd.read_csv(events_path)
    if int(len(events)) != int(annual["event_rows"]):
        raise RuntimeError(f"annual event row mismatch {year}")
    if len(events) and not (events["source_year"].astype(int) == year).all():
        raise RuntimeError("source_year mismatch")

    bars = load_ohlc_csv(str(input_path)).sort_index().copy()
    for c in ("open_bid", "high_bid", "low_bid", "close_bid", "open_ask", "high_ask", "low_ask", "close_ask"):
        if c not in bars.columns:
            raise RuntimeError(f"missing {c}")
        bars[c] = pd.to_numeric(bars[c], errors="coerce")
    sigma = robust_sigma60(bars)

    rows = []
    carry = [
        "event_id", "source_year", "doz_zone_id", "objective_zone_id", "anchor_zone_id", "anchor_family", "anchor_variant",
        "partner_zone_id", "partner_family", "partner_variant", "doz_contact_time", "objective_contact_time", "confluence_time",
        "confirm_time", "entry_time", "confluence_idx", "confirm_idx", "entry_idx", "direction", "anchor_side", "doz_side",
        "objective_side", "side_relation", "anchor_lower", "anchor_upper", "pair_lower", "pair_upper", "direct_overlap",
        "doz_origin_time", "doz_known_time", "doz_source_tf", "doz_variant", "objective_origin_time", "objective_known_time",
        "objective_source_tf", "objective_variant", "doz_activation_session", "objective_activation_session", "entry_session",
    ]
    for e in events.to_dict("records"):
        ci, fi, ei = int(e["confluence_idx"]), int(e["confirm_idx"]), int(e["entry_idx"])
        if not (0 <= ci <= fi < ei < len(bars)):
            raise RuntimeError(f"bad frozen indices {e['event_id']}")
        ct, ft, et = map(pd.Timestamp, (e["confluence_time"], e["confirm_time"], e["entry_time"]))
        if pd.Timestamp(bars.index[ci]) != ct or pd.Timestamp(bars.index[fi]) != ft or pd.Timestamp(bars.index[ei]) != et:
            raise RuntimeError(f"frozen timestamp/index mismatch {e['event_id']}")
        src_bid, src_ask = float(bars["open_bid"].iloc[ei]), float(bars["open_ask"].iloc[ei])
        if not valid_opening_quote(src_bid, src_ask):
            raise RuntimeError(f"invalid source entry quote {e['event_id']}")
        if not np.isclose(src_bid, float(e["entry_open_bid"]), rtol=0, atol=1e-9):
            raise RuntimeError(f"entry bid mismatch {e['event_id']}")
        if not np.isclose(src_ask, float(e["entry_open_ask"]), rtol=0, atol=1e-9):
            raise RuntimeError(f"entry ask mismatch {e['event_id']}")
        sig = float(sigma.iloc[ci])
        if not np.isfinite(sig) or sig <= 0:
            raise RuntimeError(f"invalid confluence sigma {e['event_id']}")
        direction = str(e["direction"])
        if (str(e["anchor_side"]) == "SUPPORT" and direction != "LONG") or (str(e["anchor_side"]) == "RESISTANCE" and direction != "SHORT"):
            raise RuntimeError(f"side/direction mismatch {e['event_id']}")

        trading_date = str(trading_day_key(et, "America/New_York", 17))
        for scenario, sc in SCENARIOS.items():
            sp = float(sc["spread"])
            comm = float(sc["commission"])
            entry_price = float(bars["open"].iloc[ei] + sp / 2) if direction == "LONG" else float(bars["open"].iloc[ei] - sp / 2)
            buf = max(2.0 * sp, 0.10 * sig)
            stop = float(e["anchor_lower"] - buf) if direction == "LONG" else float(e["anchor_upper"] + buf)
            risk = entry_price - stop if direction == "LONG" else stop - entry_price
            if not np.isfinite(risk) or risk <= 0:
                raise RuntimeError(f"invalid risk {e['event_id']} {scenario}")
            for rr in TARGET_RS:
                target = entry_price + rr * risk if direction == "LONG" else entry_price - rr * risk
                sim = simulate_trade(bars, ei, et, direction, entry_price, stop, float(target), float(risk), sp, comm, 120)
                rows.append({
                    **{k: e[k] for k in carry},
                    "entry_trading_date": trading_date,
                    "scenario": scenario,
                    "scenario_role": sc["role"],
                    "spread_usd_per_oz": sp,
                    "commission_round_turn_usd": comm,
                    "target_r": float(rr),
                    "sigma60_at_confluence": sig,
                    "buffer_price": float(buf),
                    "entry_price": float(entry_price),
                    "stop_price": float(stop),
                    "risk_price": float(risk),
                    "target_price": float(target),
                    **sim,
                })

    ledger = pd.DataFrame(rows)
    expected_rows = len(events) * len(SCENARIOS) * len(TARGET_RS)
    if len(ledger) != expected_rows:
        raise RuntimeError(f"ledger rows {len(ledger)} != {expected_rows}")
    ledger_path = out / f"causal_core_outcome_v1_1_ledger_{year}.csv.gz"
    ledger.to_csv(ledger_path, index=False, compression={"method": "gzip", "mtime": 0})
    summary = {
        "version": "XAU_CORE_OUTCOME_V1_1_ANNUAL",
        "year": year,
        "events": int(len(events)),
        "ledger_rows": int(len(ledger)),
        "input_sha256": sha256_file(input_path),
        "annual_event_manifest_sha256": sha256_file(events_path),
        "protocol_sha256": sha256_file(protocol_path),
        "freeze_manifest_sha256": sha256_file(freeze_path),
        "ledger_sha256": sha256_file(ledger_path),
    }
    (out / f"causal_core_outcome_v1_1_summary_{year}.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
