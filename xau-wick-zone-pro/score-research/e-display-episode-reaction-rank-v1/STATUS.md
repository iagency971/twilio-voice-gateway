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
- Pro post-replication scientific gate: `PASS`
- Current authorization: `GO_PROSPECTIVE_CONFIRMATION_PLANNING`
- Authorized phase: `PROSPECTIVE_CONFIRMATION_PROTOCOL_AND_INFRASTRUCTURE_FREEZE_ONLY`
- Prospective outcome execution: `NOT_AUTHORIZED`
- Frozen DEV model refit: `FORBIDDEN`
- Post-DEV / post-replication tuning: `FORBIDDEN`
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

- Replication workflow run: `33266656414`
- Replication artifact: `9719184524`
- Replication artifact digest: `sha256:734bd0e14f9017dc23822175aa21bc341cfa5b27b5058dc5e028eb5fb5997688`
- Execution commit: `2aa4abf4839558b42f5c999bf9e16127ece5b655`
- Materialization commit: `685efd0dc89e6e71ab542c268f75f76cf8699f76`
- Immutable copy commit: `78af3d80af1a536babef17e05049bc320234c88a`
- Immutable directory: `replication-freeze-canonical-33266656414/`
- Replication canonical seal: `REPLICATION_CANONICAL_SEAL.json`

## Frozen replication evidence

- Display episodes: `34,007`
- Primary contacts: `17,454`
- Primary NY sessions: `257`
- Overall primary success rate: `49.5531%`
- AUC: `0.5657692600871821`
- AUC minus 0.5: `0.06576926008718209`
- Session-cluster 95% CI for AUC minus 0.5: `[0.0568889679606293, 0.0744911973596545]`
- Q1: `44.4962%`
- Q2: `45.6602%`
- Q3: `48.6763%`
- Q4: `59.2567%`
- Q4-Q1: `14.7605 percentage points`
- Q4-Q1 session-cluster 95% CI: `[12.5731, 16.9296] percentage points`
- Q4-Q1 chronological blocks: `[17.4812, 14.1193, 13.1060] percentage points`
- Feature exclusion rate: `0.0`
- Unseen-family rate: `0.0`
- Frozen DEV model loaded without refit: `PASS`
- Known partial sessions retained: `2026-06-19`, `2026-07-03`
- Missing M1 opens retained under frozen rule: `482`

All frozen historical-replication support checks passed. Historical replication remains supporting evidence and cannot authorize production.

## Pro post-replication decision

- Decision file: `E_DISPLAY_EPISODE_V1_PRO_POST_REPLICATION_GATE.json`
- Memo: `XAUUSD_E_DISPLAY_EPISODE_PRO_POST_REPLICATION_GATE_2026-08-29.md`
- Interpretive diagnostic: `POST_REPLICATION_PRO_INTERPRETIVE_DIAGNOSTICS.json`
- Decision: `GO_PROSPECTIVE_CONFIRMATION_PLANNING`

The historical evidence supports prospective confirmation of the frozen reaction rank. It does not validate trading profitability or a universal E-strength score.

A mandatory semantic caveat is now recorded: the frozen score is almost entirely driven by `zone_width_v`. The future plan must include a deterministic width-only comparator as an interpretation control, without changing or rescuing the primary candidate.

## Mandatory next checkpoint

Switch to **Très élevé** and build the complete prospective-confirmation planning package without opening any prospective outcome.

The planning package must freeze:

- the first eligible prospective-session rule;
- append-only data acquisition and SHA-256 provenance;
- outcome-free feature snapshots;
- the anti-peeking firewall;
- missing/duplicate/revision data rules;
- the single checkpoint at the first completed session satisfying both `>=90` eligible sessions and `>=1000` primary contacts;
- the unchanged model, target, ranks, quartiles, bootstrap and primary gates;
- the separate non-rescue width-only interpretation control;
- synthetic tests, historical dry-runs, environment and immutable hashes.

The planning phase must stop at:

`READY_FOR_PRO_PRE_PROSPECTIVE_EXECUTION_GATE`

Then return to **Pro** for one decision only:

- `GO_PROSPECTIVE_CONFIRMATION_EXECUTION`, or
- `NO_GO_PROSPECTIVE_CONFIRMATION_EXECUTION`.

Until that decision, no prospective label, performance statistic, production use or Pine modification is authorized.
