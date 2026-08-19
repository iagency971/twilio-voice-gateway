# PRO REPAIR GATE — COMEX native reaction control support

Date: 2026-08-19  
Repository: `iagency971/twilio-voice-gateway`  
Branch: `agent/xau-comex-acquisition-plan`  
Review mode required: **OUTCOME-BLIND METHODOLOGICAL REPAIR REVIEW**  
Reaction outcomes inspected or computed: **NO**  
New market-data acquisition authorized: **NO**

## 0. Mission

Perform a narrowly scoped Pro revalidation of the **matched-control repair only** for Track A of the native COMEX reaction study.

Do **not** read, compute, derive, estimate, or inspect any post-anchor reaction outcome: no W5/W15/W60/SC NRB, no MFE/MAE, no terminal displacement, no family/year/session reaction ranking, no economic simulation.

Do **not** authorize any Databento purchase, DEV_RANK2, RETRO_CONFIRM, or LOCKED_COMEX_TEST.

The original Pro memo remains authoritative except where this repair review explicitly approves a replacement rule.

## 1. Required reading

Read fully:

1. `xau-multiyear/docs/PRO_DECISION_MEMO_COMEX_NATIVE_REACTION_PROTOCOL_2026-08-19.md`
2. `xau-multiyear/docs/COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_PREPRO_v0_9.md`
3. `xau-multiyear/docs/CHECKPOINT_COMEX_NATIVE_N2_EXACT_CONTACT_COMPLETE_2026-08-19.md`
4. `xau-final-results/comex_dev_rank1_native_reaction_source_last30_fallback_v1/source_last30_fallback.json`
5. `xau-final-results/comex_dev_rank1_native_reaction_source_last30_fallback_v1/support_prior_close_only_by_year.csv`
6. `xau-final-results/comex_dev_rank1_native_reaction_source_last30_fallback_v1/support_prior_close_only.csv`
7. `xau-final-results/comex_dev_rank1_native_reaction_source_last30_zero_qa_v1/source_last30_zero_qa.json`
8. `xau-multiyear/scripts/audit_comex_native_reaction_source_last30_fallback.py`
9. `xau-final-results/comex_dev_rank1_native_reaction_v1_preoutcome/preoutcome_manifest_qa.json` only as evidence of why the original support design had to be repaired; do not treat its old matched manifest as executable.

## 2. Why a repair was required

The original Pro control specification used only the already-owned raw-contract J+1 sessions belonging to the 92 DEV_RANK1 source/retest blocks, with:

- another treated date;
- same calendar/source year;
- same 30-minute minute-of-session bin;
- same pseudo-approach;
- complete causal pre-anchor 30-minute local window;
- W15 available;
- more than ±60 minutes from every exact native contact on the control date;
- source-session range ratio 0.5–2;
- pre-anchor local 30-minute range ratio 0.5–2;
- K=5 controls on five distinct dates.

Before any outcome extraction this design failed its own Pro support gate: only about 100 of 235 defined-approach contacts obtained K=5, on about 54 treated dates. This was correctly classified `STOP_AND_REPAIR_DESIGN`; no reaction result was opened.

A subsequent audit also found that an early implementation of the matching covariates had allowed information from the treated contact minute into some matching variables. That implementation was blocked and abandoned before outcome extraction. The repaired design described below uses **no treated contact-minute value** for matching.

## 3. Proposed repair A — expand the control-source pool, zero new market-data cost

The repository already owns a broader `GC.n.0` OHLCV-1m context covering approximately 2010-06-06 through 2019-01-01 and carrying the underlying `instrument_id`.

Proposal:

- keep the 92 canonical raw N1 blocks;
- additionally admit already-owned context source→next-session blocks only when the continuous context maps to a **single identical underlying raw `instrument_id` on both source and next session**;
- use the absolute unadjusted OHLCV values of that stable raw instrument only;
- exclude every reserved/non-DEV_RANK1 source or next date belonging to DEV_RANK2, RETRO_CONFIRM, LOCKED_COMEX_TEST, or other frozen non-DEV_RANK1 allocations;
- keep same source year as the treated event; do not use ±1-year matching;
- retain same 30-minute bin, same approach sign, K=5, five control dates, ±60-minute native-contact exclusion, and 0.5–2 calipers.

