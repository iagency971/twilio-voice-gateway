# CHECKPOINT — XAUUSD / COMEX DEV_RANK1 primary results

Date: 2026-08-18
Branch: `agent/xau-comex-acquisition-plan`

## Acquisition / data state

- DEV_RANK1 architecture: `DUAL_V0_N0_CAUSAL_ACTIVE`.
- 96 analytical sessions, 2011–2018.
- 31,710 canonical XAU events.
- 92 sessions have usable raw GC tape under current acquisition.
- Missing tape dates retained, not replaced: 2011-12-26, 2012-11-22, 2014-01-20, 2015-02-05.
- 2015-02-05 failed after one paid range request; no retry authorized.
- No DEV_RANK2 / CONFIRM / LOCKED_TEST COMEX data opened.
- No additional Databento purchase authorized after DEV_RANK1.

## Frozen primary target 1 — binary XAU reaction

Sample for B0/B1/B2: 30,525 B2-causally-available events / 92 sessions.

### B1 GC M1 context vs B0 XAU
- family-balanced log-loss delta: -0.0011996
- population: -0.0068613
- session-balanced: -0.0064331
- positive years: 4/8
- cluster bootstrap spans zero
- gate: FAIL

### B2 GC raw trades/auction vs B1
- family-balanced: -0.0112243
- population: -0.0208993
- session-balanced: -0.0199132
- positive years: 2/8
- cluster bootstrap 95% entirely negative: [-0.0208229, -0.0037311]
- gate: FAIL

Decision: B1/B2 cannot be promoted for the primary reaction target.

## Frozen primary target 2 — multiclass behavior

Target: CLEAN_REJECTION / FAILED_AUCTION / ACCEPTED_BREAK / UNRESOLVED.
Exact nested LOYO recovered as 24 independent folds after the monolithic GitHub job timed out. All 24 folds completed successfully with the same scientific specification.

### B1 vs B0
- family-balanced: -0.0889565
- population: -0.0160607
- session-balanced: -0.0153930
- positive years: 1/8
- cluster bootstrap 95% entirely negative: [-0.1850983, -0.0147140]
- gate: FAIL

### B2 vs B1
- family-balanced: -0.0414928
- population: -0.0387640
- session-balanced: -0.0374185
- positive years: 2/8
- cluster bootstrap 95% entirely negative: [-0.0702124, -0.0112806]
- gate: FAIL

B2 vs B1 is adverse under both population and session weighting for CONFLUENCE, DOZ_ONLY, FVG_ONLY, MEMORY_ONLY and OBJECTIVE_ONLY.

Decision: B1/B2 cannot be promoted for the primary multiclass behavior target.

## Interpretation boundary

These two failures are real DEV_RANK1 results and may not be rescued by:
- pruning features after seeing outcomes;
- dropping years;
- changing C grid/solver/model class;
- isolating a rare favorable family as the new primary question;
- redefining reaction or behavior labels.

They do NOT yet answer the complete COMEX research question.

## Open preregistered axes

1. Entry eligibility/fill at each model-specific causal decision time.
2. Net-R conditional on entry/fill under frozen XAU execution/cost rules.
3. COMEX-native source zones and future exact-tape retests.

Secondary binary REJECT-vs-ACCEPT diagnostic is interpretive only and cannot override the primary multiclass failure.

## Native-zone source state

- 92 usable source sessions.
- 4 primary terminal levels per source: VWAP, POC, VAH, VAL.
- 368 source levels before future-retail acquisition.
- Source levels use no XAU outcomes.
- Future primary contact requires an exact GC trade at the frozen 0.10 tick in the next session on the same raw instrument.
- No M1-crossing substitute and no cross-contract level carry.

## Current work

Model-specific decision-time feature tables are being built separately for:
- PASSIVE_TOUCH
- TOUCH_NEXT_OPEN
- CLEAN_REJECTION
- FAILED_AUCTION
- ACCEPTANCE_RETEST
- RECLAIM_PULLBACK

Fill modeling specification was frozen before reading model-specific rates. Net-R/RR handling remains a later separate freeze decision.
