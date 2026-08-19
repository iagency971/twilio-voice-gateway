# COMEX DEV_RANK1 — Native reaction protocol v1

Date: 2026-08-19  
Branch: `agent/xau-comex-acquisition-plan`  
Status: **FROZEN — OUTCOME EXTRACTION AUTHORIZED ONLY AFTER FINAL ZERO-OUTCOME MANIFEST/FREEZE QA**

Canonical methodological authorities:

- `PRO_DECISION_MEMO_COMEX_NATIVE_REACTION_PROTOCOL_2026-08-19.md`
- `PRO_DECISION_MEMO_COMEX_NATIVE_REACTION_CONTROL_SUPPORT_REPAIR_2026-08-19.md`
- `CHECKPOINT_COMEX_NATIVE_N2_EXACT_CONTACT_COMPLETE_2026-08-19.md`

This document freezes Track A before any post-anchor reaction outcome is opened. No W5/W15/W60/SC result, NRB, MFE/MAE, terminal displacement, family/year/session reaction ranking, profitability metric, or XAUUSD mapping may be computed until the final pre-outcome freeze defined in Section 14 passes.

## 1. Scientific question and population

Track A asks, conditional on a confirmed exact native COMEX contact during the frozen next eligible GC auction session J+1, whether post-contact-minute price behavior differs from matched ordinary GC reference anchors.

Frozen population:

- 368 native source levels = 92 POC / 92 VAH / 92 VAL / 92 VWAP;
- 238 confirmed first exact raw-GC contacts in J+1;
- 130 J+1 no-contacts;
- 0 unresolved;
- final 368-status SHA-256: `8a825b0bc1deba51959b78ab6e62206fe49232e76329558e83949bf6d3d4151a`.

The 130 J+1 no-contacts are not zero-reaction observations and are excluded from Track-A reaction estimands. Contact incidence and conditional reaction remain separate quantities.

## 2. Exact event definition

For each of the 238 contacted levels:

- `L` = frozen executable `contact_tick_price` on the GC 0.10 tick;
- `source_instrument_id` = the same raw GC instrument that created the level;
- `t0` = first chronological raw trade in frozen J+1 on that same raw instrument with executed price exactly equal to `L`;
- only the first exact contact is a Track-A primary event;
- later same-level retests are not additional primary events.

Continuous GC, another expiry, adjusted/spread-transposed prices, XAUUSD/CFD prices, or M1 high/low crossing are prohibited substitutes for exact event definition.

## 3. Causal approach-side rule

Approach is defined mechanically and outcome-blind:

1. Search already-owned exact raw trades strictly before `t0` in the downloaded contact interval.
2. Use the latest raw trade strictly different from `L`.
3. Price below `L` => `APPROACH_FROM_BELOW`, `away_sign=-1`.
4. Price above `L` => `APPROACH_FROM_ABOVE`, `away_sign=+1`.
5. If unavailable, search completed J+1 M1 closes strictly before the contact minute, backward to the frozen J+1 session open, and use the latest close strictly different from `L`.
6. If still unavailable, label `APPROACH_UNDEFINED`.

`APPROACH_UNDEFINED` remains in descriptive inventory but is excluded from signed primary/control estimands. No side may be imputed.

## 4. Event time versus primary-analysis anchor

Define:

- `m0 = floor_UTC_minute(t0)`;
- `a0 = m0 + 1 minute`;
- `A0` = last executed raw-GC price in `[m0,a0)`, equivalently the M1 close of the contact minute.

`t0` is the scientific exact-contact time. `a0/A0` is the control-comparable post-contact-minute analysis anchor.

### Hard matching cutoff

No treated-event matching covariate may use any OHLC/price value from `[m0,a0)`, `A0`, or any later value.

All mature treated local matching variables terminate strictly before `m0`. Exact `t0` and the pre-`t0` approach determination are event-definition information only and may not carry post-contact price information into matching.

