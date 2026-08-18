# XAUUSD / COMEX — DEV_RANK1 binary behavior diagnostic mapping freeze v1

Date: 2026-08-18
Status: frozen while the preregistered multiclass behavior model is still running; therefore not selected from its result.

## Role

The preregistered `behavior_v2` multiclass target remains PRIMARY:
- CLEAN_REJECTION
- FAILED_AUCTION
- ACCEPTED_BREAK
- UNRESOLVED

A binary diagnostic is allowed by the preregistration but cannot replace or override the multiclass primary result.

## Frozen binary mapping

- `REJECT` = `CLEAN_REJECTION` OR `FAILED_AUCTION`
- `ACCEPT` = `ACCEPTED_BREAK`
- `UNRESOLVED` = excluded from the binary diagnostic sample

Rationale: both CLEAN_REJECTION and FAILED_AUCTION end in rejection/reclaim behavior, while ACCEPTED_BREAK is the explicit acceptance class. UNRESOLVED has no resolved rejection/acceptance label and is not forced into either class.

## Frozen modeling rules

- Same B0 → B1 → B2 nested groups as the primary behavior model.
- Ridge logistic regression only.
- C grid `{0.01, 0.1, 1, 10, 100}`.
- Outer leave-one-year-out 2011–2018; C chosen by inner LOYO on remaining years.
- Same observations within each B0/B1/B2 comparison.
- Training preprocessing fitted only on training folds.
- Trading date is the bootstrap cluster.
- Family balancing and session-balanced diagnostics remain mandatory.
- No threshold tuning or class remapping after seeing results.

The binary diagnostic is secondary and cannot promote a COMEX feature group if the multiclass primary fails the preregistered gate; it may only help interpret where information exists.
