# XAUUSD Z4 C5 → Pine R display-label parity — prereg v0.1

**Date:** 2026-08-24  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Status:** FROZEN BEFORE C5 R-LABEL PARITY RESULTS  
**Future outcomes used:** NONE

## 1. Purpose

C5 passed the preregistered historical temporal-replication gate and is being evaluated as an engineering candidate. The user-visible value is `R 0–100`, not the raw frozen C5 M0GL logistic output.

The C15 R map and C15 R-label parity result may not be inherited. C5 requires its own DEV-only equal-landmark-weighted percentile map and a separate display parity audit on the final authorized C5 Pine proxy.

`R` remains a percentile/rank of revisit likelihood versus the C5 DEV reference. It is not a probability, not reaction strength, and not support/resistance strength.

## 2. Reference and candidate

Use **Dukascopy BID Jan-Jul 2024 DEV only**.

- reference: exact C5 Z4 geometry/lineage using scientific 0.01 grid, SciPy Gaussian, exact one-to-one lineage and full-history frozen C5 M0GL;
- candidate: final C5 engineering proxy authorized by the C5 post-replication gate, i.e. 0.05 grid + 3-box smoothing + explicit Pine peak/prominence/P50 + greedy lineage + the C5 warm-up cap selected outcome-blind in the C5 warm-up gate;
- model: frozen C5 BID M0GL trained on Jan-Jul 2024 DEV only before historical replication;
- percentile map: C5-specific 101-threshold DEV-only score map generated from the exact C5 BID DEV table with equal total weight per landmark;
- mapping: same frozen piecewise-linear interpolation between adjacent R thresholds as the original Z4 display specification.

No future/contact/reaction/P&L field may enter this audit.

## 3. Metrics

On geometry-matched exact/proxy zones, compute:

- absolute difference in continuous `R_float`;
- absolute difference in displayed rounded integer R;
- share within ±1 / ±2 / ±5 displayed R points;
- continuous-R Pearson and Spearman;
- matched top-1 agreement by landmark.

## 4. PASS gate

Keep the original C15 R-display gate thresholds unchanged. ALL must pass:

- median absolute continuous-R error ≤ **1.0** point;
- p95 absolute continuous-R error ≤ **5.0** points;
- at least **80%** of displayed integer R values within ±2 points;
- at least **95%** within ±5 points;
- continuous-R Spearman ≥ **0.98**;
- matched top-1 agreement ≥ **0.85**.

No threshold may be relaxed after reading the result.

## 5. Decision rule

- PASS: C5 Pine QA candidate may display the C5-specific R map, subject to all other C5 engineering gates and TradingView runtime QA.
- FAIL: C5 must not display numeric R under the current proxy. A new outcome-blind display representation would need a separate preregistration.

A PASS does not by itself authorize `VALIDATED_PROXY`, FOREXCOM transfer, reaction/reversal claims, or any execution/SL/TP/RR rule.
