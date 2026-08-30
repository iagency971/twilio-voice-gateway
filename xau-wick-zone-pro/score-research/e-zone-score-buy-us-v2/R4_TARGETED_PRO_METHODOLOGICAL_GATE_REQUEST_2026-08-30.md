# Targeted Pro methodological gate — E-zone score BUY-US V2 R4 control matching

Date: 2026-08-30
Repository: `iagency971/twilio-voice-gateway`
Branch: `agent/xau-wick-zone-pro-dev`

## Purpose of this gate

Perform a **targeted methodological review only** of the proposed replacement of the V2 neutral-control matching design by the frozen outcome-blind design `R4_D5_MINIMAL_DENSE`.

This is **not** a request to revisit the frozen E definitions, outcome, feature set, model class, score gates, BUY-only scope, session, or sequential DEV/VAL/REP architecture.

**Strict outcome-blind condition:** no V2 future reaction outcome for DEV 2020-2021, VAL 2022, or REP 2023 has been opened, generated, labelled, scored, inspected, or used to choose R2/R3/R4. Do not calculate or inspect W5/W15/W60, NRB, MFE/MAE, reaction labels, fitted coefficients, AUC, matched-contact effect, score monotonicity, or any other future-reaction result during this gate.

## Previously approved architecture that remains frozen

Reference: `E_ZONE_SCORE_BUY_US_V2_PRO_GATE.json`.

Keep unchanged unless this gate explicitly says otherwise:
- direction: BUY only;
- session: 08:00-17:00 America/New_York;
- real E-zone definitions and display logic;
- requirement for at least one causal Z4 above current close;
- original display slot identity, no post-filter renumbering;
- feature availability / causal timing;
- width-neutral future-reaction outcome definition;
- same five numeric context variables used by matching: `trend15_v`, `trend60_v`, `trend240_v`, `nearest_upper_z4_dist_v`, `log_v_snapshot`;
- donor-path transplantation in normalized geometry;
- full causal real E/Z4 pool neutrality exclusion, with truncation before first conflict;
- deterministic matching/tie breaking;
- maximum five controls per donor;
- model specification and fitting only on DEV 2020-2021;
- frozen model carried unchanged to VAL 2022 and, only if the validation continuation gate passes, REP 2023;
- no refit after DEV;
- all previously frozen final statistical/quality gates.

## Why the original matching cannot be executed as approved

The R2 implementation repair correctly removed the accidental requirement that the recipient session contain a real E in the donor display slot. Despite that repair, the original exact contextual matching is mathematically too sparse.

Outcome-blind R2 counts:
- DEV 2020-2021: 67,200 donors; 550 with >=2 controls = 0.818452%; only 1 donor with 5 controls;
- VAL 2022: 35,466 donors; 153 with >=2 controls = 0.431399%; 0 with 5 controls;
- REP 2023: 36,014 donors; 228 with >=2 controls = 0.633087%; 0 with 5 controls.

Original R2 matching required:
- same 5-minute session start slot;
- >=10 represented-session separation;
- exact weekday;
- exact upper-Z4-count bucket;
- `abs(delta log(v)) <= 0.20`;
- `abs(delta nearest_upper_z4_dist_v) <= 0.25`;
- standardized Euclidean distance over the five frozen numeric context variables;
- first five valid neutral paths after the full-pool neutrality filter.

The neutral-control estimand therefore cannot be evaluated with adequate coverage under the original exact-match design.

## R3 outcome-blind feasibility ladder

R3 progressively relaxed matching under a predeclared ladder and a predeclared selection rule: the first design with:
1. >=80% of donors having at least two valid neutral controls; and
2. max absolute numeric-context SMD <=0.10.

The best R3 design, `D4_BUCKET_AS_DISTANCE`, reached:
- fraction donors >=2 controls: `0.7486888851294198` = 74.8689%;
- max |SMD|: `0.08812080255467425`.

Because the 80% threshold had been frozen in advance, it was **not retrospectively reduced** to accept D4.

Reference run: `33310670100`, job `99255016840`.

## R4 outcome-blind ladder and selected design

Reference files:
- `xau_e_zone_v2_r4_matching_ladder.py`
- `R4_MATCHING_LADDER_VAL.json`
- `R4_PREOUTCOME_CONTROL_FREEZE.md`

R4 retained the 80% / |SMD|max <=0.10 selection gate and predeclared the following ladder before calculation:
- D5: log(v) caliper 0.65; nearest-upper-Z4 caliper 1.25v;
- D6: 0.80; 1.50v;
- D7: 1.00; 2.00v;
- D8: no hard log(v)/nearest-Z4 calipers.

For all R4 designs:
- same 5-minute session start slot;
- >=10 represented-session separation;
- weekday is a soft distance term, mismatch penalty 0.10;
- upper-Z4-count bucket is a soft distance term, mismatch penalty 0.25;
- standardized Euclidean distance remains over the same five frozen numeric variables;
- same full real E/Z4 causal neutrality rule and path truncation;
- max five controls;
- deterministic SHA-256 tie-break only for exact distance ties.

The **first** predeclared R4 design already passed, so D6-D8 were not inspected or used for selection.

### Selected `R4_D5_MINIMAL_DENSE`

