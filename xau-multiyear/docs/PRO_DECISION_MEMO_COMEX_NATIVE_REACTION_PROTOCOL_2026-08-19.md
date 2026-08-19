# PRO DECISION MEMO — COMEX native reaction protocol

Date: 2026-08-19  
Branch: `agent/xau-comex-acquisition-plan`  
Review state: OUTCOME-BLIND METHODOLOGICAL REVIEW  
Reaction outcomes inspected or computed: **NO**  
New market-data acquisition authorized: **NO**

This memo audits `COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_PREPRO_v0_9.md` against the completed exact-contact checkpoint and the two earlier frozen native-contact protocols. It does not reinterpret the completed 238/368 contact incidence as performance.

## 1. Overall verdict

`APPROVE_WITH_REQUIRED_CHANGES`

The event definition, same-raw-instrument rule, exact first-contact timestamp, causal approach-side concept, J+1 boundary and intrabar-ordering prohibitions are sound. The draft is not yet executable because its proposed bar-count horizons can create unequal elapsed-time windows, and its control proposal is not yet comparable to the exact-`t0` reaction module.

The decisive required change is to separate:

1. an exact residual-contact-minute module, which is descriptive only; and
2. a control-comparable primary module beginning at the completed contact-minute close and using fixed wall-clock M1 windows.

With that change, already-owned M1 data are sufficient for a DEV_RANK1 screening pass. Exact pseudo-event tape is not required for the first pass.

## 2. Final Track-A event definition

### Population

The Track-A population is the 238 levels with a confirmed first exact raw-GC contact during the already-frozen full J+1 GC auction session. The estimand is conditional on contact. The 130 J+1 noncontacts are not zero-reaction observations and are not included in Track A.

### Event time and level

- `L` is the frozen executable `contact_tick_price` on the GC 0.10 tick.
- `t0` is the first chronological raw trade in J+1 on the same `source_instrument_id` with executed price exactly equal to `L`.
- Only the first exact contact is used.
- Later same-level contacts/retests are not additional Track-A primary observations.

### Approach-side rule

Retain the PRE-PRO rule with one clarification:

1. Search already-owned raw trades strictly before `t0` within the downloaded exact contact interval.
2. Use the last trade strictly different from `L`.
3. Below `L` means `APPROACH_FROM_BELOW`; above `L` means `APPROACH_FROM_ABOVE`.
4. If unavailable, search completed J+1 M1 closes strictly before `t0`, backward to the J+1 session open, and use the latest close strictly different from `L`.
5. If still unavailable, label `APPROACH_UNDEFINED`.

`APPROACH_UNDEFINED` events remain in inventory and unsigned descriptive output but are excluded from all signed primary/control estimands. No side may be imputed.

Define `away_sign = +1` for approach from above and `away_sign = -1` for approach from below.

### Raw-instrument rule

All event identification and native reaction measurements use the same raw `source_instrument_id` that created the level. Continuous GC, another expiry, adjusted levels and XAUUSD/CFD prices are prohibited substitutes.

### Required second timestamp: primary-analysis anchor

Define:

- `m0 = floor_UTC_minute(t0)`;
- `a0 = m0 + 1 minute`, the end of the completed contact minute;
- `A0 =` the last executed raw-GC price in the contact minute, equivalently its M1 close.

`t0` remains the scientific event time. `a0/A0` is the start/price of the control-comparable primary M1 analysis. This distinction must be explicit in v1.

## 3. Final horizons

Replace completed-bar-count horizons with fixed wall-clock windows from `a0`.

Final set:

- `R0`: `t0` to `a0`, exact already-owned residual contact-minute tape; descriptive only.
- `W5`: `[a0, a0 + 5 minutes)`.
- `W15`: `[a0, a0 + 15 minutes)` — **PRIMARY HORIZON**.
- `W60`: `[a0, a0 + 60 minutes)`.
- `SC`: `[a0, canonical J+1 session close)`.