Every matched set previously produced in `xau-final-results/comex_dev_rank1_native_reaction_v1_preoutcome/` is permanently blocked/superseded and non-executable.

## 5. Fixed horizons

All control-comparable horizons begin at `a0` and are fixed wall-clock windows:

- `R0`: `[t0,a0)` exact already-owned residual contact-minute tape — descriptive only;
- `W5`: `[a0,a0+5 minutes)`;
- `W15`: `[a0,a0+15 minutes)` — **sole primary horizon**;
- `W60`: `[a0,a0+60 minutes)`;
- `SC`: `[a0, frozen canonical J+1 close)`.

Do not define horizons as the next N observed bars. A no-trade minute does not extend a horizon and contributes no new executed-price extreme. Endpoint price is the last executed price at or before the endpoint, beginning with `A0`. If a requested fixed endpoint lies after J+1 close, that horizon is censored/missing rather than shortened, extended, or imputed.

Store actual elapsed seconds and traded/no-trade-minute counts as QA fields when outcomes are eventually computed.

## 6. Primary endpoint and secondary status

For an event or reference anchor with anchor price `A`, direction sign `s`, and completed source-session range `R` in GC ticks, define for executed prices in horizon `H`:

`X(t) = s * (P(t) - A) / 0.10`

Include anchor value zero when taking extrema:

- `M_H = max(0, sup_t X(t))`
- `Q_H = max(0, sup_t [-X(t)])`
- `NRB_H = (M_H - Q_H) / R`

For treated event `e` with K=5 matched reference anchors:

`DELTA_NRB15_e = NRB_W15_event_e - mean_k(NRB_W15_control_e,k)`

The sole confirmatory endpoint is the equal-weight treated-date aggregate of `DELTA_NRB15` across all native families pooled.

Secondary inferential outputs:

- POC / VAH / VAL / VWAP W15 effects, Holm across four tests;
- aggregate W5 / W60 / SC effects, Holm across three tests.

Descriptive only:

- `R0` exact residual-minute behavior;
- raw `M_H`, `Q_H`, `M_H-Q_H`, terminal signed displacement;
- level-centric metrics from `L`;
- type-by-horizon interactions;
- year, approach, time-of-day and named Asia/London/US buckets;
- thresholded rejection/acceptance labels;
- any XAUUSD economic mapping.

Order-dependent first-hit/TP-SL/rejection-before-failure claims are prohibited from M1 bars without separately authorized exact tape.

## 7. Source-session normalizer

The completed source-session high-low range in GC ticks is the frozen normalizer. It is admissible only when zero-outcome provenance proves that it:

- comes from the same raw source instrument;
- covers the frozen canonical completed source session;
- is fully known before J+1;
- is positive and finite;
- is not reconstructed from adjusted continuous GC, another expiry, or XAUUSD/CFD.

Failure of normalizer provenance is a pre-outcome STOP. No outcome-dependent fallback normalizer is permitted.

## 8. Final matched-reference control population

The final control universe contains two allowed origins.

### 8.1 Canonical N1 blocks

Retain the 92 already-owned canonical raw-contract source→J+1 M1 blocks using their frozen source raw instrument and frozen next eligible GC auction session.

### 8.2 Expanded already-owned stable-IID context

Additional reference blocks may come from the already-owned `GC.n.0` OHLCV-1m context only when all conditions hold:

1. source session J and its canonical next GC session J+1 are selected independently of price/outcome;
2. J contains exactly one constant underlying `instrument_id`;
3. J+1 contains exactly one constant underlying `instrument_id`;
4. the same `instrument_id` is present across J and J+1;
5. values are absolute vendor unadjusted OHLCV; no back adjustment or spread transposition;
6. source and next dates are not reserved to DEV_RANK2, CONFIRM/RETRO_CONFIRM, LOCKED_COMEX_TEST, or another frozen non-DEV_RANK1 allocation;
7. the original 92 native source dates are not duplicated through the generic source path;
8. actual source/next dates, session bounds, IID, origin artifact/file hash, coverage and adjustment status are retained;
9. no new market-data API call, download or purchase occurs.

