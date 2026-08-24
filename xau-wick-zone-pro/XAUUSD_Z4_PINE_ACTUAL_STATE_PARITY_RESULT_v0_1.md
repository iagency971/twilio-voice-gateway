# XAUUSD Z4 → Pine actual carried-state parity — result v0.1

**Status: PASS**  
**Future outcomes used: NO**

This gate directly tests the state behavior intended by the Pine file: `0.05 grid + box3 + explicit peak/P50 + greedy lineage`, with lineage state carried for as long as it is available. The separate cap96 PASS remains the justification for declaring the live score ready after a finite 96-landmark cold start.

Results versus exact frozen Z4 on DEV BID Jan–Jul 2024:

- exact rows: **89,093**
- proxy rows: **83,181**
- matched pairs: **82,183**
- exact-zone match: **92.2441%**
- proxy-zone match: **98.8002%**
- median IoU: **0.973891**
- p10 IoU: **0.906309**
- median center error: **0.038095 vseg**
- p95 center error: **0.178571 vseg**
- raw-score Pearson: **0.997432**
- raw-score Spearman: **0.998415**
- median raw-score error: **0.002311**
- p95 raw-score error: **0.031067**
- median within-landmark Spearman: **1.000**
- matched top-1 zone agreement: **86.9937%**

Every preregistered threshold passed.

The actual carried-state architecture of the M1 Pine QA file is therefore engineering-authorized as `VALIDATED_PROXY` once its 96 eligible-landmark warm-up is complete, subject to successful TradingView compilation/runtime QA and the explicit chart-feed transfer caveat.
