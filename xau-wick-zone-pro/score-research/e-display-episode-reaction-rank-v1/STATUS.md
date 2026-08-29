# E display episode reaction rank V1 — status

**Updated:** 2026-08-29  
**Scope:** XAUUSD M1, BUY, US 08:00–17:00 America/New_York  
**Candidate:** `E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1`

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
- Prospective-confirmation planning: `COMPLETE_AND_FROZEN`
- Prospective planning QA: `PROSPECTIVE_PLANNING_QA_PASS`
- Prospective planning canonical seal: `E_DISPLAY_EPISODE_V1_PROSPECTIVE_PLANNING_CANONICAL_SEAL_PASS`
- Current checkpoint: `READY_FOR_PRO_PRE_PROSPECTIVE_EXECUTION_GATE`
- Prospective collection execution: `NOT_AUTHORIZED`
- Prospective reaction outcomes: `CLOSED`
- Prospective performance statistics: `CLOSED`
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

Interpretation remains constrained: the frozen candidate is a **width-dominated reaction rank** in the upper-Z4-conditioned local top-3 displayed-E universe. It is not a universal intrinsic E-strength score and does not establish trading profitability.

## Prospective planning canonical authority

Canonical seal:

`PROSPECTIVE_PLANNING_CANONICAL_SEAL.json`

Seal commit:

`cacac18ab55cd8162b4dce24e14e2710320f88bc`

Seal commit timestamp:

`2026-08-29T20:24:32Z`

The seal therefore precedes the frozen prospective start `2026-08-31T12:00:00Z`.

Two-stage planning evidence:

- method commit: `1b84889b389d03a0ae79595cb9b58865a1934c27`
- QA materialization commit: `b429bd0fac77ba9e3b2307c61672a1031c18c066`
- QA workflow: `.github/workflows/xau-e-prospective-planning-v1-r2.yml`
- QA workflow run: `33273228430`
- run number / attempt: `2 / 1`
- QA job: `99155361926` (`planning-qa-r2`)
- run conclusion: `success`
- artifact: `9720724299`
- artifact name: `xau-e-prospective-planning-v1-r2`
- artifact digest: `sha256:c12623d52dd75bbd890c0cb5b084613a90ca9b668ff86b5d418c510fa7ed4335`

Frozen prospective start if the next Pro gate authorizes execution:

- first eligible session: `2026-08-31`
- New York open: `08:00 America/New_York`
- UTC open: `2026-08-31T12:00:00Z`
- no backfill before start
- pre-start data permitted only as causal warm-up

Frozen single checkpoint:

- minimum represented NY sessions: `90`
- minimum model-eligible primary contacts: `1000`
- lock at the first completed accepted session where both thresholds are satisfied
- no interim performance peeking
- no discretionary extension or early stop

## Causal warm-up repair frozen before prospective execution

Historical dry-run QA exposed a source-semantics requirement already present in the frozen E generator:

- Z4 active-M1 lookback: `1440`
- additional pre-session C5 landmarks after that lookback: `96`

The prospective archive now uses the latest causal active-M1 start that leaves exactly 96 eligible pre-session C5 landmarks after the 1,440-active-M1 lookback. This rule uses only pre-session information and is frozen in:

`XAUUSD_E_DISPLAY_EPISODE_PROSPECTIVE_PLANNING_QA_ADDENDUM_A_WARMUP_AND_NUMERICAL_TOLERANCE_2026-08-29.md`

## Final historical dry-run QA

Preselected session: `2026-07-15`.

- session M1 rows: `540`
- missing M1: `0`
- warm-up rows: `2520`
- eligible pre-session C5 landmarks: `96`
- Z4 rows: `459`
- exact historical Z4 parity: `PASS`
- Z4 prefix invariance to later bars: `PASS`
- prospective feature rows: `209`
- exact canonical feature parity: `PASS`
- display episodes: `164`
- primary contacts: `78`
- model-eligible primary contacts: `78`
- exact contact-only parity: `PASS`
- post-contact bars read by contact counter: `0`
- prospective outcomes generated: `false`
- prospective outcomes read: `false`

## Width-only interpretation control

`zone_width_v` remains a deterministic interpretation-only comparator.

- gating: `false`
- rescue allowed: `false`
- model selection allowed: `false`
- historical cross-serialization QA tolerance: `5e-7` only
- observed width-AUC recomputation delta: `4.6615795046278663e-7`
- observed full-minus-width delta: `4.6615795046278663e-7`
- this tolerance is **not** a prospective scientific pass threshold

## Anti-peeking / execution state

- Collector exists only as `prospective_collection_workflow_TEMPLATE_v1.yml`.
- It is **not** installed as a live scheduled workflow.
- `prospective-live-v1/` does not exist at the planning seal.
- The collector does not invoke the frozen reaction labeler.
- The collector does not invoke the prospective checkpoint evaluator.
- Unauthorized prospective outcome evaluation fails closed.
- No prospective reaction outcome or prospective performance statistic has been generated or read.

## Mandatory next checkpoint

The **Très élevé** prospective-planning phase is complete.

Next mode: **Pro**.

The next Pro review has one purpose only: audit the frozen prospective-planning package and decide either:

- `GO_PROSPECTIVE_CONFIRMATION_EXECUTION`, or
- `NO_GO_PROSPECTIVE_CONFIRMATION_EXECUTION`.

If Pro returns GO, execution remains limited to **outcome-blind prospective collection until the mechanically locked single checkpoint**. Even then, reaction outcomes remain unopened until the separately frozen checkpoint-opening conditions and authorization are satisfied.
