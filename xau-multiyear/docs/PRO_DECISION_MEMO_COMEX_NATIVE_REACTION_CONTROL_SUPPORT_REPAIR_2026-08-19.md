# PRO DECISION MEMO — COMEX native reaction control-support repair

Date: 2026-08-19  
Repository: `iagency971/twilio-voice-gateway`  
Branch: `agent/xau-comex-acquisition-plan`  
Review mode: **OUTCOME-BLIND METHODOLOGICAL REPAIR REVIEW**  
Post-anchor reaction outcomes inspected or computed: **NO**  
New market-data acquisition authorized: **NO**

This memo is limited to the repaired Track-A matched-control design. It does not evaluate W5/W15/W60/SC, NRB, MFE/MAE, terminal displacement, economic performance, level-family performance, time-of-day performance, or XAUUSD translation.

## 1. OVERALL_VERDICT

`APPROVE_WITH_REQUIRED_CHANGES`

The causal core of the repair is approved:

- the original contact-minute-leaking matched manifest remains permanently invalid;
- all treated local matching covariates must terminate strictly before `m0`, the start of the contact minute;
- the already-owned stable-identical-`instrument_id` control pool is admissible;
- the source-session final-30-minute fallback is admissible for structurally early contacts;
- `PRIOR_CLOSE_ONLY`, exact source year, same 30-minute bin, same approach sign, fixed 0.5–2 calipers, K=5 distinct control dates, and deterministic ranking remain the control design;
- the latest guarded support result passes every original Pro support threshold outcome-blind.

Approval is not yet authorization to compute reaction outcomes. Before W15 may be opened, the final v1 and all executable pre-outcome artifacts must be regenerated from scratch, reconciled, frozen, hashed, and hard-guarded as specified below.

The original Pro reaction architecture remains authoritative and unchanged: W15 is the sole primary horizon, `DELTA_NRB15` is the primary endpoint, source-session range is the normalizer, treated-date equal weighting is the aggregation rule, the frozen date-cluster inference/seeds and Holm secondary handling remain in force, and the original DEV_RANK1-to-DEV_RANK2 effect/year/family gates remain unchanged.

## 2. EXPANDED_STABLE_IID_POOL

`APPROVE_EXPANDED_STABLE_IID_POOL`

The already-owned `GC.n.0` OHLCV-1m context may supplement the 92 canonical raw/N1 blocks because the directly testable stable blocks show 85/85 exact OHLCV parity and zero failures. This approval is conditional on every executable generic source→next-session block satisfying all of the following before it enters the candidate universe:

1. source session J and its frozen canonical next eligible GC auction session J+1 are identified independently of price and outcome;
2. each session contains one constant underlying `instrument_id`, and the same `instrument_id` is present across both sessions;
3. prices are the vendor's absolute, unadjusted OHLCV values, with no back adjustment, spread transposition, XAUUSD/CFD substitution, or expiry transfer;
4. the block retains its actual row `instrument_id`, source date, next-session date, origin artifact, source file hash, and coverage bounds;
5. source year equals the treated event's source year; no ±1-year relaxation is allowed;
6. every source or next date reserved to DEV_RANK2, CONFIRM/RETRO_CONFIRM, LOCKED_COMEX_TEST, or another frozen non-DEV_RANK1 allocation is excluded;
7. the original 92 native source dates remain on the canonical raw/N1 implementation and are not duplicated through the generic context path;
8. no market-data API call or new purchase is made.

The 85/85 parity result validates use of stable-identical-IID context as raw-equivalent M1 input where the same safeguards pass; it does not waive per-block identity, adjustment, coverage, or provenance checks.

A necessary interpretive clarification must be added to final v1. On generic dates, the repository does not possess a complete exact-contact registry for every possible native level. Such anchors are therefore **matched reference anchors**, not proven treatment-free counterfactuals. The ±60-minute exclusion remains mandatory around every exact native contact actually present in the frozen exact-contact registry. Any generic block for which no complete native-contact registry exists must carry an explicit `native_contact_exclusion_status` identifying that limitation. The primary estimand is event-versus-matched-reference-anchor; a null result may not be overinterpreted as proof that no absolute native-level reaction exists if latent-contact contamination of the reference pool remains possible.

No additional raw-control purchase is required for this Track-A screening.

## 3. EARLY_SOURCE_LAST30_FALLBACK

`APPROVE_SOURCE_LAST30_EARLY_FALLBACK`

The final v1 must use exactly two mutually exclusive branches, chosen from the treated event's frozen `anchor_minute_of_session` before any outcome is read.

### Mature branch — `anchor_minute_of_session >= 30`

Retain the original Pro design, made strictly causal:

