# CHECKPOINT — COMEX native reaction final pre-outcome freeze complete

Date: 2026-08-19  
Repository: `iagency971/twilio-voice-gateway`  
Branch: `agent/xau-comex-acquisition-plan`  
Status: **FINAL PRE-OUTCOME FREEZE COMPLETE / W15 NOT OPENED**

## Scope closed by this checkpoint

The repaired Track-A matched-reference control design has now been implemented, regenerated from scratch, hard-guarded, frozen, hashed, and published before any post-anchor reaction outcome was opened.

No W5/W15/W60/SC reaction value, NRB, `DELTA_NRB15`, MFE/MAE, terminal displacement, family/year/session reaction ranking, profitability metric, entry simulation, or XAUUSD economic mapping was read, computed, derived, or inspected during this freeze.

No Databento API call, quote, download, or spend occurred.

## Canonical methodology

Final protocol:

`xau-multiyear/docs/COMEX_DEV_RANK1_NATIVE_REACTION_PROTOCOL_v1.md`

Methodological authorities:

- `xau-multiyear/docs/PRO_DECISION_MEMO_COMEX_NATIVE_REACTION_PROTOCOL_2026-08-19.md`
- `xau-multiyear/docs/PRO_DECISION_MEMO_COMEX_NATIVE_REACTION_CONTROL_SUPPORT_REPAIR_2026-08-19.md`
- `xau-multiyear/docs/CHECKPOINT_COMEX_NATIVE_REACTION_SOURCE_LAST30_PROVENANCE_CORRECTION_2026-08-19.md`

The original insufficient/contact-minute-leaking preoutcome matched manifest remains permanently superseded and non-executable.

## Source-last30 provenance correction carried into the final freeze

The final builder reconciled the recoverable full guarded historical QA artifact against a fresh reconstruction from the already-owned canonical source raw artifacts.

Final reconciled provenance:

- source sessions: **92**
- positive source-final30 windows: **87**
- missing source-final30 windows: **5**
- flat-but-present windows: **0**
- missing source dates:
  - `2011-07-04`
  - `2011-11-24`
  - `2012-11-23`
  - `2014-06-13`
  - `2015-04-01`

Exactly three defined-approach events occur in the early branch and therefore require the missing source-final30 fallback covariate:

- `8b282f806357a5b0d94b6359` — source `2011-07-04`, minute 0
- `3fbeb0c82e6201099ba1b73d` — source `2011-11-24`, minute 0
- `e300d541f2330b5cd3245ce1` — source `2011-11-24`, minute 0

All three are deterministically classified:

`FALLBACK_COVARIATE_MISSING_SOURCE_LAST30`

They remain in descriptive inventory and in the defined-approach support denominator, but are primary-control ineligible/unmatched. No imputation or substitute window is used.

The other contacts sourced from the five missing-window dates are mature and therefore use the strict pre-`m0` J+1 branch; source-final30 does not enter their matching covariates.

## Stable-IID expanded control pool QA

Final zero-outcome parity gate:

- stable same-IID directly testable blocks: **85**
- exact OHLCV parity: **85/85**
- parity failures: **0**
- `stable_parity_all_pass=true`

The final universe retains `PRIOR_CLOSE_ONLY` exclusively. `BAR_OPEN_FALLBACK` is absent and prohibited.

Generic already-owned context anchors retain their matched-reference status and explicit native-contact-registry limitation as required by the repair memo.

## Final regenerated support

Final guarded support after the corrected missingness policy:

- exact-contact Track-A population: **238**
- defined-approach events: **235**
- primary-control eligible events: **231**
- fully K=5 matched events: **227**
- matched treated dates: **81**
- full K=5 match rate among defined-approach events: **96.59574468085106%**

All five frozen support criteria pass:

- matched events >=160: PASS
- matched treated dates >=60: PASS
- every source year has >=5 matched treated dates: PASS
- >=85% of defined-approach contacts receive K=5: PASS
- every source year has >=75% full K=5 match rate: PASS

Final support status:

`SUPPORT_GATE_REPAIRED_AND_PASS`

This is a design-support result only. It is not a reaction edge, win rate, or expectancy result.

## Support by source year

| Source year | Defined | Eligible | K=5 matched | Full-match rate | Matched dates |
|---|---:|---:|---:|---:|---:|
| 2011 | 31 | 28 | 28 | 90.3225806452% | 11 |
| 2012 | 26 | 26 | 26 | 100.0000000000% | 10 |
| 2013 | 27 | 27 | 27 | 100.0000000000% | 10 |
| 2014 | 25 | 25 | 21 | 84.0000000000% | 8 |
| 2015 | 22 | 21 | 21 | 95.4545454545% | 10 |
| 2016 | 31 | 31 | 31 | 100.0000000000% | 10 |
| 2017 | 33 | 33 | 33 | 100.0000000000% | 11 |
| 2018 | 40 | 40 | 40 | 100.0000000000% | 11 |

## Matching/dependence QA

- K fixed at 5 distinct control source dates per matched treated event
- exact source year retained
- same 30-minute minute-of-session bin retained
- same approach sign retained
- source-range caliper `[0.5,2.0]` retained
- mature strict-pre-`m0` local30 caliper `[0.5,2.0]` retained
- early source-final30 caliper `[0.5,2.0]` retained
- ±60-minute exclusion around every exact native contact known in the frozen registry retained
- early `d_move`: `NOT_APPLICABLE`, omitted from the ranking tuple
- treated contact-minute values used for matching: **false**
- maximum selected rows reusing one control source date: **8**
- unique control source dates used by the final K=5 manifest: **751**

