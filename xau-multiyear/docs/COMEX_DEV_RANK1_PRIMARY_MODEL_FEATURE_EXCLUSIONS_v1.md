# COMEX DEV_RANK1 — Primary model feature exclusions v1

Date: 2026-08-18
Status: frozen before the first DEV_RANK1 reaction/behavior model fit.

The event-feature artifact has been constructed, but no predictive DEV_RANK1 model has yet been fit. This addendum prevents QA fields and deterministic clock information from masquerading as incremental COMEX information.

## B1 exclusions

The following generated columns are QA/availability diagnostics and are **not primary B1 predictors**:

- `b1_available`
- `b1_exact_prev_minute`
- `b1_last_bar_age_min`
- `b1_context_instrument_id`

They may be reported for data quality and sensitivity analysis only.

## B2 exclusions

The following generated columns are QA/routing/reference fields and are **not primary B2 predictors**:

- `b2_available`
- `b2_active_contract`
- `b2_active_instrument_id`
- `b2_p_ref`

`b2_session_elapsed_min` is also excluded from the primary B2 increment because it is deterministically known from the event timestamp rather than being COMEX market information. The B0 preregistration already contains `local_hour`; adding finer clock information only in B2 could generate an apparent incremental gain unrelated to COMEX.

As already frozen in `COMEX_DEV_RANK1_FEATURE_ENCODING_ADDENDUM_v1.md`, native-N share/volume fields are secondary and excluded from the first primary B2 comparison.

## Legitimate activity features

Window trade counts, volume, trade rate, volume rate and active-minute counts remain legitimate B2 tape features. They measure observed market activity inside a frozen causal window and are not mere pipeline QA flags.

## Comparison sets

Primary B0→B1 uses the same rows for both models and does not include B1 QA flags as predictors.

Primary B1→B2 is evaluated on the same rows with a causally available active raw tape (`b2_available=True`). Events outside the canonical GC session or with unavailable raw tape remain in the inventory and are reported separately, but their missingness is not allowed to create apparent COMEX alpha in the primary B1→B2 comparison.

A secondary all-events missingness sensitivity may be reported, but it cannot promote B2 if the complete-causal-tape primary comparison fails.

No outcome result was inspected to choose these exclusions.
