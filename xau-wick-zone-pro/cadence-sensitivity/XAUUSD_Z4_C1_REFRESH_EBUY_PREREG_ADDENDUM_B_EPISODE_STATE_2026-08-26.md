# Addendum B — C1/C5 causal episode-state propagation

**Frozen:** 2026-08-26, after source inspection and before generating or inspecting any new C1 H1/H2 reaction outcome.  
**Parent preregistration:** `XAUUSD_Z4_C1_REFRESH_EBUY_PREREG_v1_0_2026-08-26.md`  
**Causal timing addendum:** `XAUUSD_Z4_C1_REFRESH_EBUY_PREREG_ADDENDUM_A_CAUSAL_INTERVAL_2026-08-26.md`  
**Outcome status at freeze:** no new C1 H1/H2 reaction result has been generated or inspected.

## 1. Outcome-blind implementation issue found by source inspection

The historical reaction runner preconstructs the full list of display episode states before scanning later M1 bars for arming and fresh contacts. Consequently, mutable runtime fields such as `armed` and `consumed` are copied into future snapshots before those runtime events have actually been discovered. A later mutation in snapshot `i` therefore cannot reliably propagate to an already-preconstructed snapshot `i+1` of the same display episode.

This is harmless to the immutable status of the published historical C5 evidence: that evidence remains the `FROZEN_C5_BASELINE` provenance anchor and is not rewritten.

It is not acceptable for the new causal cadence comparison because the parent preregistration explicitly requires causal arming and at most one fresh contact per display episode per US session. The defect would also affect C1 much more strongly because consecutive states are only one minute apart.

## 2. Symmetric causal runtime state

For both `CAUSAL_ACTIVE_INTERVAL_V1_C5` and `CAUSAL_ACTIVE_INTERVAL_V1_C1`, episode identity and mutable state are therefore updated sequentially at runtime.

For a display zone matched one-to-one to the prior contiguous state, carry forward:

- episode id;
- episode origin family;
- episode age in cadence states;
- `armed`, `arm_time`, and `arm_close`;
- whether a fresh contact has already been consumed in the current US session.

For a newly born or non-contiguous display zone, initialize a new episode with `armed=false` and no consumed contact.

Matching remains exactly the already-frozen display matching rule: overlap or center distance within `0.25 * max(v_prev, v_cur)`, one-to-one nearest match with deterministic tie-breaking. This addendum does not alter zone geometry, de-duplication, ranking, top-3 selection, or lineage matching tolerances.

## 3. Ordering within a cadence interval

The ordering is frozen as:

1. state `S(t)` is known only after the M1 observation stamped `t` is complete;
2. `S(t)` may become armed from that confirmed close if `close(t) > zhi(t)`;
3. under `CAUSAL_ACTIVE_INTERVAL_V1`, `S(t)` governs subsequent M1 observations through and including the observation stamped at the next cadence boundary;
4. an observation that first arms an unarmed episode cannot also be its fresh contact; contact is only eligible on a subsequent M1 observation;
5. after the governed interval is processed, the next confirmed display state is matched and mutable episode state is propagated;
6. once a fresh contact occurs, the episode is consumed for that US session; later matched refreshes cannot create another fresh contact in the same session.

The contact-state `center/zlo/zhi`, `v_contact`, and TP1 target remain frozen after contact exactly as in the parent preregistration.

## 4. Frozen baseline versus causal control

The study must report separately:

- `FROZEN_C5_BASELINE`: unchanged historical implementation and published counts;
- `CAUSAL_ACTIVE_INTERVAL_V1_C5`: C5 under Addendum A timing plus this runtime-state propagation;
- `CAUSAL_ACTIVE_INTERVAL_V1_C1`: C1 under the exact same timing and runtime-state propagation.

Only the last two are used to attribute an effect to cadence. Differences between the frozen baseline and causal C5 control quantify implementation/timing effects and must not be credited to C1.

## 5. Paired uncertainty convention frozen before outcomes

For the primary BULL_REJECTION TP1-resolved-rate difference, use paired New-York trading-day block bootstrap with the same sampled days applied to C1 and causal C5. Each bootstrap replicate pools TP1 and resolved counts across the sampled days before computing `rate_C1 - rate_C5`. Use seed `20260826`, 10,000 replicates, and report the percentile 95% interval.

The point estimate is the pooled full-period difference. No minimum gain threshold is introduced.

## 6. Nonchanges

No reaction trigger, target, invalidation, session, E-family parameter, local-band threshold, warm-up, Z4 rule, E score, or production authorization is changed by this addendum.
