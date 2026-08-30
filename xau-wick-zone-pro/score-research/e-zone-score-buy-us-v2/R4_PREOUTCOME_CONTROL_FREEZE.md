# E-zone score BUY-US V2 — R4 pre-outcome control freeze

Date: 2026-08-30

## Status

`R4_D5_MINIMAL_DENSE` is frozen as the first predeclared R4 design that passed the outcome-blind feasibility gate. No V2 future reaction outcome has been read, generated, labelled, scored, or used for this selection.

Evidence:
- workflow run: `33313388291`
- job: `99262329048`
- artifact: `9732770448`
- artifact ZIP SHA-256: `eceaec6b3ff0eccd5425d8a4feb4baf1df27651f6808e732bbb05366daece2b5`
- source checkout commit: `1fee064a66c0941123e461eae43acc01b1a19328`
- committed result: `R4_MATCHING_LADDER_VAL.json`

## Why R4 was required

The Pro-approved R2 exact matching was outcome-blind but practically infeasible. On 2022 it produced only 153 / 35,466 donor episodes with at least two neutral controls (0.4314%).

R3 relaxed the matching progressively under a predeclared outcome-blind ladder. Its best design D4 reached 26,553 / 35,466 donors with at least two controls (74.8689%) and max absolute numeric-context SMD 0.08812. R3's predeclared selection threshold was 80%; it was not retrospectively lowered.

## Frozen R4 design

R4 retained the same real E definitions, same 5-minute NY start slot, same five numeric matching variables, same donor-path transplantation, same minimum separation of 10 represented sessions, same five-control cap, and the same full real E/Z4 causal neutrality exclusion/truncation.

Only matching density was changed relative to the original Pro gate:
- weekday is no longer exact; mismatch penalty = 0.10
- upper-Z4-count bucket is no longer exact; mismatch penalty = 0.25
- absolute log(v) caliper = 0.65
- nearest-upper-Z4-distance caliper = 1.25 v
- standardized Euclidean distance remains over: trend15_v, trend60_v, trend240_v, nearest_upper_z4_dist_v, log_v_snapshot
- deterministic SHA-256 tie-break remains

## Outcome-blind feasibility result on 2022 design population

Population: 35,466 real donor episodes.

- controls selected: 133,672
- donors with >=2 controls: 29,167 = 82.2393278069%
- donors with 5 controls: 21,857 = 61.6280381210%
- median controls per donor: 5
- max absolute SMD: 0.0841289751
- SMD trend15_v: -0.0841289751
- SMD trend60_v: 0.0290483409
- SMD trend240_v: 0.0614401847
- SMD nearest_upper_z4_dist_v: 0.0059855070
- SMD log_v_snapshot: 0.0202207652

Frozen R4 feasibility rule: first predeclared design with >=80% of donors having at least two controls AND max absolute numeric-context SMD <=0.10. R4_D5 passed and therefore D6-D8 were not evaluated.

## Authorization boundary

This R4 control design is a methodological change relative to `E_ZONE_SCORE_BUY_US_V2_PRO_GATE.json`. Therefore the previous Pro authorization to open DEV cannot automatically carry over. A targeted Pro methodological gate is required before any DEV/VAL/REP reaction outcome is opened under R4.

Until that gate is passed: `PREOUTCOME_ONLY`.