The directly testable stable-overlap parity requirement is 85/85 exact OHLCV parity between context and canonical raw N1 blocks. Any parity failure closes execution.

### Matched-reference interpretation

Generic anchors are **matched reference anchors**, not proven treatment-free counterfactuals, because a complete exact-contact registry for every possible native level does not exist on generic dates. Every generic candidate must carry `native_contact_exclusion_status`. The ±60-minute exclusion is applied around every exact native contact actually present in the frozen registry. A null event-minus-reference result may not be overinterpreted as proof that no absolute native-level reaction exists if latent-contact contamination remains possible.

## 9. Canonical adjacency and contact exclusion

Every control block must carry a frozen `source_research_date -> eligible_next_research_date` adjacency and exact source/next canonical session bounds. A later convenient session may never substitute for the canonical next session.

For candidate anchors on a control J+1 date:

- exclude anchors within `±60` wall-clock minutes of every exact native `t0` known on that control date in the frozen contact registry;
- for generic dates without a complete native-contact registry, retain the explicit partial-registry status described above.

## 10. Mature versus early causal matching branches

Branch is determined only from frozen treated `anchor_minute_of_session` before outcomes.

### 10.1 Mature branch — minute >= 30

Treated covariates:

- full completed source-session range;
- J+1 local 30-minute executed-price range ending strictly before `m0`;
- signed pre-5-minute move ending strictly before `m0`, normalized by source-session range.

Control covariates are computed symmetrically from completed M1 information strictly before the selected control anchor minute. The selected control minute's anchor close may define the reference anchor and pseudo-approach, but its OHLC path is not part of local pre30/pre5 matching covariates.

Required calipers:

- source-session range ratio in `[0.5,2.0]`;
- local pre30 range ratio in `[0.5,2.0]`.

### 10.2 Early branch — minute < 30

J+1 local-pre30 and pre5 are structurally unavailable and are not estimated.

Use instead:

- full completed source-session range;
- executed-price high-low range of the final 30 wall-clock minutes of completed source session J, on the same raw instrument, ending at the frozen canonical source-session close and fully known before J+1.

Required calipers:

- source-session range ratio in `[0.5,2.0]`;
- source-final30 range ratio in `[0.5,2.0]`.

The source-final30 fallback is not allowed for mature events merely because it improves support.

### Missing early fallback covariate

If source-final30 is missing/nonpositive where the early branch is required:

- label `FALLBACK_COVARIATE_MISSING_SOURCE_LAST30`;
- no imputation;
- no alternative J window;
- no J+1/contact-minute/post-contact/adjusted-continuous/XAUUSD/other-contract substitute;
- retain event in the 238-contact descriptive inventory and in the defined-approach support denominator;
- exclude it from the controlled primary estimator as ineligible/unmatched for that explicit reason.

The final provenance must reconcile to the dedicated zero QA: 92 source sessions, 91 positive source-final30 windows, one missing window, zero flat-present windows, sole missing source date `2013-12-25`, affecting exactly one defined-approach early event. Any discrepancy closes W15 until resolved outcome-blind.

## 11. Pseudo-approach and deterministic K=5 rule

### Pseudo-approach

Use `PRIOR_CLOSE_ONLY` exclusively.

For a completed control anchor minute with anchor price equal to its M1 close:

1. scan completed M1 closes strictly before the anchor backward for at most 30 wall-clock minutes;
2. use the latest close strictly different from the anchor close;
3. below anchor => `APPROACH_FROM_BELOW`, `s=-1`;
4. above anchor => `APPROACH_FROM_ABOVE`, `s=+1`;
5. no different close => candidate ineligible.

`BAR_OPEN_FALLBACK` is prohibited.

### Common exact constraints

For treated event `e`, every candidate must:

