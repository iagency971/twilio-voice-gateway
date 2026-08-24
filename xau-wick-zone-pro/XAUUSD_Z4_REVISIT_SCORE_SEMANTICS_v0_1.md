# XAUUSD Z4 — User-facing Revisit Score semantics v0.1

**Date:** 2026-08-23  
**Scientific model:** frozen Z4 M1 `P_REVISIT_240`  
**Purpose:** define a truthful 0–100 display score without calling it a calibrated probability.

## Decision

The user-facing score will be named **`R` — Revisit Score H240**.

`R` is **not** a percentage probability and is **not** a support/resistance reaction-strength score.

## Construction

1. Compute the original frozen BID M0GL raw logistic output from the validated Z4 features.
2. Build an equal-landmark-weighted empirical CDF using **DEV only, January–July 2024**. At each landmark, the total weight of all zones is 1, so landmarks with many detected zones do not dominate the reference distribution.
3. Freeze the 0th through 100th weighted percentile thresholds of the raw M0GL output.
4. For a live frozen-Z4 M1 zone, map its raw M0GL output through that frozen DEV CDF to a score from 0 to 100.

Interpretation example:

- `R 80` means the zone's frozen-model revisit likelihood ranks around the 80th percentile of the DEV reference distribution.
- It does **not** mean an 80% chance of revisit.
- It says nothing validated about whether price will reject, reclaim, reverse or continue after the revisit.

## Why percentile rather than raw probability

The frozen model passed DEV, Validation and OOS as a discriminator of revisit, but its absolute calibration drifted materially in OOS. A monotone percentile transform preserves the independently replicated ordering information while avoiding a false probability claim.

## Display restrictions

- Label: `R xx` or `Rxx`.
- Optional tooltip/debug text: `Revisit rank H240 — not reaction probability`.
- Do not append `%`.
- Do not call it `Strength`.
- Do not use it on M5/M15/H1 unless those timeframes receive their own validation.
- Do not update the validated score on arbitrary every-M1 snapshots: the frozen scientific architecture scores 15-minute landmarks. Between landmarks the last validated snapshot/score may be held visually, but it must not be presented as a freshly validated M1-by-M1 score.

## Reaction branch

`P_REACTION` remains NO-GO. No second reaction score may be inferred from `R`.
