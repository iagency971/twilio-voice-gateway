# E display episode reaction rank V1 — status

**Updated:** 2026-08-29  
**Scope:** XAUUSD M1, BUY, US 08:00–17:00 `America/New_York`  
**Candidate:** `E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1`

## Current scientific and operational state

- Canonical outcome-free package: `PASS`
- DEV phase and freeze: `COMPLETE_AND_FROZEN`
- Historical replication and freeze: `COMPLETE_AND_FROZEN`
- Pro post-replication gate: `PASS`
- Prospective planning R4: `PROSPECTIVE_PLANNING_QA_R4_PASS`
- Prospective planning canonical seal: `PASS`
- Pro pre-prospective execution gate: `PRO_PRE_PROSPECTIVE_EXECUTION_GATE_PASS`
- Current authorization: `GO_PROSPECTIVE_CONFIRMATION_EXECUTION`
- Authorization scope: `OUTCOME_BLIND_COLLECTION_UNTIL_LOCKED_SINGLE_CHECKPOINT`
- Active scheduler installation: `COMPLETE`
- Prospective start: `2026-08-31 08:00 America/New_York / 12:00 UTC`
- Backfill before start: `FORBIDDEN`
- Prospective reaction outcomes before a later Pro checkpoint-opening gate: `CLOSED`
- Prospective performance before a later Pro checkpoint-opening gate: `CLOSED`
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
- Q4−Q1: `0.147605`
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

## Final Pro pre-execution authority

- Decision file: `E_DISPLAY_EPISODE_V1_PRO_PRE_PROSPECTIVE_EXECUTION_GATE.json`
- Independent QA: `PRO_PRE_PROSPECTIVE_EXECUTION_INDEPENDENT_QA.json`
- Decision: `GO_PROSPECTIVE_CONFIRMATION_EXECUTION`
- Scope: `OUTCOME_BLIND_COLLECTION_UNTIL_LOCKED_SINGLE_CHECKPOINT`
- Successful gate run: `33278660304`
- Gate workflow head: `b2199e27c4ce4d57e46c0108b25007f957d2b04f`
- Gate artifact: `9722291765`
- Gate artifact digest: `sha256:15433fe0117b31b6a29df84f850ce2d05ca8041311d099e022dde4d0ce203380`
- Gate JSON SHA-256: `4ee1c7d3a36baa0583b8c81d8de8c075d1c32222c9deec1207bf4e91f6d10e30`
- QA JSON SHA-256: `a31f97638dbe2164b55ff0667462549a0c9dfe1fd18f9754786ef092733bde51`
- Publication commit: `40f128e8d1e1eb1abcaeee4ca136fb4e430106b0`

The successful gate verifies the complete R4 evidence chain. The preceding run had already passed the R4 scientific, artifact, frozen-hash, synthetic, fail-closed and anti-peeking steps; only its repository publication command failed. Run `33278660304` verified that frozen predecessor artifact, republished the exact gate evidence, and completed successfully.

## Active prospective protocol

### Active scheduler

- Branch: `main`
- Workflow: `.github/workflows/xau-e-v1-prospective-outcome-blind-collector.yml`
- Workflow Git blob: `54ac6ea78529ce10dc3d405806d90e016a507b6e`
- Workflow SHA-256: `24311ebb10f946669c8ed80ff328336d01f3f17faf5c9bf23b022fcfa417db52`
- Schedule: `23:30 UTC`, Monday–Friday
- Concurrency: single non-cancelling collector
- Source: exact-commit-pinned Dukascopy BID M1 mirror
- Gate run and gate artifact bytes: reverified before first source processing
- Durable authorization anchor: committed before source processing
- First accepted session bytes: immutable and committed before downstream calculation
- Revisions: append-only; duplicate revision events suppressed
- Valid zero-Z4, zero-candidate and zero-contact sessions: represented
- Reaction labeler in collector: `FORBIDDEN`
- Checkpoint evaluator in collector: `FORBIDDEN`

### Sealed scientific collector reference

- Research branch workflow: `.github/workflows/xau-e-prospective-collector-v1.yml`
- Template: `prospective-planning-v1/prospective_collection_workflow_TEMPLATE_v1.yml`
- Template Git blob: `83a41bc3fed25a7fb77b8b2c6d6d570626b24f9b`
- Template SHA-256: `77d1268a9319001b6327136dfaf39d54da7b527e95d0de72c8a7da388768a679`

The active default-branch scheduler is an operational wrapper around the sealed R4 method. It does not change the scientific method, features, target, model, thresholds or contact logic.

### Single checkpoint

The first completed accepted NY session where both thresholds are true:

- represented sessions `>= 90`;
- model-eligible primary contacts `>= 1000`.

The lock includes the exact sorted represented-session list. Valid zero-contact sessions count toward the session threshold. The collector stops extending the primary sample once the lock exists.

### Locked-checkpoint opening

The present gate does **not** authorize generation or reading of prospective reaction outcomes. When `CHECKPOINT_LOCK.json` first exists, stop at:

`READY_FOR_PRO_AT_LOCKED_PROSPECTIVE_CHECKPOINT`

A separate Pro gate must then verify the lock and explicitly authorize the sealed evaluator. Only after that later authorization may the reaction labels and the single prospective performance package be generated once.

The sealed evaluator authority remains:

- SHA-256: `2facd467b9276a48c6c558677c3f2bd81ebf1dca7560c51d599b8a078bd41524`
- Exact contact-counter parity: mandatory
- Frozen-model scored count must equal lock count
- Model refit: forbidden
- Result package: immutable and hashed

## Interpretation constraint

The candidate is a **width-dominated reaction rank** for the upper-Z4-conditioned local top-3 displayed-E universe. It is not a calibrated probability, a universal E-strength score or proof of a profitable trading strategy.

## Next state

Until the lock exists, only outcome-blind collection and restricted status reporting are authorized.

Next state:

`READY_FOR_PRO_AT_LOCKED_PROSPECTIVE_CHECKPOINT`

Production and Pine remain forbidden.