Drop `B1` and `B30` from v1 to reduce redundant multiplicity. Do not define windows as “next N observed bars,” because missing/no-trade minutes could make elapsed time unequal.

For each fixed window:

- use only completed M1 intervals wholly inside the window;
- a no-trade minute contributes no new executed-price extreme; endpoint price is the last executed price at or before the endpoint, beginning with `A0`;
- if the requested endpoint is after J+1 session close, the fixed window is censored/missing rather than shortened, extended or imputed;
- store actual elapsed seconds and counts of traded/no-trade minutes as QA fields.

The primary claim is therefore a post-contact-minute, 15-wall-clock-minute reaction/persistence effect. It is not an exact-`t0` execution claim.

## 4. Final primary endpoint

### Event/control-comparable coordinate

For an event or control anchor with anchor price `A`, direction sign `s` and source-session range `R` in GC ticks, define for executed prices inside horizon `H`:

`X(t) = s * (P(t) - A) / 0.10`

Include the anchor value zero when taking extrema:

- `M_H = max(0, sup_t X(t))`
- `Q_H = max(0, sup_t [-X(t)])`

Define normalized reaction balance:

`NRB_H = (M_H - Q_H) / R`

### Sole primary endpoint

For event `e` and its `K=5` matched controls:

`DELTA_NRB15_e = NRB_W15_event_e - mean_k(NRB_W15_control_e,k)`

The sole primary endpoint is the date-cluster average effect of `DELTA_NRB15`.

This continuous endpoint measures whether post-contact-minute excursion is more asymmetric in the away direction than at matched ordinary market moments. It does not require intrabar ordering.

### Secondary/descriptive endpoints

Secondary:

- raw-tick `M_H`, `Q_H` and `M_H-Q_H`;
- normalized and raw `END_SIGNED_H = s*(P_endpoint-A)/0.10`;
- W5, W60 and SC versions of the primary endpoint;
- level-centric metrics measured from `L` rather than `A0`;
- unsigned outputs for undefined approach.

Descriptive only:

- `R0` exact residual-minute excursions;
- all thresholded rejection/acceptance labels;
- any order-dependent first-hit, stop/target or retest-count metric.

### Normalizer decision

The completed source-session high-low range is an acceptable causal normalizer **only if** a zero-outcome provenance QA proves for every analyzed event and control session that it:

- comes from the same raw source instrument;
- covers the canonical completed source session;
- was fully known before J+1;
- is positive and finite;
- was not reconstructed from continuous, adjusted or XAU/CFD data.

If that QA fails, execution must stop and v1 must be amended before outcomes are computed. No outcome-dependent fallback normalizer is permitted.

## 5. Matched-control design

### Decision

M1 matched persistence controls are scientifically sufficient for the DEV_RANK1 first pass **because the primary estimand begins at `a0`, after the contact minute**. They are not sufficient to validate `R0` exact intraminute microstructure, which remains descriptive.

### Control population

Control candidates are completed M1 minute closes from the already-owned raw-contract J+1 sessions belonging to the same 92 usable DEV_RANK1 source/retest blocks.

For treated event `e`, a control anchor must:

- come from another source/retest date, never the treated date;
- be in the same calendar year as `e`;
- have a valid completed anchor minute, a complete causal pre-anchor 30-minute window and a complete W15 window before canonical session close;
- lie outside `±60` wall-clock minutes of every known exact native contact on that control date;
- use the raw contract belonging to that control block;
- have a defined pseudo-approach side.

### Control anchor time and price

- anchor time = end of the selected control minute;
- anchor price = its M1 close, the last executed price in that minute.

### Pseudo-approach rule

Starting immediately before the control anchor, scan completed M1 closes backward for at most 30 minutes and use the latest close strictly different from the anchor close:

- prior close below anchor close: pseudo `APPROACH_FROM_BELOW`, `s=-1`;
- prior close above anchor close: pseudo `APPROACH_FROM_ABOVE`, `s=+1`;
- no different close: candidate ineligible.

