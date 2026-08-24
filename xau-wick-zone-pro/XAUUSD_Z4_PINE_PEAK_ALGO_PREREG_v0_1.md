# XAUUSD Z4 → Pine peak/prominence/P50 algorithm — prereg v0.1

**Date:** 2026-08-23  
**Status:** FROZEN BEFORE METRICS  
**Future outcomes used:** NONE.

## Purpose

SciPy provides `find_peaks`, `peak_prominences` and `peak_widths`; Pine does not. Before writing the validated-score Pine, freeze and test explicit Pine-feasible equivalents.

The grid step used in this gate is the deterministic result of the already-frozen grid-step compression gate; if no coarser step passes, use 0.01. The smoothing primitive is the already passed 3-box proxy.

## Pine-feasible peak semantics frozen now

### Local peaks/minima

A peak index `i` satisfies:

`x[i] > x[i-1] && x[i] >= x[i+1]`.

Local minima are peaks of `-x` using the same rule.

### Prominence

For medium peak `m` with height `h`:

- scan left until the first sample strictly greater than `h`, or profile edge;
- left base = minimum sample between that stop and `m`;
- scan right analogously;
- right base = minimum sample;
- background = max(left_min, right_min);
- prominence = `h - background`.

Equal-height samples do not stop the scan.

### P50 boundaries

Target height = `h - 0.5 * prominence`.

Walk left/right from the peak to the first sample at or below target within the prominence bases, then use linear interpolation between the bracketing samples. This returns fractional grid positions, matching the intended Pine formula rather than integer-bin borders.

All coarse-family, best-medium-peak and fine-confirmation rules remain frozen Z4 semantics.

## Outcome-blind comparison

Compare this Pine-feasible peak engine with the selected 3-box/grid-step proxy that still uses SciPy peak/prominence/width routines. Same DEV BID Jan–Jul 2024, same one-to-one zone matcher and frozen M0GL score.

## PASS gate frozen before results

All must hold:

- reference-zone match rate ≥ **0.97**;
- Pine-zone match rate ≥ **0.97**;
- median IoU ≥ **0.98**;
- p10 IoU ≥ **0.90**;
- p95 center error ≤ **0.10 vseg**;
- raw-score Pearson ≥ **0.995**;
- raw-score Spearman ≥ **0.995**;
- median raw-score absolute error ≤ **0.005**;
- p95 raw-score absolute error ≤ **0.030**;
- top-1 zone agreement ≥ **0.95**.

Failure means the formulas must not be used in the validated Pine port without a newly preregistered outcome-blind repair.
