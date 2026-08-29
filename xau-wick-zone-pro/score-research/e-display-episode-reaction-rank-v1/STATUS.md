# E display episode reaction rank V1 — status

**Updated:** 2026-08-29  
**Scope:** XAUUSD M1, BUY, US 08:00–17:00 America/New_York

## Current scientific state

- Canonical outcome-free package: `PASS`
- Second Pro pre-outcome gate: `PASS`
- DEV outcome phase: `COMPLETE_AND_FROZEN`
- DEV freeze: `E_DISPLAY_EPISODE_V1_DEV_FREEZE_PASS`
- Pro post-DEV scientific gate: `PASS`
- Current authorization: `GO_HISTORICAL_REPLICATION_DIAGNOSTIC`
- Authorized phase: `HISTORICAL_REPLICATION_DIAGNOSTIC_ONLY`
- Historical replication outcomes: `AUTHORIZED_BUT_NOT_YET_OPENED`
- Frozen DEV model refit: `FORBIDDEN`
- Post-DEV tuning: `FORBIDDEN`
- Prospective outcomes: `CLOSED`
- Production authorization: `NONE`
- Pine modification: `FORBIDDEN`

## Canonical DEV authority

- DEV execution strategy: `MONTHLY_SHARDED_EXACT_FROZEN_LABELER`
- DEV workflow run: `33264659057`
- DEV artifact: `9718487805`
- DEV artifact digest: `sha256:481ad65013241f4dfcdb4f2378f4168476bb92695519de00166149c4a5ac6c0e`
- Execution commit: `637ece27b49cc71d0ab972a6d015029ed60a3ddb`
- Materialization commit: `8e9bd3166d1e3bab987fb50fa48052b5101a920e`
- Immutable copy commit: `d1e1a32a06a7ae3f6e039360122f042a0ced5f15`
- Immutable copy directory: `dev-freeze-canonical-33264659057/`
- Frozen DEV model SHA-256: `72e7548de826e2ae2ba66ddcaaf6b2fa7cd35ada0f5f2cd9db585d9734fd48e1`
- DEV canonical seal: `DEV_CANONICAL_SEAL.json`

## Frozen DEV evidence

- Display episodes labeled: `32,745`
- Primary contacts: `16,461`
- Primary NY sessions: `257`
- Favorable-first: `8,044`
- Primary binary failures: `8,417`
- AUC: `0.5756928360690787`
- AUC minus 0.5: `0.07569283606907873`
- Session-cluster 95% CI: `[0.06617732897303763, 0.08517572540579761]`
- Q1 success rate: `0.4282385834109972`
- Q2 success rate: `0.4452906829144453`
- Q3 success rate: `0.4891859052247874`
- Q4 success rate: `0.5927095990279465`
- Q4-Q1: `0.16447101561694932`
- Q4-Q1 session-cluster 95% CI: `[0.14153971131994397, 0.18741550235736845]`
- Feature exclusion rate: `0.0`
- Frozen-score roundtrip: `EXACT`

DEV is model-development evidence, not validation. It is sufficient only to justify the frozen historical replication diagnostic.

## Pro post-DEV gate

- Decision file: `E_DISPLAY_EPISODE_V1_PRO_POST_DEV_GATE.json`
- Memo: `XAUUSD_E_DISPLAY_EPISODE_PRO_POST_DEV_GATE_2026-08-29.md`
- Decision: `GO_HISTORICAL_REPLICATION_DIAGNOSTIC`
- Authorized replication ledger SHA-256: `a3baa2f48b9d397ebcdd3e0be936e5947e49caa4ca77dec531f726c321f586a6`
- Authorized model: immutable DEV model, no refit
- Replication window: `2025-08-01T00:00:00Z <= contact < 2026-08-01T00:00:00Z`

## Mandatory next checkpoint

Switch to **Très élevé** and execute the authorized historical replication diagnostic exactly once under the frozen protocol.

The replication execution must use only the replication ledger, the 12 hash-verified BID M1 files August 2025 through July 2026 and the immutable DEV model. It must retain/report the two known partial sessions and 482 missing M1 opens. No refit, threshold change, subgroup rescue or Pine modification is allowed.

After labels, diagnostics and all QA are frozen and hashed, stop at:

`READY_FOR_PRO_POST_REPLICATION_GATE`

Then return to **Pro** for the post-replication scientific verdict. Historical replication cannot authorize production.