2022 outcome-blind design population:
- real donor episodes: 35,466;
- valid neutral controls selected: 133,672;
- donors with >=2 controls: 29,167 = **82.2393278069%**;
- donors with 5 controls: 21,857 = **61.6280381210%**;
- median controls per donor: 5;
- max absolute SMD: **0.0841289751**.

Numeric-context SMDs:
- `trend15_v`: -0.0841289751;
- `trend60_v`: +0.0290483409;
- `trend240_v`: +0.0614401847;
- `nearest_upper_z4_dist_v`: +0.0059855070;
- `log_v_snapshot`: +0.0202207652.

R4 provenance:
- workflow run `33313388291`;
- job `99262329048`;
- artifact ID `9732770448`;
- artifact ZIP SHA-256 `eceaec6b3ff0eccd5425d8a4feb4baf1df27651f6808e732bbb05366daece2b5`;
- source checkout `1fee064a66c0941123e461eae43acc01b1a19328`;
- `future_price_outcomes_used = false`;
- forbidden outcome columns present = false.

## V0.4 geometry parity status

R2 had one pre-outcome run with equal row counts (88,557 / 88,557) but seven exact-float boundary differences: 3 `zlo`, 4 `zhi`.

A fresh outcome-blind reproducibility diagnostic has now rebuilt the same 24-month V0.4 overlap with the frozen M1 source, frozen Z4 artifacts and frozen Python/scientific environment:
- reference rows: 88,557;
- instrumented rows: 88,557;
- exact float64 parity: **PASS**;
- mismatch counts: `{}`;
- max absolute delta: `0.0`.

Reference: `V04_PARITY_REPRODUCIBILITY_DIAGNOSTIC_2026-08-30.json`.

Fresh parity provenance:
- workflow run `33313608974`;
- job `99262922569`;
- artifact ID `9732845739`;
- artifact ZIP SHA-256 `54f7b7a9acb79112e50b815592df5268c110151f51c66ea03634a91431df3871`.

The root cause of the prior seven one-off differences is **not proven**. Do not relax exact parity. The proposed execution keeps exact float64 parity as a fail-closed PREOUTCOME gate; if any mismatch recurs, execution must stop before opening DEV outcomes.

## Questions for Pro

Review only the methodological consequences of `R4_D5_MINIMAL_DENSE` and answer:

1. Is replacing the original R2 exact contextual matching with frozen `R4_D5_MINIMAL_DENSE` scientifically acceptable for the intended matched-neutral-control test, given the observed outcome-blind coverage and balance?
2. Are the two soft mismatch penalties (weekday 0.10, upper-Z4 bucket 0.25), hard calipers (log(v) 0.65, nearest-upper-Z4 distance 1.25v), >=10-session gap and five-control cap acceptable as frozen, without further tuning?
3. Is the outcome-blind 2022 population an acceptable design-only dataset for choosing this matching rule while retaining 2022 as forward validation for reaction outcomes, given that no future reaction labels/outcomes were used in the choice? Address the distinction explicitly.
4. Does the low median retained placebo path length of 1 snapshot create a methodological problem for the frozen contact/reaction estimand, or is it acceptable under the existing truncation rule? If it is a blocker, specify a pre-outcome repair criterion without consulting outcomes.
5. Is max |SMD| <=0.10 an adequate pre-outcome balance gate here, or should an additional pre-outcome distributional diagnostic be required before DEV? Any additional diagnostic must be defined now, before outcomes.
6. Does the fresh exact V0.4 parity PASS justify proceeding with an exact rerun gate, while keeping a fail-closed stop if any mismatch reappears?
7. If R4 is approved, may the pipeline proceed directly through a complete immutable PREOUTCOME rebuild and, if every pre-outcome gate passes, open DEV 2020-2021 without another Pro review? Or is a second Pro gate required after the R4 PREOUTCOME package but before DEV outcomes?
8. Confirm that all downstream outcome/model/validation/replication gates from the prior Pro authorization remain unchanged and that REP 2023 remains closed unless the frozen VAL 2022 continuation gate passes.

## Required decision format

Return a structured memo and a machine-readable JSON decision containing at minimum:

```json
{
  "status": "PRO_E_ZONE_SCORE_BUY_US_V2_R4_CONTROL_GATE_PASS_OR_FAIL",
  "decision": "GO_R4" or "NO_GO_R4",
  "outcome_blind_review": true,
  "r4_design_authorized": true or false,
  "authorized_design": {
    "id": "R4_D5_MINIMAL_DENSE",
    "same_start_minute": true,
    "min_session_gap": 10,
    "weekday_exact": false,
    "weekday_mismatch_penalty": 0.10,
    "upper_z4_bucket_exact": false,
    "upper_z4_bucket_mismatch_penalty": 0.25,
    "log_v_caliper": 0.65,
    "nearest_upper_z4_dist_v_caliper": 1.25,
    "max_controls": 5,
    "max_abs_smd_gate": 0.10,
    "min_fraction_donors_ge2": 0.80
  },
  "exact_v04_parity_required": true,
  "additional_preoutcome_requirements": [],
  "pro_gate_required_after_preoutcome_before_dev": true or false,
  "downstream_original_gates_unchanged": true or false,
  "replication_2023_remains_conditional_on_val_2022": true
}
```

If `NO_GO_R4`, identify the specific methodological defect and define the smallest **outcome-blind** repair or alternative design that may be evaluated next. Do not inspect future reaction outcomes to choose that repair.