- treated local 30-minute executed-price range ends strictly before `m0`;
- treated pre-5-minute signed move ends strictly before `m0`;
- control local 30-minute range and pre-5-minute move are computed symmetrically from completed M1 information strictly before the control anchor minute;
- no OHLC value from `[m0,a0)` and no `A0` value may enter matching.

### Early branch — `anchor_minute_of_session < 30`

Replace the structurally unavailable J+1 local-pre30 and pre5 covariates with:

- the executed-price high-low range of the final 30 wall-clock minutes of the completed source session J;
- on the same raw `source_instrument_id` that created the native level;
- ending at the same frozen canonical source-session boundary used by the source-level protocol;
- fully known before J+1 begins;
- computed identically for the treated block and every candidate control block.

The full completed source-session range remains a separate required caliper in both branches. The source-final30 fallback may not be used for mature events merely because it gives better support. No contact-minute, post-contact, J+1 substitute, XAUUSD/CFD, adjusted continuous price, another expiry, or outcome-dependent alternative window is allowed.

The final executable provenance must be regenerated from the fully recovered already-owned source artifacts and reconciled against the dedicated source-last30 zero QA before outcomes. This is required because the current feasibility provenance and the later dedicated zero-window QA were produced through different recovery paths. The unified final provenance must state, for all 92 source sessions, the raw artifact and SHA-256, canonical session end, final30 bounds, record count, minimum, maximum, range, and missing/flat status.

## 4. MISSING_2013_12_25_POLICY

Approve the proposed deterministic rule exactly:

- label: `FALLBACK_COVARIATE_MISSING_SOURCE_LAST30`;
- no imputation;
- no replacement from J+1, the contact minute, post-contact data, a different source-history window, adjusted continuous data, XAUUSD/CFD, or another contract;
- retain the event in the 238-contact descriptive inventory and in contact-incidence reporting;
- retain it in the 235 defined-approach denominator used for support-rate reporting;
- if the early branch is required, exclude it from the matched controlled primary estimator and classify it as ineligible/unmatched for that explicit reason.

The final unified provenance must reproduce the dedicated zero-QA conclusion that exactly one defined-approach early event is affected. If final regeneration finds any additional missing or nonpositive source-final30 covariate affecting an early defined-approach event, the same no-imputation rule applies, support must be recomputed outcome-blind, and W15 remains closed unless every frozen support threshold still passes.

## 5. EARLY_RANKING_D_MOVE

Approve the intended tie-neutral treatment, with one implementation clarification:

- the early branch has no valid J+1 pre5 comparator;
- therefore `d_move` is **not a matching dimension** in that branch;
- it should be stored as `NA` / `NOT_APPLICABLE` and omitted from the early lexicographic sort tuple.

If the implementation requires a numeric compatibility field, it may be fixed to `0` for every eligible early candidate only if a hard assertion proves that it is constant across the entire early candidate set and the sort routine excludes it as an informative criterion. A numeric zero must not be interpreted or reported as a perfect movement match.

No substitute movement variable is authorized. The early deterministic ranking is:

1. absolute log-distance of source-final30 range;
2. absolute log-distance of full source-session range;
3. absolute minute-of-session distance within the already-required same 30-minute bin;
4. control anchor timestamp ascending;
5. control source date ascending;
6. control next-session date ascending;
7. `source_instrument_id` ascending;
8. stable candidate UID ascending.

## 6. FINAL_K5_CONTROL_RULE

`APPROVE_REPAIRED_K5_MATCHING_RULE`

The executable final rule is as follows.

### Treated-event prerequisites

1. The event belongs to the frozen set of 238 exact first J+1 contacts.
2. Approach is defined by the frozen event rule using information strictly before exact `t0`; undefined-approach events remain descriptive and are excluded from the signed primary.
3. W15 fits entirely before the frozen J+1 session close.
4. The branch is assigned deterministically: mature if `anchor_minute_of_session >= 30`, early otherwise.
5. No treated matching covariate uses the contact-minute interval `[m0,a0)`, `A0`, or any later value. Exact `t0` and the pre-`t0` approach sign remain event-definition information only.

### Candidate-control prerequisites

For each treated event, a candidate must:

1. come from a different source date;
2. come from the same exact source year 2011–2018;
3. come from the same canonical 30-minute minute-of-session bin;
4. have the same pseudo-approach sign;
5. use a valid canonical source→next-session block meeting the stable-identical-IID and provenance rules in Section 2;
6. have W15 entirely available before its frozen next-session close;
7. be outside ±60 wall-clock minutes of every exact native contact known on its control date in the frozen exact-contact registry;
8. pass the full source-session range ratio caliper `[0.5,2.0]`;
9. use `PRIOR_CLOSE_ONLY`: from the completed control anchor minute close, scan completed M1 closes backward for at most 30 wall-clock minutes, take the latest close strictly different from the anchor close, and infer approach from below/above; if none exists, the candidate is ineligible;
10. never use `BAR_OPEN_FALLBACK`.

