# XAUUSD — E display episode reaction rank V1 — Pro pre-prospective execution gate

**Gate date:** 2026-08-29  
**Repository:** `iagency971/twilio-voice-gateway`  
**Research branch:** `agent/xau-wick-zone-pro-dev`  
**Default scheduler branch:** `main`  
**Scope:** XAUUSD M1, BUY, US 08:00–17:00 `America/New_York`  
**Gate:** `PRO_PRE_PROSPECTIVE_EXECUTION_GATE`  
**Production authorization:** NONE  
**Pine modification:** FORBIDDEN

# Decision

## `GO_PROSPECTIVE_CONFIRMATION_EXECUTION`

The R4 prospective-confirmation planning package and the installed default-branch scheduler are scientifically and operationally adequate to begin genuinely prospective, outcome-blind collection on the frozen candidate.

The authorization scope is exactly:

`OUTCOME_BLIND_COLLECTION_UNTIL_LOCKED_SINGLE_CHECKPOINT`

This gate authorizes source acquisition, causal geometry, outcome-free features and frozen scores, first-contact-only counting, restricted status reporting and mechanical checkpoint locking. It does **not** authorize the collector—or any other process—to generate, read or score prospective reaction outcomes.

When the mechanical checkpoint lock exists, the process must stop at:

`READY_FOR_PRO_AT_LOCKED_PROSPECTIVE_CHECKPOINT`

A separate later Pro gate is required before the sealed checkpoint evaluator may be run once. Therefore, no performance opening is pre-authorized by the present gate.

This decision does **not** validate the score, establish trading profitability, authorize production, or authorize a Pine change.

# Why the earlier planning seal was not accepted unchanged

During the Pro review, the first planning package exposed seven implementation risks:

1. a moving-branch race between source download and source metadata;
2. no guarantee that the first accepted source bytes survived a later calculation failure;
3. an incomplete session could be skipped permanently on the next run;
4. scheduled and manual collectors could overlap;
5. valid zero-Z4, zero-candidate or zero-contact sessions could be silently excluded;
6. the checkpoint lock did not contain the exact represented-session list;
7. the final evaluator did not require exact parity with the pre-checkpoint contact-only archive.

No prospective collection or outcome had started, so these points were repaired outcome-blind and the complete package was rerun before authorization.

# R4 planning evidence accepted

Canonical authority:

- method commit: `786342cfb69aaceff17cbcfb6284bb8c4d611d0d`;
- QA materialization commit: `3b07f5eef345bcb353c159b55bf501701049fd52`;
- planning QA run: `33275153603`;
- planning QA conclusion: `success`;
- planning artifact: `9721274589`;
- planning artifact digest: `sha256:6765d3d5d10854cf5b9437584e5cdc5485897a86f5a2b75e78877e0b66263ccf`;
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

# Final Pro execution-gate evidence

The authoritative execution decision is:

`E_DISPLAY_EPISODE_V1_PRO_PRE_PROSPECTIVE_EXECUTION_GATE.json`

Independent QA is recorded in:

`PRO_PRE_PROSPECTIVE_EXECUTION_INDEPENDENT_QA.json`

Final successful authority:

- workflow run: `33278660304`;
- workflow head: `b2199e27c4ce4d57e46c0108b25007f957d2b04f`;
- conclusion: `success`;
- artifact: `9722291765`;
- artifact digest: `sha256:15433fe0117b31b6a29df84f850ce2d05ca8041311d099e022dde4d0ce203380`;
- gate JSON SHA-256: `4ee1c7d3a36baa0583b8c81d8de8c075d1c32222c9deec1207bf4e91f6d10e30`;
- independent QA JSON SHA-256: `a31f97638dbe2164b55ff0667462549a0c9dfe1fd18f9754786ef092733bde51`;
- publication commit: `40f128e8d1e1eb1abcaeee4ca136fb4e430106b0`.

The immediately preceding run `33278427735` had already passed the canonical R4 authority/artifact check, frozen environment, synthetic fail-closed tests, anti-peeking tests, gate materialization and artifact upload. Only its final repository publication command failed after the evidence was frozen. The successful final run verified that predecessor run and artifact byte-for-byte, regenerated the current immutable authority, uploaded a new artifact and completed the publication.

# Prospective start

The first eligible evidence session is fixed as:

- NY session date: `2026-08-31`;
- open: `2026-08-31 08:00 America/New_York`;
- UTC: `2026-08-31T12:00:00Z`.

