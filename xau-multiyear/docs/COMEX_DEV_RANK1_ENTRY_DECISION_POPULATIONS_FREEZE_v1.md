# XAUUSD / COMEX — DEV_RANK1 entry decision populations freeze v1

Date: 2026-08-18
Status: frozen before inspecting COMEX-conditioned entry/fill/net-R results.

## Purpose

The existing event-table field `<model>_eligible` is produced by `build_entry`. For limit/retest models, `build_entry` returns `None` when the eventual order is not filled, so `eligible` is not always a pure pre-fill setup flag. Economic analysis must therefore separate the decision population from the later fill outcome.

## Frozen decision populations and causal cutoffs

### PASSIVE_TOUCH
- decision population: every canonical contact event;
- order decision cutoff: contact-bar start `t0`, predictors strictly before `t0`;
- fill outcome: `passive_touch_eligible` (standing centre limit reached within frozen wait window);
- net-R sample: filled events only.

### TOUCH_NEXT_OPEN
- decision population: every canonical contact event;
- decision cutoff: contact-bar close `t0 + 1m`;
- operational entry outcome: `touch_next_open_eligible` (next active executable bar exists under frozen rule);
- net-R sample: entered events only.

### CLEAN_REJECTION
- decision population: events with `behavior_v2 == CLEAN_REJECTION` and finite `first_reclaim_minutes_v2`;
- decision cutoff: close of reclaim bar = `t0 + first_reclaim_minutes_v2 + 1m`;
- entry-availability outcome: `clean_rejection_eligible`;
- net-R sample: entered events only.

### FAILED_AUCTION
- decision population: events with `behavior_v2 == FAILED_AUCTION` and finite `reclaim_after_breach_minutes_v2`;
- decision cutoff: close of reclaim bar = `t0 + reclaim_after_breach_minutes_v2 + 1m`;
- entry-availability outcome: `failed_auction_eligible`;
- net-R sample: entered events only.

### ACCEPTANCE_RETEST
- decision population: events with `behavior_v2 == ACCEPTED_BREAK`;
- order decision cutoff: `t0 + 5m`, regardless of whether the later retest fills;
- retest/fill outcome: `acceptance_retest_eligible` (frozen 30-minute retest limit rule);
- net-R sample: filled retests only.

### RECLAIM_PULLBACK
- decision population: events with `behavior_v2 in {CLEAN_REJECTION, FAILED_AUCTION}` and the corresponding finite reclaim-minute label;
- order decision cutoff: close of reclaim bar, reconstructed from the reclaim label independently of later fill;
- pullback/fill outcome: `reclaim_pullback_eligible` (frozen 15-minute standing-limit rule with invalidation handling);
- net-R sample: filled pullbacks only.

## Causal feature construction

For every row in a decision population:
- B0/B1/B2 are computed on the same row;
- B1/B2 stop at the model-specific cutoff above;
- DUAL V0/N0 routing uses cumulative traded size only through the completed minute preceding that cutoff;
- post-order and post-fill COMEX information is forbidden;
- a missing GC tape remains missing and is not replaced by another selected date.

## Eligibility/fill interpretation

The primary binary model is only run where both outcomes exist in adequate numbers. A near-deterministic operational availability target is reported descriptively rather than overinterpreted as predictive alpha.

Every model report must include:
- decision-population events;
- filled/entered count and rate;
- independent session count;
- years represented;
- family breakdown;
- effective sample-size diagnostics.

Underpowered family × model cells are `INCONCLUSIVE`.

## Net-R

Net-R is modeled only conditional on fill/entry and uses already-frozen XAU execution/cost rules. No COMEX feature may alter historical fill, entry, stop, TP or transaction-cost mechanics.

The existing RR surface is not collapsed to a single RR after seeing COMEX results. A separate pre-result rule is required before any RR-specific COMEX promotion decision; until then RR-conditioned net-R analysis may be generated descriptively but cannot select a DEV_RANK2 feature group.
