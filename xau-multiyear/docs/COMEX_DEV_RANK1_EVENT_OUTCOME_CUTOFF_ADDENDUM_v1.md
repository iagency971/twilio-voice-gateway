# COMEX DEV_RANK1 — Event-level outcome cutoff addendum v1

Date: 2026-08-18
Status: frozen before DEV_RANK1 COMEX feature/outcome fitting.

## Gap clarified

`COMEX_DEV_RANK1_ANALYSIS_PREREG_v1.md` freezes `reaction_0_5sigma` and `behavior_v2` as primary event-level outcomes, but it does not assign them an entry-model-specific `decision_time`. The six entry models retain their previously frozen model-specific cutoffs.

This addendum fixes the event-level cutoff before any DEV_RANK1 COMEX predictive comparison is fit.

## Primary reaction and behavior cutoff

For both primary event-level outcomes:

- `reaction_0_5sigma`;
- multiclass `behavior_v2`;

COMEX predictors must represent information available **before the XAU contact minute begins**.

For contact timestamp `t0` on the canonical M1 XAU grid:

- `event_cutoff = t0`;
- only raw trades with `ts_event < floor_minute(t0)` may enter trade-flow/profile features;
- only completed M1 GC bars with bar timestamp `< floor_minute(t0)` may enter M1 context features;
- DUAL V0/N0 active-contract routing uses cumulative traded `size` from canonical GC session start through the minute immediately preceding `t0`;
- no COMEX information from the contact minute or after contact is allowed in the primary reaction/behavior prediction.

This makes the primary question prospective: does COMEX state available on arrival at a XAU zone improve prediction of what happens after contact?

## Secondary analyses

Post-contact COMEX information is not used to redefine the event-level primary test.

It may be used only under an already frozen entry-model cutoff:

- PASSIVE_TOUCH: strictly before contact-bar start;
- TOUCH_NEXT_OPEN: contact-bar close;
- ACCEPTANCE_RETEST: t0 + 5 minutes;
- CLEAN_REJECTION / FAILED_AUCTION / RECLAIM_PULLBACK: actual reclaim close, maximum t0 + 16 minutes.

Any future early-post-contact behavior classifier not identical to these frozen model cutoffs is exploratory and cannot be promoted using DEV_RANK2 as if preregistered.

## Missingness

Events outside the canonical GC auction session, events on selected dates with unavailable tape, or events lacking sufficient backward history retain explicit missingness/availability indicators. They are not silently removed when comparing B0, B1 and B2; nested comparisons use the same observation set appropriate to the compared feature groups.

## No outcome-dependent choice

This cutoff was fixed from causal ordering only. No DEV_RANK1 COMEX feature association, reaction result, behavior result, or economic outcome was inspected to select it.
