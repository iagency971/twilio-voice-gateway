# XAUUSD — E display episode reaction rank V1 — Pro pre-prospective execution gate

**Gate date:** 2026-08-29  
**Repository:** `iagency971/twilio-voice-gateway`  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Scope:** XAUUSD M1, BUY, US 08:00–17:00 `America/New_York`  
**Gate:** `PRO_PRE_PROSPECTIVE_EXECUTION_GATE`  
**Production authorization:** NONE  
**Pine modification:** FORBIDDEN

# Decision

## `GO_PROSPECTIVE_CONFIRMATION_EXECUTION`

The R4 prospective-confirmation planning package is scientifically and operationally adequate to begin genuinely prospective, outcome-blind collection on the frozen candidate.

The authorization scope is exactly:

`OUTCOME_BLIND_COLLECTION_UNTIL_LOCKED_SINGLE_CHECKPOINT`

It also pre-authorizes exactly one performance opening by the sealed checkpoint evaluator, and only after the mechanical checkpoint lock exists and all final integrity checks pass. The collector itself cannot invoke the reaction labeler or evaluator.

This decision does **not** validate the score, establish trading profitability, authorize production, or authorize a Pine change.

# Why the earlier planning seal was not accepted unchanged

During this Pro review, the first planning package exposed seven implementation risks:

1. a moving-branch race between source download and source metadata;
2. no guarantee that the first accepted source bytes survived a later calculation failure;
3. an incomplete session could be skipped permanently on the next run;
4. scheduled and manual collectors could overlap;
5. valid zero-Z4, zero-candidate or zero-contact sessions could be silently excluded;
6. the checkpoint lock did not contain the exact represented-session list;
7. the final evaluator did not require exact parity with the pre-checkpoint contact-only archive.

No prospective collection or outcome had started, so these points were repaired outcome-blind and the complete package was rerun before this decision.

# R4 evidence accepted

Canonical authority:

- method commit: `786342cfb69aaceff17cbcfb6284bb8c4d611d0d`;
- QA materialization commit: `3b07f5eef345bcb353c159b55bf501701049fd52`;
- workflow run: `33275153603`;
- workflow conclusion: `success`;
- artifact: `9721274589`;
- artifact digest: `sha256:6765d3d5d10854cf5b9437584e5cdc5485897a86f5a2b75e78877e0b66263ccf`;
- QA status: `PROSPECTIVE_PLANNING_QA_R4_PASS`.

The R4 dry-run reproduced the frozen historical pipeline on 2026-07-15:

- 540 US-session M1 rows;
- 2,520 warm-up rows;
- exactly 96 pre-session C5 landmarks after the 1,440-active-M1 lookback;
- 459 Z4 rows with exact geometry parity;
- exact Z4 prefix invariance after adding later bars;
- 209 feature rows with exact parity;
- 164 display episodes;
- 78 primary contacts with exact contact-only parity;
- 0 post-contact bars read by the contact counter;
- no prospective outcome generated or read.

Expanded synthetic tests also pass for append-only first acceptance, duplicate-revision suppression, zero-contact-session representation, checkpoint session-list locking, pre-start rejection and the anti-peeking firewall.

# Canonical planning seal

The accepted seal is:

`PROSPECTIVE_PLANNING_CANONICAL_SEAL.json`

SHA-256:

`f088d1a18f5686c628e9e00811438dff09902c38290c84ce8c946a5e55d4d49a`

Seal commit:

`92ec56635234ce791f702747b1343e954ad3a8ff`

The seal predates the prospective start.

# Prospective start

The first eligible evidence session is fixed as:

- NY session date: `2026-08-31`;
- open: `2026-08-31 08:00 America/New_York`;
- UTC: `2026-08-31T12:00:00Z`.

No earlier August 2026 session can be backfilled. Earlier data may be used only as causal warm-up.

# Outcome-blind collector

The installed workflow must be byte-identical to the sealed template:

`prospective-planning-v1/prospective_collection_workflow_TEMPLATE_v1.yml`

Template SHA-256:

`77d1268a9319001b6327136dfaf39d54da7b527e95d0de72c8a7da388768a679`

The collector:

- observes one exact upstream commit per run;
- downloads monthly files at that exact commit;
- verifies the Git blob from the downloaded bytes;
- records SHA-256, byte length, row count, commit, blob and observation time;
- preserves the first accepted canonical session before downstream calculations;
- resumes incomplete sessions;
- records changed-source revisions without overwriting the canonical bytes;
- suppresses duplicate revision events;
- uses a single non-cancelling concurrency group;
- accepts valid zero-contact sessions as represented sessions;
- stores only outcome-free features, frozen scores and contact-only rows.

# Single checkpoint

Performance remains closed until the first completed accepted NY session where both are true:

- at least 90 represented eligible sessions;
- at least 1,000 model-eligible primary contacts.

The lock contains the exact sorted list of represented session dates. Valid zero-contact sessions count toward the session threshold. There is no interim performance access, discretionary early stop or extension.

# Final opening integrity

The frozen evaluator SHA-256 is:

`2facd467b9276a48c6c558677c3f2bd81ebf1dca7560c51d599b8a078bd41524`

At the locked checkpoint it must reproduce the contact-only archive exactly on:

- selection status for every display episode;
- first-contact timestamp for every primary contact;
- feature-row SHA-256 for every primary contact.

The eligible contact count in the lock must equal the number actually scored by the frozen DEV model. Any discrepancy fails closed.

# Frozen science

Unchanged authorities:

- DEV model SHA-256: `72e7548de826e2ae2ba66ddcaaf6b2fa7cd35ada0f5f2cd9db585d9734fd48e1`;
- reaction labeler SHA-256: `08ed29422ede890c300073789daa4669a22fbe48b74171c68402310c00aebef8`;
- model/evaluation SHA-256: `f547853609f16b00080049629f708fc0d4170c54071fd22a99228c807cd6dd2e`;
- features: `zone_width_v`, `display_persistence_c5`, `current_family`;
- target, arming/contact rules, 30-available-bar horizon and ambiguity handling;
- DEV rank mapping and quartiles;
- session-cluster bootstrap and prospective pass rule.

No refit, recalibration, alternative model, subgroup rescue or post-hoc data cleaning is allowed.

# Mandatory interpretation

The candidate remains a **width-dominated reaction rank** in the upper-Z4-conditioned local top-3 displayed-E universe.

It is not:

- a calibrated probability;
- a universal measure of E strength;
- a demonstrated profitable strategy.

The deterministic width-only comparator remains non-gating and cannot rescue the primary candidate.

# Next state

After this gate:

`PROSPECTIVE_COLLECTION_AUTHORIZED_OUTCOME_BLIND`

After the single locked performance opening and immutable freeze:

`READY_FOR_PRO_POST_PROSPECTIVE_GATE`

Only that later Pro gate may interpret the genuinely prospective result. Production and Pine remain forbidden.
