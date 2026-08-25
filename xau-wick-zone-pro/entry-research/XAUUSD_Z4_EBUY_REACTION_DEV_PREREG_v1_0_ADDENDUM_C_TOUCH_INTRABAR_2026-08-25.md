# E-BUY reaction DEV v1.0 — Addendum C: TOUCH_REF contact-bar ordering

**Frozen:** 2026-08-25 while E-BUY coverage OOS replication is still running and before any H1 reaction outcome has been computed or inspected.

## Problem detected by pre-outcome static review

`TOUCH_REF` uses the contact-state `zhi` as the analytical fill reference. On the first M1 bar whose range overlaps the zone, an OHLC high above `zhi` may have occurred before the first downward touch of `zhi`. Therefore a favorable barrier or upper-Z4 target contained in that same contact bar cannot automatically be credited as a post-fill event.

## Frozen conservative handling

For `TOUCH_REF` only:

- if a favorable first-passage barrier is contained in the contact M1 bar, that first-passage contest is `AMBIGUOUS_CONTACT_BAR`, whether or not the adverse barrier is also contained;
- if only the adverse barrier is contained in the contact bar, classify it `ADVERSE_FIRST` because under the analytical continuous-touch convention price must pass the entry boundary before reaching the lower adverse barrier; gaps through the boundary are separately flagged if encountered;
- if neither barrier is resolved in the contact bar, continue from the next M1 normally;
- if TP1 is contained in the contact bar, `TP1_BEFORE_INVALIDATION_US_END` ordering is `AMBIGUOUS_CONTACT_BAR` and TP1 is not credited to TOUCH_REF;
- if TP1 is absent but the contact-bar confirmed close is below `zlo`, classify `INVALIDATION_FIRST`;
- TOUCH_REF MFE used for descriptive summaries excludes the contact-bar high and starts from the following M1 bar, because the contact-bar high has unknown pre/post-fill ordering; TOUCH_REF MAE may include the contact-bar low. This MFE diagnostic is not part of trigger selection.

`RECLAIM_CENTER`, `RECLAIM_FULL`, and `BULL_REJECTION` are unchanged because their hypothetical execution is the next available M1 open after a completed confirmation bar.

This addendum changes no location geometry, target geometry, trigger definition, H1/H2 split, first-passage distances, selection ordering, or eligibility thresholds. It only prevents favorable pre-fill price action from being credited to the direct-touch analytical reference.
