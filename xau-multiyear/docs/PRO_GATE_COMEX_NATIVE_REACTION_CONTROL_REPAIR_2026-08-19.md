# PRO GATE — COMEX native reaction matched-control repair

Date: 2026-08-19  
Branch: `agent/xau-comex-acquisition-plan`  
Purpose: second decisive methodological audit, outcome-blind, after discovering and repairing a flaw in the first matched-control construction

## Instruction to Pro

Act as a skeptical quantitative-research reviewer. This is a **repair review only**.

Do **not** compute, inspect, request, infer, or rank any reaction outcome, MFE/MAE, W5/W15/W60/SC endpoint, level-family result, time-of-day result, profitability metric, entry result or XAUUSD mapping.

No reaction outcome has been computed under the repaired design. No additional market-data purchase is authorized.

Your job is to decide whether the repaired matched-control design below is scientifically valid enough to freeze the final Track-A preregistration, or whether it still needs a methodological redesign.

## Canonical documents to read first

Read these documents in full:

1. `xau-multiyear/docs/PRO_DECISION_MEMO_COMEX_NATIVE_REACTION_PROTOCOL_2026-08-19.md`
2. `xau-multiyear/docs/COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_PREPRO_v0_9.md`
3. `xau-multiyear/docs/CHECKPOINT_COMEX_NATIVE_N2_EXACT_CONTACT_COMPLETE_2026-08-19.md`
4. `xau-multiyear/docs/COMEX_DEV_RANK1_NATIVE_RETEST_ACQUISITION_FREEZE_v1.md`
5. `xau-multiyear/docs/COMEX_DEV_RANK1_NATIVE_N2_SEQUENTIAL_ACQUISITION_FREEZE_v1.md`

Then read the outcome-blind repair evidence listed below.

## Facts that remain fixed and are not under review

- 92 usable native raw-GC source sessions.
- 368 native levels = 92 POC / 92 VAH / 92 VAL / 92 VWAP.
- 238 exact contacts during the frozen full next eligible GC auction session J+1.
- 130 J+1 no-contacts.
- contact incidence 64.67391304347826%, which is **not** a win rate or reaction edge.
- final 368 contact-status SHA-256: `8a825b0bc1deba51959b78ab6e62206fe49232e76329558e83949bf6d3d4151a`.
- exact-contact event `t0` remains the first chronological raw trade exactly at the frozen GC tick on the same source `instrument_id`.
- first contact only for Track A.
- no US-only filter; the experiment uses the full J+1 GC auction session.
- existing-POI B1/B2 remains closed NO_GO.
- DEV_RANK2 / RETRO_CONFIRM / LOCKED_COMEX_TEST remain closed.
- no new market-data spend is authorized.

## Original Pro decisions that should remain unchanged unless the repair logically forces a change

The first Pro review froze the intended reaction framework as follows:

- scientific event time `t0` = exact raw contact;
- `m0=floor_UTC_minute(t0)`;
- `a0=m0+1 minute` = completed contact-minute end;
- `A0` = contact-minute M1 close, used only as the start price of the control-comparable post-contact-minute endpoint;
- R0 exact residual contact minute = descriptive only;
- fixed wall-clock horizons W5, W15, W60 and session close from `a0`;
- W15 = sole primary horizon;
- primary event/control coordinate from anchor `A` and approach sign `s`;
- `M_H=max(0,sup X(t))`, `Q_H=max(0,sup -X(t))`;
- `NRB_H=(M_H-Q_H)/source_session_range`;
- primary event endpoint `DELTA_NRB15 = event NRB_W15 - mean(K matched controls NRB_W15)`;
- equal-weight treated-date aggregation;
- 20,000 date-cluster bootstrap, seed `20260819`;
- 50,000 Rademacher sign-flip sensitivity, seed `20260820`;
- sole confirmatory result = all native families pooled / W15 / DELTA_NRB15;
- Holm correction for four W15 family-specific secondaries and separately for W5/W60/SC aggregate secondaries;
- fixed DEV_RANK1 -> DEV_RANK2 support/effect/year/family gate from the first Pro memo;
- Track B remains separate and not opened.

Do not change these merely because another design could also be defensible. Change them only if the repaired control construction makes one of them invalid.

# Why a second Pro gate is necessary

## 1. The first implementation of the Pro control design is blocked

The first outcome-blind manifest construction produced:

- 238 exact-contact events;
- 235 with defined approach;
- 180 primary-eligible under the initial implementation;
- 100 with K=5 matches;
- 54 matched treated dates;
- 42.55% full-match rate.

This was a support failure, but a more important issue was then discovered by source-code audit:

> some local matching covariates for the treated event were computed through `a0`, thereby using the M1 high/low/close of the **contact minute** even though `t0` occurred inside that minute.

