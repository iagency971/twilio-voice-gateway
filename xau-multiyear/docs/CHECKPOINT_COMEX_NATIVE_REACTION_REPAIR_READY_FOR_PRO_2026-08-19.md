# CHECKPOINT — COMEX native reaction control repair ready for second Pro gate

Date: 2026-08-19  
Branch: `agent/xau-comex-acquisition-plan`  
Status: OUTCOME-BLIND CONTROL REPAIR PREP COMPLETE / SECOND PRO REVIEW REQUIRED

## Hard state

No Track-A reaction outcome has been computed or inspected under the repaired design.

- post-contact MFE/MAE: NOT COMPUTED
- W5/W15/W60/SC reaction endpoints: NOT COMPUTED
- level-family reaction ranking: NOT COMPUTED
- session/time reaction ranking: NOT COMPUTED
- profitability / XAUUSD mapping: NOT COMPUTED
- new market-data API call: NONE
- new market-data purchase: NONE
- DEV_RANK2: CLOSED
- RETRO_CONFIRM / CONFIRM outcomes: CLOSED
- LOCKED_COMEX_TEST: CLOSED
- Track B J+2+: CLOSED

## Canonical completed contact population

Unchanged:

- 368 native levels;
- 238 exact first contacts in full J+1 GC auction session;
- 130 J+1 noncontacts;
- 0 unresolved;
- contact incidence 64.67391304347826%, incidence only;
- final contact-status SHA-256 `8a825b0bc1deba51959b78ab6e62206fe49232e76329558e83949bf6d3d4151a`.

Canonical contact checkpoint:

`CHECKPOINT_COMEX_NATIVE_N2_EXACT_CONTACT_COMPLETE_2026-08-19.md`

## First Pro decision

Canonical memo:

`PRO_DECISION_MEMO_COMEX_NATIVE_REACTION_PROTOCOL_2026-08-19.md`

Verdict was `APPROVE_WITH_REQUIRED_CHANGES` and fixed the primary reaction architecture, including W15 / DELTA_NRB15 / date-cluster inference / K=5 matched controls and the DEV_RANK2 promotion gate.

## First preoutcome matching implementation — BLOCKED

The first outcome-blind matched-control implementation is NOT valid for execution.

Reason discovered by source-code audit:

- some treated local matching covariates were computed through `a0`;
- this included high/low/close information from the contact minute `[m0,a0)`;
- because exact `t0` lies inside that minute, part of those covariates may be after contact;
- using them to select controls is post-treatment matching leakage.

Therefore every matched set from the original PREOUTCOME implementation is permanently superseded and may not be reused.

No reaction outcome was extracted from it.

## Strict pre-contact reconstruction

Canonical repair audit:

`xau-final-results/comex_dev_rank1_native_reaction_precontact_control_repair_v1/precontact_control_repair.json`

All local treated matching covariates were rebuilt to terminate strictly before `m0`, the start of the contact minute.

Population facts:

- 238 exact contacts;
- 235 defined approach;
- 27 defined contacts at session minute 0;
- 54 defined contacts in first 30 session minutes.

Strict mature pre-m0 support:

- 176/235 K=5 matched;
- 74 dates;
- 74.89% full-match rate;
- support gate FAIL.

Using only available session-open-to-m0 local history for early events:

- 203/235 K=5 matched;
- 78 dates;
- 86.38% overall full-match rate;
- annual criterion still fails in 2014 and 2015.

The support problem is therefore structural for early-session contacts rather than outcome-driven.

## Expanded zero-cost neutral control pool

The project already owns `GC.n.0` M1 context over 2010-06-06 to 2019-01-01 from run `32179377819`.

No new data were acquired for the repair.

Generic neutral control blocks are allowed in the candidate repair only when:

- source J and next session J+1 use one constant identical underlying `instrument_id`;
- vendor price is original/unadjusted;
- dates reserved to DEV_RANK2 / CONFIRM / LOCKED_TEST are excluded as generic source or next dates;
- the original 92 native source dates retain their canonical raw/N1 control implementation.

