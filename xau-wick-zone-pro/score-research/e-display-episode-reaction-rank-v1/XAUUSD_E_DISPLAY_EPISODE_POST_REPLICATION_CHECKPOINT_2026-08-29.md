# XAUUSD — E display episode reaction rank V1 — post-replication checkpoint

**Date:** 2026-08-29  
**Scope:** XAUUSD M1 BUY US 08:00–17:00 America/New_York  
**Checkpoint:** `READY_FOR_PRO_POST_REPLICATION_GATE`

## Canonical replication execution

- workflow run: `33266656414`
- execution commit: `2aa4abf4839558b42f5c999bf9e16127ece5b655`
- materialization commit: `685efd0dc89e6e71ab542c268f75f76cf8699f76`
- immutable copy commit: `78af3d80af1a536babef17e05049bc320234c88a`
- artifact: `9719184524`
- artifact digest: `sha256:734bd0e14f9017dc23822175aa21bc341cfa5b27b5058dc5e028eb5fb5997688`
- immutable package: `replication-freeze-canonical-33266656414/`
- canonical seal: `REPLICATION_CANONICAL_SEAL.json`

The downloaded artifact digest was independently rechecked and matched GitHub. All ten evidence-file hashes listed by `REPLICATION_FREEZE_MANIFEST.json` matched the downloaded artifact contents.

## Frozen execution contract actually used

- replication ledger SHA-256: `a3baa2f48b9d397ebcdd3e0be936e5947e49caa4ca77dec531f726c321f586a6`
- frozen DEV model SHA-256: `72e7548de826e2ae2ba66ddcaaf6b2fa7cd35ada0f5f2cd9db585d9734fd48e1`
- reaction labeler SHA-256: `08ed29422ede890c300073789daa4669a22fbe48b74171c68402310c00aebef8`
- model/evaluation SHA-256: `f547853609f16b00080049629f708fc0d4170c54071fd22a99228c807cd6dd2e`
- token: `GO_HISTORICAL_REPLICATION_DIAGNOSTIC`
- model refit: **false**
- DEV labels loaded for selection/refit: **false**
- production authorization: **none**

## Data QA

The replication ledger contains 258 NY sessions. Two known partial sessions were retained exactly as preregistered:

- 2026-06-19: 241 missing M1 opens;
- 2026-07-03: 241 missing M1 opens.

Total missing opens: 482. Missing minutes were skipped as unavailable bars and no post-outcome session deletion was performed.

## Replication population

- displayed episodes: **34,007**
- primary contacts: **17,454**
- primary-contact sessions: **257**
- favorable first: **8,649**
- invalidation first: **8,227**
- ambiguous same bar: **541**
- neither: **37**
- binary success rate: **49.5531%**

## Frozen out-of-sample score evidence

The immutable DEV model was applied without refit.

- AUC: **0.5657692601**
- AUC minus 0.5: **+0.0657692601**
- session-cluster 95% CI for AUC minus 0.5: **[+0.0568889680, +0.0744911974]**

Fixed DEV quartiles applied to replication:

| Quartile | N | Success rate |
|---|---:|---:|
| Q1 | 4,506 | 44.4962% |
| Q2 | 4,067 | 45.6602% |
| Q3 | 4,495 | 48.6763% |
| Q4 | 4,386 | 59.2567% |

- Q4 minus Q1: **+14.7605 percentage points**
- session-cluster 95% CI: **[+12.5731, +16.9296] percentage points**

Three contiguous replication session blocks, using the frozen rule:

- block 1: **+17.4812 pp**
- block 2: **+14.1193 pp**
- block 3: **+13.1060 pp**

Feature exclusion rate: **0%**. Unseen-family rate: **0%**.

## Frozen support gate result

Every predeclared replication-support check passed:

- sample threshold: PASS
- session threshold: PASS
- AUC positive: PASS
- AUC cluster-CI lower bound > 0: PASS
- all four quartiles non-empty: PASS
- Q1 ≤ Q2 ≤ Q3 ≤ Q4: PASS
- Q4−Q1 positive: PASS
- Q4−Q1 cluster-CI lower bound > 0: PASS
- Q4−Q1 positive in all three chronological blocks: PASS
- feature exclusion ≤ 2%: PASS
- unseen-family rate ≤ 5%: PASS

`REPLICATION_SUPPORT_GATE.json` therefore records `pass: true`.

## Interpretation boundary

No scientific promotion decision is made in this checkpoint. Historical replication is supporting out-of-sample evidence only. It cannot authorize production, prospective execution or Pine modification.

The replication execution workflow has been removed after the canonical freeze to prevent accidental rerun or altered re-execution before Pro review.

## Required next action

Switch to **Pro** for:

`PRO_POST_REPLICATION_SCIENTIFIC_GATE`

Pro should review the immutable DEV and replication packages and decide only whether the evidence justifies a separately preregistered prospective-confirmation plan.

Requested decision:

- `GO_PROSPECTIVE_CONFIRMATION_PLANNING`, or
- `NO_GO_PROSPECTIVE_CONFIRMATION_PLANNING`.