Consequently those covariates could contain price information **after the treatment/contact had already occurred**. That is post-treatment matching leakage.

The first matched-set manifest is therefore **BLOCKED / SUPERSEDED** and must never be used for reaction extraction.

No reaction outcome was computed or inspected from it.

## 2. Strict pre-contact reconstruction

The repaired event-local covariates terminate strictly at `m0`, the **start of the contact minute**.

The strict-precontact audit is canonical here:

- `xau-final-results/comex_dev_rank1_native_reaction_precontact_control_repair_v1/precontact_control_repair.json`
- `xau-final-results/comex_dev_rank1_native_reaction_precontact_control_repair_v1/treated_event_strict_precontact_context.csv`

Key outcome-blind facts:

- exact contacts: 238;
- defined approach: 235;
- defined contacts at minute-of-session 0: **27**;
- defined contacts in first 30 minutes: **54**;
- no post-contact values used for matching;
- no reaction outcomes computed;
- no market-data API call.

With the original Pro local-30m requirement made strictly causal, support becomes:

- 176 / 235 matched;
- 74 matched dates;
- 74.89% full-match rate;
- support gate fails.

A purely causal `session-open -> m0` available-range fallback for early events improves support to:

- 203 / 235 matched;
- 78 dates;
- 86.38% full-match rate;

but 2014 and 2015 remain below the frozen annual 75% full-match criterion. This is because many early events, especially minute-0 events, simply do not possess enough J+1 pre-contact local history.

The issue is therefore structural rather than outcome-related.

# Expanded zero-cost control pool

## Already-owned M1 context

The project already owns an M1 `GC.n.0` context artifact from approximately 2010-06-06 through 2019-01-01, acquired before this reaction study:

- artifact source run: `32179377819`;
- artifact name: `comex-dev-rank1-dual-n0_ohlcv_1m_context_20100606_20190101`.

This is not a new market-data acquisition.

The vendor M1 continuous records contain original/unadjusted prices and the actual mapped `instrument_id` for each bar.

For expanded controls, a generic source-date block is eligible only if:

1. the same underlying `instrument_id` is constant throughout source session J and next session J+1;
2. source J and next date J+1 are not explicitly reserved as non-DEV_RANK1 research dates;
3. the original 92 native source dates remain on their canonical raw/N1 implementation rather than being duplicated from the generic pool;
4. the source and control price are raw/unadjusted vendor prices, not back-adjusted or spread-transposed values.

Every date explicitly assigned to `DEV_RANK2`, `CONFIRM` or `LOCKED_TEST` in the frozen session registry is excluded from the expanded generic pool. This does **not** open those locked research blocks or inspect their outcomes.

Frozen session-registry counts are:

- DEV_RANK1: 96;
- DEV_RANK2: 96;
- CONFIRM: 95;
- LOCKED_TEST: 70.

Non-DEV_RANK1 reserved dates excluded from this generic control construction: **261**.

## Parity evidence

Where the already-owned `GC.n.0` context can be compared directly with the already-owned raw-contract N1 session block and the mapped `instrument_id` is constant, exact OHLCV parity is:

- stable same-instrument test blocks: **85**;
- exact parity blocks: **85 / 85**;
- failures: **0**.

Canonical feasibility evidence:

- `xau-final-results/comex_dev_rank1_native_reaction_expanded_control_feasibility_v1/expanded_control_feasibility.json`
- `xau-final-results/comex_dev_rank1_native_reaction_expanded_control_feasibility_v1/continuous_vs_raw_n1_parity.csv`

The expanded pool produced approximately 1,727 generic same-instrument control blocks in addition to the canonical 92 source blocks, without new data purchase.

# Preferred repair candidate — source-session final-30m fallback

## Rationale

For a mature contact occurring at least 30 minutes after the J+1 session open, retain the original Pro idea but make it strictly causal:

- local 30-minute executed-price range ending **strictly before `m0`**;
- causal pre-5-minute signed move ending strictly before `m0`;
- full completed source-session range;
- source year;
- same 30-minute minute-of-session bin;
- same approach sign;
- ±60-minute exclusion around exact native contacts on control date;
- source-range ratio 0.5–2;
- local pre30-range ratio 0.5–2;
- K=5 distinct control dates;
- deterministic tie-breaking as in the first Pro memo.

For an early contact with `minute_of_session < 30`, local 30-minute J+1 history is structurally unavailable. The proposed causal fallback is therefore:

> use the **executed-price high-low range of the final 30 wall-clock minutes of the completed source session J**, on the same raw source instrument that created the native level.

This source-final-30m range is fully known before J+1 begins and cannot contain reaction information from J+1.

For early-event/control matching, preserve:

