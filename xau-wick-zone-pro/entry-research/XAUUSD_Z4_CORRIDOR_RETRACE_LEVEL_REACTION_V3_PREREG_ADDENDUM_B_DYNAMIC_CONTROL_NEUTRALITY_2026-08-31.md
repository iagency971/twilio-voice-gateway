# XAUUSD Z4 corridor retrace V3 — Addendum B: dynamic control neutrality

**Date:** 2026-08-31  
**Status:** PREOUTCOME engineering finding / authoritative correction  
**V3 reaction outcomes opened:** `FALSE`

A synthetic causal integration test exposed an ambiguity not covered by Addendum A: a neutral pseudo-level can be valid at its generation time but a new V3 structural candidate can later be born near that pseudo-level before the pseudo-level is contacted.

Such a control is no longer neutral at the time of its eventual touch and therefore must not remain eligible.

## Frozen rule

Whenever new candidate clustering is completed at an M1 close:

1. contacts on that M1 have already been evaluated under Addendum A ordering, because the newly born candidate did not exist before the close;
2. after the new/updated candidate clusters become causally available, inspect every **uncontacted LIVE control** in that authority episode;
3. if a control lies within `0.10 * control.v_birth` of the center of any causally available V3 candidate cluster, mark it `CENSORED_STRUCTURAL_LEVEL_BORN` at that close;
4. a censored control can never contact later and is excluded from the primary matched-control count;
5. a control that had already contacted before the new structural candidate was born is not retrospectively removed;
6. candidate outcomes, reaction labels or any post-contact information are not used in this censoring rule.

This is a causal neutrality correction, not an outcome-driven design change.

The original generation-time exclusion remains in force. Addendum B adds the missing **prospective neutrality maintenance** between control birth and control contact.
