# PRO GATE — COMEX native reaction protocol validation

Date: 2026-08-19
Branch: `agent/xau-comex-acquisition-plan`
Purpose: decisive methodological audit BEFORE any reaction outcome is computed

## Instruction to Pro

Act as a skeptical quantitative-research reviewer. Do **not** optimize on reaction outcomes and do not ask to inspect them: they have intentionally not been computed yet.

Review the current project state and the PRE-PRO protocol draft, then return a decisive, implementable preregistration for the reaction study.

Primary document to audit:

- `xau-multiyear/docs/COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_PREPRO_v0_9.md`

Canonical completed contact checkpoint:

- `xau-multiyear/docs/CHECKPOINT_COMEX_NATIVE_N2_EXACT_CONTACT_COMPLETE_2026-08-19.md`

Earlier frozen native-retest protocol:

- `xau-multiyear/docs/COMEX_DEV_RANK1_NATIVE_RETEST_ACQUISITION_FREEZE_v1.md`

Sequential exact-contact protocol:

- `xau-multiyear/docs/COMEX_DEV_RANK1_NATIVE_N2_SEQUENTIAL_ACQUISITION_FREEZE_v1.md`

## Facts already fixed — do not reinterpret as performance

- DEV_RANK1 source sessions selected: 96; usable native raw-GC source sessions: 92.
- Four native levels per usable source session: POC / VAH / VAL / VWAP = 368 levels.
- Contact is first raw trade exactly at the frozen 0.10 GC tick on the same raw source instrument.
- Primary contact horizon already frozen and completed: the next eligible **full GC auction session J+1 only**, not US-only and not a civil-day-only test.
- Final classification: 368/368.
- Exact J+1 contacts: 238.
- No J+1 exact contact: 130.
- Contact incidence: 64.67391304347826% — this is NOT a win rate and NOT evidence of an edge.
- Final status SHA-256: `8a825b0bc1deba51959b78ab6e62206fe49232e76329558e83949bf6d3d4151a`.
- Existing-POI COMEX B1/B2 path remains closed NO_GO.
- DEV_RANK2 / RETRO_CONFIRM / LOCKED_COMEX_TEST remain closed.
- No additional market-data spend is authorized.

## Data already owned for the proposed reaction pass

- exact raw N2 `trades` for the contact candidate interval(s), sufficient to recover exact `t0` and already-owned post-contact trades remaining inside that downloaded interval;
- raw-contract `ohlcv-1m` for the full eligible J+1 auction session from N1;
- fixed source-session information used to create native levels, subject to a zero-outcome provenance/availability QA.

Important resolution limitation:

- M1 can measure high/low excursion magnitudes over completed bars;
- M1 cannot determine the chronological order of two events occurring within the same minute;
- therefore stop/target first-hit logic, exact retest counts and `rejection before failure` labels must not be inferred from M1 without extra exact tape.

## Scientific questions to decide

### A. Reaction Track A — exact J+1 contacts

For the 238 exact contacts, determine the defensible reaction estimands and horizons without looking at outcomes.

The draft proposes:

- causal approach side from the last off-level raw trade before `t0`, with prior M1 close fallback;
- signed away/through coordinate independent of level family;
- exact residual-contact-minute module;
- bar-aligned completed-M1 horizons B1 / B5 / B15 / B30 / B60 / session close;
- continuous endpoints:
  - away MFE ticks;
  - through penetration ticks;
  - reaction balance = away MFE - through penetration;
  - signed endpoint displacement;
- raw ticks plus optional normalization by completed source-session range;
- no binary win/rejection label unless preregistered now;
- no Asia/London/US filtering; time-of-day retained as context;
- date-cluster inference because POC/VAH/VAL/VWAP within a source/retest date are dependent.

### B. Controls — blocking issue

The earlier frozen protocol requires matched controls preserving year, time-of-day, direction/approach and volatility context.

The PRE-PRO draft gives two possibilities:

1. zero-new-cost M1 matched **persistence** controls anchored after the contact minute;
2. higher-fidelity exact-tape pseudo-event controls, which would require a new metadata quote and explicit user authorization.

You must decide whether option 1 is scientifically sufficient for DEV_RANK1 screening. If not, define an outcome-free exact pseudo-event construction that can be quoted before purchase.

