# XAUUSD Z4 → Pine R display-label parity — prereg v0.1

**Date:** 2026-08-23  
**Status:** FROZEN BEFORE R-LABEL METRICS  
**Future outcomes used:** NONE.

## Purpose

The combined Pine proxy has passed the frozen raw M0GL score parity gate. The user-visible value is not the raw logistic output but `R 0–100`, obtained from the frozen DEV equal-landmark-weighted percentile map. This final display audit quantifies how much the engineering proxy can move the displayed R rank.

## Reference and candidate

- reference: exact frozen Z4 0.01/SciPy/Hungarian/full-history M0GL raw output;
- candidate: final authorized Pine proxy (0.05 grid + box3 + explicit peak/P50 + greedy lineage + 96-landmark cold-start state);
- percentile map: frozen `XAUUSD_Z4_REVISIT_SCORE_MAP_v0_1.json`;
- mapping: the already frozen piecewise-linear interpolation in `XAUUSD_Z4_REVISIT_SCORE_DISPLAY_MAP_v0_1.md`.

DEV BID January–July 2024 only. No future/contact/reaction field may enter this audit.

## Metrics

On geometry-matched zones:

- absolute difference in continuous `R_float`;
- absolute difference in displayed rounded integer R;
- share within ±1 / ±2 / ±5 displayed R points;
- continuous-R Pearson/Spearman;
- within-landmark rank correlation (identical monotone ordering to raw unless ties are introduced);
- matched top-1 zone agreement.

## PASS gate frozen before results

All must hold:

- median absolute continuous-R error ≤ **1.0** point;
- p95 absolute continuous-R error ≤ **5.0** points;
- at least **80%** of displayed integer R values within ±2 points;
- at least **95%** within ±5 points;
- continuous-R Spearman ≥ **0.98**;
- matched top-1 agreement ≥ **0.85**.

Failure means the Pine display may use raw/ordinal classes only until a new outcome-blind display mapping is preregistered; thresholds will not be relaxed after the result.
