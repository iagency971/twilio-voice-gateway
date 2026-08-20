# XAU CORE CAUSAL CONFLUENCE TIMEFRAME ALIGNMENT REPAIR PROTOCOL v1

Date frozen: 2026-08-19
Branch: `agent/xau-core-evidence-audit-v1`
Status: `FROZEN_BEFORE_TIMEFRAME_ALIGNED_SUPPORT_AND_PNL`
Authority: Pro decision `B — REPAIR_PREOUTCOME` after discovery that Dukascopy M1 timestamps are bar-start timestamps while `resample_ohlc` used `closed="right"`.

## 1. Purpose

Repair only the M15/M30/H1 displacement-origin resampling alignment, then rebuild the already-frozen causal DOZ + Objective Liquidity + irreversible CLEAN_REJECTION population on 2011–2025 without opening P&L.

The prior repaired preoutcome freeze is invalid for outcome opening:

- freeze manifest SHA-256: `5792ee3aba012c46ae0e44868b80fd5b0e3acd630a3595ae4d21056663143075`
- event manifest SHA-256: `e14180106c659262c7345f428db1dacb1c0aa9e92c770aefef8692d4c1038f28`

No post-hoc deletion of visibly affected events is permitted. The complete DOZ universe must be rebuilt.

## 2. Frozen M1 timestamp semantics

`m1_timestamp_semantics = BAR_START_UTC`.

For all HTF bars used by `DISPLACEMENT_ORIGIN`:

- `resample_closed = left`
- `resample_label = right`
- `doz_known_time_semantics = HTF_BAR_CLOSE_BOUNDARY`

Therefore:

- M15 label 13:15 uses source M1 starts 13:00..13:14;
- M30 label 13:30 uses source M1 starts 13:00..13:29;
- H1 label 14:00 uses source M1 starts 13:00..13:59.

A source M1 timestamp equal to the HTF label is forbidden from contributing to that HTF bar.

## 3. Frozen strategy construction

Everything except HTF alignment remains unchanged:

- source: already-used Dukascopy XAUUSD M1 replay, 2011–2025;
- DOZ timeframes: 15min / 30min / 1h;
- displacement quantile, efficiency threshold, recent-break logic and opposite-bar search unchanged;
- variants: DOZ_LAST / DOZ_BODY / DOZ_BASE unchanged;
- Objective Liquidity generation unchanged;
- causal direct DOZ–Objective pair overlap >= 0.50;
- contact-time gap <= 2 minutes;
- causal Memory/FVG exclusion unchanged;
- deterministic first-completion deduplication unchanged;
- irreversible causal CLEAN_REJECTION trigger unchanged;
- adverse same-M1 breach/reclaim ambiguity unchanged;
- entry eligibility = next active minute after confirmation, maximum wait 2 minutes;
- no session, direction, age, timeframe, variant, side-relation or RR filter.

## 4. Mandatory DOZ provenance gate

For every generated `DISPLACEMENT_ORIGIN` zone, before contacts or event selection:

1. identify the resampled breakout bar at `zone.known_time` for `zone.source_tf`;
2. retain the maximum source M1 start timestamp actually used by that breakout bar;
3. require strictly:

`source_last_m1_timestamp < zone.known_time`.

Missing provenance is a violation.

The gate applies to the entire generated DOZ universe, not only to eventual entry candidates.

## 5. Mandatory event timing gates

For every emitted entry candidate:

- `doz_known_time <= doz_contact_time <= confluence_time <= confirm_time < entry_time`;
- Objective Liquidity known/contact timing remains causal;
- anchor contact fixes confluence time;
- irreversible CLEAN_REJECTION prefix invariance must pass;
- no future bar may change event identity, direction, confirmation or entry.

## 6. Determinism and support gate

Before any P&L may be opened:

- zero DOZ provenance violations;
- zero timing-integrity violations;
- zero prefix-invariance violations;
- zero duplicate event IDs;
- deterministic raw-contact shuffle identity PASS;
- at least 200 entry candidates;
- at least 12 active years out of 15.

Failure status:

`CAUSAL_CORE_PREOUTCOME_TIMEFRAME_ALIGNMENT_SUPPORT_FAIL`

Pass status:

`CAUSAL_CORE_PREOUTCOME_TIMEFRAME_ALIGNED_READY_FOR_PNL`

## 7. Required freeze metadata

The aggregate freeze manifest must explicitly contain:

```json
{
  "m1_timestamp_semantics": "BAR_START_UTC",
  "resample_closed": "left",
  "resample_label": "right",
  "doz_known_time_semantics": "HTF_BAR_CLOSE_BOUNDARY",
  "pnl_inspected_or_used": false,
  "tp_sl_exit_simulated": false,
  "new_market_data_spend": 0,
  "mandatory_stop": "STOP_BEFORE_PNL"
}
```

It must hash the event manifest and all implementation dependencies, including the corrected `resample.py`.

## 8. Outcome prohibition

This protocol does not authorize TP, SL, target, exit, gross-R, net-R, PF, winrate, drawdown or any economic comparison.

No outcome run may use the invalidated 736-event freeze.

## 9. No-rescue rule

During this repair it is forbidden to change or select:

- session;
- LONG/SHORT;
- M30 only;
- zone age;
- DOZ_BODY only;
- Objective subtype;
- SAME_SIDE only;
- overlap threshold;
- 2-minute confluence window;
- CLEAN_REJECTION trigger;
- RR;
- costs;
- COMEX or M5.

New market-data spend: `0 €`.

## 10. Mandatory stop

After a successful timeframe-aligned preoutcome freeze, STOP before P&L and return the new hashes for Pro review.
