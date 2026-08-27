# XAUUSD Z4 / E-BUY — FIRST_BULL fresh Aug-2026 prereg Addendum A: bootstrap cluster universe

**Recorded:** 2026-08-27, after the first fresh workflow completed and during mandatory QA of its output.

## Reason for the engineering correction

The frozen preregistration requires whole-US-session bootstrap resampling. The first implementation correctly determined the mechanically eligible raw August session IDs, but its AUC bootstrap helper constructed the resampling universe from sessions that contained resolved FIRST_BULL observations only. Three mechanically eligible raw sessions had zero resolved FIRST_BULL observations, so the first AUC bootstrap used 14 non-empty sessions whereas the preregistered eligible raw-session universe contained 17 sessions.

The score-band bootstrap already used the full eligible-session universe.

## Frozen correction

For every whole-session bootstrap metric in the corrected run:

- resample from the exact mechanically eligible raw session-ID list;
- retain zero-observation eligible sessions as zero-row clusters;
- use seed `20260827` and 1000 draws exactly as preregistered;
- do not change any observation, outcome, model coefficient, scaler value, H1 score cutpoint, feature, session definition, source byte stream, point estimate, or decision threshold.

The corrected AUC and AUC-difference bootstrap helpers therefore receive the frozen eligible-session-ID list explicitly rather than deriving cluster IDs from non-empty event rows.

## Scientific status

This is a post-outcome engineering correction, not a new hypothesis and not a new fresh sample. The original fresh outcomes have already been opened, so this rerun must be described as a deterministic prereg-compliance correction of the same holdout.

No result-dependent model or threshold adjustment is permitted. The primary PASS/FAIL rules remain exactly those in `XAUUSD_Z4_EBUY_FIRST_BULL_GEOMETRY_FRESH_AUG2026_PREREG_v1_0_2026-08-27.md`.

No Pine change is authorized by this addendum.