- come from a different source date;
- have the same exact **source year** 2011–2018;
- be in the same canonical 30-minute minute-of-session bin;
- have the same approach sign;
- come from a valid block under Sections 8–9;
- have W15 entirely before its frozen next-session close;
- pass the source-session range caliper;
- pass the branch-specific volatility caliper;
- satisfy the ±60-minute known-contact exclusion.

### Mature lexicographic ranking

1. `abs(log(control_pre30_range / treated_pre30_range))`;
2. `abs(log(control_source_range / treated_source_range))`;
3. absolute distance in normalized pre5 signed move;
4. absolute minute-of-session distance;
5. control anchor timestamp ascending;
6. control source date ascending;
7. control next-session date ascending;
8. `source_instrument_id` ascending;
9. stable candidate UID ascending.

### Early lexicographic ranking

1. `abs(log(control_source_final30_range / treated_source_final30_range))`;
2. `abs(log(control_source_range / treated_source_range))`;
3. absolute minute-of-session distance;
4. control anchor timestamp ascending;
5. control source date ascending;
6. control next-session date ascending;
7. `source_instrument_id` ascending;
8. stable candidate UID ascending.

The early branch has no `d_move` matching dimension. Store it as `NOT_APPLICABLE`; a numeric compatibility zero is allowed only if a hard assertion proves it is constant and it is excluded from the sort tuple.

### K=5 selection

- first select the highest-ranked representative within each control source date;
- then rank those date representatives with the same branch tuple;
- retain the first `K=5` distinct control source dates;
- fewer than five qualifying dates => `CONTROL_UNMATCHED`;
- no caliper, year, bin, sign, K, date-distinctness or exclusion rule may be relaxed after any outcome becomes visible.

Control dates may recur across different treated events. Final pre-outcome QA must report reuse counts/concentration and source/date overlaps.

## 12. Support gate

Before any reaction outcome is interpreted, final regenerated manifests must satisfy all five frozen support conditions:

- >=160 matched defined-approach events;
- >=60 matched treated source/retest dates;
- >=5 matched treated dates in every source year 2011–2018;
- >=85% of all defined-approach contacts receive all five controls;
- no source year has a full K=5 match rate below 75%.

Failure => `STOP_AND_REPAIR_DESIGN`; no reaction performance may be opened/interpreted.

The latest feasibility audit passed these criteria outcome-blind, but feasibility counts are not executable until the final regenerated universe and matched manifest independently reproduce a passing gate.

## 13. Inference, multiplicity and DEV_RANK2 promotion

### Primary aggregation

1. Compute `DELTA_NRB15_e` for every final K=5 matched event.
2. Average event differences within each treated source/retest date with equal weight across that date's contacted levels, producing `DELTA_date`.
3. Primary effect = unweighted mean of `DELTA_date` across eligible treated dates.

Individual levels are not independent inferential units.

### Bootstrap

- 20,000 valid date-cluster bootstrap replicates of the full 92-date panel;
- resample source/retest dates with replacement;
- rerun the frozen matching algorithm inside each replicate using causal covariates only;
- replace invalid replicates until 20,000 valid replicates exist;
- valid replicate must retain >=80% of the original matched treated-date count;
- 95% percentile CI;
- RNG seed `20260819`.

Sensitivity:

- 50,000 Rademacher sign-flip draws on original treated-date `DELTA_date` values;
- two-sided randomization p-value;
- seed `20260820`.

### Multiplicity

- sole confirmatory result: pooled native families / W15 / `DELTA_NRB15` / date-cluster estimator;
- Holm across four family-specific W15 tests;
- separately Holm across aggregate W5/W60/SC tests;
- all other slices descriptive.

### DEV_RANK2 gate

A. Support: all Section 12 criteria pass.

B. Primary effect and uncertainty:

- `theta_NRB15 >= 0.02` source-session-range units;
- lower bound of two-sided 95% date-cluster bootstrap CI > 0;
- corresponding date-weighted raw reaction-balance difference >= `+2.0` GC ticks.

C. Year stability:

