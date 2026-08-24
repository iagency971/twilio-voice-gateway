# XAUUSD Z4 → Pine lineage bootstrap cap — result v0.1

**Status: PASS**  
**Selected cap: 96 eligible 15-minute lineage landmarks**  
**Future outcomes used: NO**

The cap candidates `{96,128,160,192}` and all engineering thresholds were frozen before results. The deterministic rule was to select the smallest cap that passed every criterion.

## Full DEV lineage distribution

- rows: 89,093
- lineages: 5,395
- landmarks: 13,705
- median lineage age: 24 landmarks
- p75: 50
- p90: 74
- p95: 85
- p99: 97
- p99.5: 116
- p99.9: 155
- maximum: 186
- rows with age >96: **1.0966%**

## Cap 96 score parity

Despite truncating carried lineage state for the oldest ~1.1% of rows:

- Pearson frozen raw M0GL: **0.999999664**
- Spearman: **0.999999573**
- median absolute score error: **0**
- p95 absolute score error: **2.0e-12**
- p99 absolute score error: **3.16e-8**
- fraction error >0.03: **0**
- fraction error >0.05: **0**
- median within-landmark Spearman: **1.000**
- mean within-landmark Spearman: **0.9999867**
- top-1 zone agreement: **100%**
- mean top-3 Jaccard: **100%**

Every preregistered criterion passed. Cap 96 is therefore selected.

## Interpretation

For the frozen Z4 revisit model, lineage history older than 96 consecutive eligible 15-minute snapshots has essentially no practical influence on the final frozen score because the long-history coefficients/features contribute very little at those tails. A Pine implementation may cold-start lineage state over 96 eligible landmarks without materially changing the validated M0GL ranking.

This is an engineering portability result, not a new predictive optimization and not a reaction/trading result.