### Mature-event caliper and ranking

A mature candidate must also pass the strict pre-anchor local30 range ratio caliper `[0.5,2.0]`. Rank lexicographically by:

1. `abs(log(control_pre30_range / treated_pre30_range))`;
2. `abs(log(control_source_range / treated_source_range))`;
3. absolute distance of the frozen normalized pre5 signed-move covariate;
4. absolute minute-of-session distance;
5. control anchor timestamp ascending;
6. control source date ascending;
7. control next-session date ascending;
8. `source_instrument_id` ascending;
9. stable candidate UID ascending.

### Early-event caliper and ranking

An early candidate must instead pass the source-final30 range ratio caliper `[0.5,2.0]`. Rank using the exact tuple in Section 5. No pre5 or other movement term is used.

### K=5 selection

- keep at most the highest-ranked representative from each control source date;
- select the first five distinct control source dates;
- K is fixed at 5;
- fewer than five qualifying dates gives `CONTROL_UNMATCHED`;
- no caliper, year, bin, sign, date-distinctness, exclusion window, or K rule may be relaxed after any outcome becomes visible.

The final pre-outcome QA must report control-date reuse across treated dates. The original treated-date inference remains the primary analysis as frozen by the first Pro memo; reuse concentration must be disclosed as a dependence diagnostic, and no inference rule may be changed after W15 is opened.

## 7. SUPPORT_GATE_STATUS

`SUPPORT_GATE_REPAIRED_AND_PASS`

This status is a **design-support feasibility result only**, not an effect or edge result.

Latest guarded `PRIOR_CLOSE_ONLY` support:

- defined-approach contacts: 235;
- eligible after the missing-covariate rule: 234;
- K=5 matched contacts: 227;
- matched treated dates: 81;
- full-match rate among defined contacts: 96.59574468085106%.

Annual support:

- 2011: 28/31, 11 dates;
- 2012: 26/26, 10 dates;
- 2013: 27/27, 10 dates;
- 2014: 21/25, 8 dates;
- 2015: 21/22, 10 dates;
- 2016: 31/31, 10 dates;
- 2017: 33/33, 11 dates;
- 2018: 40/40, 11 dates.

Thus the original Pro thresholds pass outcome-blind: at least 160 matched events, at least 60 treated dates, at least five matched dates in every year, at least 85% full K=5 among defined contacts, and no year below 75% full matching.

The older insufficient first-pass manifest remains `STOP_AND_REPAIR_DESIGN`, diagnostic only, and permanently non-executable. The `SUPPORT_GATE_REPAIRED_AND_PASS` status becomes executable only after the final regenerated universe and K=5 manifest satisfy the same thresholds and all freeze requirements below. If final regeneration changes counts or causes any support threshold to fail, no reaction outcome may be opened and the status reverts to `STOP_AND_REPAIR_DESIGN`.

## 8. EXACT_V1_EDITS

Create `xau-multiyear/docs/COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_v1.md` with these exact amendments to the original Pro-approved framework:

1. Permanently block and supersede every matched set from `comex_dev_rank1_native_reaction_v1_preoutcome/`.
2. State that every treated local matching covariate ends strictly before `m0`; `[m0,a0)`, `A0`, and post-anchor values are forbidden for matching.
3. Preserve exact `t0` and frozen pre-`t0` approach solely as event-definition information.
4. Add the expanded stable-identical-IID already-owned control-pool eligibility and provenance rules from Section 2.
5. Add an explicit canonical source→next-session adjacency field and prevent substitution by a later convenient session.
6. Add the mature/early branch assignment and formulas from Section 3.
7. Add the exact `FALLBACK_COVARIATE_MISSING_SOURCE_LAST30` rule.
8. Retain `PRIOR_CLOSE_ONLY` exclusively and prohibit `BAR_OPEN_FALLBACK`.
9. Remove `d_move` from the early ranking tuple; allow only a hard-guarded compatibility zero that is excluded from ranking.
10. Add the exact calipers, lexicographic ranking tuples, one-representative-per-control-date rule, K=5 distinct-date rule, and `CONTROL_UNMATCHED` result from Section 6.
11. Identify generic controls as matched reference anchors unless a complete exact-contact exclusion registry exists for their dates; state the resulting estimand/interpretation limitation.
12. Require reporting of control-date reuse and all source/date overlaps as pre-outcome dependence QA.
13. Reaffirm without alteration W15, `DELTA_NRB15`, source-range normalization, treated-date equal weighting, the frozen bootstrap/sign-flip seeds, Holm correction, and all original DEV_RANK2 gates.
14. Record `NO_NEW_DATA_REQUIRED_FOR_REPAIRED_TRACK_A`.
15. Keep DEV_RANK2, RETRO_CONFIRM/CONFIRM, LOCKED_COMEX_TEST, Track B J+2+, and XAUUSD economic mapping closed.
16. State that support passing is not reaction performance and cannot promote DEV_RANK2 by itself.

