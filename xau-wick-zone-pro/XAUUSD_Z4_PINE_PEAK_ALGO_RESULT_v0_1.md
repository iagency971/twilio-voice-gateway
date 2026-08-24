# XAUUSD Z4 → Pine peak/prominence/P50 algorithm — result v0.1

**Status: PASS**  
**Grid step: 0.05 USD**  
**Future outcomes used: NO**

Reference: selected `0.05` 3-box Z4 proxy with SciPy `find_peaks`, `peak_prominences`, `peak_widths`.  
Candidate: same engine with explicit Pine-feasible local-peak, prominence-base and linearly interpolated P50 formulas frozen before comparison.

Results on DEV BID Jan–Jul 2024:

- reference rows: 83,502
- Pine-formula rows: 83,181
- matched pairs: 83,083
- reference-zone match: **99.4982%**
- Pine-zone match: **99.8822%**
- same zone count by landmark: **96.3257%**
- median IoU: **1.000**
- p10 IoU: **1.000**
- median/p95 center error: **0 vseg**
- frozen score Pearson: **0.9999897**
- frozen score Spearman: **0.9999916**
- median/p95/p99 raw-score absolute error: **0**
- median within-landmark Spearman: **1.000**
- top-1 zone agreement: **99.8323%**

Every preregistered threshold passed. These explicit formulas are authorized for the M1 Pine Z4 implementation.
