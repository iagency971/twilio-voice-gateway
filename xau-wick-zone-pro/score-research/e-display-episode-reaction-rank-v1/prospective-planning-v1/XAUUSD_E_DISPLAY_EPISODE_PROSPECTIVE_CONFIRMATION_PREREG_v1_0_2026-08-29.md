# XAUUSD — E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1 — prospective confirmation preregistration v1.0

**Frozen planning date:** 2026-08-29  
**Scope:** XAUUSD M1, BUY only, US 08:00–17:00 `America/New_York`  
**Current authorization:** `GO_PROSPECTIVE_CONFIRMATION_PLANNING`  
**Prospective outcome execution during planning:** FORBIDDEN  
**Production authorization:** NONE  
**Pine modification:** FORBIDDEN

## 1. Purpose

This package defines and implements the infrastructure for a genuinely prospective confirmation of the already frozen `E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1` candidate. Nothing in this package may refit, recalibrate, select, rescue or otherwise change the candidate.

The candidate remains a **width-dominated reaction rank** for the frozen upper-Z4-conditioned local top-3 displayed E universe. It is not a universal intrinsic E-strength score, not a calibrated probability and not evidence of trading profitability.

## 2. Immutable authorities

The prospective study must use exactly the canonical DEV model:

`dev-freeze-canonical-33264659057/DEV_FROZEN_MODEL.json`

SHA-256: `72e7548de826e2ae2ba66ddcaaf6b2fa7cd35ada0f5f2cd9db585d9734fd48e1`.

The following frozen components remain unchanged:

- feature set: `zone_width_v`, `display_persistence_c5`, `current_family`;
- logistic coefficients/intercept;
- DEV standardization and family vocabulary;
- empirical DEV rank mapping;
- fixed DEV quartile cutpoints;
- E display architecture and provenance identity rules;
- reaction target, arming/contact rules, ambiguity treatment and 30-available-bar horizon;
- session-cluster bootstrap, seed `20260829`, 5,000 resamples;
- primary prospective pass criteria.

## 3. First eligible prospective session

The general rule is immutable:

> The prospective evidence window starts at the 08:00 New York open of the first complete NY session strictly after the final prospective-planning package seal.

The planning package is being sealed on Saturday 2026-08-29. Provided the canonical seal is completed before Monday 2026-08-31 08:00 `America/New_York`, the first eligible session is fixed as:

- session date: `2026-08-31`;
- local start: `2026-08-31T08:00:00-04:00`;
- UTC start: `2026-08-31T12:00:00Z`.

The final canonical planning seal must verify that its commit timestamp precedes this start. If not, the start must fail closed and be moved by a new Pro-reviewed planning package to the next complete NY session strictly after that later seal.

No session before the fixed start, including earlier August 2026 data, may ever be counted as prospective evidence. Pre-start price data may be used only as causal warm-up for the frozen feature generators.

## 4. Prospective source and first-seen rule

Price source remains the public `kevingtlin/Market-Data-Lab` mirror of Dukascopy XAUUSD BID M1, path:

`xauusd/bid/m1/xauusd_bid_m1_YYYY_MM.csv`

The upstream branch is `main`. Historical data established the same schema and source lineage. Prospective evidence is not tied to a future upstream commit in advance because future monthly files are mutable as the month grows.

For each NY session:

1. after 17:00 New York, acquire the first upstream version observed by the prospective collector that contains that session;
2. record acquisition UTC timestamp, upstream HEAD commit, Git blob SHA, source-file SHA-256, byte length and row count;
3. extract and freeze the session plus enough causal warm-up to contain at least the previous 1,440 active M1 bars;
4. write a canonical per-session M1 slice and warm-up slice into an append-only archive;
5. never overwrite the first accepted canonical session or warm-up slice;
6. if the upstream file later changes historical bytes, store a revision event and its hash, but keep the canonical first accepted session unchanged.

Delayed upstream publication does not make a session optional. The collector must ingest every session date at or after the prospective start that eventually appears in the source, in chronological order, irrespective of price behavior.

## 5. Missing, duplicate and revision rules

- exact duplicate M1 rows: remove one copy and record the count;
- conflicting duplicate timestamp with differing OHLC: fail closed for that acquisition;
- missing M1 opens: never impute; they remain unavailable bars, exactly as in the frozen reaction rule;
- a session with missing opens remains in the study if it contains usable data; missing count is reported;
- a date with no usable US-session M1 data is not represented until data becomes available and cannot contribute contacts;
- a later source revision never replaces the canonical first accepted session;
- all acceptance/revision records form a SHA-256 hash chain.

No data-quality exclusion may be introduced after performance is visible.

## 6. Prospective Z4/C5 geometry

Future Z4 geometry must be generated from the same source-faithful C5 engine used for the historical frozen geometry:

`xau-wick-zone-pro/entry-research/geometry-shifted-grid-parity/xau_z4_c5_geometry_shifted_grid_equivalent.py`

The engine content is guarded by its Git blob identity and by a SHA-256 recorded in the final planning seal. The prospective wrapper uses the same historical geometry-only cut at the unique `m=len(Z)` anchor: it writes only `time, landmark_i, center, zlo, zhi, side` and returns before all outcome calculations.

