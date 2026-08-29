# E display episode reaction rank V1 — status

**Updated:** 2026-08-29  
**Scope:** XAUUSD M1, BUY, US 08:00–17:00 America/New_York

## Current scientific state

- Canonical outcome-free package: `PASS`
- Second Pro pre-outcome gate: `PASS`
- DEV outcome phase: `COMPLETE_AND_FROZEN`
- DEV freeze: `E_DISPLAY_EPISODE_V1_DEV_FREEZE_PASS`
- Current checkpoint: `READY_FOR_PRO_POST_DEV_GATE`
- Historical replication outcomes: `CLOSED`
- Historical replication authorization: `NOT_GRANTED`
- Prospective outcomes: `CLOSED`
- Production authorization: `NONE`
- Pine modification: `FORBIDDEN`
- Post-DEV tuning: `FORBIDDEN`

## Canonical DEV authority

- DEV execution strategy: `MONTHLY_SHARDED_EXACT_FROZEN_LABELER`
- DEV workflow run: `33264659057`
- DEV artifact: `9718487805`
- DEV artifact digest: `sha256:481ad65013241f4dfcdb4f2378f4168476bb92695519de00166149c4a5ac6c0e`
- Execution commit: `637ece27b49cc71d0ab972a6d015029ed60a3ddb`
- Materialization commit: `8e9bd3166d1e3bab987fb50fa48052b5101a920e`
- Immutable copy commit: `d1e1a32a06a7ae3f6e039360122f042a0ced5f15`
- Immutable copy directory: `dev-freeze-canonical-33264659057/`
- DEV canonical seal: `DEV_CANONICAL_SEAL.json`
- Post-DEV gate request: `POST_DEV_PRO_GATE_REQUEST.json`

The earlier monolithic DEV run is explicitly non-canonical. Both DEV-opening workflow files have been removed from the branch after the canonical freeze to prevent accidental re-opening/re-fitting before Pro review.

## Frozen DEV evidence

- Display episodes labeled: `32,745`
- Primary contacts: `16,461`
- Primary NY sessions: `257`
- Favorable-first: `8,044`
- Primary binary failures: `8,417`
- AUC - 0.5: `0.07569283606907873`
- Session-cluster 95% CI: `[0.06617732897303763, 0.08517572540579761]`
- Q1 success rate: `0.4282385834109972`
- Q2 success rate: `0.4452906829144453`
- Q3 success rate: `0.4891859052247874`
- Q4 success rate: `0.5927095990279465`
- Q4-Q1: `0.16447101561694932`
- Q4-Q1 session-cluster 95% CI: `[0.14153971131994397, 0.18741550235736845]`
- Feature exclusion rate: `0.0`
- Frozen-score roundtrip: `EXACT`

## Mandatory next checkpoint

Switch to **Pro** for `PRO_POST_DEV_SCIENTIFIC_GATE`.

Pro must review the immutable DEV package and decide only whether to grant `GO_HISTORICAL_REPLICATION_DIAGNOSTIC` or `NO_GO_HISTORICAL_REPLICATION_DIAGNOSTIC`.

Until that verdict, no historical-replication outcome may be generated, read or scored. The frozen DEV model may not be changed.
