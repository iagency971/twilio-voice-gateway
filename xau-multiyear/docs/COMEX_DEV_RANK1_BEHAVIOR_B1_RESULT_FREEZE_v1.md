# XAUUSD / COMEX — DEV_RANK1 multiclass behavior B1 result freeze v1

Date: 2026-08-18
Status: B1-vs-B0 primary component frozen before B2 result.

Target: preregistered multiclass `behavior_v2`.
Sample: 30,525 B2-causally-available events / 92 sessions / 2011–2018.
Validation: exact outer leave-one-year-out; C selected by inner LOYO on remaining years. All 8 B0 and all 8 B1 outer folds were complete before aggregation. B2 was still running.

## B1 versus B0

- family-balanced event log-loss improvement: **-0.08895647681196683**
- population-event improvement: **-0.016060680627900115**
- session-balanced improvement: **-0.015393042682600222**
- positive outer years: **1/8**
- year deltas:
  - 2011: -0.02015882713902406
  - 2012: -0.010782694498771006
  - 2013: -0.16706838673388413
  - 2014: -0.02135666953631221
  - 2015: -0.11990424788317933
  - 2016: -0.026099625362943413
  - 2017: -0.03355967740514243
  - 2018: +0.007831751540755993
- trading-date cluster bootstrap 95% on family-balanced delta:
  - lo: -0.18509828602253298
  - median: -0.08304791453877952
  - hi: -0.014713994851130466
- preregistered directional gate: **FAIL**

## Freeze decision

For the primary multiclass behavior target, continuous GC M1 context B1 is NOT eligible for promotion over B0 in DEV_RANK1.

This result is frozen before the raw-trades/auction B2 result. No feature pruning, year removal, family exception, redefinition of behavior, or alternative model class may retroactively turn B1 into a primary pass.

B2 remains a distinct incremental comparison against the now-frozen B1. The secondary binary reject-vs-accept diagnostic remains secondary and cannot override the multiclass primary gate.
