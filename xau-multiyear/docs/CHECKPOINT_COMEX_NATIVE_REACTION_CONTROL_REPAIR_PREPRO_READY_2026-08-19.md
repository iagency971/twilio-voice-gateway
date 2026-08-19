# CHECKPOINT — COMEX native reaction control repair PRE-PRO ready

Date: 2026-08-19  
Repository: `iagency971/twilio-voice-gateway`  
Branch: `agent/xau-comex-acquisition-plan`

## Status

Track A exact-contact population remains frozen at 238 J+1 exact contacts out of 368 native levels. No reaction outcome has been computed or inspected in the control-repair work described here.

Current phase status:

- exact-contact classification: COMPLETE
- reaction protocol original Pro review: `APPROVE_WITH_REQUIRED_CHANGES`
- original control support implementation: FAILED support gate outcome-blind (`STOP_AND_REPAIR_DESIGN`)
- repaired control support feasibility: PASSES all original Pro support thresholds outcome-blind
- final reaction protocol v1: NOT YET FROZEN
- final executable repaired control manifest: NOT YET FROZEN
- W15/W5/W60/SC outcomes: NOT OPENED
- new market-data spend: NONE
- DEV_RANK2: CLOSED
- RETRO_CONFIRM: CLOSED
- LOCKED_COMEX_TEST: CLOSED

## Original Pro memo

Canonical methodological memo:

`xau-multiyear/docs/PRO_DECISION_MEMO_COMEX_NATIVE_REACTION_PROTOCOL_2026-08-19.md`

Primary endpoint remains W15 `DELTA_NRB15`, date-cluster inference, K=5 matched controls, with all original effect/stability promotion gates unchanged unless a future Pro decision explicitly amends them.

## Why repair was necessary

The first implementation of the original control pool was too sparse: about 100/235 defined-approach contacts received five controls, on about 54 dates, below the Pro support gate. No reaction outcome was opened.

A later code audit also detected use of treated contact-minute information in some matching covariates. That implementation was blocked and is non-executable. The repaired design is strictly pre-contact for treated matching variables.

## Repaired design proposed for Pro approval

### Expanded control pool

Use already-owned `GC.n.0` M1 context in addition to canonical N1 blocks, but only for source→next-session blocks where the same single underlying raw `instrument_id` is stable across both sessions. Exclude all reserved/non-DEV_RANK1 dates. No new Databento data are acquired.

Parity QA: 85/85 testable stable-same-IID blocks match canonical raw N1 OHLCV exactly.

### Early contacts

For contacts with a complete J+1 pre-contact 30-minute window, keep original Pro local pre30 + pre5 matching.

For contacts in the first 30 minutes, use source-session J final-30-minute raw executed-price range, fully known before J+1, symmetrically for treated and control blocks. Do not use treated contact-minute values.

Pseudo-approach remains original Pro `PRIOR_CLOSE_ONLY`; BAR_OPEN fallback is not proposed.

One source date, 2013-12-25, has no trades in the final 30-minute source window. It affects one defined-approach contact. Proposed policy: no imputation; event remains unmatched/ineligible if fallback is required.

## Latest guarded repair result

Workflow:
`.github/workflows/xau-comex-native-reaction-source-last30-fallback.yml`

Latest successful run:
`32278975008`

Guarded facts:

- `post_contact_values_used_for_matching=false`
- `post_anchor_outcomes_read=false`
- `reaction_outcomes_computed=false`
- `market_data_api_called=false`
- `market_data_download_performed=false`

Preferred `PRIOR_CLOSE_ONLY` support:

- defined events: 235
- eligible events: 234
- matched K5 events: 227
- matched dates: 81
- full-match rate: 96.59574468085106%

Annual support:

- 2011: 28/31, 11 dates
- 2012: 26/26, 10 dates
- 2013: 27/27, 10 dates
- 2014: 21/25, 8 dates
- 2015: 21/22, 10 dates
- 2016: 31/31, 10 dates
- 2017: 33/33, 11 dates
- 2018: 40/40, 11 dates

All original Pro support thresholds pass.

Canonical repair summary:
`xau-final-results/comex_dev_rank1_native_reaction_source_last30_fallback_v1/source_last30_fallback.json`

Annual QA:
`xau-final-results/comex_dev_rank1_native_reaction_source_last30_fallback_v1/support_prior_close_only_by_year.csv`

Source-last30 missing-window QA:
`xau-final-results/comex_dev_rank1_native_reaction_source_last30_zero_qa_v1/source_last30_zero_qa.json`

Current repair hashes:

- source-last30 provenance SHA-256: `3d762b8184c5bd2f6e67ab9219aea864553ffc495530c0af3da823ae59403c52`
- repaired event context SHA-256: `1423dd287928481391be47301017cb1a73680a24cd9dc6e6211a039949e1118b`

## Important non-final artifacts

The old directory:
`xau-final-results/comex_dev_rank1_native_reaction_v1_preoutcome/`
contains the original insufficient/partly flawed first-pass control universe and matched-control manifest. These files are evidence/diagnostics only and MUST NOT be used for reaction execution.

After Pro repair approval, Très élevé must regenerate from scratch:

1. final protocol `COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_v1.md`;
2. repaired full control-candidate universe;
3. deterministic actual K=5 matched-control manifest;
4. per-event/date/year support QA;
5. provenance QA;
6. SHA-256 manifest for all pre-outcome artifacts;
7. hard guard proving no reaction outcomes were read/computed during construction.

Only after those are frozen may W15 outcomes be computed.

## Next gate

Pro repair prompt:
`xau-multiyear/docs/PRO_REPAIR_GATE_COMEX_NATIVE_REACTION_CONTROL_SUPPORT_2026-08-19.md`

Required action now: switch briefly to Pro and perform only that outcome-blind repair review. Do not execute reaction outcomes in Très élevé before the Pro repair verdict.