No earlier August 2026 session can be backfilled. Earlier data may be used only as causal warm-up. Manual execution before the start timestamp fails closed.

# Active outcome-blind collector

The scheduled workflow that GitHub can execute is installed on the default branch:

`.github/workflows/xau-e-v1-prospective-outcome-blind-collector.yml`

Authority:

- branch: `main`;
- Git blob: `54ac6ea78529ce10dc3d405806d90e016a507b6e`;
- SHA-256: `24311ebb10f946669c8ed80ff328336d01f3f17faf5c9bf23b022fcfa417db52`;
- schedule: `30 23 * * 1-5` UTC;
- concurrency: one non-cancelling collector.

The exact sealed scientific reference remains on the research branch:

`.github/workflows/xau-e-prospective-collector-v1.yml`

It is byte-identical to:

`prospective-planning-v1/prospective_collection_workflow_TEMPLATE_v1.yml`

Template authority:

- Git blob: `83a41bc3fed25a7fb77b8b2c6d6d570626b24f9b`;
- SHA-256: `77d1268a9319001b6327136dfaf39d54da7b527e95d0de72c8a7da388768a679`.

The active default-branch workflow is an operational wrapper around that sealed R4 method. It does not change the scientific method, features, target, model, thresholds, geometry or contact rules.

Before first source processing, the active collector must verify:

- its own workflow reference, Git blob and SHA-256;
- the successful Pro gate run and exact gate artifact bytes;
- the planning seal and every frozen method hash;
- the frozen model, labeler, evaluator, environment lock and Z4 engine;
- the prospective start timestamp.

It then commits a durable authorization anchor before touching source data.

For every source observation, it:

- pins one exact upstream commit;
- downloads monthly files at that exact commit;
- verifies the Git blob from downloaded bytes;
- records SHA-256, byte length, row count, time range, commit, blob and observation time;
- selects only the current and previous monthly files needed by the session;
- preserves and commits the first accepted canonical session before downstream calculations;
- resumes incomplete sessions;
- records changed-source revisions without overwriting canonical bytes;
- suppresses duplicate revision events;
- represents valid zero-Z4, zero-candidate and zero-contact sessions;
- stores only outcome-free features, frozen scores and contact-only rows.

The collector cannot invoke the reaction labeler or checkpoint evaluator.

# Single checkpoint

Outcome generation and performance remain closed until the first completed accepted NY session where both are true:

- at least 90 represented eligible sessions;
- at least 1,000 model-eligible primary contacts.

The lock contains the exact sorted list of represented session dates. Valid zero-contact sessions count toward the session threshold. There is no interim performance access, discretionary early stop or discretionary extension.

# Later locked-checkpoint integrity gate

The frozen evaluator SHA-256 is:

`2facd467b9276a48c6c558677c3f2bd81ebf1dca7560c51d599b8a078bd41524`

It remains dormant. At the locked checkpoint, a separate Pro review must first verify the lock, archive and firewall. Only if that later gate explicitly authorizes opening may the evaluator reproduce the contact-only archive exactly on:

- selection status for every display episode;
- first-contact timestamp for every primary contact;
- feature-row SHA-256 for every primary contact.

The eligible contact count in the lock must equal the number actually scored by the frozen DEV model. Any discrepancy fails closed. Model refit, recalibration, alternative models, subgroup rescue and post-hoc cleaning remain forbidden.

# Frozen science

Unchanged authorities:

- DEV model SHA-256: `72e7548de826e2ae2ba66ddcaaf6b2fa7cd35ada0f5f2cd9db585d9734fd48e1`;
- reaction labeler SHA-256: `08ed29422ede890c300073789daa4669a22fbe48b74171c68402310c00aebef8`;
- model/evaluation SHA-256: `f547853609f16b00080049629f708fc0d4170c54071fd22a99228c807cd6dd2e`;
- features: `zone_width_v`, `display_persistence_c5`, `current_family`;
- target, arming/contact rules, 30-available-bar horizon and ambiguity handling;
- DEV rank mapping and quartiles;
- session-cluster bootstrap and prospective pass rule.

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

When the single checkpoint lock exists:

`READY_FOR_PRO_AT_LOCKED_PROSPECTIVE_CHECKPOINT`

Only a later Pro gate may authorize the single outcome opening. After a separately authorized evaluator run and immutable result freeze, the state may become:

`READY_FOR_PRO_POST_PROSPECTIVE_GATE`

Production and Pine remain forbidden throughout unless a later explicit decision changes them.