Control-date reuse remains a dependence diagnostic; the frozen treated-date inference from the Pro memo remains unchanged.

## Hard guard

Final machine-readable guard:

`xau-final-results/comex_dev_rank1_native_reaction_preoutcome_final_v1/preoutcome_guard.json`

Final values:

- `post_contact_values_used_for_matching=false`
- `post_anchor_outcomes_read=false`
- `reaction_outcomes_computed=false`
- `mfe_mae_computed=false`
- `market_data_api_called=false`
- `market_data_download_performed=false`
- `bar_open_fallback_used=false`
- `source_last30_reconciliation_pass=true`
- `stable_parity_all_pass=true`
- `support_gate_status=SUPPORT_GATE_REPAIRED_AND_PASS`
- `reaction_outcome_execution_authorized_by_this_run=false`

## Frozen executable artifacts

Canonical directory:

`xau-final-results/comex_dev_rank1_native_reaction_preoutcome_final_v1/`

Key files include:

- `source_session_causal_provenance.csv`
- `source_last30_reconciliation.json`
- `treated_event_causal_context_final.csv`
- `session_adjacency_manifest.csv`
- `reserved_date_exclusions.csv`
- `control_block_provenance.csv`
- `continuous_vs_raw_n1_parity.csv`
- `control_candidate_universe_2011.csv.gz`
- `control_candidate_universe_2012.csv.gz`
- `control_candidate_universe_2013.csv.gz`
- `control_candidate_universe_2014.csv.gz`
- `control_candidate_universe_2015.csv.gz`
- `control_candidate_universe_2016.csv.gz`
- `control_candidate_universe_2017.csv.gz`
- `control_candidate_universe_2018.csv.gz`
- `matched_control_manifest.csv`
- `treated_event_support.csv`
- `matching_filter_counts.csv`
- `support_by_year.csv`
- `support_by_date.csv`
- `control_date_reuse.csv`
- `preoutcome_guard.json`
- `preoutcome_freeze_manifest.json`
- `preoutcome_freeze_manifest.sha256`
- `FREEZE_PUBLICATION.json`

## Canonical commits and freeze binding

Generation/run head SHA:

`6af6027305080c1251904a3753248248245cb856`

Atomic artifact freeze commit:

`6ca89054cffffca6a93f7c973d0f9230b4690994`

SHA-256 of `preoutcome_freeze_manifest.json`:

`c202ed717f60dffc7ac06998e2bcbef024c700617728568217edad38424c1028`

Frozen 368-level contact-status SHA-256 remains:

`8a825b0bc1deba51959b78ab6e62206fe49232e76329558e83949bf6d3d4151a`

Selected generated-output SHA-256 bindings:

- `source_session_causal_provenance.csv`: `be58048063468ceb2129a9888448355d26ce468dcc81be19d3eda1d477120bfe`
- `source_last30_reconciliation.json`: `421866d78535a75883efaad2f19fa4ba45f8fa5d52c51ef5ba83787dfa737637`
- `treated_event_causal_context_final.csv`: `17725edab24fdea6755b20135c50f4ef4f7c9e272bcd2c8990a5c57a19423777`
- `control_block_provenance.csv`: `a58a19a67dcc709ae571deaa1de052adfdf2d56b7479d0104ba6783920b97c21`
- `continuous_vs_raw_n1_parity.csv`: `ff98277ea8fb9cdce7c864298cdc0de5e8250e46c9d0658c62ac960069055597`
- `matched_control_manifest.csv`: `ca0a27647e8ff1a0b832923d777ae66da14dcb10db755841c4b359c3b80b87e`
- `treated_event_support.csv`: `47d6ee14e6b149e7966d35fd5611a37ebd68d423a583f932f181972dca96cc2b`
- `support_by_year.csv`: `0c61f715e95ac076960f98384062dfbba6b7eaa9a3bd2c9a5cb9b3fc3b30f39d`
- `control_date_reuse.csv`: `5e3b2dfe2ede4cb1ee2fe8e57cf2cf25d28fef1fbffbddaa4ce1a110fe25c2d4`
- `preoutcome_guard.json`: `167d29c6bb6471a63bc22a86477b98239d83ab7c2d947eadfc52dc65c7d040bd`

The eight yearly control-universe shard hashes are bound in `preoutcome_freeze_manifest.json`.

## Locked state at this checkpoint

- final repaired pre-outcome universe: **FROZEN**
- final deterministic K=5 manifest: **FROZEN**
- support gate: **PASS**
- W15 opened: **false**
- reaction outcomes computed: **false**
- DEV_RANK2: CLOSED
- RETRO_CONFIRM / CONFIRM: CLOSED
- LOCKED_COMEX_TEST: CLOSED
- Track B J+2+: CLOSED
- XAUUSD economic mapping: CLOSED
- new market-data spend: NONE

## Next permitted action

The methodological/support prerequisite for Track-A reaction extraction is now satisfied.

The next permitted action is a mechanical Track-A outcome execution using **only** the frozen protocol, frozen event context, frozen K=5 matched-control manifest, frozen normalizer/provenance, and fixed inference/multiplicity/promotion rules.

This checkpoint deliberately stops before that action. W15 remains unopened here.