- exact source year;
- same 30-minute minute-of-session bin;
- same approach sign;
- full source-session range ratio 0.5–2;
- source-final-30m range ratio 0.5–2;
- ±60-minute native-contact exclusion;
- K=5 distinct control dates;
- deterministic nearest-neighbor ordering using source-final-30m range distance, full source-range distance, minute distance and fixed timestamp/date/instrument tie-breaks.

For mature events, continue using strict pre-m0 J+1 local30/pre5 matching; source-final-30m is only the predefined fallback for `minute_of_session < 30`.

## Control pseudo-approach

Preferred repair keeps the **original Pro control pseudo-approach rule**:

- scan completed M1 closes backward for at most 30 minutes before the control anchor;
- latest close different from anchor close determines pseudo-approach;
- if none exists, that candidate control is ineligible.

This is called `PRIOR_CLOSE_ONLY` in the repair audit.

A diagnostic `BAR_OPEN_FALLBACK` was also examined, but it is **not needed** and should not be adopted unless Pro explicitly finds it superior for a substantive reason.

# Outcome-blind support of the preferred repair

The `source_last30` repair audit computed no reaction endpoint and made no market-data API call.

Under `PRIOR_CLOSE_ONLY`:

- defined-approach events: **235**;
- eligible events before the final missing-covariate QA: **234**;
- fully K=5 matched events: **226**;
- matched treated dates: **81**;
- full-match rate over defined-approach contacts: **96.17021276595744%**;
- >=160 matched events: PASS;
- >=60 treated dates: PASS;
- >=5 treated dates in every source year 2011–2018: PASS;
- >=85% full-match rate: PASS;
- every source year >=75% full-match rate: PASS.

The diagnostic `BAR_OPEN_FALLBACK` reached 234/235 but is unnecessary because `PRIOR_CLOSE_ONLY` already clears every frozen support criterion.

# Sole missing source-final-30m case

A dedicated raw-source QA was run because one of the 92 source-final-30m ranges was non-positive.

Canonical compact result:

- `xau-final-results/comex_dev_rank1_native_reaction_source_last30_zero_qa_v1/source_last30_zero_qa.json`

Origin audit:

- run `32263559201`;
- job `96101250568`;
- artifact `9352159692`;
- artifact digest `sha256:9ffe36231b805cf6e75b568ef35558e61ca9ae1a2894611401bc8799fa05433d`.

Exact QA facts:

- source sessions total: 92;
- source-final-30m positive: 91;
- non-positive: 1;
- **missing final-30m trade window: 1**;
- flat-but-present final-30m windows: 0;
- sole source date: **2013-12-25**;
- affected exact-contact events: **1**;
- affected contacts with defined approach: **1**.

Thus this is not a zero-volatility observation. There are simply no source raw trades in that final-30m wall-clock window.

## Proposed treatment of the missing fallback covariate

Do not impute it.

Do not use J+1 contact-minute or post-contact data as a substitute.

Do not choose another source-history window because it improves eventual outcomes.

Proposed deterministic label:

`FALLBACK_COVARIATE_MISSING_SOURCE_LAST30`

The event remains in the 238-event descriptive inventory and the contact-incidence population, but is **ineligible for the matched controlled primary estimator** because a preregistered pre-treatment matching covariate is missing.

This leaves the controlled support at the already-measured 226/235 defined-approach contacts, still comfortably above every frozen support requirement.

# Critical hidden-bias repair to validate

The final v1 must explicitly state:

1. **No treated-event matching covariate may use any OHLC value from the contact minute `[m0,a0)`** because `t0` lies inside that minute.
2. `A0`, the contact-minute close, remains allowed only as the primary outcome coordinate anchor from `a0` onward, as originally approved by Pro. It must not be used to select controls.
3. Mature-event local matching variables end strictly before `m0`.
4. Early-event fallback variables come entirely from source session J and therefore predate J+1.
5. Exact `t0` and the pre-`t0` approach determination remain event-definition information, not post-outcome selection.
6. The original first matched-set manifest is blocked forever and may not be reused.

# Specific decisions requested from Pro

Return a concise but decisive repair memo with the sections below.

## 1. Overall repair verdict

Choose exactly one:

- `APPROVE_REPAIR_AS_SPECIFIED`
- `APPROVE_REPAIR_WITH_REQUIRED_CHANGES`
- `STOP_AND_REDESIGN_CONTROLS`

## 2. Contact-minute leakage decision

Confirm whether the first manifest was correctly invalidated because treated local matching covariates could include `[t0,a0)` price information.

State the exact temporal cutoff for every treated local matching variable in final v1.

## 3. Early-contact volatility fallback

Approve or reject the following rule:

