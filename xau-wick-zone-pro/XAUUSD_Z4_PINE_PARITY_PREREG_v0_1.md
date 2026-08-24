# XAUUSD Z4 → Pine implementation parity — prereg v0.1

**Date:** 2026-08-23  
**Status:** FROZEN BEFORE PARITY METRICS  
**Purpose:** engineering parity only; no future outcomes are used to pass/fail this gate.

## Scope

The validated scientific candidate is Z4 M1 `P_REVISIT_240`. The existing Pine v1.3.4 is not equivalent to Z4 and therefore may not display the validated score yet.

This gate tests whether a Pine-feasible replacement for SciPy's exact Gaussian smoothing — three causal/static box passes with matched variance — preserves the frozen Z4 zone geometry and frozen-model score closely enough to justify a Pine port.

The comparison is performed on DEV BID January–July 2024 only. Reaction/revisit labels are not inspected or used by the parity comparator.

## Exact reference

Reference engine: `xau-wick-zone-pro/xau_zone_episode_dev_z4.py`, Git blob `a8a147615c3fd366c49e93b340fd2018b5b66e9e`.

Reference Z4 uses:
- 1,440 active M1;
- price step 0.01 USD, origin 0.00;
- `vseg` = median TR over the same 1,440 active M1;
- SciPy exact Gaussian 0.25× / 0.50× / 1.00× vseg;
- frozen family/peak/prominence/P50 logic;
- frozen lineage/stability logic.

## Pine-feasible proxy

Only the smoothing primitive is replaced. Every other Z4 operation remains identical in the Python proxy.

For requested Gaussian sigma `σ` in price bins, choose integer radius

`r = round((sqrt(1 + 4 σ²) - 1) / 2)`

and apply three centered box averages of radius `r`, truncating the window at profile edges and dividing by the number of available bins. This matches the variance construction used by the current Pine `f_gaussian3` implementation.

The proxy **does not** use the current Pine TR60 convention. It keeps Z4 `vseg=TRmed1440`, because the goal is to port the validated Z4 model rather than validate the current descriptive Pine.

## Matching

Reference and proxy zones are matched at the same 15-minute landmark and same BUY/SELL side using one-to-one Hungarian assignment. Candidate pairs require either interval overlap or center distance ≤ 1×vseg. Cost is frozen as:

`center_distance/vseg + 0.5*(1-IoU) + 0.1*abs(log(width_proxy/width_exact))`.

## Outcome-blind metrics

1. exact-zone match rate;
2. proxy-zone match rate;
3. zone-count agreement by landmark;
4. center error / vseg;
5. interval IoU;
6. lower/upper boundary error / vseg;
7. frozen M0GL raw-score Pearson and Spearman correlation on matched zones;
8. median and p95 absolute raw-score error;
9. within-landmark rank correlation where at least 3 pairs exist;
10. same top-1 M0GL zone at a landmark, after zone matching.

No `revisited`, MFE/MAE, reaction, P&L or future-contact field may enter these metrics.

## PASS gate frozen before results

Engineering parity is PASS only if all conditions hold:

- exact-zone match rate ≥ **0.90**;
- proxy-zone match rate ≥ **0.90**;
- median IoU ≥ **0.75**;
- 10th-percentile IoU ≥ **0.45**;
- median absolute center error ≤ **0.10 vseg**;
- 95th-percentile absolute center error ≤ **0.35 vseg**;
- frozen M0GL raw-score Spearman ≥ **0.95**;
- median absolute raw-score error ≤ **0.03**;
- 95th-percentile absolute raw-score error ≤ **0.10**;
- matched top-1 zone agreement ≥ **0.85** for eligible landmarks.

If this gate fails, the validated score may not be copied into Pine using the 3-box smoothing proxy. A closer implementation must be designed outcome-blind and subjected to a new parity prereg before another comparison.

Even a parity PASS does not validate higher timeframes. It authorizes only an M1 Z4 Pine port, with score updates on the frozen 15-minute landmark cadence.
