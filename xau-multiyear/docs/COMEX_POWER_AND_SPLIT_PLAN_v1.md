# COMEX incremental-value power and split plan v1

Date: 2026-08-18
Status: frozen before any COMEX market-data download.

## Temporal splits

These splits are for COMEX-feature development only. They are not claimed to be virgin strategy OOS because XAUUSD outcomes from 2011-2025 have already been inspected.

- 2011-2018: DEV
- 2019-2022: VALIDATION
- 2023-2025: COMEX_FEATURE_HOLDOUT
- 2026+: FORWARD_AUDIT / later prospective validation

No feature threshold may be tuned on COMEX_FEATURE_HOLDOUT.

## FVG-only sampling

FVG-only is retained, not discarded. Every event receives a deterministic SHA-256 rank before COMEX is observed, stratified by year, XAU session, side, sigma quartile and FVG-width/sigma quartile.

Candidate tiers select rank <= 1, 2 or 4 within each stratum. Final tier will be chosen from power and exact cost, never from COMEX outcomes.

## Binary-outcome power reference

Two-sided alpha 0.05, equal groups, 80% power. Approximate observations required per group:

- baseline 70%, detect +2 percentage points: 8,080/group
- baseline 70%, detect +3 percentage points: 3,554/group
- baseline 70%, detect +5 percentage points: 1,251/group
- baseline 80%, detect +3 percentage points: 2,629/group
- baseline 80%, detect +5 percentage points: 906/group

At 90% power the corresponding 70% baseline values are approximately 10,816, 4,757 and 1,674 per group.

These are reference bounds for pre-specified binary splits, not a substitute for walk-forward predictive evaluation of continuous COMEX features.

## Session-panel tiers

Session candidates are ranked outcome-blind within year x quarter x XAU volatility tercile. Candidate tiers select 2, 3 or 4 sessions per stratum, which targets approximately 24, 36 or 48 full-session envelopes per complete year.

The final session tier will be selected from exact cost and the requirement to preserve meaningful numbers in DEV, VALIDATION and COMEX_FEATURE_HOLDOUT. Session-derived observations are clustered by session; raw POI counts must not be treated as independent sample size.

## Statistical decision rule

COMEX value must be evaluated incrementally:

1. price-only baseline;
2. + complete M1 GC context;
3. + local trades/TBBO feature group;
4. + complete-session profile feature group;
5. optional + MBP-1 feature group.

Retain a feature group only if improvement is directionally stable across DEV and VALIDATION and survives the locked COMEX_FEATURE_HOLDOUT without threshold retuning. Report calibration, effect size, frequency, net-R impact and cluster/bootstrap uncertainty; do not promote on p-value alone.

A later prospective block remains mandatory for any deployable strategy.
