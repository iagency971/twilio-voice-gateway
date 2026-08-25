# XAUUSD Z4 — Targeted Pro Cadence Gate Framework v0.1

**Freeze date:** 2026-08-24  
**Status:** FROZEN BEFORE ANY CADENCE-SPECIFIC AUG-2024→JUL-2026 HISTORICAL REPLICATION  
**Branch:** `agent/xau-wick-zone-pro-dev`

## Scope

This is the targeted methodological gate planned after the preregistered DEV cadence sensitivity study. DEV outcomes for C1/C5/C15 are already known, therefore this memo is **not outcome-blind to DEV**. It is frozen before opening any cadence-specific Aug-2024+ historical replication outcome.

The validated production incumbent remains **C15 / LOOKBACK 1440 / REVISIT_240** until a later explicit promotion gate.

## Evidence available at freeze

All three cadences passed the preregistered DEV predictive robustness checks on their own populations and on common 15-minute anchors:

- C1 BID pooled ΔBrier ≈ +0.001623; ASK ≈ +0.001889;
- C5 BID pooled ΔBrier ≈ +0.001603; ASK ≈ +0.001739;
- C15 BID pooled ΔBrier ≈ +0.001473; ASK ≈ +0.001743.

All four BID chronological folds were positive for C1, C5 and C15, and the weekly bootstrap lower 95% bound was >0 for all three.

C5 same-run common-anchor geometry parity against C15 has already passed exactly within the predeclared tolerances. C1 same-run geometry QA is running under the same preregistered invariant and must pass before C1 can be considered provenance-clean.

## Why DEV does not select C1 merely because its pooled score is numerically highest

The DEV differences between C1 and C5 are small and mixed across feed/common-anchor views. Selecting the largest pooled ΔBrier after looking at three candidates would create a winner's-curse risk.

Cadence also changes lineage/stability semantics. This is not a free refresh-rate parameter.

Observed outcome-blind DEV stability diagnostics show materially stronger lineage fragmentation as cadence gets shorter:

- C15 common-15 one-step drop ≈ 6.05%; median lineage maximum active age ≈ 30 M1;
- C5 common-15 drop ≈ 8.06%; median lineage maximum active age ≈ 20 M1 on common anchors / 10 M1 on native C5 updates;
- C1 common-15 drop ≈ 9.78%; native median lineage maximum active age ≈ 2 M1.

The faster cadence also changes the time meaning of four-snapshot stability and reinforcement features. C1 therefore represents a much more radical architecture change than C5 even though the detector geometry at identical timestamps is invariant.

Engineering cost is also materially different: on the same Jan-Jul 2024 engine family, C5 reconstruction runtime is roughly ~2x C15 while C1 is roughly ~14x C15. Pine feasibility must be treated as a real production constraint, not ignored after predictive screening.

## Targeted Pro methodological decision rule

### C5

**C5 is the primary cadence candidate authorized for historical temporal replication.**

Rationale:

1. It cuts scientific-state staleness from up to 15 minutes to up to 5 minutes.
2. It passed every preregistered DEV predictive gate on BID and ASK.
3. Its common-anchor geometry is provenance-clean versus C15.
4. Its lineage fragmentation is meaningfully less severe than C1.
5. Its computational burden is substantially lower than C1.
6. There is no sufficiently strong DEV evidence that C1's extra 4-minute refresh advantage compensates for the extra fragmentation/compute.

### C1

C1 remains a **scientifically interesting sensitivity result**, but it is **not selected as the primary production-replacement candidate from this DEV gate**.

If its same-run geometry QA fails, it is excluded outright. If it passes, that confirms the detector invariant but does not override the Pro decision above.

C1 must not be used as a post-hoc rescue candidate if C5 later fails historical replication. A separate preregistered C1 research branch would be required.

### C15

C15 remains the validated incumbent and production reference throughout the C5 replication.

## C5 model freeze before historical replication

Before any C5 Aug-2024+ result is scored:

1. mechanically generate the C5 engine from frozen Z4 reference blob `a8a147615c3fd366c49e93b340fd2018b5b66e9e` by changing only `landmark_ok` 15→5;
2. rebuild exact Jan-Jul 2024 DEV BID and ASK using the original source hashes;
3. fit full-DEV C5 M0 and M0GL with the already frozen feature sets, StandardScaler, LogisticRegression C=0.10/lbfgs/max_iter=500/tol=1e-6 and equal total weight per landmark;
4. serialize scaler means/scales, intercepts and coefficients;
5. hash and freeze those parameters before downloading/scoring any cadence-specific Aug-2024+ outcome.

No feature change, calibration tuning, R threshold, SL/TP/RR or reaction endpoint may enter this gate.

## Historical temporal replication periods

These periods are already known from the original C15 project and therefore are **not pristine new holdouts for the new cadence hypothesis**. They are historical temporal replication only.

- H1: 2024-08-01 UTC → 2025-08-01 UTC (former independent Validation period)
- H2: 2025-08-01 UTC → 2026-08-01 UTC (former frozen OOS period)

The C5 model is frozen from Jan-Jul 2024 and is never refit/recalibrated on H1 or H2.

## Frozen C5 replication metrics and pass rule

For H1 and H2 separately, report on BID and ASK:

- rows and landmarks;
- raw revisit rate;
- M0 Brier / M0GL Brier / ΔBrier;
- M0 LogLoss / M0GL LogLoss / ΔLogLoss;
- weekly ΔBrier count and positive-week count;
- weekly block/bootstrap 95% interval for mean ΔBrier;
- BUY/SELL and US/non-US diagnostics (non-gating).

### Period primary BID pass

For each of H1 and H2:

1. ΔBrier > 0;
2. ΔLogLoss > 0;
3. weekly bootstrap lower 95% bound for ΔBrier > 0.

### Cross-feed support

For each of H1 and H2, ASK must have:

1. ΔBrier > 0;
2. ΔLogLoss > 0.

ASK bootstrap is reported but is not required for the primary pass.

### `C5_HISTORICAL_REPLICATION_PASS`

True only if:

- H1 primary BID pass;
- H2 primary BID pass;
- ASK has positive ΔBrier and ΔLogLoss in both periods;
- no provenance/data/code-freeze gate fails.

If this fails: **retain C15**. Do not tune C5 and do not switch post hoc to C1.

If this passes: C5 becomes eligible for a final engineering/production gate, not automatically `VALIDATED_PROXY`.

## Required post-replication engineering gate before Pine promotion

Even after a C5 historical replication PASS, production requires:

- candidate-specific C5 R score map from DEV only;
- R semantics remain percentile/rank, never probability;
- Pine C5 math/proxy parity;
- Pine lineage parity at C5 cadence;
- runtime/Replay QA;
- confirmed-bar behavior;
- 96-landmark warm-up reconsidered in **time units** because 96 C5 landmarks represent a different elapsed horizon than 96 C15 landmarks; the old C15 warm-up label cannot be copied blindly;
- cross-feed TradingView caveat remains.

No current C15 R may be reused as a C5 validated score.
