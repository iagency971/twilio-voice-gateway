# XAUUSD Z4 → Pine R display-label parity — result v0.1

**Status: PASS**  
**Future outcomes used: NO**

The final combined Pine proxy was mapped through the frozen DEV equal-landmark-weighted percentile map and compared with the exact Z4 display rank on 82,183 matched DEV BID zones.

Results:

- median absolute continuous-R error: **0.283 point**
- p90: **1.767 points**
- p95: **2.974 points**
- p99: **7.519 points**
- median absolute displayed integer-R error: **0 point**
- p95 displayed error: **3 points**
- displayed R within ±1: **87.22%**
- within ±2: **93.45%**
- within ±5: **98.10%**
- R Pearson: **0.998217**
- R Spearman: **0.998415**
- matched top-1 agreement: **96.99%**

Every preregistered R-display threshold passed.

The user-facing `R xx` label is therefore engineering-authorized for the M1 validated proxy. `R` remains a percentile/rank of revisit likelihood, not a probability percentage and not a reaction-strength score.
