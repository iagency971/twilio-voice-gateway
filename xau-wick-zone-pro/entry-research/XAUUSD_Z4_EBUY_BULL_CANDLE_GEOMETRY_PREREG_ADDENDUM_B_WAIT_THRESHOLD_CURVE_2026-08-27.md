# Addendum B — incumbent-style waiting threshold curve

**Frozen:** 2026-08-27 before geometry outcomes are computed.

The parent study analyzes the first bullish M1 candle without a close-position cutoff. To answer directly whether the incumbent `0.70` is special within the **existing wait-until-strong-bull** trigger architecture, also compute a descriptive threshold curve.

For each fixed threshold:

`c ∈ {0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95}`

replay the current BULL_REJECTION search exactly except replace `close_pos >= 0.70` with `close_pos >= c`:
- first bullish M1 at/after contact satisfying the threshold;
- stop if invalidation occurs first;
- no trade if TP1 was already reached before trigger/execution;
- next available M1 open execution before 17:00 NY;
- same frozen TP1/invalidation and ambiguity rules.

For H1 and H2 report for every c:
- fired N;
- fired share of contacts;
- resolved share;
- TP1 positive rate;
- invalidation-first rate;
- neither rate;
- median minutes from contact to trigger;
- median TP1 distance/v at execution.

Also report successive 5-point changes in fired share and TP1 positive rate.

**No threshold may be selected from this grid in this study.** The grid is descriptive. `0.70` is considered empirically distinctive only if the curve shows a visible local structural change around it that is directionally reproduced in H1 and H2; otherwise 0.70 remains merely one arbitrary operating point on a smooth frequency/quality trade-off.

Any proposal to replace 0.70 must be frozen in a new preregistration and tested on fresh data.