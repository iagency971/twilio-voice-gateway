# XAUUSD Z4 → Pine implementation parity — result v0.1

**Status: PASS**  
**Scope: M1 Z4 only**  
**Future outcomes used in parity metrics: NO**

Reference: frozen Z4 with exact SciPy Gaussian.  
Proxy: identical frozen Z4 engine except Gaussian replaced by the Pine-feasible 3-box approximation preregistered before metrics.

## Results

- exact Z4 rows: 89,093
- 3-box proxy rows: 82,954
- matched pairs: 82,331
- exact-zone match rate: **92.41%**
- proxy-zone match rate: **99.25%**
- same exact zone count at landmark: 59.92% (the proxy tends to omit some marginal extra peaks)
- mean absolute zone-count difference: 0.503

Geometry among matched zones:

- IoU p10: **0.9499**
- IoU median: **0.9876**
- center error median: **0.0217 vseg**
- center error p95: **0.0833 vseg**
- lower-bound error median: **0.0157 vseg**
- upper-bound error median: **0.0158 vseg**

Frozen M0GL raw-score parity:

- Pearson: **0.99838**
- Spearman: **0.99895**
- median absolute score error: **0.00120**
- p95 absolute score error: **0.02275**
- median within-landmark Spearman: **1.000**
- mean within-landmark Spearman: **0.99187**
- top-1 zone agreement: **89.27%**

Every preregistered engineering threshold passed.

## Interpretation

The three-box Gaussian approximation is acceptable for a Pine implementation of the validated Z4 candidate **provided the rest of the Z4 architecture is ported faithfully**: TRmed1440 segmentation, 15-minute landmarks, P50 zones, exposure features, and causal lineage/stability features.

This result does not authorize copying the score into the old Pine v1.3.4 geometry as-is. v1.3.4 still differs materially in TR scale, cadence and absence of Z4 lineage state.

The port should therefore be a new Z4-based M1 implementation, not a cosmetic change to the old `Strength` label.

Higher timeframes remain unvalidated and are outside this parity PASS.
