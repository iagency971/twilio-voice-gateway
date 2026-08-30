# R4 DEV labeler performance repair — predeclaration

Date: 2026-08-30
Scope: XAUUSD M1 / BUY / US / E1-E2-E3 / E-zone V2 R4

## Status before repair

The authoritative R4 sequential run `33322598145` reached DEV only after the complete R4 PREOUTCOME authority chain passed and was frozen. The DEV step then remained in progress for hours.

No DEV label manifest, zone-test report, score report, model, AUC, coefficient, matched effect, W5/W15/W60, MFE/MAE or other DEV outcome result from that run has been consulted for this repair. The repair trigger is static code inspection of the labeler implementation, not an observed outcome.

## Static implementation defect

`xau_e_zone_v2_labeler.py::label_one` repeatedly scans the complete merged M1 DataFrame for each real or placebo episode:

1. it filters the full M1 table to the episode validity interval;
2. after a contact, it again filters all rows after the contact and maps the NY-session predicate over all of them, even though only the first 30 eligible bars are consumed.

For DEV this is applied to tens of thousands of real episodes and hundreds of thousands of placebo episodes. This does not alter scientific semantics but creates pathological computational complexity.

## Authorized implementation-only repair

The only permitted repair is to pre-index the already normalized M1 rows once by NY session and to use binary search on each session's sorted timestamps to obtain:

- the same `[start, end)` episode bars;
- the same rows strictly after contact;
- the same first 30 eligible US-session bars.

The following are frozen and MUST NOT change:

- arming rule;
- one-minute arm effective delay;
- contact rule;
- feature-validity interval `[feature_available_time, +5m)`;
- contact-bar exclusion from outcome;
- favorable/adverse thresholds `contact_close +/- 0.50*v0`;
- 30-bar horizon;
- same-bar favorable+adverse conservative failure;
- NY date and 08:00 <= hour < 17 session rule;
- REAL/PLACEBO episode populations;
- R4 matching/control design;
- all downstream gates.

## Required parity gate

Before any replacement run may open DEV, synthetic causal tests must compare the legacy full-scan implementation and the indexed implementation and require identical returned label dictionaries on the frozen edge cases, including out-of-session and other-date noise rows. Any parity mismatch is fail-closed.

The replacement authoritative run must restart from PREOUTCOME and discard any partial DEV products from run `33322598145`.
