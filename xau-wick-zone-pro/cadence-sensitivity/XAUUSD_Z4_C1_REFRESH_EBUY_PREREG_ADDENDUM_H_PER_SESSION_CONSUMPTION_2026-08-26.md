# XAUUSD Z4 / E-BUY — C1 refresh preregistration Addendum H: per-US-session consumption

**Frozen:** 2026-08-26, before any valid H1/H2 C1 reaction outcome is opened or interpreted.  
**Scope:** causal episode-state implementation correction only; symmetric for C1, matched mechanical C5, and source-faithful C5.

## Pre-existing frozen rule

The parent preregistration states: **maximum one fresh contact per display episode per US session**.

The pre-outcome QA of the causal runner found that its provisional implementation propagated `consumed` as a permanent boolean across the lifetime of an episode. That would incorrectly suppress a valid fresh contact if the same display episode survives into a later New York trading session.

## Required correction

Consumption must be keyed to the New York session day rather than stored as an episode-lifetime boolean:

- each runtime episode state carries `consumed_ny_day`, initially `None`;
- a contact on New York date `D` sets `consumed_ny_day = D`;
- while processing state/contact opportunities on date `D`, skip the episode only when `consumed_ny_day == D`;
- when the same episode survives to a later New York date, the prior date does not block a new fresh contact;
- no more than one fresh contact for that episode may occur on the same NY date;
- episode identity, arm state, geometry matching, cadence timing, target freeze, invalidation freeze, and all other rules remain unchanged.

`armed` remains an episode state and is not reset solely because the calendar date changes; the parent preregistration did not require re-arming at each session.

## Symmetry

The exact same per-session consumption state must be used for:

1. C1 mechanical causal reaction;
2. C5 mechanical matched causal reaction;
3. C5 source-faithful causal reaction.

Thus this correction cannot create a cadence-specific bookkeeping advantage.

## Interpretation

Any runner/output produced with the provisional permanent-consumption boolean is invalid for the final cadence comparison. No such valid H1/H2 C1 reaction output had been opened before this addendum was frozen.

**Authorization:** implementation repair only. No result, Pine change, E-score transfer, or production promotion is authorized.