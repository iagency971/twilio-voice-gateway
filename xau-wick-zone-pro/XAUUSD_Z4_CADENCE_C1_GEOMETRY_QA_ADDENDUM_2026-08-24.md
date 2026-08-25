# XAUUSD Z4 — C1/C15 Geometry QA Addendum

**Date:** 2026-08-24  
**Status:** IMPLEMENTATION QA COMPLETE — NO CHANGE TO FROZEN C5 REPLICATION DECISION

This addendum records the outcome of the preregistered, outcome-blind same-run geometry QA for C1 versus C15.

## Result

Artifact: `cadence-sensitivity/qa/XAUUSD_Z4_CADENCE_C1_C15_GEOMETRY_PARITY_QA_v0_1.json`

Overall `GEOMETRY_PARITY_PASS = true`.

### BID
- common-anchor rows: 89,093 vs 89,093;
- landmarks: 13,705 vs 13,705;
- per-landmark zone-count mismatches: 0;
- side mismatches: 0;
- center max absolute error: 0 USD;
- zlo max absolute error: 0 USD;
- zhi max absolute error: 0 USD.

### ASK
- common-anchor rows: 89,863 vs 89,863;
- landmarks: 13,718 vs 13,718;
- per-landmark zone-count mismatches: 0;
- side mismatches: 0;
- center max absolute error: 0 USD;
- zlo max absolute error: 0 USD;
- zhi max absolute error: 0 USD.

## Interpretation

The earlier cross-run byte-hash mismatch was not a scientific geometry divergence. At identical 15-minute timestamps, C1 and C15 produce the same frozen Z4 detector geometry and side eligibility when rebuilt on the same runner/input/environment.

This QA confirms C1 provenance cleanliness only. It does **not** change the already frozen targeted cadence decision in `XAUUSD_Z4_CADENCE_TARGETED_PRO_GATE_FRAMEWORK_v0_1_2026-08-24.md`:

- C5 remains the primary candidate authorized for historical temporal replication;
- C1 remains a scientifically interesting sensitivity result;
- C1 must not become a post-hoc rescue candidate if C5 fails;
- C15 remains the validated production incumbent until a later explicit promotion gate.

No cadence-specific Aug-2024→Jul-2026 outcome was used to make or alter this decision.
