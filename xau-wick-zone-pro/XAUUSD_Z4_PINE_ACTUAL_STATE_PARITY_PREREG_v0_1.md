# XAUUSD Z4 → Pine actual carried-state parity — prereg v0.1

**Date:** 2026-08-23  
**Status:** FROZEN BEFORE METRICS  
**Future outcomes used:** NONE.

## Why this extra gate exists

The previous combined engineering gate conservatively applied a fixed 96-landmark lineage-state cap. The actual Pine implementation can carry lineage state for longer once it has loaded sufficient history. The separate cap96 audit established that a 96-landmark cold start is enough to remove practically all dependence on missing older state, but the live code thereafter carries its available state rather than resetting it every 96 landmarks.

This gate therefore tests the exact intended carried-state combination directly on the full DEV history.

## Candidate

- 0.05 USD absolute grid;
- 3-box Gaussian;
- explicit Pine peak/prominence/P50 formulas;
- deterministic greedy one-to-one lineage assignment;
- full carried lineage state from the beginning of the available DEV sequence.

The live Pine requires 96 eligible-landmark warm-up before labeling its score `VALIDATED_PROXY`; the already-passed cap96 audit justifies this finite cold-start requirement.

## Reference and metrics

Reference = exact frozen Z4 0.01/SciPy/Hungarian/full-history. DEV BID Jan–Jul 2024 only. Use the same outcome-blind geometry/score comparator as the frozen combined gate.

## PASS thresholds

Exactly the same as the already-frozen combined gate:

- exact-zone match ≥ 0.90;
- proxy-zone match ≥ 0.90;
- median IoU ≥ 0.80;
- p10 IoU ≥ 0.55;
- median center error ≤ 0.08 vseg;
- p95 center error ≤ 0.25 vseg;
- raw-score Pearson ≥ 0.98;
- raw-score Spearman ≥ 0.98;
- median raw-score error ≤ 0.015;
- p95 raw-score error ≤ 0.060;
- top-1 agreement ≥ 0.85.

No threshold may be changed after results.
