# E display episode reaction rank V1 — status

**Updated:** 2026-08-29  
**Scope:** XAUUSD M1, BUY, US 08:00–17:00 `America/New_York`  
**Candidate:** `E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1`

## Current scientific state

- Canonical outcome-free package: `PASS`
- DEV phase and freeze: `COMPLETE_AND_FROZEN`
- Historical replication and freeze: `COMPLETE_AND_FROZEN`
- Pro post-replication gate: `PASS`
- Prospective planning R4: `PROSPECTIVE_PLANNING_QA_R4_PASS`
- Prospective planning canonical seal: `PASS`
- Pro pre-prospective execution gate: `PASS`
- Current authorization: `GO_PROSPECTIVE_CONFIRMATION_EXECUTION`
- Authorization scope: `OUTCOME_BLIND_COLLECTION_UNTIL_LOCKED_SINGLE_CHECKPOINT`
- Prospective collection: `AUTHORIZED`
- Prospective start: `2026-08-31 08:00 America/New_York / 12:00 UTC`
- Backfill before start: `FORBIDDEN`
- Prospective reaction outcomes before checkpoint: `CLOSED`
- Prospective performance before checkpoint: `CLOSED`
- Frozen DEV model refit: `FORBIDDEN`
- Post-DEV / post-replication tuning: `FORBIDDEN`
- Production authorization: `NONE`
- Pine modification: `FORBIDDEN`

## Canonical historical authorities

### DEV

- Run: `33264659057`
- Artifact: `9718487805`
- Artifact digest: `sha256:481ad65013241f4dfcdb4f2378f4168476bb92695519de00166149c4a5ac6c0e`
- Frozen model SHA-256: `72e7548de826e2ae2ba66ddcaaf6b2fa7cd35ada0f5f2cd9db585d9734fd48e1`

### Historical replication

- Run: `33266656414`
- Artifact: `9719184524`
- Artifact digest: `sha256:734bd0e14f9017dc23822175aa21bc341cfa5b27b5058dc5e028eb5fb5997688`
- Primary contacts: `17,454`
- Sessions: `257`
- AUC: `0.5657692600871821`
- Q4-Q1: `0.147605`
- Model refit: `NO`

Historical evidence supports prospective confirmation only. It does not establish production readiness or trading profitability.

## Canonical prospective planning authority

- Seal path: `PROSPECTIVE_PLANNING_CANONICAL_SEAL.json`
- Seal SHA-256: `f088d1a18f5686c628e9e00811438dff09902c38290c84ce8c946a5e55d4d49a`
- Seal commit: `92ec56635234ce791f702747b1343e954ad3a8ff`
- Method commit: `786342cfb69aaceff17cbcfb6284bb8c4d611d0d`
- QA materialization commit: `3b07f5eef345bcb353c159b55bf501701049fd52`
- QA run: `33275153603`
- QA artifact: `9721274589`
- QA artifact digest: `sha256:6765d3d5d10854cf5b9437584e5cdc5485897a86f5a2b75e78877e0b66263ccf`
- QA manifest: `prospective-planning-v1/qa-r4/PROSPECTIVE_PLANNING_QA_R4.json`

R4 closes the pre-execution source-atomicity, persistence/resume, concurrency, zero-contact-session, checkpoint-list and final contact-parity gaps. No prospective outcome was generated or read during planning or the Pro gate.

## Pro pre-execution authority

- Decision file: `E_DISPLAY_EPISODE_V1_PRO_PRE_PROSPECTIVE_EXECUTION_GATE.json`
- Memo: `XAUUSD_E_DISPLAY_EPISODE_PRO_PRE_PROSPECTIVE_EXECUTION_GATE_2026-08-29.md`
- Decision: `GO_PROSPECTIVE_CONFIRMATION_EXECUTION`
- Scope: `OUTCOME_BLIND_COLLECTION_UNTIL_LOCKED_SINGLE_CHECKPOINT`
- Gate commit: `efa2d4ecea3e4c15e0e5e7f2e1058f00cb11c9c8`

## Active prospective protocol

### Collector

- Workflow: `.github/workflows/xau-e-prospective-collector-v1.yml`
- Template SHA-256: `77d1268a9319001b6327136dfaf39d54da7b527e95d0de72c8a7da388768a679`
- Schedule: `23:30 UTC`, Monday–Friday
- Concurrency: single non-cancelling collector
- Source: exact-commit-pinned Dukascopy BID M1 mirror
- First accepted session bytes: immutable
- Revisions: append-only
- Valid zero-contact sessions: represented
- Reaction labeler in collector: `FORBIDDEN`
- Checkpoint evaluator in collector: `FORBIDDEN`

### Single checkpoint

The first completed accepted NY session where both thresholds are true:

- represented sessions `>= 90`;
- model-eligible primary contacts `>= 1000`.

The lock includes the exact sorted represented-session list. No performance may be viewed before it exists.

### Final checkpoint evaluator

- SHA-256: `2facd467b9276a48c6c558677c3f2bd81ebf1dca7560c51d599b8a078bd41524`
- Exact contact-counter parity: mandatory
- Frozen-model scored count must equal lock count
- Model refit: forbidden
- Result package: immutable and hashed

## Interpretation constraint

The candidate is a **width-dominated reaction rank** for the upper-Z4-conditioned local top-3 displayed-E universe. It is not a calibrated probability, a universal E-strength score or proof of a profitable trading strategy.

## Next checkpoint

Until the single lock is reached, only outcome-blind collection/status is authorized.

After the frozen single-checkpoint result package exists, stop at:

`READY_FOR_PRO_POST_PROSPECTIVE_GATE`

Then perform one Pro scientific review. Production and Pine remain forbidden.
