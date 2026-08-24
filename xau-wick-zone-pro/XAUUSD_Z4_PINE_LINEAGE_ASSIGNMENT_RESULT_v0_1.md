# XAUUSD Z4 → Pine greedy lineage assignment — result v0.1

**Status: PASS**  
**Future outcomes used: NO**

The deterministic greedy matcher was preregistered before metrics as a Pine-feasible substitute for the Hungarian assignment used in the frozen Python Z4 lineage engine.

DEV BID January–July 2024 results:

- zone rows: 89,093
- eligible landmarks: 13,727
- previous-link agreement: **99.9776%**
- frozen raw M0GL Pearson: **0.9999349**
- frozen raw M0GL Spearman: **0.9999589**
- median raw-score error: **0**
- p95 raw-score error: **0**
- p99 raw-score error: **0**
- median within-landmark Spearman: **1.000**
- mean within-landmark Spearman: **0.9997117**
- top-1 zone agreement: **99.9562%**
- mean top-3 Jaccard: **99.9686%**

All preregistered thresholds passed. The Pine port may therefore use the frozen deterministic greedy pair assignment rather than implementing a full Hungarian solver.

Rare lineage divergences affect a tiny fraction of rows; the preregistered score/ranking gate demonstrates negligible practical impact on the validated revisit score. This remains an engineering parity result, not a new predictive optimization.