Zero-outcome parity QA:

- 92 canonical N1 blocks examined;
- 85 blocks were testable where `GC.n.0` had the same stable single underlying instrument id;
- **85/85 had exact OHLCV parity with the canonical raw N1 block**;
- `stable_parity_all_pass = true`.

The repaired pool contains approximately 2,293,182 `PRIOR_CLOSE_ONLY` candidate rows across 1,739 source blocks after excluding 261 reserved non-DEV_RANK1 dates.

No market-data API was called and no download/spend occurred.

### Pro decision required — A

Choose one:

- `APPROVE_EXPANDED_STABLE_IID_POOL`
- `REJECT_EXPANDED_STABLE_IID_POOL`

If rejected, state one minimal outcome-blind alternative that does not inspect reaction outcomes.

## 4. Proposed repair B — causal volatility fallback for contacts in first 30 minutes

The original Pro design requires a complete causal J+1 pre-anchor 30-minute local range. This is structurally unavailable for contacts in the first 30 minutes of J+1; 27 defined contacts occur at minute 0 alone.

For treated contacts with a complete pre-contact J+1 30-minute window, **retain the original Pro rule unchanged**:

- local pre-30-minute executed-price range ending strictly before the contact-minute start `m0`;
- pre-5-minute signed move;
- source-session range.

For treated contacts with `anchor_minute_of_session < 30`, proposed fallback:

- use the **final 30-minute executed-price range of the source session J**, on the same raw instrument that created the level;
- this range is fully known before J+1 begins;
- match it symmetrically against each control candidate's own source-session final-30-minute range;
- retain the source-session range ratio 0.5–2;
- do not use any treated contact-minute value;
- for the early fallback branch, the absent J+1 pre-5 signed-move comparator is not used in ranking (`d_move = 0` for all eligible candidates), so it cannot select controls using post-treatment information.

The preferred pseudo-approach remains the **original Pro `PRIOR_CLOSE_ONLY` rule**. A tested `BAR_OPEN_FALLBACK` produces identical aggregate support and is **not proposed for adoption**.

### Provenance QA

`source_last30_zero_qa.json` shows:

- 92 source sessions total;
- 91 positive source-session final-30-minute ranges;
- exactly one missing/nonpositive window: `2013-12-25`;
- that case is **missing final-30-minute trades**, not a flat executed-price window;
- exactly one defined-approach contact is affected.

Proposed rule for that case:

- **no imputation** from J+1, contact-minute, post-contact, continuous adjusted, XAUUSD, or another contract data;
- if the early fallback is required and source-last30 is missing/nonpositive, the event is ineligible/unmatched for the controlled primary analysis, but retained in descriptive inventory.

### Pro decision required — B

Choose one:

- `APPROVE_SOURCE_LAST30_EARLY_FALLBACK`
- `REJECT_SOURCE_LAST30_EARLY_FALLBACK`

Also explicitly approve/reject the proposed `d_move = 0` tie-neutral handling in the early branch. If rejected, provide one causal pre-J+1 substitute ranking rule.

## 5. Proposed repair C — final control rule retained otherwise

Preferred final control design is `PRIOR_CLOSE_ONLY` only.

For every treated event:

1. approach must be defined by the frozen event rule;
2. W15 must fit before J+1 close;
3. controls come from a different source date;
4. same **source year** 2011–2018;
5. same 30-minute minute-of-session bin;
6. same pseudo-approach sign;
7. ±60 wall-clock minutes around every known exact native contact on the control date excluded;
8. same stable raw instrument identity within the candidate source→next block;
9. source-range ratio 0.5–2;
10. mature treated events: local pre30 range ratio 0.5–2, then original pre5 signed-move ranking;
11. early treated events: source-last30 range ratio 0.5–2, with no local pre5 ranking term;
12. lexicographic deterministic nearest-neighbor ranking using only causal covariates;
13. select at most one representative per control date, then first K=5 distinct control dates;
14. fewer than five controls = `CONTROL_UNMATCHED`.

