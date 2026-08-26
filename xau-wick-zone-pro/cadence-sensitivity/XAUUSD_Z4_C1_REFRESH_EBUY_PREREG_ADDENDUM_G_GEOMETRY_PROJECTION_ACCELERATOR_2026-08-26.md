# XAUUSD Z4 / E-BUY — C1 refresh preregistration Addendum G: geometry-projection accelerator

**Frozen:** 2026-08-26, before any valid H1/H2 C1 reaction outcome is opened or interpreted.  
**Scope:** computational acceleration only; no scientific detector, E-BUY, contact, target, invalidation, scoring, or decision-rule change.

## Why this addendum exists

The frozen research detector `xau_zone_episode_dev_z4.py` calculates future reaction labels and lineage/features after the causal Z4 geometry has already been determined. The C1 cadence study consumes only the outcome-blind geometry columns `time`, `side`, `center`, `zlo`, `zhi`. On high-price 2026 months, the unused downstream work is materially expensive.

## Authorized projection

A fast C1 geometry projection may be generated from the same frozen source blob `a8a147615c3fd366c49e93b340fd2018b5b66e9e` only by all of the following mechanical edits:

1. cadence literal `p.minute%15==0` -> `p.minute%1==0`;
2. preserve the original lookback and original future-file guard exactly, including `LOOKBACK=1440`, `HORIZON=240`, `REACT_MAX=60`, and `i+HORIZON+REACT_MAX>=N`;
3. replace only `out=outcome_zone(...)` by `out={}` after the same geometry has already been computed;
4. immediately after the base geometry DataFrame is complete, write only `time/side/center/zlo/zhi` and return before lineage construction;
5. no change to grid origin, step, density accumulation, smoothing, peaks, prominences, widths, boundaries, side classification, cadence timestamps, or source data.

This projection is outcome-blind and is not a new detector candidate.

## Mandatory full-detector parity gate

The projection is admissible for the missing 2026 C1 monthly shards only if it reproduces the already-completed **full frozen C1 detector** on both:

- `2025-10` (completed full-detector reference), and
- `2026-04` (completed high-price/full-grid reference),

using the same exact monthly partition context (`previous + target + next`).

For each parity month, require:

- same target-month timestamp set;
- same zone count at every timestamp;
- same side for every sorted zone;
- center max absolute error <= `1e-12 USD`;
- zlo/zhi max absolute error <= `1e-8 USD`.

Any parity failure invalidates the accelerator and the full detector/fallback remains required.

## Missing months

Only after both parity months pass may the projected outputs for `2026-01`, `2026-02`, and `2026-03` substitute for missing full-detector monthly artifacts. If a full-detector artifact is available, prefer it; a projected artifact is only a timeout/performance substitute.

## Provenance and interpretation

The final evidence bundle must identify which months, if any, came from this projection and record the parity results. The final C1-vs-C5 geometry invariant, frozen C5 baseline provenance, common-session support, dual-C5 controls, H1/H2 coherence rule, and no-auto-promotion rule remain mandatory and unchanged.

**Authorization:** computation-only fallback. No reaction result, Pine change, or production promotion is authorized by this addendum.