Only the canonical first-seen warm-up-plus-session M1 slice is supplied. Therefore future days cannot affect an earlier prospective session.

Historical dry-run parity and prefix-invariance tests are mandatory before the package can be sealed.

## 7. E display and feature ledger

For each accepted session, the frozen provenance-instrumented v0.4 architecture is run unchanged:

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`, maximum three sticky displayed zones.

The frozen display-episode identity remains family-preserving. The three model features are generated pre-contact only. Every feature row receives its canonical row SHA-256.

The frozen DEV model may be applied to these **outcome-free** feature rows to store:

- continuous logit;
- empirical DEV rank;
- fixed DEV quartile;
- deterministic raw `zone_width_v` interpretation comparator.

These fields are predictions/features, not realized outcomes.

## 8. Contact-only prospective counter

During prospective collection the reaction labeler is not run. A separate contact-only automaton reproduces only the frozen logic through first contact:

- episode liveness and snapshot availability;
- arming after completed close strictly above current `zhi`;
- arming bar cannot contact;
- first later range intersection is the contact;
- freeze the causally available feature row at contact.

The contact-only automaton **stops reading the episode at first contact** and never evaluates favorable level, invalidation, event order or any post-contact bar.

Its historical dry-run must reproduce frozen DEV/replication selection status, first-contact timestamp and feature-row linkage exactly.

## 9. Anti-peeking firewall

Before the single checkpoint, the live prospective store may contain only:

- raw/session/warm-up acquisition evidence;
- Z4 geometry;
- E candidate/provenance rows;
- outcome-free feature ledgers and frozen scores;
- contact-only rows;
- data-quality/status manifests.

It must not contain or expose:

- reaction labels/classes;
- favorable/invalidation event fields;
- success/failure rates;
- AUC or other outcome association statistics;
- quartile success rates or Q4-Q1 outcome separation;
- MFE/MAE or any post-contact outcome proxy.

The public pre-checkpoint status is restricted to cumulative accepted session count, model-eligible primary-contact count, missing/duplicate/revision counts, feature-exclusion count/rate, unseen-family count/rate and whether the stopping condition has been reached.

## 10. Single stopping/checkpoint rule

Performance may be opened exactly once, at the first completed accepted NY session for which both cumulative conditions are true:

- at least `90` represented eligible NY session dates;
- at least `1000` model-eligible primary contacts.

The contact-only status tool determines the first qualifying session mechanically. Once reached, the prospective analysis end date is locked to that session. No later session may be added to the primary prospective confirmation, even if performance opening or review occurs later.

There is no interim performance peeking and no discretionary extension, delay or early stop based on market behavior.

## 11. Primary prospective gate

At the single checkpoint, using the frozen reaction labeler and the locked prospective window, every condition must pass:

1. at least 1,000 model-eligible primary contacts;
2. at least 90 represented eligible NY sessions;
3. AUC minus 0.5 > 0 and session-cluster 95% CI lower bound > 0;
4. fixed DEV quartile success rates satisfy `Q1 <= Q2 <= Q3 <= Q4`;
5. fixed DEV Q4-Q1 > 0 and session-cluster 95% CI lower bound > 0;
6. fixed DEV Q4-Q1 positive in each of three contiguous complete-session-count blocks;
7. feature exclusion rate <= 2%;
8. unseen-family rate <= 5%;
9. no frozen model, target, feature, geometry, identity, data-definition or statistical component changed.

Failure cannot be rescued by subgroup selection, another threshold, different quartiles, another model or post-hoc data cleaning.

## 12. Width-only interpretation control

Because Pro found that the frozen rank is almost entirely width-driven, `zone_width_v` is preregistered as a deterministic interpretation-only comparator.

At the final performance opening, report separately:

- width-only AUC;
- full-model AUC;
- full minus width-only AUC;
- optionally their session-cluster paired bootstrap difference under the same resamples.

The comparator is **non-gating**. It cannot rescue a failed primary candidate, cannot replace the primary model and cannot trigger model selection. If the full model has no material incremental value, the correct interpretation remains “width-dominated reaction rank”.

## 13. Prospective outcome-opening implementation

The prospective infrastructure may include code for the eventual checkpoint, but while the current authorization is planning-only that code may run only on synthetic fixtures and historical dry-runs.

A future `GO_PROSPECTIVE_CONFIRMATION_EXECUTION` may authorize prospective collection under this sealed protocol. No prospective reaction outcome may be generated or read before that gate.

The execution workflow must fail closed unless its planning seal, start date, model/code hashes and future authorization token match exactly.

## 14. Post-checkpoint governance

Regardless of prospective pass/fail, the system stops for a new Pro scientific review after the single performance opening.

Even a prospective reaction-rank pass does not by itself establish trading profitability, transaction-cost robustness or production readiness.

## 15. Current fail-closed status

`PROSPECTIVE_OUTCOME_GENERATION = FORBIDDEN`

`PROSPECTIVE_OUTCOME_READING = FORBIDDEN`

`PROSPECTIVE_PERFORMANCE_SCORING = FORBIDDEN`

`MODEL_REFIT = FORBIDDEN`

`PRODUCTION = NONE`

`PINE_MODIFICATION = FORBIDDEN`

The planning phase may stop only at:

`READY_FOR_PRO_PRE_PROSPECTIVE_EXECUTION_GATE`
