# XAUUSD Z4 → Pine combined implementation parity — prereg v0.1

**Date:** 2026-08-23  
**Status:** FROZEN BEFORE COMBINED METRICS  
**Future outcomes used:** NONE.

## Candidate

Combine only engineering substitutions that already passed their own outcome-blind gates:

- absolute grid step **0.05 USD**;
- 3-box Gaussian approximation;
- explicit Pine local-peak / prominence / interpolated P50 formulas;
- deterministic greedy one-to-one lineage assignment;
- lineage state cold-start cap **96 eligible 15-minute landmarks**.

All scientific definitions, 1,440 active-M1 memory, v60/vseg, feature formulas, frozen M0GL scaler/coefficients and 15-minute cadence remain unchanged.

## Reference

Exact frozen Python Z4: 0.01 grid, SciPy Gaussian/peak routines, Hungarian lineage, full carried history. DEV BID January–July 2024 only.

## Outcome-blind metrics

Use the frozen zone matcher and compare geometry plus frozen raw M0GL score/ranking. No revisit/reaction/future field is allowed.

## PASS gate frozen before results

All must hold:

- exact-zone match ≥ **0.90**;
- proxy-zone match ≥ **0.90**;
- median IoU ≥ **0.80**;
- p10 IoU ≥ **0.55**;
- median center error ≤ **0.08 vseg**;
- p95 center error ≤ **0.25 vseg**;
- raw-score Pearson ≥ **0.98**;
- raw-score Spearman ≥ **0.98**;
- median raw-score absolute error ≤ **0.015**;
- p95 raw-score absolute error ≤ **0.060**;
- matched top-1 zone agreement ≥ **0.85**.

This is the final engineering authorization gate before a Pine QA implementation may call itself `VALIDATED_PROXY`. Failure means the Pine file must remain QA-only and cannot display the validated R score as such.
