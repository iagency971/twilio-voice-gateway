# XAUUSD Z4 Revisit Score — display mapping v0.1

**Status:** FROZEN BEFORE PINE SCORE QA  
**Future outcomes used:** NONE.

The scientific model output is the frozen BID M0GL logistic value. User-facing `R` is a rank score, not a probability.

Given the already frozen DEV equal-landmark-weighted percentile thresholds `T[0..100]`:

- raw <= T[0] → R=0;
- raw >= T[100] → R=100;
- otherwise locate integer `k` such that `T[k] <= raw < T[k+1]`;
- compute `R_float = k + (raw-T[k])/(T[k+1]-T[k])`;
- display `R = round(R_float)` using Pine's standard non-negative rounding.

This piecewise-linear interpolation is monotone and uses no outcomes. It only avoids visual jumps caused by displaying a 101-bin step function.

The label remains `R xx`, never `xx%` and never `Strength`.
