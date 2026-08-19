# CHECKPOINT — COMEX native reaction source-last30 provenance correction

Date: 2026-08-19  
Repository: `iagency971/twilio-voice-gateway`  
Branch: `agent/xau-comex-acquisition-plan`  
Mode: **OUTCOME-BLIND PROVENANCE CORRECTION**

## Scope

This checkpoint corrects only the provenance/missingness record for the source-session final-30-minute covariate used by the approved early-contact matching fallback.

No W5/W15/W60/SC, NRB, MFE/MAE, terminal displacement, family/year/session reaction ranking, profitability result, entry simulation, or XAUUSD mapping was read or computed. No market-data API call, quote, download, or spend was made.

## Problem discovered by the final pre-outcome rebuild

The first final-v1 rebuild stopped before matching/outcome publication because the then-canonical compact file:

`xau-final-results/comex_dev_rank1_native_reaction_source_last30_zero_qa_v1/source_last30_zero_qa.json`

claimed:

- 92 source sessions;
- 91 positive source-last30 windows;
- 1 missing window;
- sole missing source date `2013-12-25`.

A fresh reconstruction from the already-owned canonical source raw artifacts instead found five missing final-30-minute windows:

- `2011-07-04`
- `2011-11-24`
- `2012-11-23`
- `2014-06-13`
- `2015-04-01`

The hard reconciliation gate correctly stopped the build before any final control manifest or reaction outcome could be published.

## Recovery of the original full guarded QA artifact

The compact JSON's provenance fields were themselves inconsistent. It named run `32263559201` and artifact `9352159692`; neither resolves as the cited artifact. Its cited `job_id=96101250568`, however, belongs to the recoverable guarded workflow run:

- workflow run: `32263213194`
- head SHA: `0209bfe1e1f4fddd97ba4d1c51a9e39434800e14`
- job: `96101250568`
- artifact: `9369117804`
- artifact name: `comex-dev-rank1-native-reaction-source-last30-zero-qa-v1`
- artifact digest: `sha256:6b7166a3ead461c8d1dc72b4313d641395c51bb3fb075977774817a3b00b6a16`

The full artifact contains the four original QA files. Their SHA-256 values are:

- `source_last30_zero_qa.json`: `ddffde11a7f3a34bc6a78ce85127dd97b3ed311095c992db7b9c4efc53425154`
- `source_last30_all_sessions.csv`: `cddd92b044e97d6b052b8df2bf03c60fc01632fa4e29ce65e74b886c568669de`
- `source_last30_nonpositive_sessions.csv`: `3c6b8e33c3b196e1c6ce91486c07f19ff4b1889413bb81e1fa909e05b459ccc5`
- `source_last30_nonpositive_affected_contacts.csv`: `5008cfd25c18a5b7e61fd84828245e3e6568128134d570c7889a3116945f6661`

## Correct guarded source-last30 result

The recoverable full historical artifact and the fresh reconstruction agree:

- source sessions: **92**
- positive source-last30: **87**
- nonpositive/missing: **5**
- missing: **5**
- flat-but-present: **0**
- contacts sourced from those five dates: **11**
- all 11 have defined approach

The five missing source dates are exactly the five listed above. There is no guarded full-artifact evidence for a sole `2013-12-25` missing case.

The compact 91/1 JSON is therefore superseded as incorrect provenance metadata. The canonical JSON has been corrected to bind the recoverable full artifact and the fresh reconstruction.

## Effect on the approved early fallback rule

Source-last30 is used only when `anchor_minute_of_session < 30`. Of the 11 contacted events sourced from the five missing-window dates, exactly **3** are early contacts requiring this fallback:

- `8b282f806357a5b0d94b6359` — source `2011-07-04`, minute 0
- `3fbeb0c82e6201099ba1b73d` — source `2011-11-24`, minute 0
- `e300d541f2330b5cd3245ce1` — source `2011-11-24`, minute 0

The Pro-approved generic missing-covariate rule applies mechanically to all three:

- label `FALLBACK_COVARIATE_MISSING_SOURCE_LAST30`;
- no imputation;
- no contact-minute, post-contact, J+1, alternative-window, adjusted-continuous, XAUUSD/CFD, or other-contract substitute;
- retain descriptively and in the defined-approach support denominator;
- classify as primary-control ineligible/unmatched.

The remaining affected contacts occur at minute >=30 and therefore use the mature strict-pre-`m0` J+1 branch; missing source-last30 does not enter their matching covariates.

## Methodological authorization

The Pro repair memo explicitly states that if final regeneration discovers additional missing/nonpositive source-final30 covariates, the same no-imputation rule applies, support must be recomputed outcome-blind, and W15 remains closed unless every frozen support threshold still passes.

Therefore no new rule is being invented here. This correction applies the already-approved generic missingness rule to the accurately recovered provenance.

## State after correction

- source-last30 provenance correction: COMPLETE
- reaction outcomes opened: **NO**
- final repaired K=5 universe frozen: **NOT YET**
- W15 authorized: **NO**
- DEV_RANK2 / RETRO_CONFIRM / LOCKED_COMEX_TEST: CLOSED
- new market-data spend: NONE

Next allowed action: rerun the final outcome-blind pre-outcome builder with the corrected 87/5 provenance, classify the three early missing-covariate contacts deterministically, recompute support only, and proceed to freeze only if every original support criterion still passes.