No caliper was chosen using reaction outcomes.

### Pro decision required — C

Choose one:

- `APPROVE_REPAIRED_K5_MATCHING_RULE`
- `REJECT_REPAIRED_K5_MATCHING_RULE`

## 6. Outcome-blind support result under the proposed repair

Latest successful guarded run: `32278975008`.

Guards:

- `post_contact_values_used_for_matching = false`
- `post_anchor_outcomes_read = false`
- `reaction_outcomes_computed = false`
- `market_data_api_called = false`
- `market_data_download_performed = false`

Preferred `PRIOR_CLOSE_ONLY` support:

- defined-approach events: **235**
- eligible events: **234**
- K=5 matched events: **227**
- matched treated dates: **81**
- full-match rate among defined events: **96.5957%**

By source year:

- 2011: 28/31 = 90.32%, 11 matched dates
- 2012: 26/26 = 100%, 10 matched dates
- 2013: 27/27 = 100%, 10 matched dates
- 2014: 21/25 = 84.00%, 8 matched dates
- 2015: 21/22 = 95.45%, 10 matched dates
- 2016: 31/31 = 100%, 10 matched dates
- 2017: 33/33 = 100%, 11 matched dates
- 2018: 40/40 = 100%, 11 matched dates

Thus every original Pro support criterion passes outcome-blind:

- matched events >=160: PASS
- matched dates >=60: PASS
- every source year >=5 matched dates: PASS
- >=85% defined contacts receive K=5: PASS
- every source year >=75% full-match rate: PASS

Current hashes:

- source-last30 provenance CSV SHA-256: `3d762b8184c5bd2f6e67ab9219aea864553ffc495530c0af3da823ae59403c52`
- repaired treated-event context CSV SHA-256: `1423dd287928481391be47301017cb1a73680a24cd9dc6e6211a039949e1118b`

Important: this successful audit proves **support feasibility**, not a reaction edge. A final executable full control-candidate universe and K=5 matched-set manifest must still be regenerated, frozen and hashed after Pro approves the repair and before any outcome extraction.

### Pro decision required — D

State whether the original support gate can legitimately be marked:

- `SUPPORT_GATE_REPAIRED_AND_PASS`

or must remain:

- `STOP_AND_REPAIR_DESIGN`.

## 7. Required final Pro output

Return a concise structured memo with exactly these sections:

1. `OVERALL_VERDICT`: one of `APPROVE_REPAIR`, `APPROVE_WITH_REQUIRED_CHANGES`, `REJECT_REPAIR`.
2. `EXPANDED_STABLE_IID_POOL`: approve/reject + rationale.
3. `EARLY_SOURCE_LAST30_FALLBACK`: approve/reject + rationale.
4. `MISSING_2013_12_25_POLICY`: exact rule.
5. `EARLY_RANKING_D_MOVE`: approve `d_move=0` or prescribe exact causal replacement.
6. `FINAL_K5_CONTROL_RULE`: exact executable rule.
7. `SUPPORT_GATE_STATUS`: `SUPPORT_GATE_REPAIRED_AND_PASS` or `STOP_AND_REPAIR_DESIGN`.
8. `EXACT_V1_EDITS`: precise edits required to create `COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_v1.md`.
9. `PRE_OUTCOME_FREEZE_REQUIREMENTS`: exact files/hashes/QA that must exist before W15 may be computed.
10. `PROHIBITIONS`: reaffirm no new data spend, no DEV_RANK2/RETRO_CONFIRM/LOCKED opening, no reaction outcome read during this review.

If you approve the repair, do not compute outcomes. The next step will return to Très élevé to implement the approved final v1, regenerate the final outcome-blind control universe/matched manifest, freeze hashes, then and only then execute Track A outcomes.