### C. Lifetime Track B — J+2 and later

The current 64.67% incidence is J+1 only.

We explicitly want to preserve for later analysis:

- first contact of the 130 J+1 noncontacts at J+2 / J+3 / later;
- possible validity decay / expiration of native levels;
- later retests after a first contact;
- session/time-of-day of later contacts.

But later sessions introduce a contract-lifetime/roll issue: the original raw GC instrument may become inactive. Decide whether Track B should be designed now or only after Track A, and state the scientifically valid contract rule. Default PRE-PRO position is **no silent level transfer to a new expiry and no continuous/adjusted substitution**.

## Required Pro output

Return one structured decision memo with the following sections.

### 1. Overall verdict

Choose exactly one:

- `APPROVE_WITHOUT_CHANGE`
- `APPROVE_WITH_REQUIRED_CHANGES`
- `STOP_AND_REDESIGN`

Explain the decisive reason.

### 2. Final Track-A event definition

State exactly:

- population;
- event time;
- approach-side rule;
- handling of undefined approach;
- raw instrument rule;
- whether only first contact is used.

### 3. Final horizons

Choose the exact horizon set and identify **one primary horizon**. Do not defer this until after results.

Audit the bar-aligned design for lookahead / unequal elapsed-time concerns.

### 4. Final primary endpoint

Choose **one primary continuous endpoint** and define it algebraically.

State which other endpoints are secondary/descriptive.

Decide whether source-session range is an acceptable causal normalizer; if not, specify one replacement normalizer using only pre-contact information.

### 5. Matched-control design

This is mandatory.

Specify:

- control population;
- exact anchor time/price;
- matching variables;
- time-of-day tolerance/bin;
- direction/approach matching rule;
- volatility matching rule;
- exclusion window around native contacts;
- number K of controls;
- deterministic tie-breaking;
- whether controls may come from the same or only other dates;
- how dependence is handled;
- whether M1 controls are sufficient or exact tape is required.

If exact tape is required, give a deterministic pseudo-event manifest rule suitable for `metadata.get_cost()` before any purchase.

### 6. Inference / dependence

Specify:

- cluster unit;
- estimator (median/mean/paired difference/etc.);
- CI/resampling method;
- bootstrap/permutation count;
- fixed random seed requirements;
- handling of overlapping level-event windows.

### 7. Multiplicity

Choose:

- status of aggregate vs POC/VAH/VAL/VWAP results;
- which type/horizon results are confirmatory vs secondary;
- multiplicity correction, if any;
- what conclusions are forbidden from best-looking post-hoc slices.

### 8. Promotion gate to DEV_RANK2

Define the exact DEV_RANK1 reaction criteria that would justify opening DEV_RANK2 **before seeing reaction results**.

Do not use a vague phrase like `looks promising`.

The gate must address:

- effect vs matched controls;
- uncertainty;
- year stability / concentration;
- dependence on one level family;
- minimum sample/cluster support;
- what result forces NO_GO.

### 9. Need for additional market data

Choose:

- `NO_NEW_DATA_FOR_TRACK_A_FIRST_PASS`
- `QUOTE_EXACT_CONTROL_TAPE_BEFORE_EXECUTION`
- another explicitly defined data need.

No purchase is authorized by your answer; this is a methodological recommendation only.

### 10. Track-B lifetime recommendation

State:

- whether to design Track B before or after Track-A execution;
- maximum later-session horizon or method for choosing it before outcomes;
- raw-contract/roll rule;
- level expiration/invalidation rule;
- whether later retests are a separate hypothesis;
- whether a first contact consumes the level for the primary analysis.

### 11. Hidden-bias audit

Explicitly check for:

- lookahead;
- intrabar ordering ambiguity;
- contract roll / survivorship;
- contact selection bias;
- conditioning on contact;
- multiple testing;
- clustered dependence;
- time-of-day confounding;
- volatility confounding;
- outcome-dependent data acquisition;
- any leakage from prior XAU/CFD results into native COMEX level evaluation.

### 12. Exact edits for final v1

Give concise, implementable changes that can be applied to PRE-PRO v0.9 to produce:

`COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_v1.md`

Do not compute or request reaction results until that v1 is frozen.