- >=6 of 8 yearly point estimates positive;
- every leave-one-year-out aggregate positive;
- no year >35% of sum of absolute yearly aggregate contributions.

D. Family robustness:

- >=3 of 4 family point estimates positive;
- every leave-one-family-out aggregate positive;
- no family >50% of sum of absolute family contributions.

Decision:

- A–D pass => `OPEN_DEV_RANK2_NATIVE_REACTION`;
- A fails => `STOP_AND_REPAIR_DESIGN` with no outcome interpretation;
- A passes but B/C/D fails => `NO_GO_DEV_RANK2_NATIVE_REACTION`.

No rescue by best family, horizon, year, session, approach or threshold is allowed.

## 14. Mandatory final pre-outcome freeze

Before any W15/W5/W60/SC, NRB, MFE/MAE or other post-anchor result is computed, the branch must contain and SHA-256 bind:

1. this final protocol v1;
2. frozen 368-level contact-status registry and canonical SHA;
3. final 238-event causal context with approach provenance, `t0/m0/a0`, source year, session bin, branch, source range, branch-specific covariates, W15 availability and exclusion reason;
4. unified 92-session source-range/source-final30 raw provenance with file hashes, exact bounds, record counts, min/max/range, missing/flat flags and reconciliation against dedicated zero QA;
5. frozen canonical source→next-session adjacency/session-boundary manifest;
6. frozen 261-date non-DEV_RANK1 reserved exclusion manifest;
7. control-block provenance for canonical and expanded origins, with stable-IID/adjustment/coverage/artifact hashes and exclusion flags;
8. 85/85 context-versus-raw-N1 parity QA;
9. complete outcome-free `PRIOR_CLOSE_ONLY` control-candidate universe;
10. deterministic final K=5 matched-control manifest;
11. event/date/year support QA plus control-date reuse/concentration diagnostics;
12. machine-readable hard guard proving all of:
    - `post_contact_values_used_for_matching=false`;
    - `post_anchor_outcomes_read=false`;
    - `reaction_outcomes_computed=false`;
    - `mfe_mae_computed=false`;
    - `market_data_api_called=false`;
    - `market_data_download_performed=false`;
13. SHA-256 freeze manifest covering protocol, code/workflow, source inputs and all generated pre-outcome artifacts, together with the generation Git commit SHA;
14. final checkpoint declaring whether the regenerated support gate is `SUPPORT_GATE_REPAIRED_AND_PASS` or `STOP_AND_REPAIR_DESIGN` and explicitly keeping W15 closed until this freeze is complete.

Only after every item passes may Track-A reaction extraction be executed.

## 15. Data and locked-state policy

`NO_NEW_DATA_REQUIRED_FOR_REPAIRED_TRACK_A`

No new Databento quote, API call, download or spend is authorized for this Track-A first pass.

Until the Section 14 freeze passes:

- W5/W15/W60/SC outcomes: CLOSED;
- NRB / MFE / MAE / terminal displacement: CLOSED;
- DEV_RANK2: CLOSED;
- RETRO_CONFIRM / CONFIRM: CLOSED;
- LOCKED_COMEX_TEST: CLOSED;
- XAUUSD economic mapping: CLOSED;
- Track B J+2+: CLOSED.

Support feasibility is not a reaction edge, win rate, or tradable expectancy.

## 16. Track B preserved separately

After the Track-A DEV_RANK1 decision, Track B may study the 130 J+1 non-contact levels with this already-frozen skeleton:

- first-contact search J+2 through J+5 inclusive;
- untouched expiry at canonical J+5 close;
- same original `source_instrument_id` and absolute `contact_tick_price`;
- no transfer to another expiry;
- no continuous/back-adjusted/spread-transposed substitute;
- right-censor at earlier of J+5 close or exchange-defined last-trade time;
- raw data unavailable => missing/censored, not `NO_CONTACT`;
- first exact contact consumes the level for the primary lifetime study;
- later retests are a separate hypothesis.

Track B may not repair, relabel or replace the Track-A J+1 result.