A control must have the same approach label/sign as its treated event.

### Matching variables and calipers

Exact constraints:

- same year;
- same canonical 30-minute minute-of-session bin;
- same approach sign;
- source-session range ratio between 0.5 and 2.0;
- causal pre-anchor 30-minute executed-price range ratio between 0.5 and 2.0.

Nearest-neighbor ranking variables, all causal:

1. absolute log ratio of pre-anchor 30-minute ranges;
2. absolute log ratio of source-session ranges;
3. absolute difference in pre-anchor 5-minute signed move, each normalized by its source-session range;
4. absolute minute-of-session difference;
5. control timestamp ascending.

### Number and date restrictions

- `K = 5` controls per treated event.
- The five controls must come from five distinct control dates.
- Controls from the treated date are prohibited.
- No caliper may be relaxed after outcomes are visible.
- An event with fewer than five eligible controls is `CONTROL_UNMATCHED` and excluded from the controlled primary analysis, but retained in descriptive output.

### Deterministic construction

For each treated event and each eligible control date, select that date’s best anchor by the lexicographic ranking above. Rank those date representatives by the same tuple and retain the first five. Stable final tie-break is `(control_date, anchor_minute_utc, source_instrument_id)` ascending.

Before any reaction outcome extraction, publish and hash:

1. the full outcome-free control-candidate universe;
2. the five-control matched-set manifest;
3. a support QA by event, date, year and matching caliper.

### Dependence

Control dates may recur across different treated events, so inference must resample full date clusters and reapply the frozen matching algorithm; independent row-level standard errors are prohibited.

### Exact-tape controls

Exact pseudo-event tape is not required for Track-A first pass. It would become mandatory only if a later preregistered study makes `R0`, exact first-hit order or exact intraminute execution a confirmatory endpoint. Such a study requires a deterministic metadata quote and separate authorization.

## 6. Inference / dependence

### Cluster unit

The cluster is the source/retest trading date. Levels and overlapping windows within a date are dependent.

### Estimator

1. Compute `DELTA_NRB15_e` for every matched event.
2. Average event differences within each treated date with equal weight across that date’s contacted levels, producing `DELTA_date`.
3. The primary effect estimate is the unweighted mean of `DELTA_date` across eligible treated dates.

This gives each date equal primary weight, regardless of whether one or four native levels contacted.

Report event-level and type-level Ns, but do not use them as independent inferential observations. Date-level median and IQR are secondary robust summaries.

### Confidence interval

Use 20,000 bootstrap replicates of the full 92-date panel:

- resample source/retest date clusters with replacement;
- rerun the frozen matching algorithm inside each replicate using only causal covariates;
- recompute event, treated-date and aggregate estimates;
- replace invalid replicates until 20,000 valid replicates are obtained;
- a valid replicate must retain at least 80% of the original matched treated-date count.

Use a 95% percentile bootstrap CI. Fixed RNG seed: `20260819`.

As a sensitivity check, perform 50,000 Rademacher sign-flip draws on the original treated-date `DELTA_date` values, seed `20260820`; report a two-sided randomization p-value. The bootstrap CI, not the p-value alone, governs promotion.

### Overlapping windows

Retain all preregistered events. Average within date before inference; do not delete a level because its window overlaps another native-level event. Overlap counts are QA/descriptive fields.

## 7. Multiplicity

### Confirmatory result

There is exactly one confirmatory test in DEV_RANK1 Track A:

- all native level families pooled;
- W15;
- `DELTA_NRB15`;
- date-cluster estimator defined above.

### Secondary inferential families

1. Type-specific W15 effects for POC, VAH, VAL and VWAP: Holm correction across four tests.
2. Aggregate endpoint at W5, W60 and SC: Holm correction across three tests.

### Descriptive only

- all type-by-horizon interactions;
- R0;
- thresholded labels;
- named Asia/London/US buckets;
- best-looking time-of-day, year, approach-side or volatility slices;
- all XAUUSD economic mappings.