Frozen non-DEV_RANK1 reserved dates excluded: 261.

Direct parity QA where stable context/raw overlap is testable:

- 85 stable same-instrument blocks;
- 85/85 exact OHLCV parity;
- 0 failures.

Canonical feasibility evidence:

`xau-final-results/comex_dev_rank1_native_reaction_expanded_control_feasibility_v1/expanded_control_feasibility.json`

## Preferred early-contact repair candidate

For contacts at session minute >=30:

- exact source year;
- same 30-minute session bin;
- same approach sign;
- full source-session range ratio 0.5–2;
- J+1 local 30m range ending strictly before `m0`, ratio 0.5–2;
- pre-m0 pre5 signed move;
- ±60 minutes exact-native-contact exclusion;
- K=5 distinct control dates;
- original deterministic ranking/tie-break.

For contacts at session minute <30:

- replace the structurally unavailable J+1 local30/pre5 volatility context with the executed-price range of the **final 30 wall-clock minutes of completed source session J**;
- this source-final-30m range is computed on the same raw GC instrument that created the level and is fully known before J+1;
- retain exact source year, same 30-minute session bin, same approach sign, full source-session range ratio 0.5–2, source-final30 range ratio 0.5–2, ±60 exclusion and K=5 distinct dates.

Preferred control pseudo-approach remains the first Pro rule `PRIOR_CLOSE_ONLY`.

The diagnostic `BAR_OPEN_FALLBACK` is not proposed because support already passes without it.

## Outcome-blind support of preferred candidate

`PRIOR_CLOSE_ONLY + source_last30` produced:

- defined-approach contacts: 235;
- eligible before missing-covariate final classification: 234;
- K=5 matched: 226;
- matched treated dates: 81;
- full-match rate: 96.17021276595744%;
- >=160 matched events: PASS;
- >=60 dates: PASS;
- >=5 dates in every source year 2011–2018: PASS;
- >=85% full-match rate: PASS;
- every source year >=75% full-match rate: PASS.

No reaction endpoint was read or computed to obtain those support counts.

## Sole source-final30 missing-covariate case

Canonical guarded compact QA:

`xau-final-results/comex_dev_rank1_native_reaction_source_last30_zero_qa_v1/source_last30_zero_qa.json`

Origin:

- run `32263559201`;
- job `96101250568`;
- artifact `9352159692`;
- artifact digest `sha256:9ffe36231b805cf6e75b568ef35558e61ca9ae1a2894611401bc8799fa05433d`.

Result:

- 92 source sessions checked;
- 91 have positive final-30m range;
- exactly 1 has no trades in the final-30m window;
- flat-but-present windows: 0;
- affected source date: `2013-12-25`;
- affected exact-contact events: 1;
- affected defined-approach events: 1.

This is missing pre-J+1 matching information, not a market reaction result.

Candidate treatment for second Pro review:

`FALLBACK_COVARIATE_MISSING_SOURCE_LAST30`

- no imputation;
- retain in descriptive 238-event inventory;
- exclude from controlled matched primary estimator;
- do not replace using contact-minute or post-contact information.

## Second Pro gate

Canonical prompt:

`PRO_GATE_COMEX_NATIVE_REACTION_CONTROL_REPAIR_2026-08-19.md`

Pro must validate or revise:

1. invalidation of the original contact-minute-leaking manifest;
2. strict `m0` cutoff for local treated matching variables;
3. source-final30 fallback for contacts before minute 30;
4. treatment of the sole 2013-12-25 missing fallback covariate;
5. expanded already-owned stable-instrument control pool;
6. retention of `PRIOR_CLOSE_ONLY` pseudo-approach;
7. exact matching/ranking rules;
8. sufficiency of 226/235 / 81-date support;
9. whether original W15 / DELTA_NRB15 / inference / DEV_RANK2 gates remain unchanged;
10. whether any new market data are necessary.

## Next allowed action

Only the second Pro methodology review is allowed next.

Do NOT freeze `COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_v1.md` and do NOT run any reaction extraction until Pro has returned the repair verdict.