## 9. PRE_OUTCOME_FREEZE_REQUIREMENTS

Before any W15/W5/W60/SC, NRB, MFE/MAE, terminal-displacement, family, year, session, or economic result may be computed, the branch must contain and hash all of the following outcome-blind artifacts:

1. Final protocol: `xau-multiyear/docs/COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_v1.md`.
2. Frozen 368-level contact-status registry, retaining contact-status SHA-256 `8a825b0bc1deba51959b78ab6e62206fe49232e76329558e83949bf6d3d4151a`.
3. Final treated-event causal context for all 238 contacts, including approach provenance, `t0/m0/a0`, source year, session bin, branch, source range, mature pre30/pre5 fields, early source-final30 field, W15 availability, and explicit exclusion reason.
4. Unified 92-session source-last30 provenance rebuilt from the fully recovered already-owned raw artifacts, including source raw SHA-256, exact session/final30 bounds, record count, min/max/range, missing/flat flags, and a reconciliation report proving the dedicated 91-positive/1-missing conclusion or stopping if it does not reproduce.
5. Frozen canonical source→next-session adjacency and session-boundary manifest used by both treated and control blocks.
6. Frozen reserved-date exclusion manifest covering all 261 non-DEV_RANK1 reserved dates.
7. Expanded control-block provenance manifest with origin (`CANONICAL_N1` or `OWNED_GC_N0_CONTEXT`), source/next dates, constant IID checks, adjustment status, coverage, artifact/file hashes, and exclusion flags.
8. Exact 85/85 continuous-context versus raw-N1 parity QA and its inputs/hashes.
9. Complete `PRIOR_CLOSE_ONLY` control-candidate universe containing only causal covariates, all caliper flags, contact-exclusion/reference-anchor status, deterministic rank fields, and stable candidate UIDs.
10. Final deterministic K=5 matched-control manifest with five distinct control dates per matched event, selected ranks, branch, all distances, and unmatched reason where applicable.
11. Event/date/year support QA reproducing every frozen support threshold, plus control-date reuse, overlap, and concentration diagnostics.
12. A machine-readable pre-outcome guard JSON proving:
    - `post_contact_values_used_for_matching=false`;
    - `post_anchor_outcomes_read=false`;
    - `reaction_outcomes_computed=false`;
    - `mfe_mae_computed=false`;
    - `market_data_api_called=false`;
    - `market_data_download_performed=false`.
13. A SHA-256 freeze manifest covering the protocol, scripts, workflow, source inputs, candidate universe, K=5 manifest, provenance tables, and all QA outputs, together with the exact Git commit SHA.
14. A fresh final checkpoint stating that W15 remains closed until the freeze commit is complete.

The current feasibility hashes — source-last30 provenance `3d762b8184c5bd2f6e67ab9219aea864553ffc495530c0af3da823ae59403c52` and repaired treated-event context `1423dd287928481391be47301017cb1a73680a24cd9dc6e6211a039949e1118b` — remain audit inputs. They are not substitutes for the final executable-output hashes required above.

## 10. PROHIBITIONS

Reaffirmed until the final pre-outcome freeze is complete:

- no W5, W15, W60, or session-close reaction extraction;
- no NRB, `DELTA_NRB15`, MFE/MAE, terminal displacement, first-hit ordering, rejection label, family/year/session ranking, profitability result, or XAUUSD mapping;
- no reading of any pre-existing reaction-output artifact for this decision;
- no use of the blocked original matched manifest;
- no treated contact-minute or post-contact value in matching;
- no `BAR_OPEN_FALLBACK`;
- no imputation of the 2013-12-25 missing source-final30 covariate;
- no outcome-driven change to calipers, K, year, bin, sign, ranking, exclusions, support thresholds, inference, or promotion gates;
- no Databento quote, API call, download, or spend;
- no opening of DEV_RANK2, RETRO_CONFIRM/CONFIRM, LOCKED_COMEX_TEST, or Track B J+2+;
- no claim that support feasibility is a reaction edge, win rate, or tradable expectancy.

Next permitted action: return to Très élevé, implement the required final-v1 edits, regenerate the complete repaired pre-outcome universe and K=5 manifest from scratch, freeze and hash all artifacts, and stop again before any reaction outcome is opened.