# XAUUSD Z4 — C5 post-replication engineering gate v0.1

**Date:** 2026-08-24  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Status:** FROZEN AFTER C5 HISTORICAL REPLICATION, BEFORE C5 PINE/PORT ENGINEERING RESULTS

## 1. Scientific state entering this gate

The cadence choice was frozen before cadence-specific Aug-2024→Jul-2026 outcomes were opened:

- C15 remains the previously validated incumbent;
- C5 was selected as the sole primary production-replacement candidate;
- C1 was retained only as a sensitivity result and is not a post-hoc rescue candidate.

The frozen C5 model was trained on Jan-Jul 2024 DEV only, before historical H1/H2 scoring, with the frozen Z4 feature sets and fitting procedure. No H1/H2 refit or calibration refit was performed.

The published C5 historical temporal replication v0.2 passed every preregistered gate:

### BID primary

| Period | ΔBrier | ΔLogLoss | weekly bootstrap 95% ΔBrier | Primary gate |
|---|---:|---:|---:|---|
| H1 2024-08-01→2025-08-01 | +0.0023430073914105787 | +0.007370430718726229 | [+0.0015754862438442855, +0.0031830432738671473] | PASS |
| H2 2025-08-01→2026-08-01 | +0.01240781104724148 | +0.04262644136104682 | [+0.010232867093936053, +0.01449247684879381] | PASS |

### ASK support

| Period | ΔBrier | ΔLogLoss | Support gate |
|---|---:|---:|---|
| H1 | +0.0020965279394521696 | +0.006800031115229255 | PASS |
| H2 | +0.012319540799001577 | +0.04272140184998929 | PASS |

Therefore `C5_HISTORICAL_REPLICATION_PASS = true`.

These are historical temporal replication periods for the new cadence hypothesis, not pristine new holdouts, because the periods were already known from the original C15 programme. The PASS establishes robust historical transfer of the frozen C5 cadence variant; it does not by itself authorize a Pine production label.

## 2. Production decision at this point

**C5 is promoted from research candidate to ENGINEERING CANDIDATE.**

It is not yet `VALIDATED_PROXY` and must not replace C15 in the TradingView implementation until all gates below pass.

No C15 R thresholds, C15 warm-up rule, or C15 Pine parity result may be silently inherited by C5.

## 3. C5 user-facing R map — DEV only

Build the C5 score map from the exact C5 Jan-Jul 2024 BID DEV table and the already frozen C5 BID M0GL parameters.

Rules:

- equal total weight per landmark, identical to the original Z4 score-map definition;
- 101 empirical percentile thresholds R0…R100;
- raw M0GL score only;
- no Validation/H1/H2/OOS outcome enters the map;
- `R` remains a rank/percentile, never a probability and never reaction strength.

Pass is provenance/implementation based: the output must be generated from the exact frozen C5 DEV model/data only, have 101 monotone thresholds, and carry hashes/provenance sufficient to reproduce it.

## 4. C5 lineage bootstrap/warm-up audit — outcome-blind

The C15 selected cap of 96 landmarks cannot be copied blindly because 96 C5 landmarks represent only one third of the elapsed landmark time of 96 C15 landmarks.

The C5 audit will evaluate the following cap set, frozen before reading the audit metrics:

`C ∈ {96, 192, 288, 384, 480, 576}` C5 landmarks.

At a nominal 5-minute cadence these correspond to 8 h, 16 h, 24 h, 32 h, 40 h and 48 h of landmark time. The set contains the old numerical cap as an explicit low-cost diagnostic and the full time-equivalent family of the original C15 `{96,128,160,192}` candidates scaled by ×3 (`{288,384,480,576}`).

Use exact C5 DEV BID and frozen C5 M0GL. Do not reference `revisited` or any future-price outcome in the audit.

For each cap, recompute only the lineage-carried state that would be available after a cold start:

- age_active / age_civil;
- historical maximum prominence;
- reinforcement streak;
- recent center/width histories as applicable.

Compare capped C5 frozen raw M0GL output to full-history C5 frozen raw M0GL output.

### Pass criteria

Keep the original outcome-blind Pine bootstrap criteria unchanged:

- global raw-score Spearman ≥ 0.995;
- global raw-score Pearson ≥ 0.995;
- median absolute raw-score error ≤ 0.005;
- p95 absolute raw-score error ≤ 0.030;
- fraction absolute error >0.05 ≤ 0.02;
- median within-landmark Spearman ≥ 0.995;
- top-1 agreement ≥ 0.95;
- mean top-3 Jaccard ≥ 0.95.

**Selection rule:** smallest candidate cap passing all criteria. No threshold relaxation after results.

## 5. C5 greedy-lineage portability gate — outcome-blind

At C5 cadence, rerun the already approved greedy-vs-exact lineage comparison using exact C5 DEV BID and frozen C5 parameters. The only mechanical cadence change is the eligible landmark rule 15→5 minutes.

Retain the original gate criteria; do not choose a new lineage matcher based on outcomes.

## 6. C5 detector/Pine-math proxy gate — outcome-blind

Rebuild exact C5 DEV geometry and the Pine-math proxy at C5 cadence using the already approved portability approximations only:

- scientific 0.01 USD remains the exact reference;
- Pine grid candidate remains 0.05 USD; 0.10 remains rejected;
- Gaussian → three box-blur approximation only;
- explicit Pine peak/prominence/P50 logic only;
- greedy lineage only if section 5 passes;
- no side-rule change;
- no threshold/model/feature change.

Compare exact C5 to C5 proxy using the original frozen geometry/score parity metrics and thresholds. No future outcome may enter this gate.

## 7. TradingView implementation requirements after Python-side engineering PASS

Only after sections 3–6 pass may a C5 Pine QA candidate be built.

That candidate must:

- use the C5-specific frozen scaler/coefficients/intercept;
- use the C5-specific 101-threshold R map;
- use the selected C5 lineage warm-up cap;
- snapshot on confirmed M1 bars at the 5-minute cadence;
- keep LOOKBACK = 1440 active M1;
- keep the original Z4 side rule and exclude P50 overlap from scored LIVE zones;
- rearm warm-up after state/grid invalidation;
- preserve fail-closed behavior;
- keep UI-only changes separated from science.

Before any `VALIDATED_PROXY` label is restored, require TradingView compilation, Replay QA, confirmed-bar/live-landmark QA, forced warm-up recovery QA, and a static audit of all frozen parameters and R thresholds.

## 8. Cross-feed caveat

C5 remains scientifically supported on Dukascopy BID with ASK support. A TradingView FOREXCOM:XAUUSD implementation remains a transfer hypothesis. This engineering gate does not upgrade FOREXCOM to a validated feed.

## 9. Execution scenarios

The existing execution-scenario prereg v0.1 is explicitly defined on confirmed **15-minute** Z4 landmarks. It must not be silently relabelled as a C5 execution study.

Decision order:

1. complete the C5 engineering/production gate;
2. decide whether C5 replaces C15 as the scientific-state cadence used in the indicator;
3. if C5 is promoted, freeze a cadence-adjusted execution prereg before evaluating E1–E6/CANCEL-vs-KEEP on C5.

This prevents mixing an execution study with a still-unfinished cadence promotion.

## 10. Forbidden actions

- no C1 post-hoc rescue;
- no new lookback optimization;
- no reaction/reversal promotion;
- no SL/TP/RR optimization;
- no C15 R reuse for C5;
- no outcome-based relaxation of parity thresholds;
- no direct Pine production promotion from the historical PASS alone.