No DEV_RANK2 promotion may be based on a secondary or post-hoc slice if the aggregate primary gate fails.

## 8. Promotion gate to DEV_RANK2

Before any outcome is computed, DEV_RANK2 may open only if **all** conditions below hold.

### A. Support and control quality

- at least 160 matched events with defined approach;
- at least 60 treated source/retest date clusters;
- at least 5 treated date clusters in every year 2011–2018;
- at least 85% of all defined-approach contacts receive all five controls;
- no year has a full-control match rate below 75%.

Failure here is `STOP_AND_REPAIR_DESIGN`, not evidence of market NO_GO. No reaction result may be interpreted until support is repaired and a revised protocol is frozen.

### B. Primary effect and uncertainty

On the frozen primary estimator:

- point estimate `theta_NRB15 >= 0.02` source-session-range units;
- lower bound of the two-sided 95% date-cluster bootstrap CI is strictly greater than zero;
- corresponding date-weighted raw reaction-balance difference is at least `+2.0` GC ticks.

### C. Year stability

- at least 6 of 8 fixed yearly point estimates are positive;
- every leave-one-year-out aggregate estimate is positive;
- no single year contributes more than 35% of the sum of absolute yearly aggregate contributions.

### D. Level-family robustness

- at least 3 of 4 fixed family point estimates are positive;
- every leave-one-family-out aggregate estimate is positive;
- no single family contributes more than 50% of the sum of absolute family contributions.

### E. Decision rule

- All A–D pass: `OPEN_DEV_RANK2_NATIVE_REACTION`.
- Data/support A fails: `STOP_AND_REPAIR_DESIGN`, with no outcome interpretation.
- A passes but any B–D criterion fails: `NO_GO_DEV_RANK2_NATIVE_REACTION`.

No rescue is allowed by selecting the best family, horizon, year, session bucket, approach side or threshold after the primary gate fails.

## 9. Need for additional market data

`NO_NEW_DATA_FOR_TRACK_A_FIRST_PASS`

The primary and secondary W5/W15/W60/SC estimands use already-owned M1 after a completed anchor minute. Existing exact tape is used only for exact `t0`, causal approach where available and descriptive R0.

No market-data API quote or purchase is authorized by this recommendation.

## 10. Track-B lifetime recommendation

### Timing

Detailed Track-B acquisition/execution should be designed after the Track-A DEV_RANK1 decision, to avoid expanding scope before the immediate reaction hypothesis is resolved. The following skeleton is fixed now so Track-A outcomes cannot choose a favorable lifetime rule.

### Primary lifetime population and horizon

- population: the 130 J+1 no-contact levels;
- first-contact search: J+2 through J+5 inclusive;
- level expires untouched at canonical close of J+5.

J+5 is a fixed one-trading-week horizon. It may not be extended because later results look favorable.

### Raw-contract/roll rule

- retain the original raw `source_instrument_id` and original absolute `contact_tick_price`;
- no transfer to another expiry;
- no continuous, back-adjusted or spread-transposed substitute;
- right-censor at the earlier of J+5 close or the source contract’s exchange-defined last-trade time;
- a session with unavailable raw source-contract data is missing/censored, not `NO_CONTACT`.

A transferred-expiry hypothesis would be a separate experiment requiring a causal mapping frozen before later-contact outcomes and a new data quote.

### Expiration/invalidation

No price-path invalidation rule is used in the primary lifetime study. The only primary exits are exact first contact, fixed J+5 expiration, exchange last-trade censoring or data unavailability censoring.

### Later retests

A first exact contact consumes the level for the primary lifetime analysis. Second and later retests are a separate hypothesis and must not be pooled with first contacts.

Track B may not repair, relabel or replace the J+1 Track-A result.

## 11. Hidden-bias audit

### Lookahead

PASS with required anchor clarification. `L`, source instrument and J+1 eligibility are fixed before J+1; `t0` is exact. The primary analysis begins only after the completed contact minute, so it must be described as post-contact-minute reaction, not an entry available at `t0`.

