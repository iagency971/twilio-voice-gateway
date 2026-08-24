# XAUUSD Z4 — Execution Scenarios Prereg v0.1

**Date:** 2026-08-24  
**Status:** FROZEN BEFORE EXECUTION-SCENARIO RESULTS  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Scientific base:** frozen Z4 M1 `P_REVISIT_240` only.  
**No optimization / no outcome-based threshold selection.**

## 1. Scientific status carried forward

Only one predictive statement is currently validated:

> A frozen Z4 LIVE M1 zone on Dukascopy contains reproducible incremental information for revisit within the next 240 active M1, relative to frozen causal baseline M0.

Not validated:
- reaction/rejection/reversal;
- profitable entry;
- peak as entry;
- stop/target;
- persistence after disappearance;
- FOREXCOM transfer;
- higher TF;
- BODY variants.

`R` is a DEV percentile rank of revisit likelihood, not a probability and not reaction strength.

## 2. Why this prereg exists

The validated Z4 signal ends at the question `will the zone be revisited?`. For discretionary trading, the missing question is execution after a LIVE zone exists and price approaches/enters it.

This document freezes a small set of execution scenarios before reading their execution outcomes. It does not modify Z4 geometry, lineage, side, model, score, or R mapping.

## 3. Common definitions

For a LIVE Z4 zone at confirmed 15-minute landmark t:

- BUY-side zone: `side=-1`, entirely below current close.
- SELL-side zone: `side=+1`, entirely above current close.
- `near_edge`: boundary first reached from current-price side:
  - BUY: `zhi`
  - SELL: `zlo`
- `far_edge`: opposite boundary:
  - BUY: `zlo`
  - SELL: `zhi`
- `peak`: Z4 medium peak center.
- `mid`: geometric midpoint `(zlo+zhi)/2`.
- `LIVE`: zone is present and eligible in current frozen Z4 snapshot.
- `DROP`: lineage present at previous eligible landmark has no eligible match at current landmark.
- `RETURN`: a later LIVE zone appears close enough to the last dropped geometry under a separately frozen causal matcher. RETURN is not automatically the same scientific lineage.

All execution levels are frozen at the latest confirmed LIVE snapshot before fill. No future geometry is used to move a pending order.

## 4. Core execution scenarios

### E0 — REVISIT_ONLY control

No trade. Observe whether `[zlo,zhi]` is revisited within H240.

Purpose: preserve the validated scientific reference.

### E1 — NEAR_EDGE_TOUCH

Pending entry at `near_edge` from the LIVE snapshot.

This is equivalent to entering on first contact with the zone.

Status before test: experimental execution rule.

### E2 — PEAK_LIMIT

Pending entry at frozen `peak`.

Status before test: experimental. The cyan peak is a density maximum, not a validated entry level.

### E3 — MID_LIMIT

Pending entry at frozen geometric midpoint `mid=(zlo+zhi)/2`.

Status before test: experimental.

### E4 — FAR_EDGE_LIMIT

Pending entry at frozen `far_edge`.

Status before test: experimental.

## 5. Pending-order cancellation policy — primary practical question

For E2/E3/E4, compare two preregistered policies.

### C1 — CANCEL_ON_DROP

If the pending order is not filled and the zone becomes non-LIVE at a confirmed 15-minute snapshot, cancel immediately at that snapshot.

### C2 — KEEP_AFTER_DROP

If the pending order is not filled and the zone becomes non-LIVE, keep the original frozen order until the original H240 horizon expires.

C2 is a comparator, not a recommendation.

The primary cancellation question is:

> For unfilled peak/mid/far-edge orders, does C1 improve execution-path quality relative to C2, or does it discard useful fills?

No discretionary grace period is allowed in v0.1.

## 6. Post-contact confirmation scenarios — secondary branch

These are intentionally secondary because the earlier reaction branch was NO-GO.

### E5 — PEAK_RECLAIM

After first zone contact/penetration, require a causal close back across the frozen peak in the direction away from the zone before considering an execution signal.

### E6 — FAR_SWEEP_FULL_RECLAIM_RETEST

Require:
1. penetration beyond frozen far edge;
2. full reclaim of the frozen zone;
3. later retest of the frozen zone or peak.

No threshold tuning is allowed. These are descriptive/secondary until evidence is stable.

## 7. DROP / RETURN / MEMORY branch

### M0 — DROP_ONLY

Track dropped zones without treating them as valid trade zones.

### M1 — RETURN_AS_NEW

If a dropped area later produces a new eligible Z4 zone, treat it as a new LIVE signal with its new geometry and new R.

### M2 — MEMORY_ORDER

Keep the last frozen geometry after DROP and permit a later fill from that old geometry.

M2 is exactly the behavior represented by C2 for pending orders and is experimental. It must not inherit the old R as a current validated score.

No visual or execution rule `valid until broken` is authorized.

## 8. Primary outcome family for execution screening

No P&L optimization in the first gate.

For every filled execution scenario, compute direction-normalized path after fill at 5/15/30/60 active M1:

- favorable excursion in units of contemporaneous v60;
- adverse excursion in units of v60;
- signed directional response `(fav-adv)/(fav+adv+eps)`;
- probability `fav > adv`;
- time-to-fill from original LIVE landmark;
- fill rate within H240;
- whether fill occurred while zone was LIVE or after DROP;
- zone R at order creation;
- BUY/SELL and US diagnostics.

For E2/E3/E4 also report:
- proportion canceled by C1 before fill;
- among those canceled, how many would later fill under C2;
- post-fill path quality of C1 fills vs C2-only fills.

No RR, SL, TP, PF, win rate, expectancy, or money sizing may be optimized in this gate.

## 9. Chronology and evidence status

Because these execution hypotheses are being formalized on 2026-08-24 after prior Z4 research:

- Jan–Jul 2024 may be used as execution DEV/screening.
- Aug 2024–Jul 2026 may be used only as historical temporal replication; it is not a pristine new holdout for this newly formulated execution claim.
- A truly independent confirmation must use future data reserved after preregistration. Proposed start: 2026-09-01 UTC.

No future prospective data may be read before the execution rule set and pass criteria for that prospective gate are separately frozen.

## 10. What is "retained today"

### Scientifically retained
- Z4 LIVE zone.
- `P_REVISIT_240` signal.
- R as revisit rank only.

### Execution candidates retained for screening
- E1 NEAR_EDGE_TOUCH.
- E2 PEAK_LIMIT.
- E3 MID_LIMIT.
- E4 FAR_EDGE_LIMIT.
- C1 CANCEL_ON_DROP.
- C2 KEEP_AFTER_DROP comparator.

### Secondary only
- E5 PEAK_RECLAIM.
- E6 FAR_SWEEP_FULL_RECLAIM_RETEST.
- RETURN / MEMORY diagnostics.

### Explicitly not retained as validated rules
- peak = validated entry;
- zone remains valid until broken;
- old R remains valid after DROP;
- reaction/reversal claim;
- any stop/target or RR rule;
- any R threshold selected for trading.

## 11. Next gate

Run an outcome-blind implementation QA first to verify execution levels and DROP timing from frozen Z4 outputs. Then evaluate DEV Jan–Jul 2024 across the exact scenarios above. Report all scenarios; no winner may be selected by silently dropping poor variants.
