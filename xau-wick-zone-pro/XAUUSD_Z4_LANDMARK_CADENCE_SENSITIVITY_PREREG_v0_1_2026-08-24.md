# XAUUSD Z4 — Landmark Cadence Sensitivity Prereg v0.1

**Freeze date:** 2026-08-24  
**Status:** FROZEN BEFORE CADENCE-SENSITIVITY DEV OUTCOMES  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Incumbent validated architecture:** Z4 with 1,440 active-M1 memory and 15-minute UTC landmarks  
**Scope:** DEV sensitivity only; no Validation/OOS read and no TradingView production change.

## 1. Question

Does the frozen 15-minute landmark cadence unnecessarily delay or destabilize the user-facing Z4 state, and can a 5-minute or 1-minute cadence preserve the validated `REVISIT_240` predictive signal while updating the scientific zone/lineage state more frequently?

This is a one-factor architecture sensitivity study. It is not a trading-entry optimization and it does not modify the already re-confirmed 1,440-active-M1 memory.

## 2. Candidate cadences — frozen

UTC landmark cadences:

- **C1** = every active M1 whose UTC minute is divisible by 1;
- **C5** = every active M1 whose UTC minute is divisible by 5;
- **C15** = every active M1 whose UTC minute is divisible by 15 — validated incumbent control.

No other cadence may be added after DEV results are seen in this gate.

## 3. Exactly what changes

Only the frozen Z4 `landmark_ok(ts)` clock condition changes mechanically:

- C1: `p.minute % 1 == 0 and p.second == 0`;
- C5: `p.minute % 5 == 0 and p.second == 0`;
- C15: `p.minute % 15 == 0 and p.second == 0`.

Candidate engines must be mechanically generated from frozen Z4 reference engine git blob `a8a147615c3fd366c49e93b340fd2018b5b66e9e`. Any other source mutation invalidates a candidate.

Changing cadence intentionally changes the sequence on which Z4 lineage/stability features are updated. In particular, `reinforce_streak`, recent lineage changes and four-snapshot stability summaries acquire the cadence-specific meaning implied by the new sequence. This is part of the architecture being tested; these features are not manually rescaled after outcomes.

## 4. What remains frozen

Across C1/C5/C15:

- source: exact Dukascopy XAUUSD M1 mirror used by Z4;
- active-bar rule: `high > low`;
- historical memory: **1,440 active M1**;
- segmentation `vseg`: median TR over the same 1,440 active M1;
- `v60`: frozen 60-active-M1 median TR mechanic;
- grid: 0.01 USD, absolute origin 0.00;
- Gaussian scales 0.25 / 0.50 / 1.00 × `vseg`;
- coarse family / best medium peak / fine confirmation;
- prominence and P50 zone bounds;
- no Top N;
- side eligibility rule;
- one-to-one lineage matching and no-gap-bridge rule;
- exact active-bar age mechanic;
- endpoint: `REVISIT_240`;
- M0 and M0GL feature definitions;
- StandardScaler training only;
- LogisticRegression C=0.10, lbfgs, max_iter=500, tol=1e-6;
- equal total weight per landmark;
- chronological folds APR/MAY/JUN/JUL 2024;
- BID primary, ASK independent feed replication;
- no P&L, SL, TP, RR, peak-entry rule or R threshold.

## 5. Data boundary — frozen

DEV only, January through July 2024. Exact BID/ASK source hashes must match `results/XAUUSD_Z4_DEV_SOURCE_MANIFEST_v0_1.json`.

No Aug-2024+ Validation/OOS result may be used to select a cadence in this DEV gate.

## 6. Primary predictive evaluation on each cadence population

For each cadence and feed, fit/evaluate M0 and M0GL on that cadence's own causal snapshot sequence and report:

- APR/MAY/JUN/JUL fold ΔBrier and ΔLogLoss;
- pooled OOF M0/M0GL Brier and LogLoss;
- pooled ΔBrier and ΔLogLoss;
- weekly positive-week count;
- weekly bootstrap 95% interval of ΔBrier.

### `BID_ROBUST_PASS`
True only if all four BID fold ΔBrier values are > 0, pooled BID ΔBrier > 0, and BID weekly bootstrap lower 95% bound > 0.

### `DUAL_FEED_STRONG_PASS`
True only if `BID_ROBUST_PASS` is true and the same three conditions hold on ASK.

## 7. Common-15-minute-anchor diagnostic — frozen

Candidate populations differ in snapshot frequency, so their raw Brier levels are not directly comparable. A paired diagnostic is therefore fixed before outcomes:

For C1/C5/C15, predictions from the cadence-specific model are also scored only on rows whose UTC timestamp is a 15-minute anchor (`minute % 15 == 0`). At those common anchors, the underlying Z4 geometry should be identical because lookback and zone detection are unchanged; only cadence-dependent lineage state/model training may differ.

For each feed/cadence report:

- common-anchor rows and landmarks;
- common-anchor geometry SHA-256 over `(landmark_i, center, zlo, zhi, side)`;
- fold and pooled ΔBrier/ΔLogLoss on common anchors;
- weekly bootstrap 95% interval on common-anchor ΔBrier.

All three candidate geometry hashes must be identical within a feed. Any mismatch is an implementation failure.

### `COMMON15_BID_ROBUST_PASS`
True only if all four common-anchor BID fold ΔBrier values are > 0, pooled common-anchor BID ΔBrier > 0, and common-anchor BID weekly bootstrap lower 95% bound > 0.

### `COMMON15_DUAL_FEED_STRONG_PASS`
True only if the BID condition is true and the equivalent ASK condition is true.

## 8. Outcome-blind cadence/stability diagnostics

For each candidate/feed report:

- zone snapshots and represented landmarks;
- distinct lineages;
- zones per landmark;
- lineage length in snapshots;
- per-update continuation/drop rate (descriptive only; not directly comparable across different cadence intervals);
- lineage maximum age in active M1: median/p90/p95;
- lineage maximum civil age in minutes: median/p90/p95;
- common-15-anchor lineage continuation/drop rate using the cadence-specific lineage IDs;
- common-anchor distribution of `age_active_min`;
- median/p95 absolute center shift in vseg units and width log-change.

A shorter cadence may expose transient one-minute/five-minute disappearances that C15 never observes, causing stricter lineage fragmentation. This is a real architectural consequence, not a bug to hide.

## 9. DEV shortlist rule — frozen

A shorter cadence can enter the targeted Pro review shortlist only if all of the following are true:

1. `DUAL_FEED_STRONG_PASS`;
2. `COMMON15_DUAL_FEED_STRONG_PASS`;
3. common-anchor geometry hash parity passes on BID and ASK;
4. no implementation/provenance gate fails.

C15 is the incumbent control and remains production-authorized regardless of whether a shorter candidate passes DEV.

If neither C1 nor C5 enters the shortlist, retain C15 and do not spend historical Validation/OOS on failed cadence candidates.

If one or both shorter candidates enter the shortlist, do **not** select a winner from DEV alone. Run the planned targeted Pro methodological review before deciding what, if anything, deserves separately frozen historical replication.

## 10. Production protection

Until a later explicit decision:

- `LOOKBACK=1440` remains frozen;
- C15 remains the validated scientific cadence;
- current R semantics remain tied to the validated C15 architecture;
- no Pine `VALIDATED_PROXY` may use a 1m/5m scientific R;
- a descriptive fast-refresh overlay may be studied separately, but may not be mislabeled as validated Z4/R.
