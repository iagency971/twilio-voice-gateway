# XAUUSD Z4 — Cadence Common-Anchor Geometry Parity QA v0.1

**Freeze date:** 2026-08-24  
**Status:** FROZEN BEFORE READING ANY NUMERICAL GEOMETRY DIFFERENCES  
**Reason for QA:** the cadence DEV run produced equal common-15 row/landmark counts for C5 and C15 but different byte-level geometry hashes. Candidate jobs ran on separate hosted runners, so the original exact-float hash invariant may be too strict for independently executed SciPy floating-point pipelines.

This QA is implementation/provenance only. It must not inspect `REVISIT_240`, Brier, LogLoss, or any future outcome.

## Frozen invariant

At a UTC 15-minute common anchor, C1/C5/C15 must produce the same pre-lineage zone geometry because cadence only changes `landmark_ok`; the rolling 1,440-active-M1 field, vseg, range, detector, P50 bounds, close, and side filter are unchanged and update on every active M1.

Lineage columns are explicitly excluded from this geometry QA.

## Same-run comparison

For each feed, rebuild frozen C15 and each shorter cadence on the **same GitHub runner**, same input bytes, same Python/SciPy environment. Compare final candidate rows restricted to common 15-minute anchors using only:

`(landmark_i, center, zlo, zhi, side)`

The final pickle is acceptable because lineage processing does not mutate those five fields.

## Frozen matching and pass criteria

For each common `landmark_i`:

1. zone count must match exactly;
2. after sorting by `(side, center, zlo, zhi)`, side must match exactly row-by-row;
3. center must match exactly to within `1e-12 USD` (centers are 0.01-grid values);
4. `zlo` and `zhi` maximum absolute error must each be <= **1e-8 USD**;
5. total common-anchor rows and landmarks must match exactly.

Report max/median/p99 absolute errors for center/zlo/zhi and the number of landmarks/rows failing each condition.

### Verdict

- `GEOMETRY_PARITY_PASS` only if all criteria above pass on both BID and ASK.
- If same-run parity fails, the shorter cadence fails provenance and cannot be promoted regardless of predictive metrics.
- If same-run parity passes, the earlier differing byte-level hashes are classified as an over-strict cross-run floating-point attestation failure rather than a scientific geometry divergence. The aggregate decision must then use this QA verdict as the repaired provenance gate, without changing any predictive result or shortlist criterion.

No tolerance may be widened after numerical differences are read.