- if `minute_of_session >= 30`: match local volatility using J+1 pre-m0 30-minute executed-price range and pre-m0 pre5 signed move;
- if `minute_of_session < 30`: replace those unavailable local J+1 covariates with source-session J final-30m executed-price range, plus the already-approved full source-session range.

If rejected, specify one deterministic causal alternative that can handle minute-0 events without using post-contact information.

## 4. Missing `2013-12-25` fallback covariate

Approve or reject:

- no imputation;
- label `FALLBACK_COVARIATE_MISSING_SOURCE_LAST30`;
- retain event descriptively;
- exclude it from the matched controlled primary estimator.

If rejected, give the exact causal replacement rule now, before outcomes.

## 5. Expanded already-owned control pool

Decide whether the generic control dates built from the already-owned `GC.n.0` M1 context are scientifically acceptable under all of these safeguards:

- original/unadjusted vendor price;
- actual row `instrument_id` retained;
- same underlying `instrument_id` constant across source J and J+1;
- 85/85 exact raw-N1 parity on directly testable stable blocks;
- original 92 native source dates remain on canonical raw/N1 implementation;
- every date reserved to DEV_RANK2 / CONFIRM / LOCKED_TEST excluded as a generic source or next date;
- control data used only for covariates/outcomes of matched pseudo-events, never to reopen those locked research blocks or their native-level hypotheses;
- no new market-data purchase.

Choose one:

- `EXPANDED_POOL_APPROVED`
- `EXPANDED_POOL_APPROVED_WITH_CHANGES`
- `EXPANDED_POOL_REJECTED`

If rejected, state whether exact raw-contract M1 for additional neutral dates must instead be quoted/purchased before Track A.

## 6. Control pseudo-approach

Choose exactly one:

- retain `PRIOR_CLOSE_ONLY` from the original Pro memo;
- require a different rule.

The diagnostic `BAR_OPEN_FALLBACK` is **not proposed** because it is unnecessary for support.

## 7. Matching variables and deterministic ranking

Confirm or replace the final matching rules for:

### Mature events (`minute >= 30`)

- exact source year;
- same 30-minute session bin;
- same approach sign;
- source-session range ratio 0.5–2;
- strict pre-m0 J+1 local30 range ratio 0.5–2;
- K=5 distinct dates;
- ±60 native-contact exclusion;
- deterministic ranking by local30 distance, source-range distance, pre5 signed-move distance, minute distance, timestamp/date/instrument tie-break.

### Early events (`minute < 30`)

- exact source year;
- same 30-minute session bin;
- same approach sign;
- source-session range ratio 0.5–2;
- source-final-30m range ratio 0.5–2;
- K=5 distinct dates;
- ±60 native-contact exclusion;
- deterministic ranking by source-final30 distance, source-range distance, minute distance, timestamp/date/instrument tie-break.

No caliper may be relaxed after outcomes are visible.

## 8. Support-gate interpretation

Given the outcome-blind preferred-repair support:

- 226 K=5 matched defined-approach contacts;
- 81 treated dates;
- 96.17% full-match rate;
- every original support criterion passes;

confirm whether this is sufficient to proceed to reaction extraction once final manifests are rebuilt and hashed.

This section is about design support only, not reaction performance.

## 9. Reaffirm or amend the original primary/inference/promotion framework

Unless the control repair logically forces a change, explicitly reaffirm:

- W15 primary;
- DELTA_NRB15 primary;
- source-session-range normalization;
- date-level aggregation;
- 20k date bootstrap seed 20260819;
- 50k sign-flip seed 20260820;
- Holm secondary handling;
- DEV_RANK2 effect/year/family gate from the first Pro memo.

If any must change because of the repair, specify the exact replacement now, before outcomes.

## 10. Market-data decision

Choose exactly one:

- `NO_NEW_DATA_REQUIRED_FOR_REPAIRED_TRACK_A`
- `QUOTE_ADDITIONAL_RAW_CONTROL_DATA_BEFORE_EXECUTION`
- another exact recommendation.

No purchase is authorized by this review.

## 11. Exact edits to final v1

Provide a short implementable list of edits required to produce:

`xau-multiyear/docs/COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_v1.md`

The final v1 must not be frozen and no reaction extraction may be run until this second Pro repair gate is completed.

# Locked state during this review

- reaction endpoints: NOT COMPUTED / NOT AUTHORIZED;
- MFE/MAE: NOT COMPUTED;
- new Databento market-data acquisition: NOT AUTHORIZED;
- DEV_RANK2: CLOSED;
- RETRO_CONFIRM / CONFIRM outcomes: CLOSED;
- LOCKED_COMEX_TEST: CLOSED;
- Track B J+2+: NOT OPENED;
- XAUUSD economic mapping: NOT OPENED.
