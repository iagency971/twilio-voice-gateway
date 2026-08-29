# E display episode reaction rank V1 — status

**Updated:** 2026-08-29  
**Scope:** XAUUSD M1, BUY, US 08:00–17:00 America/New_York

## Current scientific state

- Canonical outcome-free package: `PASS`
- Second Pro pre-outcome gate: `PASS`
- DEV outcome phase: `COMPLETE_AND_FROZEN`
- DEV freeze: `E_DISPLAY_EPISODE_V1_DEV_FREEZE_PASS`
- Pro post-DEV scientific gate: `PASS`
- Historical replication phase: `COMPLETE_AND_FROZEN`
- Replication freeze: `E_DISPLAY_EPISODE_V1_REPLICATION_FREEZE_PASS`
- Replication support gate: `PASS`
- Current checkpoint: `READY_FOR_PRO_POST_REPLICATION_GATE`
- Current execution authorization: `NONE_PENDING_PRO_REVIEW`
- Frozen DEV model refit: `FORBIDDEN`
- Post-DEV / post-replication tuning: `FORBIDDEN`
- Prospective execution: `CLOSED`
- Production authorization: `NONE`
- Pine modification: `FORBIDDEN`

## Canonical DEV authority

- DEV workflow run: `33264659057`
- DEV artifact: `9718487805`
- DEV artifact digest: `sha256:481ad65013241f4dfcdb4f2378f4168476bb92695519de00166149c4a5ac6c0e`
- DEV immutable directory: `dev-freeze-canonical-33264659057/`
- Frozen DEV model SHA-256: `72e7548de826e2ae2ba66ddcaaf6b2fa7cd35ada0f5f2cd9db585d9734fd48e1`
- DEV canonical seal: `DEV_CANONICAL_SEAL.json`

## Canonical historical replication authority

- Replication execution strategy: `MONTHLY_SHARDED_EXACT_FROZEN_LABELER`
- Replication workflow run: `33266656414`
- Replication artifact: `9719184524`
- Replication artifact digest: `sha256:734bd0e14f9017dc23822175aa21bc341cfa5b27b5058dc5e028eb5fb5997688`
- Execution commit: `2aa4abf4839558b42f5c999bf9e16127ece5b655`
- Materialization commit: `685efd0dc89e6e71ab542c268f75f76cf8699f76`
- Immutable copy commit: `78af3d80af1a536babef17e05049bc320234c88a`
- Immutable directory: `replication-freeze-canonical-33266656414/`
- Replication canonical seal: `REPLICATION_CANONICAL_SEAL.json`
- Post-replication Pro request: `POST_REPLICATION_PRO_GATE_REQUEST.json`
- Post-replication checkpoint memo: `XAUUSD_E_DISPLAY_EPISODE_POST_REPLICATION_CHECKPOINT_2026-08-29.md`

The replication workflow was removed after canonical freeze to prevent accidental re-execution before Pro review.

## Frozen replication evidence

- Display episodes labeled: `34,007`
- Primary contacts: `17,454`
- Primary NY sessions: `257`
- Favorable-first: `8,649`
- Primary binary failures: `8,805`
- Overall primary success rate: `0.4955311103471983`
- AUC: `0.5657692600871821`
- AUC minus 0.5: `0.06576926008718209`
- Session-cluster 95% CI for AUC minus 0.5: `[0.0568889679606293, 0.0744911973596545]`
- Q1 success rate: `0.4449622725255215`
- Q2 success rate: `0.45660191787558396`
- Q3 success rate: `0.4867630700778643`
- Q4 success rate: `0.5925672594619243`
- Q4-Q1: `0.14760498693640284`
- Q4-Q1 session-cluster 95% CI: `[0.12573139125432922, 0.1692963776824019]`
- Q4-Q1 chronological blocks: `[0.1748121353925043, 0.14119328283607624, 0.13106018437298533]`
- Feature exclusion rate: `0.0`
- Unseen-family rate: `0.0`
- Frozen DEV model loaded without refit: `PASS`
- Known partial sessions retained: `2026-06-19`, `2026-07-03`
- Missing M1 opens retained under frozen rule: `482`

## Frozen replication support gate

All predeclared support checks passed:

- `threshold_episodes_ge_1000`: PASS
- `threshold_sessions_ge_90`: PASS
- `auc_positive`: PASS
- `auc_ci_lower_gt_0`: PASS
- `quartiles_all_nonempty`: PASS
- `quartiles_monotone`: PASS
- `q4_q1_positive`: PASS
- `q4_q1_ci_lower_gt_0`: PASS
- `q4_q1_positive_all_3_blocks`: PASS
- `feature_exclusion_le_2pct`: PASS
- `unseen_family_le_5pct`: PASS

Historical replication is supporting out-of-sample evidence only. It does not authorize production.

## Mandatory next checkpoint

Switch to **Pro** for:

`PRO_POST_REPLICATION_SCIENTIFIC_GATE`

Pro must review the immutable DEV and historical replication evidence and decide only whether the evidence justifies a separately preregistered prospective-confirmation plan:

- `GO_PROSPECTIVE_CONFIRMATION_PLANNING`, or
- `NO_GO_PROSPECTIVE_CONFIRMATION_PLANNING`.

Until that verdict, no prospective outcome execution, model change, threshold change, subgroup rescue, production use or Pine modification is authorized.
