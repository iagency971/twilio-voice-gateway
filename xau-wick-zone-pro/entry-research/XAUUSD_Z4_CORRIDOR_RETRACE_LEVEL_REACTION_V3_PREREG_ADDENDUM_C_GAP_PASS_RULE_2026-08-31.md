# XAUUSD Z4 corridor retrace V3 — Addendum C: pass-below without printed touch

**Date:** 2026-08-31  
**Status:** PREOUTCOME exact contact clarification  
**V3 reaction outcomes opened:** `FALSE`

The preregistration requires the first retracement contact **from above**. M1 data can in principle move from above a level to a bar whose entire printed range is below that level, without `low <= level <= high` on that bar.

## Frozen rule

For every uncontacted candidate cluster and every uncontacted LIVE control:

1. if the current eligible M1 range contains the level, register the contact;
2. otherwise, if `high < level`, mark the level `PASSED_BELOW_WITHOUT_TOUCH` immediately;
3. such a level can never later register a V3 first contact from below;
4. this test is applied after TARGET/MAIN termination precedence and before same-close candidate births;
5. no reaction outcome is used.

This preserves the intended direction of approach and prevents a later bounce from below from being mislabeled as the original BUY retracement contact.