### Intrabar ordering ambiguity

PASS if v1 preserves the prohibition on order-dependent M1 claims. High/low extrema are permitted; first-hit order, target/stop order and rejection-before-failure are forbidden without exact tape.

### Contract roll / survivorship

PASS for Track A under same raw instrument. Track B must use the fixed same-contract/right-censor rule above. Silent expiry transfer is prohibited.

### Contact selection bias and conditioning on contact

Track A estimates a conditional effect among exact J+1 contacts only. It cannot be described as the unconditional value of all generated levels. The 130 noncontacts are not zero outcomes. Contact incidence and conditional reaction must remain separate.

### Multiple testing

PASS only under the single primary and Holm-controlled secondary families in this memo. Best-slice promotion is prohibited.

### Clustered dependence

PASS only with treated-date aggregation and date-cluster resampling. Independent level-row inference is invalid.

### Time-of-day confounding

Addressed by same 30-minute minute-of-session bin matching. Named session buckets remain descriptive.

### Volatility confounding

Addressed by source-range and causal pre-anchor 30-minute range calipers plus normalization. Provenance QA remains mandatory.

### Outcome-dependent data acquisition

The complete control universe and matched-set manifest must be frozen and hashed before reaction extraction. Any exact-control acquisition would require a separate metadata quote and authorization.

### Leakage from prior XAU/CFD work

No XAUUSD/CFD price, prior POI result, prior entry model or win-rate target may define, filter, rank or reinterpret native COMEX events. The existing-POI B1/B2 NO_GO path remains separate.

### Additional hidden risks

- `APPROACH_UNDEFINED` missingness must be reported by year/type/time, without outcome-based imputation.
- Contact acquisition stage is QA metadata only and may not become a post-hoc filter.
- Control-support exclusions must be finalized before outcomes and reported transparently.
- The causal normalizer provenance must be audited without reading post-contact prices.

## 12. Exact edits for final v1

Apply these changes to produce `COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_v1.md`:

1. Change status to `FROZEN — OUTCOME EXTRACTION AUTHORIZED ONLY AFTER ZERO-OUTCOME MANIFEST QA`.
2. Preserve the 238-event first-contact population and exact `t0` definition.
3. Clarify the approach fallback as the latest prior completed J+1 close different from `L`, searched back to session open.
4. Add `a0` and `A0` as the completed contact-minute primary-analysis anchor/time and price.
5. Replace B1/B5/B15/B30/B60 with R0, W5, W15, W60 and SC; designate W15 primary and use fixed wall-clock windows.
6. State that R0 is exact descriptive only and cannot support the primary matched-control claim.
7. Add the algebraic `NRB_H`, `DELTA_NRB15` and date-cluster primary estimator from this memo.
8. Retain source-session range normalization only after the specified zero-outcome same-raw-instrument provenance QA; otherwise stop before outcomes.
9. Insert the complete M1 control-universe, exclusion, matching, K=5, distinct-date, caliper and tie-break rules.
10. Require publication and SHA-256 binding of the control-candidate universe, matched-set manifest and support QA before any reaction endpoint is computed.
11. Replace row-level/unspecified inference with equal-weight treated-date aggregation, 20,000 date-cluster bootstrap replicates and the fixed seeds in this memo.
12. Freeze the single aggregate W15 primary; apply Holm correction to the two secondary families; make all other slices descriptive.
13. Insert the exact DEV_RANK2 support/effect/CI/year/family promotion gate.
14. Set Track-A data recommendation to `NO_NEW_DATA_FOR_TRACK_A_FIRST_PASS`.
15. Preserve Track B separately with the fixed J+2–J+5, same-original-contract, no-transfer, right-censor and first-contact-consumes-level rules.
16. Restate that no threshold search, entry simulation, XAUUSD translation or reaction result may occur before v1 plus the zero-outcome manifests are committed and hashed.

Only after those edits and zero-outcome control/provenance QA pass may the Track-A extraction code be run.