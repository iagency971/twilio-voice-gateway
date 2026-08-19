# PRO Amendment Gate — COMEX Native Reaction Controls — 2026-08-19

Status: **OUTCOME-BLIND DRAFT — DO NOT COMPUTE REACTION OUTCOMES**

Branch: `agent/xau-comex-acquisition-plan`

## Purpose

Request a narrow Pro revalidation of the control design before freezing `COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_v1.md` and before reading or computing any W5/W15/W60/SC reaction outcome.

The original Pro memo is `xau-multiyear/docs/PRO_DECISION_MEMO_COMEX_NATIVE_REACTION_PROTOCOL_2026-08-19.md`.

## What remains unchanged from the Pro decision

- Track A population remains the 238 exact J+1 native COMEX contacts.
- `t0`, `m0`, `a0`, `A0`, R0/W5/W15/W60/SC definitions remain unchanged.
- W15 remains the unique primary horizon.
- `NRB` / `DELTA_NRB15` remain the primary endpoint definitions.
- K=5 controls on five distinct dates remains unchanged.
- Same source year remains unchanged.
- Same 30-minute session bin remains unchanged.
- Same causal approach direction remains unchanged.
- Source-session range caliper 0.5–2 remains unchanged.
- Mature-contact local pre-30 range caliper 0.5–2 remains unchanged.
- Deterministic ranking, date clustering, multiplicity rules and DEV_RANK2 gate remain unchanged.
- `PRIOR_CLOSE_ONLY` is retained for control pseudo-approach. `BAR_OPEN_FALLBACK` is NOT proposed for adoption.
- No market-data purchase is requested.
- No reaction outcome has been read or computed during this amendment work.

## Why an amendment is needed

The strict first implementation using only the 92 canonical J+1 N1 blocks had insufficient control support. Outcome-blind diagnostics then identified two structural issues:

1. the control pool was unnecessarily limited even though an already-owned `GC.n.0` M1 context covering 2010-06-06 through 2019-01-01 exists with underlying `instrument_id`;
2. contacts in the first 30 minutes of J+1 cannot have a complete local J+1 pre-30 window by construction, including contacts in the first minute.

A separate audit also found that using any value from the treated contact minute in matching would be post-treatment leakage. That approach was rejected. All proposed covariates below end strictly before the treated contact minute or come from source session J, which is fully known before J+1.

## Proposed Amendment A — expand the already-owned control pool

Permit control candidates from the already-owned `GC.n.0` M1 context only when all of the following are true:

- source/control year is 2011–2018 and equals the treated event source year;
- source and next session each map to exactly one underlying `instrument_id`;
- the same underlying `instrument_id` is present across the source and next sessions;
- no roll/cross-contract substitution occurs;
- DEV_RANK2, RETRO_CONFIRM and LOCKED_COMEX_TEST reserved dates are excluded;
- original DEV_RANK1 source dates are not duplicated through the expanded pool;
- all original K=5, same-year, same-bin, same-approach, caliper and deterministic-ranking rules still apply.

Outcome-blind parity QA on canonical testable blocks found 85/85 exact M1 OHLCV parity when the continuous context's underlying `instrument_id` equals the frozen raw N1 instrument. This supports using the stable-IID context as a larger control reservoir, not as a replacement structural instrument.

## Proposed Amendment B — early-contact volatility covariate

For treated contacts with at least 30 minutes of J+1 history before `m0`, keep the Pro-approved local pre-30 range ending strictly before `m0`.

For treated contacts with `anchor_minute_of_session < 30`, replace the unavailable local pre-30 volatility covariate with:

`source_last30_range_ticks` = high-low range, in GC ticks, of the final 30 minutes of source session J, computed from the same raw source contract/session used to create the native VWAP/POC/VAH/VAL levels.

This covariate is fully known before J+1 and therefore before `t0`.

For an early treated event, a control must be matched symmetrically using the control candidate's own source-session final-30-minute range, with the same 0.5–2 caliper. The full source-session range caliper remains in force.

No treated contact-minute open/high/low/close or post-`t0` value may be used in matching.

## Pseudo-approach rule

Adopt only `PRIOR_CLOSE_ONLY`, i.e. retain the Pro rule based on the latest completed M1 close strictly prior to the control anchor that differs from the control anchor price. Do not use the current control minute open as fallback.

## Outcome-blind support evidence available for review

The compact diagnostic at:

`xau-final-results/comex_dev_rank1_native_reaction_source_last30_fallback_diagnostic_v1/source_last30_fallback.json`

reports, before any reaction outcome:

- 235 approach-defined treated events;
- `PRIOR_CLOSE_ONLY`: 227 fully K=5 matched events;
- 81 matched treated dates;
- full-match rate 96.5957%;
- every source year has at least five matched dates;
- every source year has at least 75% full matching;
- all Pro support criteria pass;
- `post_contact_values_used_for_matching=false`;
- `post_anchor_outcomes_read=false`;
- `reaction_outcomes_computed=false`;
- `market_data_api_called=false`;
- `market_data_download_performed=false`.

A final provenance hard-guard rerun is being completed before this amendment is treated as ready for Pro decision.

## Questions for Pro

Provide a binary/structured decision on the following only, without requesting or inspecting any reaction outcome:

1. Is Amendment A (expanded already-owned stable-underlying-IID M1 control pool) methodologically acceptable while preserving same source year, same 30-minute bin, same approach, K=5 and original calipers?
2. Is Amendment B (`source_last30_range_ticks` for treated/control events in the first 30 minutes only) an acceptable causal replacement for an unavailable J+1 local pre-30 range?
3. Is retaining `PRIOR_CLOSE_ONLY` and rejecting `BAR_OPEN_FALLBACK` the preferred conservative pseudo-approach rule?
4. Are additional balance diagnostics required before freezing the control manifest (e.g. standardized covariate differences or overlap summaries), provided those diagnostics remain strictly pre-outcome?
5. If approved, may the protocol be frozen and the deterministic K=5 manifests hashed before computing W15 outcomes?

## Required Pro verdict format

- `APPROVE_AMENDMENT`
- `APPROVE_WITH_REQUIRED_CHANGES`
- `REJECT_AND_REDESIGN`

Then list exact required edits, if any.

## Hard prohibitions

- Do not compute or inspect W5/W15/W60/SC reaction outcomes.
- Do not rank POC/VAH/VAL/VWAP by reaction.
- Do not open DEV_RANK2, RETRO_CONFIRM or LOCKED_COMEX_TEST.
- Do not authorize or perform any new market-data purchase.
