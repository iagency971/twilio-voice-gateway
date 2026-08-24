# XAUUSD Z4 → Pine combined implementation parity — result v0.1

**Status: PASS**  
**Scope: M1 Z4 validated revisit model only**  
**Future outcomes used: NO**

The final Pine-feasible candidate combined only engineering substitutions that had already passed separate outcome-blind preregistered gates:

- absolute price grid step **0.05 USD**;
- three-box Gaussian approximation;
- explicit Pine local-peak / prominence / linearly interpolated P50 formulas;
- deterministic greedy one-to-one lineage assignment;
- lineage state cold-start cap **96 eligible 15-minute landmarks**.

Reference was the exact frozen Python Z4: 0.01 grid, SciPy Gaussian/peak routines, Hungarian lineage assignment, full carried lineage history. DEV BID January–July 2024 only; no future outcome was used in this engineering parity gate.

## Combined result

- exact reference rows: **89,093**
- Pine-proxy rows: **83,181**
- matched zone pairs: **82,183**
- exact-zone match rate: **92.2441%**
- proxy-zone match rate: **98.8002%**
- median IoU: **0.973891**
- p10 IoU: **0.906309**
- median center error: **0.038095 vseg**
- p95 center error: **0.178571 vseg**
- frozen M0GL raw-score Pearson: **0.997434**
- frozen M0GL raw-score Spearman: **0.998415**
- median absolute raw-score error: **0.002313**
- p95 absolute raw-score error: **0.031047**
- median within-landmark Spearman: **1.000**
- mean within-landmark Spearman: **0.990213**
- matched top-1 zone agreement: **86.9937%**

Every preregistered combined threshold passed.

## Authorization

The M1 Pine implementation may therefore use this combined proxy and may label its status `VALIDATED_PROXY` **only when all frozen implementation conditions are satisfied** (M1, sufficient history/warm-up, fixed 0.05 grid, 15-minute frozen snapshot cadence, frozen coefficients/map, no silent fallback).

`VALIDATED_PROXY` means engineering-equivalent to the independently validated Dukascopy Z4 revisit model within the preregistered parity tolerances. It does **not** mean the TradingView broker feed itself has been validated; feed transfer remains an explicit assumption.

Higher timeframes remain descriptive/unvalidated and may not display the validated `R` score.
